import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import telegram_alerts as app


class ConsoleTests(unittest.TestCase):
    def test_console_wrapper_masks_parser_exception_contents(self):
        with patch.object(app, "main", side_effect=ValueError("PRIVATE_CONFIG_VALUE")), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(app.cli(), 1)
        self.assertNotIn("PRIVATE_CONFIG_VALUE", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_console_wrapper_returns_success(self):
        with patch.object(app, "main", return_value=None):
            self.assertEqual(app.cli(), 0)

    def test_console_wrapper_handles_interrupt_without_config_claims(self):
        with patch.object(app, "main", side_effect=KeyboardInterrupt), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(app.cli(), 1)
        self.assertIn("Cancelled", output.getvalue())
        self.assertNotIn("not enabled", output.getvalue())

    def test_public_version_and_help_do_not_create_state(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "TELEGRAM_ALERTS_HOME": directory}
            for option in ("--version", "--help"):
                result = subprocess.run([sys.executable, str(Path(app.__file__)), option], env=environment, capture_output=True, text=True, check=True)
                self.assertTrue(result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_nested_bad_preference_falls_back_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory}):
            app.settings_path().parent.mkdir(parents=True)
            app.settings_path().write_text("[" * 1100 + "0" + "]" * 1100)
            self.assertEqual(app.selected_verbosity(), "brief")

    def test_malformed_safety_table_fails_closed_without_disclosing_values(self):
        for command in ("status", "disable"):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "config.toml"
                original = 'safety = "PRIVATE_CONFIG_VALUE"\n'
                config.write_text(original)
                result = subprocess.run([sys.executable, str(Path(app.__file__)), command],
                                        env={**os.environ, "TELEGRAM_ALERTS_HOME": directory},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("PRIVATE_CONFIG_VALUE", result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(config.read_text(), original)

    def test_generic_cli_does_not_read_or_rewrite_unowned_hook_table(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            original = 'hooks = "PRIVATE_CONFIG_VALUE"\n'
            config.write_text(original)
            environment = {**os.environ, "TELEGRAM_ALERTS_HOME": directory}
            status = subprocess.run([sys.executable, str(Path(app.__file__)), "status"],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertNotIn("PRIVATE_CONFIG_VALUE", status.stdout + status.stderr)
            self.assertEqual(config.read_text(), original)
            disabled = subprocess.run([sys.executable, str(Path(app.__file__)), "disable"],
                                      env=environment, capture_output=True, text=True)
            self.assertEqual(disabled.returncode, 0, disabled.stderr)
            updated = tomllib.loads(config.read_text())
            self.assertEqual(updated["hooks"], "PRIVATE_CONFIG_VALUE")
            self.assertFalse(updated["safety"]["telegram_enabled"])
            self.assertNotIn("PRIVATE_CONFIG_VALUE", disabled.stdout + disabled.stderr)

    def test_malformed_receipt_does_not_break_status(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "notifications" / "telegram-last-alert.json"
            receipt.parent.mkdir()
            receipt.write_text('["PRIVATE_DIAGNOSTIC_VALUE"]')
            result = subprocess.run([sys.executable, str(Path(app.__file__)), "status"],
                                    env={**os.environ, "TELEGRAM_ALERTS_HOME": directory},
                                    capture_output=True, text=True, check=True)
            self.assertIn("none recorded yet", result.stdout)
            self.assertNotIn("PRIVATE_DIAGNOSTIC_VALUE", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
