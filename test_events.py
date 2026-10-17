import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import jcode_telegram as app


class EventInterfaceTests(unittest.TestCase):
    def test_lifecycle_receipts_do_not_erase_completion_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                "JCODE_HOME": directory, "JCODE_HOOK_SESSION_ID": "synthetic-private-session"}):
            app.record_receipt("sent", kind="completion", response_confirmed=True,
                               text="PRIVATE_CONTENT", chat_id="PRIVATE_DESTINATION")
            app.record_receipt("disabled", kind="session_end")
            folder = Path(directory) / "notifications"
            completion = json.loads((folder / "telegram-last-completion.json").read_text())
            self.assertEqual(completion["state"], "sent")
            self.assertTrue(completion["response_confirmed"])
            self.assertEqual(json.loads(app.receipt_path().read_text())["kind"], "session_end")
            for path in folder.glob("telegram-last-*.json"):
                self.assertNotIn("PRIVATE", path.read_text())
                self.assertNotIn("synthetic-private-session", path.read_text())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            app.record_receipt("ignored", kind="../../untrusted")
            self.assertFalse((Path(directory) / "untrusted.json").exists())

    def test_policy_changes_preserve_verbosity_and_native_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            environment = {**os.environ, "JCODE_HOME": directory}
            config = home / "config.toml"
            original = '[safety]\ntelegram_reply_enabled = true\n[hooks]\nturn_end = ["foreign-hook"]\n'
            config.write_text(original)
            command = [sys.executable, str(Path(app.__file__))]
            subprocess.run(command + ["verbosity", "expanded"], env=environment, capture_output=True, check=True)
            preference = home / "notifications/telegram-settings.json"
            before = preference.read_bytes()
            selected = subprocess.run(command + ["policy", "attention", "--enable", "completion",
                                                  "--cooldown-seconds", "120", "--silent", "completion"],
                                      env=environment, text=True, capture_output=True, check=True)
            policy = json.loads(selected.stdout)
            self.assertEqual(policy["cooldown_seconds"], 120)
            self.assertTrue(policy["events"]["completion"])
            self.assertTrue(policy["events"]["error"])
            self.assertIn("completion", policy["silent_events"])
            self.assertEqual(config.read_text(), original)
            self.assertEqual(preference.read_bytes(), before)
            queried = subprocess.run(command + ["policy"], env=environment, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(queried.stdout), policy)
            self.assertEqual((home / "notifications/telegram-policy.json").stat().st_mode & 0o777, 0o600)

    def test_unknown_or_conflicting_event_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments in (["policy", "--enable", "crash"],
                              ["policy", "--enable", "completion", "--disable", "completion"],
                              ["preview", "--cooldown-seconds", "0"],
                              ["policy", "--cooldown-seconds", "-1"]):
                result = subprocess.run([sys.executable, str(Path(app.__file__)), *arguments],
                                        env={**os.environ, "JCODE_HOME": directory}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(list(Path(directory).iterdir()))

    def test_default_quiet_lifecycle_and_grouped_completion_use_real_policy(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                "JCODE_HOME": directory, "JCODE_HOOK_SESSION_ID": "session_policy_interface",
                "JCODE_HOOK_EVENT": "turn_start", "JCODE_HOOK_STATUS": "ok",
                "JCODE_HOOK_DURATION_MS": "60000", "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Result: Synthetic task result"}):
            app.config_path().write_text('[safety]\ntelegram_enabled = true\ntelegram_bot_token = "synthetic-value"\ntelegram_chat_id = "42"\n')
            calls = []
            def deliver(token, method, body):
                calls.append(method)
                return {**body, "message_id": 7}
            with patch.object(app, "api", side_effect=deliver), patch.object(app.sys, "argv", ["jcode-telegram", "event", "--min-seconds", "0"]):
                app.main()
                self.assertEqual(calls, [])
                self.assertEqual(json.loads(app.receipt_path().read_text())["state"], "disabled")
                os.environ["JCODE_HOOK_EVENT"] = "turn_end"
                app.main()
                first = json.loads(app.receipt_path().read_text())
                self.assertEqual(first["state"], "sent")
                self.assertTrue(first["response_confirmed"])
                app.main()
                self.assertEqual(json.loads(app.receipt_path().read_text())["state"], "suppressed_cooldown")
                self.assertEqual(calls, ["sendMessage"])
                os.environ.update(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current synthetic error")
                app.main()
                self.assertEqual(json.loads(app.receipt_path().read_text())["state"], "sent")
                self.assertEqual(calls, ["sendMessage", "sendMessage"])
                app.main()
                self.assertEqual(json.loads(app.receipt_path().read_text())["state"], "suppressed_repeat_error")
                self.assertEqual(calls, ["sendMessage", "sendMessage"])

    def test_policy_defaults_can_be_queried_without_creating_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(Path(app.__file__)), "policy"],
                                    env={**os.environ, "JCODE_HOME": directory},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            policy = json.loads(result.stdout)
            self.assertEqual(policy["preset"], "balanced")
            self.assertEqual(policy["cooldown_seconds"], 300)
            self.assertFalse(policy["status_card"])
            self.assertTrue(policy["events"]["completion"])
            self.assertFalse(policy["events"]["turn_start"])
            self.assertFalse(list(Path(directory).iterdir()))

    def test_working_preview_never_reuses_previous_response_or_contacts_telegram(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "JCODE_HOME": directory,
                           "JCODE_HOOK_LAST_ASSISTANT_TEXT": "STALE_PRIVATE_RESPONSE",
                           "JCODE_HOOK_ERROR": "STALE_PRIVATE_ERROR"}
            result = subprocess.run([sys.executable, str(Path(app.__file__)),
                                     "preview", "--event", "turn_start"],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Jcode working", result.stdout)
            self.assertNotIn("STALE_PRIVATE", result.stdout + result.stderr)
            self.assertFalse(list(Path(directory).iterdir()))


if __name__ == "__main__":
    unittest.main()
