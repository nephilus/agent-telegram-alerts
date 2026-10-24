import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_format as fmt
import alert_policy as policy
import jcode_telegram as app


PR = "https://github.com/example/project/pull/42"
DOC = "https://docs.python.org/3/library/urllib.parse.html"


def event(**changes):
    return {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
            "JCODE_HOOK_SESSION_ID": "session_link_fixture", "JCODE_HOOK_CWD": "/workspace/alerts",
            "JCODE_HOOK_DURATION_MS": "95000", "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Result: Opened [review](" + PR + ").", **changes}


def link_entities(message):
    return [entity for entity in message["entities"] if entity["type"] == "text_link"]


def fragment(message, entity):
    encoded = message["text"].encode("utf-16-le")
    return encoded[entity["offset"] * 2:(entity["offset"] + entity["length"]) * 2].decode("utf-16-le")


class OutputLinkTests(unittest.TestCase):
    def test_wrapped_links_and_newline_prose_have_no_dead_body_placeholders(self):
        for wrapped in (PR, '[Readable review](' + PR + ')', '<' + PR + '>', '`' + PR + '`'):
            for profile in fmt.PROFILES:
                with self.subTest(wrapped=wrapped, profile=profile):
                    output = 'Result: 🚀 Review ' + wrapped + '\n- Added focused tests.'
                    message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output), profile)
                    entities = link_entities(message)
                    self.assertEqual([item['url'] for item in entities], [PR])
                    self.assertEqual(fragment(message, entities[0]), 'GitHub PR #42')
                    self.assertNotIn('[link]', message['text'])
                    self.assertNotIn('<>', message['text'])
                    if wrapped.startswith('[') and profile == 'expanded':
                        self.assertIn('Readable review', message['text'])
                    self.assertTrue(fmt.formatting_confirmed(message, message))

    def test_rejected_urls_and_prompt_urls_do_not_leave_dead_placeholders(self):
        message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=
            'Result: Read [the guide](https://example.com/?token=PRIVATE_QUERY).'),
            prompt='Review <' + DOC + '>')
        self.assertFalse(link_entities(message))
        self.assertIn('the guide', message['text'])
        self.assertNotIn('[link]', message['text'])
        self.assertNotIn('PRIVATE_QUERY', message['text'])
        self.assertNotIn('<>', message['text'])

    def test_bare_and_markdown_pr_outputs_get_derived_clickable_labels_not_source_labels(self):
        for output in ("Result: Opened " + PR, "Result: Opened [Definitely another site](" + PR + ")."):
            with self.subTest(output=output):
                message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output))
                links = link_entities(message)
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0]["url"], PR)
                self.assertIn("42", fragment(message, links[0]))
                self.assertIn("\n\n🔗 Links:", message["text"])
                self.assertNotIn(PR, message["text"])
                self.assertNotIn("parse_mode", message)
                self.assertTrue(fmt.formatting_confirmed(message, message))

    def test_output_links_survive_excerpt_truncation_and_all_profile_caps(self):
        for profile, limits in fmt.PROFILES.items():
            with self.subTest(profile=profile):
                output = "Result: Updated " + "界🚀" * 1000 + "\nReview: " + PR + "\nDocs: " + DOC
                message = fmt.render_message(event(JCODE_HOOK_CWD="/workspace/" + "folder-name-" * 100,
                                                    JCODE_HOOK_LAST_ASSISTANT_TEXT=output), profile,
                                             "X" * 1000, session_name="Release migration " * 200)
                self.assertTrue(link_entities(message))
                self.assertEqual(link_entities(message)[0]["url"], PR)
                self.assertIn("Result:", message["text"])
                self.assertIn("Updated", message["text"])
                self.assertLessEqual(len(message["text"]), limits["chars"])
                self.assertLessEqual(len(message["text"].split()), limits["words"])
                for entity in message["entities"]:
                    self.assertTrue(fragment(message, entity))
                self.assertTrue(fmt.formatting_confirmed(message, message))

    def test_only_current_output_not_prompt_name_folder_or_stale_error_response_can_supply_links(self):
        clean = event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Updated alerts.", JCODE_HOOK_CWD=PR)
        message = fmt.render_message(clean, prompt=PR, session_name=PR)
        self.assertFalse(link_entities(message))
        failed = fmt.render_message(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current failure"))
        self.assertFalse(link_entities(failed))
        current = fmt.render_message(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current error details: " + DOC))
        self.assertEqual([e["url"] for e in link_entities(current)], [DOC])
        for kind in ("session_start", "turn_start", "session_end"):
            self.assertFalse(link_entities(fmt.render_lifecycle_message(event(JCODE_HOOK_EVENT=kind))))

    def test_secret_values_code_fences_and_normalized_secret_keys_do_not_become_links(self):
        for output in ('{"password": "' + PR + '"}', '**password**: ' + PR,
                       'api\u200b_key="' + PR + '"', 'token=' + PR,
                       'password=[label with spaces](' + PR + ')',
                       'password=PRIVATE_VALUE and review ' + PR,
                       '```text\n' + PR + '\n```', '~~~\n' + PR,
                       'private ' + PR):
            with self.subTest(output=output):
                secrets = (PR,) if output.startswith("private ") else ()
                message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output), secrets=secrets)
                self.assertFalse(link_entities(message))
                self.assertNotIn(PR, json.dumps(message))

    def test_masked_first_candidates_do_not_starve_later_real_pr_and_markers_cannot_be_spoofed(self):
        output = 'password=https://example.com/one\nsecret=https://example.com/two\napi_key=https://example.com/three\nResult: Opened ' + PR
        message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output))
        self.assertEqual([e["url"] for e in link_entities(message)], [PR])
        for marker in ("JCODEALERTLINK0END", "JCODE**ALERTLINK0END", "JCODE\u200bALERTLINK0END"):
            spoofed = marker + '\npassword=' + PR
            self.assertFalse(link_entities(fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=spoofed))))

    def test_input_boundary_and_fence_removal_never_fabricate_targets(self):
        for suffix in ("?token=PRIVATE_QUERY", "/different-target", "0"):
            output = " " * (16000 - len(PR)) + PR + suffix
            with self.subTest(suffix=suffix):
                self.assertFalse(fmt.response_links(output))
        for fence in ("```hidden```", "~~~hidden~~~", "```hidden"):
            output = "https://github.com/example/" + fence + "project/pull/42"
            with self.subTest(fence=fence):
                self.assertNotIn(PR, [link["url"] for link in fmt.response_links(output)])
        output = "Result: Done.\n```hidden```\nReview: " + PR
        self.assertEqual([link["url"] for link in fmt.response_links(output)], [PR])

    def test_candidate_prefixes_are_not_replaced_inside_longer_or_unsafe_urls(self):
        other = PR + "0"
        message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Review " + PR + " and " + other))
        self.assertEqual([e["url"] for e in link_entities(message)], [PR, other])
        output = 'password=' + PR + '\nUnsafe: ' + PR + '?token=PRIVATE_QUERY'
        self.assertFalse(link_entities(fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output))))

    def test_original_url_characters_are_preserved_not_mutated_by_body_markup_cleanup(self):
        url = "https://github.com/example/project__tools/pull/42"
        message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Review [PR](" + url + ")"))
        self.assertEqual([e["url"] for e in link_entities(message)], [url])

    def test_duplicate_urls_and_profile_link_limits(self):
        urls = ["https://github.com/example/project/pull/" + str(n) for n in range(1, 8)]
        output = "Result: Review " + " ".join([urls[0], urls[0], *urls[1:]])
        for profile, maximum in (("brief", 1), ("contextual", 2), ("expanded", 3)):
            message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=output), profile)
            self.assertEqual([e["url"] for e in link_entities(message)], urls[:maximum])

    def test_prefixed_test_message_preserves_link_url_and_utf16_shift(self):
        original = fmt.render_message(event())
        shifted = fmt.prepend_message(original, "👀 Illustrative only.\n\n")
        old, new = link_entities(original)[0], link_entities(shifted)[0]
        self.assertEqual(old["url"], new["url"])
        self.assertEqual(fragment(original, old), fragment(shifted, new))
        self.assertEqual(new["offset"], old["offset"] + fmt.utf16_length("👀 Illustrative only.\n\n"))

    def test_delivery_boundary_preserves_valid_links_but_rejects_unsafe_or_partial_entities(self):
        original = fmt.render_message(event())
        outgoing = policy._message(original, "expanded", 0)
        self.assertEqual(link_entities(outgoing), link_entities(original))
        self.assertEqual(outgoing["link_preview_options"], {"is_disabled": True})
        for bad_url in (None, [], {}, 42, "", "javascript:alert(1)", "http://example.com/", "https://example.com/?token=PRIVATE", "https://127.0.0.1/", "https://u:p@example.com/"):
            candidate = {"text": "Review link", "entities": [{"type": "text_link", "offset": 7, "length": 4, "url": bad_url}]}
            self.assertFalse(link_entities(policy._message(candidate, "expanded", 0)))
        candidate = {"text": "🚀 link", "entities": [{"type": "text_link", "offset": 1, "length": 2, "url": PR}]}
        self.assertFalse(link_entities(policy._message(candidate, "expanded", 0)))
        long = {"text": "x" * 1500, "entities": [{"type": "text_link", "offset": 1390, "length": 20, "url": PR}]}
        self.assertFalse(link_entities(policy._message(long, "expanded", 2)))

    def test_grouped_counter_never_truncates_otherwise_complete_output_links(self):
        for profile, limits in fmt.PROFILES.items():
            message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Updated " + "word " * 200 + PR),
                                         profile, "requested task " * 100, session_name="Release migration " * 100)
            outgoing = policy._message(message, profile, 12)
            self.assertEqual(link_entities(outgoing), link_entities(message))
            self.assertLessEqual(len(outgoing["text"]), limits["chars"])
            self.assertLessEqual(len(outgoing["text"].split()), limits["words"])

    def test_confirmation_binds_clickable_span_and_exact_destination_not_just_bold_labels(self):
        message = fmt.render_message(event())
        self.assertTrue(fmt.formatting_confirmed(message, message))
        for change in ("missing", "wrong-url", "malformed-url", "malformed-offset"):
            actual = json.loads(json.dumps(message))
            entity = link_entities(actual)[0]
            if change == "missing": actual["entities"].remove(entity)
            elif change == "wrong-url": entity["url"] = "https://example.com/another"
            elif change == "malformed-url": entity["url"] = []
            else: entity["offset"] = True
            self.assertFalse(fmt.formatting_confirmed(message, actual), change)

    def test_actual_observer_records_link_counts_not_urls_or_contents(self):
        def acknowledge(token, method, values):
            self.assertEqual(method, "sendMessage")
            self.assertEqual([e["url"] for e in link_entities(values)], [PR])
            self.assertEqual(values["link_preview_options"], {"is_disabled": True})
            return {"message_id": 7, "text": values["text"], "entities": values["entities"]}
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {**event(), "JCODE_HOME": home}), patch.object(app, "credentials", return_value=("SYNTHETIC_TOKEN", "42")), patch.object(app, "api", side_effect=acknowledge):
            app.observe_event(os.environ, min_seconds=0)
            receipt = json.loads(app.receipt_path().read_text())
            self.assertEqual(receipt["state"], "sent")
            self.assertEqual(receipt["link_entities"], 1)
            self.assertEqual(receipt["bold_entities"], 4)
            self.assertTrue(receipt["response_confirmed"])
            self.assertTrue(receipt["formatting_confirmed"])
            self.assertNotIn(PR, app.receipt_path().read_text())


if __name__ == "__main__":
    unittest.main()
