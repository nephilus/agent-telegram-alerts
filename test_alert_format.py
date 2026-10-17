import json
import os
from pathlib import Path
import tempfile
import unittest

import alert_format as fmt


RESPONSE = (
    "Implemented selectable alert verbosity and kept the existing notification frequency.\n"
    "Added persistent brief, contextual, and expanded profiles with expanded as the default.\n"
    "Checked: formatter tests passed and native remote settings were preserved.\n"
    "Needs you: try the expanded alert and choose a shorter profile if preferred."
)


def event(**changes):
    return {
        "JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
        "JCODE_HOOK_DURATION_MS": "95000", "JCODE_HOOK_CWD": "/home/private/sample-project",
        "JCODE_HOOK_LAST_ASSISTANT_TEXT": RESPONSE, **changes,
    }


def message(role, text, **extra):
    return {"role": role, "content": [{"type": "text", "text": text}], **extra}


class FormattingTests(unittest.TestCase):
    def test_default_expanded_contains_request_result_checks_and_next_step(self):
        result = fmt.render(event(), prompt="Add selectable Telegram alert verbosity and default it to expanded.")
        self.assertIn("sample-project", result)
        self.assertIn("Asked:", result)
        self.assertIn("selectable Telegram", result)
        self.assertIn("Result:", result)
        self.assertIn("Checked:", result)
        self.assertIn("Needs you:", result)
        self.assertNotIn("/home/private", result)
        self.assertLessEqual(len(result.split()), 100)

    def test_every_profile_has_a_hard_word_and_character_cap(self):
        huge = "word " * 3000
        for level, profile in fmt.PROFILES.items():
            with self.subTest(level=level):
                output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=huge), level, huge)
                self.assertLessEqual(len(output.split()), profile["words"])
                self.assertLessEqual(len(output), profile["chars"])
                self.assertLessEqual(len(output), 1400)
        self.assertNotIn("Checked:", fmt.render(event(), "brief", "Adjust the Telegram alert."))
        self.assertIn("Checked:", fmt.render(event(), "contextual", "Adjust the Telegram alert."))

    def test_verification_is_never_invented(self):
        output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Updated the formatter."), prompt="Change the alert.")
        self.assertNotIn("Checked:", output)
        self.assertNotIn("passed", output)

    def test_secrets_links_paths_and_code_are_not_forwarded(self):
        token = "123456:" + "a" * 35
        api_key = "sk-" + "abcdef1234567890"  # Synthetic fixture, never a real credential.
        raw = (
            f"Updated the alert. password='private password' api_key={api_key} {token}\n"
            "Checked: tests passed. https://private.invalid/admin?q=secret /home/private/credentials\n"
            "```\nDO_NOT_FORWARD_RAW_LOG secret_value\n```\n"
            "Needs you: review safely."
        )
        output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=raw), prompt=f"Use token={token}", secrets=(token,))
        for secret in (token, "private password", api_key, "private.invalid", "/home/private", "DO_NOT_FORWARD_RAW_LOG"):
            self.assertNotIn(secret, output)
        self.assertIn("[redacted]", output)

    def test_failure_uses_sanitized_error_without_claiming_tests_passed(self):
        output = fmt.render(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_LAST_ASSISTANT_TEXT="", JCODE_HOOK_ERROR="Request failed: password=secret-value"))
        self.assertIn("failed", output)
        self.assertNotIn("secret-value", output)
        self.assertNotIn("Checked:", output)

    def test_unicode_and_long_unbroken_text_remain_bounded(self):
        output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="界" * 6000), prompt="é" * 5000)
        self.assertLessEqual(len(output), 1400)
        self.assertNotIn("\ufffd", output)

    def test_prompt_is_bound_to_matching_response_not_a_newer_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            data = {"id": "session_test", "messages": [
                message("user", "Investigate the backup schedule."),
                message("assistant", RESPONSE),
                message("user", "Unrelated newer request that must not be paired."),
            ]}
            (root / "session_test.json").write_text(json.dumps(data))
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", RESPONSE), "Investigate the backup schedule.")
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", "Different assistant output"), "")

    def test_internal_reminders_and_tool_blocks_are_not_prompt_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            data = {"id": "session_test", "messages": [
                message("user", "Fix the backup schedule."),
                message("user", "[auto] Review weak points before finishing."),
                message("user", "<system-reminder>PRIVATE_ENVIRONMENT</system-reminder>"),
                {"role": "user", "content": [{"type": "tool_result", "content": "RAW_TOOL_OUTPUT"}]},
                {"role": "assistant", "content": [{"type": "thinking", "text": "PRIVATE_REASONING"}, {"type": "text", "text": RESPONSE}]},
            ]}
            (root / "session_test.json").write_text(json.dumps(data))
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", RESPONSE), "Fix the backup schedule.")

    def test_session_traversal_symlinks_and_mismatched_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            real = Path(directory) / "private.json"
            real.write_text(json.dumps({"id": "session_test", "messages": []}))
            (root / "session_test.json").symlink_to(real)
            self.assertEqual(fmt.read_session(Path(directory), "session_test"), {})
            self.assertEqual(fmt.read_session(Path(directory), "../private"), {})
            (root / "session_other.json").write_text(json.dumps({"id": "session_wrong", "messages": []}))
            self.assertEqual(fmt.read_session(Path(directory), "session_other"), {})

    def test_missing_corrupt_and_oversized_sessions_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            self.assertEqual(fmt.session_prompt(Path(directory), "session_missing", RESPONSE), "")
            path = root / "session_test.json"
            path.write_text("invalid json")
            self.assertEqual(fmt.read_session(Path(directory), "session_test"), {})
            with path.open("wb") as stream:
                stream.truncate(fmt.MAX_SESSION_BYTES + 1)
            self.assertEqual(fmt.read_session(Path(directory), "session_test"), {})


    def test_quoted_json_credentials_are_redacted(self):
        raw = '{"password": "CANARY_PASSWORD", "api_key": "CANARY_KEY", "client_secret": "CANARY_SECRET"}'
        output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT=raw), prompt=raw)
        for canary in ("CANARY_PASSWORD", "CANARY_KEY", "CANARY_SECRET"):
            self.assertNotIn(canary, output)
        self.assertIn("[redacted]", output)

    def test_markdown_unicode_and_escaped_credentials_are_redacted(self):
        variants = ('**password**: CANARY_PASSWORD', 'api\u200b_key=CANARY_KEY', 'password="public\\"CANARY_TAIL"')
        for text in variants:
            with self.subTest(text=text):
                self.assertNotIn("CANARY", fmt.sanitize(text))

    def test_brief_keeps_result_even_with_long_unbroken_prompt(self):
        output = fmt.render(event(JCODE_HOOK_LAST_ASSISTANT_TEXT="Updated the selectable profile."), "brief", "X" * 1000)
        self.assertIn("Result:", output)
        self.assertIn("Updated", output)
        self.assertLessEqual(len(output), 320)

    def test_failed_turn_prioritizes_current_error_over_successful_text(self):
        output = fmt.render(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_LAST_ASSISTANT_TEXT="Everything succeeded. Checked: all tests passed.", JCODE_HOOK_ERROR="Connection refused while saving the result."), prompt="Change the profile.")
        self.assertIn("Connection refused", output)
        self.assertNotIn("Everything succeeded", output)
        self.assertNotIn("tests passed", output)

    def test_short_shared_prefix_and_repeated_answers_do_not_pick_new_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            data = {"id": "session_test", "messages": [message("user", "OLD_TASK"), message("assistant", "Done."), message("user", "NEW_TASK"), message("assistant", "Done. More information.")]}
            path = root / "session_test.json"
            path.write_text(json.dumps(data))
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", "Done."), "OLD_TASK")
            data["messages"][-1] = message("assistant", "Done.")
            path.write_text(json.dumps(data))
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", "Done."), "")

    def test_native_4000_character_excerpt_can_match_a_long_saved_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            root.mkdir()
            response = "Known response text. " * 300
            (root / "session_test.json").write_text(json.dumps({"id": "session_test", "messages": [message("user", "Original request."), message("assistant", response)]}))
            self.assertEqual(fmt.session_prompt(Path(directory), "session_test", response[:4000]), "Original request.")


if __name__ == "__main__":
    unittest.main()
