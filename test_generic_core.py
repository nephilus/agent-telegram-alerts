import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import alert_format
import alert_policy
import telegram_alerts as core


class GenericCoreIsolationTests(unittest.TestCase):
    def test_no_native_state_required_and_hook_environment_cannot_emit_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / ".config" / "telegram-alerts"
            home.mkdir(parents=True)
            (home / "config.toml").write_text(
                '[safety]\ntelegram_enabled = true\n'
                'telegram_bot_token = "synthetic-token"\n'
                'telegram_chat_id = "42"\n')
            native = root / ".jcode"
            environment = {
                "TELEGRAM_ALERTS_HOME": str(home),
                "JCODE_HOOK_EVENT": "turn_end",
                "JCODE_HOOK_STATUS": "error",
                "JCODE_HOOK_SESSION_ID": "session_absent_native_state",
                "JCODE_HOOK_ERROR": "PRIVATE_SYNTHETIC_FAILURE",
            }
            sent = []

            def deliver(token, method, values):
                sent.append((method, values.copy()))
                return {"message_id": len(sent)}

            with patch.object(Path, "home", return_value=root), patch.dict(os.environ, environment, clear=True), \
                    patch.object(alert_format, "read_session", side_effect=AssertionError("generic CLI read a Jcode session")), \
                    patch.object(alert_format, "session_prompt", side_effect=AssertionError("generic CLI read a Jcode session")), \
                    patch.object(alert_format, "chat_identity", side_effect=AssertionError("generic CLI read a Jcode session")), \
                    patch.object(alert_format, "selector_context", side_effect=AssertionError("generic CLI read a Jcode session")), \
                    patch.object(alert_policy, "notify", side_effect=AssertionError("generic CLI dispatched an event")), \
                    patch.object(core, "api", side_effect=deliver), contextlib.redirect_stdout(io.StringIO()) as output:
                for command in ("status", "preview"):
                    with patch.object(core.sys, "argv", ["telegram-alerts", command]):
                        core.main()
                self.assertEqual(sent, [])
                with patch.object(core.sys, "argv", ["telegram-alerts", "test"]):
                    core.main()

            self.assertEqual(len(sent), 1)
            text = sent[0][1]["text"]
            self.assertIn("Telegram Alerts test (illustrative", text)
            self.assertIn("🔔 Update", text)
            self.assertNotIn("Agent needs you", text)
            self.assertNotIn("Jcode turn", text)
            self.assertNotIn("PRIVATE_SYNTHETIC_FAILURE", text)
            self.assertNotIn("session_absent_native_state", text)
            self.assertNotIn("PRIVATE_SYNTHETIC_FAILURE", output.getvalue())
            self.assertFalse(native.exists())

    def test_generic_parser_has_no_implicit_event_selector_or_native_preview_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "TELEGRAM_ALERTS_HOME": directory}
            for command in ("alert", "event", "selector", "policy", "verbosity",
                            "preview --session synthetic", "preview --event turn_start"):
                result = subprocess.run([sys.executable, str(Path(core.__file__)), *command.split()],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, (command, result.stderr))
                self.assertNotIn("Jcode turn", result.stdout + result.stderr)
            alias = subprocess.run(
                [sys.executable, "-c", "import sys, telegram_alerts; sys.argv = ['jcode-telegram', 'event']; sys.exit(telegram_alerts.legacy_cli())"],
                cwd=Path(core.__file__).parent, env=env, capture_output=True, text=True)
            self.assertEqual(alias.returncode, 2, alias.stderr)
            self.assertIn("use telegram-alerts", alias.stderr)
            self.assertIn("invalid choice", alias.stderr)
            self.assertNotIn("Jcode turn", alias.stdout + alias.stderr)
            help_text = subprocess.run([sys.executable, str(Path(core.__file__)), "--help"],
                                       env=env, capture_output=True, text=True, check=True).stdout
            for command in ("alert", "event", "selector"):
                self.assertNotIn("{" + command, help_text)
            self.assertNotIn("--session", help_text)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_generic_module_does_not_import_the_opt_in_adapter(self):
        result = subprocess.run(
            [sys.executable, "-c", "import sys, telegram_alerts; assert 'legacy_jcode' not in sys.modules"],
            cwd=Path(core.__file__).parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
