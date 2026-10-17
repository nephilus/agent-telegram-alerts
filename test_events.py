import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import jcode_telegram as app


class EventInterfaceTests(unittest.TestCase):
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
