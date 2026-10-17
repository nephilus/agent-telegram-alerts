import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import jcode_telegram as app


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
            environment = {**os.environ, "JCODE_HOME": directory}
            for option in ("--version", "--help"):
                result = subprocess.run([sys.executable, str(Path(app.__file__)), option], env=environment, capture_output=True, text=True, check=True)
                self.assertTrue(result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_nested_bad_preference_falls_back_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"JCODE_HOME": directory}):
            app.settings_path().parent.mkdir(parents=True)
            app.settings_path().write_text("[" * 1100 + "0" + "]" * 1100)
            self.assertEqual(app.selected_verbosity(), "brief")


if __name__ == "__main__":
    unittest.main()
