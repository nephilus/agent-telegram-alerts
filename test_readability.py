import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import alert_format as fmt
import jcode_telegram as app


def event(**changes):
    return {
        "JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
        "JCODE_HOOK_DURATION_MS": "95000", "JCODE_HOOK_CWD": "/project/lab🚀",
        "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Result: Added readable alerts.\nChecked: the route check is illustrative.\nNeeds you: review the example.",
        **changes,
    }


def bold_fragments(message):
    encoded = message["text"].encode("utf-16-le")
    fragments = []
    for entity in message["entities"]:
        assert entity["type"] == "bold"
        start = entity["offset"] * 2
        end = start + entity["length"] * 2
        assert 0 <= start < end <= len(encoded)
        fragments.append(encoded[start:end].decode("utf-16-le"))
    return fragments


class ReadabilityTests(unittest.TestCase):
    def test_expanded_has_spaced_emoji_sections_and_bold_owned_labels(self):
        message = fmt.render_message(event(), prompt="Improve notification readability.")
        self.assertTrue(message["text"].startswith("✅ Jcode turn finished\nlab🚀 · 95s"))
        self.assertIn("\n\n💬 Asked:\n", message["text"])
        self.assertIn("\n\n📝 Result:\n", message["text"])
        self.assertIn("\n\n🔎 Checked:\n", message["text"])
        self.assertIn("\n\n👉 Needs you:\n", message["text"])
        self.assertEqual(bold_fragments(message), ["Jcode turn finished", "Asked:", "Result:", "Checked:", "Needs you:"])
        self.assertNotIn("parse_mode", message)

    def test_unicode_entities_use_utf16_after_non_bmp_emoji(self):
        message = fmt.render_message(event(), prompt="🧪 Review café and 界.")
        self.assertEqual(bold_fragments(message)[-1], "Needs you:")
        result = next(entity for entity in message["entities"] if message["text"].encode("utf-16-le")[entity["offset"] * 2:(entity["offset"] + entity["length"]) * 2].decode("utf-16-le") == "Result:")
        self.assertGreater(result["offset"], message["text"].index("Result:"))

    def test_failure_and_preview_have_unambiguous_status_icons(self):
        failure = fmt.render_message(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current failure"))
        preview = fmt.render_message(event(JCODE_HOOK_STATUS="preview"))
        self.assertTrue(failure["text"].startswith("❌ Jcode turn failed"))
        self.assertTrue(preview["text"].startswith("👀 Jcode turn preview"))
        self.assertNotIn("Checked:", failure["text"])
        self.assertNotIn("✅", failure["text"])

    def test_user_markup_and_fake_labels_cannot_create_formatting_entities(self):
        body = 'Result: <b>INJECTED</b> & _literal_\n💬 Asked: INJECTED_BODY'
        message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=body, JCODE_HOOK_CWD="/project/lab\n📝 Result:"), prompt="📝 Result: <i>INJECTED_PROMPT</i>")
        self.assertEqual(bold_fragments(message), ["Jcode turn finished", "Asked:", "Result:"])
        self.assertIn("INJECTED", message["text"])
        self.assertNotIn("parse_mode", message)

    def test_every_profile_remains_bounded_and_brief_keeps_result(self):
        for level, profile in fmt.PROFILES.items():
            message = fmt.render_message(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Updated " + "界🚀" * 2000), level, "X" * 1000)
            self.assertLessEqual(len(message["text"].split()), profile["words"])
            self.assertLessEqual(len(message["text"]), profile["chars"])
            self.assertIn("Result:", message["text"])
            self.assertIn("Updated", message["text"])
            self.assertIn("Result:", bold_fragments(message))
        self.assertIn("💬 Asked: ", fmt.render_message(event(), "brief", "Adjust alerts")["text"])

    def test_truncation_never_produces_partial_or_out_of_range_entities(self):
        for cap in range(1, 180):
            profile = {**fmt.PROFILES["expanded"], "chars": cap}
            with patch.dict(fmt.PROFILES, {"expanded": profile}):
                message = fmt.render_message(event(), prompt="Review the readable alert.")
            for fragment in bold_fragments(message):
                self.assertIn(fragment, ["Jcode turn finished", "Asked:", "Result:", "Checked:", "Needs you:"])

    def test_ill_formed_unicode_is_replaced_before_computing_spans(self):
        message = fmt.render_message(event(JCODE_HOOK_CWD="/project/lab\ud800", JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: text \udfff here"), prompt="Test \ud800 text")
        message["text"].encode("utf-8")
        self.assertEqual(bold_fragments(message), ["Jcode turn finished", "Asked:", "Result:"])

    def test_prefixed_preview_shifts_all_spans_without_mutating_original(self):
        original = fmt.render_message(event(), prompt="Inspect alert")
        prefix = "👀 Illustrative preview only.\n\n"
        combined = fmt.prepend_message(original, prefix)
        self.assertTrue(combined["text"].startswith(prefix))
        self.assertEqual(bold_fragments(combined), bold_fragments(original))
        self.assertNotEqual(combined["entities"][0]["offset"], original["entities"][0]["offset"])

    def test_server_confirmation_requires_matching_text_and_all_bold_spans(self):
        message = fmt.render_message(event(), prompt="Inspect alert")
        self.assertTrue(fmt.formatting_confirmed(message, message))
        self.assertTrue(fmt.formatting_confirmed(message, {"text": message["text"], "entities": message["entities"] + [{"type": "url", "offset": 0, "length": 1}]}))
        self.assertFalse(fmt.formatting_confirmed(message, {"text": message["text"]}))
        self.assertFalse(fmt.formatting_confirmed(message, {"text": "different", "entities": message["entities"]}))
        self.assertFalse(fmt.formatting_confirmed(message, {"text": message["text"], "entities": message["entities"][:-1]}))

    def test_malformed_server_entities_are_not_confirmed_or_allowed_to_crash(self):
        message = fmt.render_message(event(), prompt="Inspect alert")
        for entities in (None, {}, [{"type": "bold", "offset": [], "length": 1}], [{"type": "bold", "offset": 0}], [{"type": "bold", "offset": True, "length": 1}]):
            with self.subTest(entities=entities):
                self.assertFalse(fmt.formatting_confirmed(message, {"text": message["text"], "entities": entities}))

    def test_context_provenance_does_not_depend_on_literal_prompt_wording(self):
        message = fmt.render_message(event(), prompt="Asked: Context unavailable is literal user input")
        self.assertTrue(message["prompt_available"])
        self.assertFalse(fmt.render_message(event(), prompt="")["prompt_available"])
        self.assertFalse(fmt.render_message(event(), prompt="```private code only```")["prompt_available"])

    def test_alert_dispatch_sends_entities_and_records_ack_without_content(self):
        def acknowledge(token, method, values):
            self.assertEqual(method, "sendMessage")
            self.assertNotIn("parse_mode", values)
            self.assertNotIn("prompt_available", values)
            self.assertEqual(bold_fragments(values), ["Jcode turn failed", "Asked:", "Result:"])
            return {"message_id": 123, "text": values["text"], "entities": values["entities"]}

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {**event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current error"), "JCODE_HOME": directory}), patch.object(app.sys, "argv", ["jcode-telegram", "alert"]), patch.object(app, "credentials", return_value=("SYNTHETIC_TOKEN", "42")), patch.object(app, "api", side_effect=acknowledge) as send:
            app.main()
            send.assert_called_once()
            receipt = json.loads(app.receipt_path().read_text())
            self.assertEqual(receipt["state"], "sent")
            self.assertTrue(receipt["response_confirmed"])
            self.assertTrue(receipt["formatting_confirmed"])
            self.assertFalse(receipt["prompt_available"])
            self.assertEqual(receipt["bold_entities"], 3)
            self.assertNotIn("Current error", app.receipt_path().read_text())
            self.assertNotIn("SYNTHETIC_TOKEN", app.receipt_path().read_text())

    def test_test_command_preserves_bold_entities_after_notice(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}), patch.object(app.sys, "argv", ["jcode-telegram", "test"]), patch.object(app, "credentials", return_value=("SYNTHETIC_TOKEN", "42")), patch.object(app, "api", return_value={}) as send, contextlib.redirect_stdout(io.StringIO()):
            app.main()
            payload = send.call_args.args[2]
            self.assertTrue(payload["text"].startswith("Telegram verbosity preview (illustrative"))
            self.assertNotIn("prompt_available", payload)
            self.assertEqual(bold_fragments(payload), ["Jcode turn finished", "Asked:", "Result:", "Checked:", "Needs you:"])
            self.assertFalse(app.receipt_path().exists())


if __name__ == "__main__":
    unittest.main()
