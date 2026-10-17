"""Readable context at the public formatter seam, synthetic inputs only."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import alert_format as fmt


def event(**changes):
    return {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
            "JCODE_HOOK_DURATION_MS": "95000", "JCODE_HOOK_CWD": "/workspace/team/service",
            "JCODE_HOOK_LAST_ASSISTANT_TEXT": "Result: Updated readable alerts.", **changes}


class ContextDisplayTests(unittest.TestCase):
    def test_duration_is_minutes_and_seconds_with_carry_and_no_hour_conversion(self):
        cases = {"0": "0m 0s", "499": "0m 0s", "500": "0m 1s", "59000": "0m 59s",
                 "59999": "1m 0s", "60000": "1m 0s", "95000": "1m 35s",
                 "3661000": "61m 1s", "-1000": "0m 0s"}
        for milliseconds, expected in cases.items():
            with self.subTest(milliseconds=milliseconds):
                text = fmt.render(event(JCODE_HOOK_DURATION_MS=milliseconds))
                self.assertIn(" · " + expected, text)
        for value in (None, "invalid", "9" * 5000):
            with self.subTest(invalid_type=type(value).__name__):
                self.assertIn("time unavailable", fmt.render(event(JCODE_HOOK_DURATION_MS=value)))

    def test_unavailable_or_sanitized_away_request_is_omitted_not_placeholder(self):
        for prompt in ("", "okay", "[auto] Internal reminder", "```private code```", None):
            for level in fmt.PROFILES:
                with self.subTest(prompt=prompt, level=level):
                    message = fmt.render_message(event(), level, prompt)
                    self.assertNotIn("Asked:", message["text"])
                    self.assertNotIn("Context unavailable", message["text"])
                    self.assertIn("Result:", message["text"])
                    self.assertFalse(message["prompt_available"])
        meaningful = fmt.render_message(event(), prompt="Asked: Context unavailable is literal user input")
        self.assertTrue(meaningful["prompt_available"])
        self.assertIn("💬 Asked:", meaningful["text"])

    def test_working_folder_keeps_ancestry_instead_of_basename_or_session_name(self):
        first = fmt.render(event(JCODE_HOOK_CWD="/workspace/alpha/service", JCODE_HOOK_SESSION_ID="session_arbitrary_animal"))
        second = fmt.render(event(JCODE_HOOK_CWD="/workspace/beta/service", JCODE_HOOK_SESSION_ID="session_arbitrary_animal"))
        self.assertIn("📁 /workspace/alpha/service", first)
        self.assertIn("📁 /workspace/beta/service", second)
        self.assertNotEqual(first, second)
        self.assertNotIn("arbitrary_animal", first)

    def test_home_is_abbreviated_only_on_a_complete_directory_boundary(self):
        with patch.dict(os.environ, {"HOME": "/home/synthetic-owner"}):
            self.assertIn("📁 ~/workspace/service", fmt.render(event(JCODE_HOOK_CWD="/home/synthetic-owner/workspace/service")))
            self.assertIn("📁 ~ ·", fmt.render(event(JCODE_HOOK_CWD="/home/synthetic-owner")))
            self.assertIn("/home/synthetic-owner-other/service", fmt.render(event(JCODE_HOOK_CWD="/home/synthetic-owner-other/service")))

    def test_missing_folder_is_not_guessed_from_observer_or_arbitrary_names(self):
        for value in (None, "", "   ", [], 42):
            with self.subTest(value=value):
                text = fmt.render(event(JCODE_HOOK_CWD=value, JCODE_HOOK_SESSION_NAME="animal"))
                self.assertIn("📁 Folder unavailable", text)
                self.assertNotIn("animal", text)
                self.assertNotIn(str(Path.cwd()), text)

    def test_path_metadata_is_single_line_sanitized_but_body_paths_stay_redacted(self):
        token = "123456:" + "a" * 35
        raw = "/workspace/password=CANARY_FOLDER/" + token + "/service\nInjected: line"
        text = fmt.render(event(JCODE_HOOK_CWD=raw,
                                JCODE_HOOK_LAST_ASSISTANT_TEXT="Result: Inspect /private/credentials safely."), secrets=(token,))
        self.assertNotIn("CANARY_FOLDER", text)
        self.assertNotIn(token, text)
        self.assertNotIn("/private/credentials", text)
        self.assertNotIn("\nInjected:", text)
        self.assertIn("[redacted]", text)
        self.assertIn("[path]", text)

    def test_long_folder_preserves_leaf_and_brief_result_under_all_caps(self):
        folder = "/workspace/" + "very long parent directory/" * 25 + "meaningful-project"
        for level, limits in fmt.PROFILES.items():
            with self.subTest(level=level):
                message = fmt.render_message(event(JCODE_HOOK_CWD=folder), level, "X" * 1000)
                self.assertIn("meaningful-project", message["text"])
                self.assertIn("Result:", message["text"])
                self.assertIn("Updated", message["text"])
                self.assertLessEqual(len(message["text"]), limits["chars"])
                self.assertLessEqual(len(message["text"].split()), limits["words"])

    def test_lifecycle_uses_same_folder_identity_without_stale_content(self):
        for kind in ("session_start", "turn_start", "session_end"):
            message = fmt.render_lifecycle_message(event(JCODE_HOOK_EVENT=kind,
                JCODE_HOOK_CWD="/workspace/State:/service🚀", JCODE_HOOK_LAST_ASSISTANT_TEXT="STALE_PRIVATE_TEXT"))
            self.assertIn("📁 /workspace/State:/service🚀", message["text"])
            self.assertNotIn("STALE_PRIVATE", message["text"])
            bold = []
            encoded = message["text"].encode("utf-16-le")
            for entity in message["entities"]:
                start = entity["offset"] * 2
                bold.append(encoded[start:start + entity["length"] * 2].decode("utf-16-le"))
            self.assertEqual(bold[-1], "State:")


if __name__ == "__main__":
    unittest.main()
