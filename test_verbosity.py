import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import jcode_telegram as app


class VerbosityTests(unittest.TestCase):
    def test_default_is_expanded_and_selection_is_private_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            self.assertEqual(app.selected_verbosity(), "expanded")
            for value in ("brief", "contextual", "expanded"):
                app.save_verbosity(value)
                self.assertEqual(app.selected_verbosity(), value)
                self.assertEqual(app.settings_path().stat().st_mode & 0o777, 0o600)
            self.assertFalse(app.config_path().exists())

    def test_invalid_settings_fail_to_brief_not_more_disclosure(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            app.settings_path().parent.mkdir(parents=True)
            for value in ("invalid-json", 'null', '[]', '{"verbosity":"unknown"}', '{"verbosity":null}', '{"verbosity":[]}', '{"verbosity":{}}'):
                app.settings_path().write_text(value)
                self.assertEqual(app.selected_verbosity(), "brief")
            app.settings_path().write_text("x" * 4097)
            self.assertEqual(app.selected_verbosity(), "brief")

    def test_symlinked_settings_are_not_followed_or_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            app.settings_path().parent.mkdir(parents=True)
            target = Path(directory) / "other.json"
            target.write_text('{"verbosity":"expanded"}')
            app.settings_path().symlink_to(target)
            self.assertEqual(app.selected_verbosity(), "brief")
            with self.assertRaises(app.SetupError):
                app.save_verbosity("contextual")
            self.assertEqual(json.loads(target.read_text())["verbosity"], "expanded")

    def test_selection_does_not_touch_native_credentials_replies_or_hooks(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            original = '[safety]\ntelegram_enabled = true\ntelegram_reply_enabled = true\ntelegram_bot_token = "synthetic-private-value"\ntelegram_chat_id = "42"\n[hooks]\nturn_end = ["existing alert --min-seconds 30"]\n'
            app.config_path().write_text(original)
            for level in ("brief", "contextual", "expanded"):
                app.save_verbosity(level)
                self.assertEqual(app.config_path().read_text(), original)

    def test_one_off_override_does_not_change_saved_preference(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            app.save_verbosity("expanded")
            self.assertEqual(app.selected_verbosity("brief"), "brief")
            self.assertEqual(app.selected_verbosity(), "expanded")
            self.assertEqual(json.loads(app.settings_path().read_text()), {"verbosity": "expanded"})

    def test_preview_never_calls_telegram_or_writes_a_receipt(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}), patch.object(app.sys, "argv", ["jcode-telegram", "preview", "--verbosity", "expanded"]), patch.object(app, "api") as send, contextlib.redirect_stdout(io.StringIO()) as output:
            app.main()
            self.assertIn("Preview only, not sent", output.getvalue())
            self.assertIn("Asked:", output.getvalue())
            send.assert_not_called()
            self.assertFalse(app.receipt_path().exists())
            self.assertFalse(app.settings_path().exists())

    def test_saved_session_preview_does_not_claim_a_successful_turn(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}), patch.object(app, "api") as send:
            session_id = "session_preview_test"
            sessions = Path(directory) / "sessions"
            sessions.mkdir()
            (sessions / (session_id + ".json")).write_text(json.dumps({
                "id": session_id, "working_dir": "/project/example",
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Preview this task"}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "Result: Saved response"}]},
                ],
            }))
            result = app.preview_text("expanded", session_id)
            self.assertIn("Jcode turn preview", result)
            self.assertNotIn("turn finished", result)
            self.assertIn("Asked:\nPreview this task", result)
            self.assertIn("Result:\nSaved response", result)
            send.assert_not_called()
            self.assertFalse(app.receipt_path().exists())

    def test_actual_cli_can_choose_each_level_and_query_it(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "JCODE_HOME": directory}
            command = [sys.executable, str(Path(app.__file__))]
            for level in ("brief", "contextual", "expanded"):
                selected = subprocess.run(command + ["verbosity", level], env=environment, text=True, capture_output=True, check=True)
                self.assertIn(level, selected.stdout)
                queried = subprocess.run(command + ["verbosity"], env=environment, text=True, capture_output=True, check=True)
                self.assertIn(level, queried.stdout)
                preview = subprocess.run(command + ["preview"], env=environment, text=True, capture_output=True, check=True)
                self.assertIn("not sent (" + level + ")", preview.stdout)

    def test_invalid_cli_profile_is_rejected_without_writing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(Path(app.__file__)), "verbosity", "unlimited"], env={**os.environ, "JCODE_HOME": directory}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(directory) / "notifications/telegram-settings.json").exists())

    def test_failed_turn_does_not_attach_a_stale_success_prompt(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}), patch.object(app.formatting, "session_prompt", return_value="OLD_PRIVATE_TASK") as prompt:
            result = app.alert_text({"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "error", "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Old successful response", "JCODE_HOOK_ERROR": "Current failure"})
            self.assertNotIn("OLD_PRIVATE_TASK", result)
            self.assertIn("Current failure", result)
            prompt.assert_not_called()

    def test_delivery_receipt_keeps_metadata_not_message_contents(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            app.record_receipt("sent", verbosity="expanded", words=50, characters=400, telegram_message_id=9, text_fingerprint="abc", response_confirmed=True, prompt_available=True, text="PRIVATE_TEXT", token="PRIVATE_TOKEN")
            receipt = json.loads(app.receipt_path().read_text())
            self.assertEqual(receipt["verbosity"], "expanded")
            self.assertEqual(receipt["telegram_message_id"], 9)
            self.assertNotIn("PRIVATE_TEXT", app.receipt_path().read_text())
            self.assertNotIn("PRIVATE_TOKEN", app.receipt_path().read_text())


if __name__ == "__main__":
    unittest.main()
