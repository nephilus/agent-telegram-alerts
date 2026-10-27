import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_format as fmt
import telegram_alerts as app
from test_readability import bold_fragments


SESSION = "session_named_fixture"


def event(**changes):
    return {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
            "JCODE_HOOK_SESSION_ID": SESSION, "JCODE_HOOK_DURATION_MS": "95000",
            "JCODE_HOOK_CWD": "/workspace/alerts",
            "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Result: Updated alerts.", **changes}


def saved(home, **changes):
    path = Path(home) / "sessions" / (SESSION + ".json")
    path.parent.mkdir(exist_ok=True)
    data = {"id": SESSION, "working_dir": "/workspace/alerts", "messages": [
        {"role": "user", "content": "Improve notification identity."},
        {"role": "assistant", "content": "Result: Updated alerts."},
    ], **changes}
    path.write_text(json.dumps(data))
    return path


class NamedSessionTests(unittest.TestCase):
    def test_explicit_name_precedence_matches_native_but_no_generated_fallback(self):
        cases = [
            ({"custom_title": " Storage migration ", "saved": True, "save_label": "Older saved label"}, "Storage migration"),
            ({"custom_title": "Renamed without saving", "saved": False}, "Renamed without saving"),
            ({"custom_title": " ", "saved": True, "save_label": " Saved deployment "}, "Saved deployment"),
            ({"saved": True, "save_label": "Saved deployment"}, "Saved deployment"),
            ({"saved": False, "save_label": "Stale saved label"}, ""),
            ({"saved": "true", "save_label": "Malformed saved flag"}, ""),
            ({"saved": 1, "save_label": "Malformed saved flag"}, ""),
            ({"title": "Generated summary", "short_name": "friendly-animal"}, ""),
            ({"custom_title": [], "saved": True, "save_label": "Legacy saved label"}, "Legacy saved label"),
            ({"custom_title": {}, "saved": True, "save_label": []}, ""),
        ]
        with tempfile.TemporaryDirectory() as home:
            for metadata, expected in cases:
                with self.subTest(metadata=metadata):
                    saved(home, **{"title": "Automatic summary", **metadata})
                    self.assertEqual(fmt.saved_session_name(home, SESSION), expected)

    def test_metadata_lookup_is_exact_fail_closed_and_never_follows_a_session_symlink(self):
        with tempfile.TemporaryDirectory() as home:
            path = saved(home, custom_title="Allowed session")
            self.assertEqual(fmt.saved_session_name(home, SESSION), "Allowed session")
            for identity in (None, [], "../../other", "session_missing"):
                self.assertEqual(fmt.saved_session_name(home, identity), "")
            saved(home, id="session_different", custom_title="WRONG_SESSION")
            self.assertEqual(fmt.saved_session_name(home, SESSION), "")
            path.write_text('{"id":"session_named_fixture","custom_title":"INCOMPLETE"}')
            self.assertEqual(fmt.saved_session_name(home, SESSION), "")
            path.unlink()
            target = Path(home) / "other.json"
            target.write_text(json.dumps({"id": SESSION, "messages": [], "custom_title": "SYMLINK_PRIVATE"}))
            path.symlink_to(target)
            self.assertEqual(fmt.saved_session_name(home, SESSION), "")

    def test_explicit_name_is_optional_inline_bold_metadata_separate_from_folder(self):
        for profile in fmt.PROFILES:
            with self.subTest(profile=profile):
                message = fmt.render_message(event(), profile, session_name="Storage migration")
                self.assertIn("\n🏷 Session: Storage migration\n📁 /workspace/alerts · 1m 35s", message["text"])
                self.assertIn("Session:", bold_fragments(message))
                self.assertIn("Result:", bold_fragments(message))
                self.assertIn("Updated alerts.", message["text"])
                self.assertNotIn("parse_mode", message)
                self.assertNotIn("Session:", fmt.render_message(event(), profile)["text"])
                self.assertIn("Storage migration", fmt.render(event(), profile, session_name="Storage migration"))

    def test_name_scanned_before_clipping_and_never_exports_name_paths_or_markup_entities(self):
        name = '**Release**\n📝 Result: api\u200b_key="CANARY_KEY" /private/keys <b>literal</b> CANARY_TOKEN '
        message = fmt.render_message(event(), session_name=name, secrets=("CANARY_TOKEN",))
        self.assertNotIn("CANARY_KEY", message["text"])
        self.assertNotIn("CANARY_TOKEN", message["text"])
        self.assertNotIn("/private/keys", message["text"])
        self.assertIn("[path]", message["text"])
        line = next(line for line in message["text"].splitlines() if line.startswith("🏷 "))
        self.assertIn("Release", line)
        self.assertEqual(bold_fragments(message), ["Jcode turn finished", "Session:", "Result:"])
        self.assertNotIn("parse_mode", message)

    def test_empty_malformed_or_code_only_names_do_not_add_a_placeholder(self):
        for name in (None, [], {}, 42, "", "  ", "```private code```", "\u200b"):
            with self.subTest(name=name):
                message = fmt.render_message(event(), session_name=name)
                self.assertNotIn("Session:", message["text"])
                self.assertNotIn("unavailable", message["text"])

    def test_long_unicode_names_preserve_caps_result_and_valid_owned_bold_entities(self):
        for profile, limits in fmt.PROFILES.items():
            with self.subTest(profile=profile):
                message = fmt.render_message(event(JCODE_HOOK_CWD="/workspace/" + "long-folder-" * 50,
                                                    JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Updated " + "界🚀" * 1000),
                                             profile, "X" * 1000, session_name="🚀 Release " * 2000)
                self.assertLessEqual(len(message["text"].split()), limits["words"])
                self.assertLessEqual(len(message["text"]), limits["chars"])
                self.assertIn("Updated", message["text"])
                self.assertIn("Result:", bold_fragments(message))
                self.assertIn("Session:", bold_fragments(message))
                self.assertTrue(fmt.formatting_confirmed(message, message))
                message["text"].encode("utf-8")

    def test_lifecycle_events_share_name_but_not_prompt_or_previous_response(self):
        for profile, limits in fmt.PROFILES.items():
            for kind in ("session_start", "turn_start", "session_end"):
                with self.subTest(profile=profile, kind=kind):
                    message = fmt.render_lifecycle_message(event(JCODE_HOOK_EVENT=kind), profile,
                                                          session_name="🚀 State: Session: Release")
                    self.assertIn("\n🏷 Session:", message["text"])
                    self.assertEqual(bold_fragments(message)[1:], ["Session:", "State:"])
                    self.assertNotIn("Updated alerts", message["text"])
                    self.assertFalse(message["prompt_available"])
                    self.assertLessEqual(len(message["text"].split()), limits["words"])
                    self.assertLessEqual(len(message["text"]), limits["chars"])

    def test_hook_and_saved_preview_read_explicit_metadata_and_hot_reload_renames(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": home}), patch.object(app, "api") as network:
            saved(home, custom_title="Storage migration", short_name="automatic-animal", title="Automatic summary")
            for render in (lambda: app.alert_message(event()), lambda: app.preview_message("expanded", SESSION)):
                self.assertIn("🏷 Session: Storage migration", render()["text"])
            for kind in ("session_start", "turn_start", "session_end"):
                self.assertIn("🏷 Session: Storage migration", app.event_message(event(JCODE_HOOK_EVENT=kind))["text"])
            saved(home, custom_title="Meaningful new name")
            self.assertIn("Meaningful new name", app.alert_message(event())["text"])
            self.assertNotIn("Storage migration", app.alert_message(event())["text"])
            saved(home, custom_title=None, saved=False, title="Auto summary", short_name="animal")
            self.assertIn("🏷 Session: animal\n", app.alert_message(event(JCODE_HOOK_SESSION_NAME="UNTRUSTED_ENV"))["text"])
            self.assertNotIn("UNTRUSTED_ENV", app.alert_message(event(JCODE_HOOK_SESSION_NAME="UNTRUSTED_ENV"))["text"])
            network.assert_not_called()
            self.assertFalse(app.receipt_path().exists())

    def test_error_can_identify_same_session_without_exporting_old_prompt_or_response(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": home}):
            saved(home, custom_title="Named recovery task")
            message = app.alert_message(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current failure"))
            self.assertIn("🏷 Session: Named recovery task", message["text"])
            self.assertIn("Current failure", message["text"])
            self.assertNotIn("Updated alerts", message["text"])
            self.assertNotIn("Improve notification", message["text"])
            self.assertNotIn("Asked:", message["text"])
            self.assertFalse(message["prompt_available"])


if __name__ == "__main__":
    unittest.main()
