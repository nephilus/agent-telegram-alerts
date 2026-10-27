import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_home


class AlertHomeTests(unittest.TestCase):
    def test_generic_default_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generic = root / "custom-alerts"
            legacy = root / "legacy-jcode"
            with patch.object(Path, "home", return_value=root), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(alert_home.home_path(), root / ".config" / "telegram-alerts")
                self.assertEqual(alert_home.legacy_read_home(), root / ".jcode")
            with patch.object(Path, "home", return_value=root), patch.dict(
                    os.environ, {"JCODE_HOME": str(legacy)}, clear=True):
                self.assertEqual(alert_home.home_path(), legacy)
                self.assertIsNone(alert_home.legacy_read_home())
            with patch.object(Path, "home", return_value=root), patch.dict(
                    os.environ, {"JCODE_HOME": str(legacy), "TELEGRAM_ALERTS_HOME": str(generic)}, clear=True):
                self.assertEqual(alert_home.home_path(), generic)
                self.assertIsNone(alert_home.legacy_read_home())


if __name__ == "__main__":
    unittest.main()
