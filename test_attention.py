import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import alert_attention as attention
import alert_format as formatting
import alert_policy as policy
import jcode_telegram as app


class AttentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.environment = {"JCODE_SESSION_ID": "session_attention_fixture", "JCODE_HOOK_CWD": "sample-project"}
        self.request = {"context": "A staged rollout needs owner review.",
                        "needs_you": "Review the proposed change before rollout.",
                        "recommendation": "Use the staged option because it preserves rollback.",
                        "links": [{"label": "Review PR", "url": "https://github.com/example/project/pull/123"}]}
        self.deliveries = []

    def deliver(self, method, message):
        self.deliveries.append((method, copy.deepcopy(message)))
        return {"message_id": len(self.deliveries) + 100, **copy.deepcopy(message)}

    def publish(self, **kwargs):
        return attention.publish(self.home, self.environment, self.request, "example/project:review:revision1",
                                 self.deliver, "a" * 64, **kwargs)

    def test_fresh_push_ignores_routine_cooldown_and_card_without_changing_them(self):
        policy.save_policy(self.home, {"status_card": True, "cooldown_seconds": 86400,
                                      "events": {"completion": False}, "silent_events": ["completion"]})
        settings = (self.home / "notifications" / policy.POLICY_FILE).read_bytes()
        result = self.publish()
        self.assertEqual(result["state"], "sent")
        method, body = self.deliveries[0]
        self.assertEqual(method, "sendMessage")
        self.assertIs(body["disable_notification"], False)
        self.assertNotIn("message_id", body)
        self.assertEqual((self.home / "notifications" / policy.POLICY_FILE).read_bytes(), settings)
        self.assertFalse((self.home / "notifications" / policy.STATE_FILE).exists())

    def test_repeat_is_suppressed_and_explicit_resend_sends_once(self):
        self.assertEqual(self.publish()["state"], "sent")
        self.assertEqual(self.publish()["state"], "already_sent")
        self.assertEqual(len(self.deliveries), 1)
        self.assertEqual(self.publish(resend=True)["state"], "sent")
        self.assertEqual(self.publish()["state"], "already_sent")
        self.assertEqual(len(self.deliveries), 2)

    def test_deduplication_tracks_destination_and_revision_not_just_session(self):
        self.publish()
        self.environment["JCODE_SESSION_ID"] = "session_second_fixture"
        self.assertEqual(self.publish()["state"], "already_sent")
        changed = attention.publish(self.home, self.environment, self.request, "example/project:review:revision2",
                                    self.deliver, "a" * 64)
        self.assertEqual(changed["state"], "sent")
        changed = attention.publish(self.home, self.environment, self.request, "example/project:review:revision1",
                                    self.deliver, "b" * 64)
        self.assertEqual(changed["state"], "sent")
        self.assertEqual(len(self.deliveries), 3)

    def test_filters_fail_visibly_without_transport_or_state(self):
        for changes in ({"exclude_sessions": [self.environment["JCODE_SESSION_ID"]]},
                        {"include_sessions": ["session_other_fixture"]}):
            with self.subTest(changes=changes):
                policy.save_policy(self.home, {"include_sessions": [], "exclude_sessions": [], **changes})
                with self.assertRaisesRegex(attention.AttentionError, "session filters"):
                    self.publish()
        with self.assertRaisesRegex(attention.AttentionError, "session filters"):
            attention.publish(self.home, {"JCODE_HOOK_CWD": "sample-project"}, self.request,
                              "example/project:review:revision1", self.deliver, "a" * 64)
        self.assertEqual(self.deliveries, [])
        self.assertFalse((self.home / "notifications" / attention.STATE_FILE).exists())

    def test_session_name_is_omitted_and_unicode_entities_use_exact_utf16_ranges(self):
        (self.home / "sessions").mkdir()
        (self.home / "sessions" / (self.environment["JCODE_SESSION_ID"] + ".json")).write_text(json.dumps({
            "id": self.environment["JCODE_SESSION_ID"], "custom_title": "Useful rollout name", "messages": []}))
        self.request["needs_you"] = "Choose 🐝 A or B."
        self.publish()
        message = self.deliveries[0][1]
        self.assertNotIn("Useful rollout name", message["text"])
        self.assertNotIn("🏷 Session:", message["text"])
        self.assertNotIn(self.environment["JCODE_SESSION_ID"], message["text"])
        self.assertIn("sample-project", message["text"])
        self.assertIn("Context:", message["text"])
        self.assertIn("Needs you:", message["text"])
        self.assertIn("Recommended:", message["text"])
        raw = message["text"].encode("utf-16-le")
        labels = [raw[e["offset"] * 2:(e["offset"] + e["length"]) * 2].decode("utf-16-le")
                  for e in message["entities"] if e["type"] == "text_link"]
        self.assertEqual(labels, ["Review PR · github.com"])
        self.assertTrue(formatting.formatting_confirmed(message, {"text": message["text"], "entities": message["entities"]}))

    def test_optional_recommendation_and_links_can_be_omitted(self):
        self.request = {"context": "Access is required.", "needs_you": "Complete the owner-side access step."}
        self.publish()
        text = self.deliveries[0][1]["text"]
        self.assertNotIn("Recommended:", text)
        self.assertNotIn("Links:", text)
        self.assertNotIn("unavailable", text)

    def test_invalid_records_and_required_links_fail_before_delivery(self):
        bad = [[], {}, {"context": "x", "needs_you": "y", "extra": "z"},
               {**self.request, "context": " "}, {**self.request, "needs_you": 1},
               {**self.request, "recommendation": None}, {**self.request, "links": {}},
               {**self.request, "links": self.request["links"] * 4},
               {**self.request, "context": "x" * 401}, {**self.request, "needs_you": "x" * 801},
               {**self.request, "recommendation": "x" * 601},
               {**self.request, "needs_you": "See https://github.com/example/project/pull/123"}]
        for prefix in ("h\u200bttps", "ht**tps", "ht`tp", "w\u2060ss"):
            bad.append({**self.request, "needs_you": f"Review {prefix}://github.com/example/project/pull/123"})
        for url in ("http://github.com/example/project", "https://user:password@github.com/example/project",
                    "https://github.com/example/project?token=private", "https://github.com/example/project#fragment",
                    "https://preview.example.org:4328/", "https://127.0.0.1/", "https://example.local/"):
            bad.append({**self.request, "links": [{"label": "Review", "url": url}]})
        for link in ({"label": "Review"}, {"url": "https://github.com/example/project"},
                     {"label": "A\nB", "url": "https://github.com/example/project"},
                     {"label": "password=private", "url": "https://github.com/example/project"}):
            bad.append({**self.request, "links": [link]})
        for separator in ("\u2028", "\u2029", "\x85"):
            bad.append({**self.request, "links": [{"label": f"Review{separator}Approved", "url": "https://github.com/example/project"}]})
        for value in bad:
            with self.subTest(kind=type(value).__name__), self.assertRaises(attention.AttentionError):
                attention.publish(self.home, self.environment, value, "example/project:review:revision1", self.deliver, "a" * 64)
        self.assertEqual(self.deliveries, [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_session_identity_is_optional_but_keys_are_required(self):
        sessions = (None, "", "ordinary-agent-fixture", "../private-session", 12)
        for index, session in enumerate(sessions):
            with self.subTest(session=session):
                environment = {**self.environment, "JCODE_SESSION_ID": session}
                result = attention.publish(self.home, environment, self.request,
                                           f"example/project:optional-session:revision{index}",
                                           self.deliver, "a" * 64)
                self.assertEqual(result["state"], "sent")
                message = self.deliveries[-1][1]["text"]
                self.assertNotIn("🏷 Session:", message)
                if isinstance(session, str) and session:
                    self.assertNotIn(session, message)
        for key in (None, "", "x" * 201, "with spaces", "line\nbreak", 12):
            with self.subTest(key=key), self.assertRaises(attention.AttentionError):
                attention.publish(self.home, self.environment, self.request, key, self.deliver, "a" * 64)
        self.assertEqual(len(self.deliveries), len(sessions))

    def test_unicode_overflow_is_rejected_not_silently_clipped(self):
        self.request.update(context="🐝" * 400, needs_you="🐝" * 800, recommendation="🐝" * 600)
        with self.assertRaisesRegex(attention.AttentionError, "too long"):
            self.publish()
        self.assertEqual(self.deliveries, [])

    def test_redaction_and_private_fingerprint_only_state(self):
        self.request["context"] = 'password="CANARY_PASSWORD" and api_key=CANARY_KEY and PRIVATE_CANARY'
        self.publish(secrets=("PRIVATE_CANARY",))
        text = self.deliveries[0][1]["text"]
        for value in ("CANARY_PASSWORD", "CANARY_KEY", "PRIVATE_CANARY"):
            self.assertNotIn(value, text)
        state = self.home / "notifications" / attention.STATE_FILE
        stored = state.read_text()
        for value in (self.request["needs_you"], self.request["links"][0]["url"], self.environment["JCODE_SESSION_ID"], "revision1"):
            self.assertNotIn(value, stored)
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(state.parent.stat().st_mode & 0o777, 0o700)

    def test_unconfirmed_text_or_entities_does_not_mark_request_sent(self):
        for response in ({}, {"message_id": 1, "text": "wrong", "entities": []}):
            with patch.object(self, "deliver", return_value=response), self.assertRaisesRegex(attention.AttentionError, "not confirmed"):
                self.publish()
        with patch.object(formatting, "formatting_confirmed", return_value=False), self.assertRaises(attention.AttentionError):
            self.publish()
        self.assertFalse((self.home / "notifications" / attention.STATE_FILE).exists())
        self.assertEqual(self.publish()["state"], "sent")

    def test_state_failure_after_acknowledgement_is_honest(self):
        with patch.object(policy, "_write", side_effect=ValueError("PRIVATE_VALUE")):
            with self.assertRaisesRegex(attention.AttentionError, "Telegram accepted.*Do not retry") as result:
                self.publish()
        self.assertNotIn("PRIVATE_VALUE", str(result.exception))
        self.assertEqual(len(self.deliveries), 1)

    def test_symlink_and_corrupt_state_fail_closed(self):
        folder = self.home / "notifications"
        folder.mkdir(mode=0o700)
        state = folder / attention.STATE_FILE
        other = self.home / "untouched"
        other.write_text("PRIVATE_VALUE")
        state.symlink_to(other)
        with self.assertRaises(attention.AttentionError):
            self.publish()
        self.assertEqual(other.read_text(), "PRIVATE_VALUE")
        state.unlink()
        state.write_text('{"version": 1, "requests": [], "secret": "PRIVATE_VALUE"}')
        state.chmod(0o600)
        with self.assertRaises(attention.AttentionError) as result:
            self.publish()
        self.assertNotIn("PRIVATE_VALUE", str(result.exception))
        self.assertEqual(self.deliveries, [])

    def test_expired_history_is_pruned_but_active_capacity_fails_closed(self):
        with patch.object(attention.time, "time", return_value=1_000_000):
            self.publish()
        with patch.object(attention.time, "time", return_value=1_000_000 + attention.RETENTION_SECONDS + 1):
            self.assertEqual(self.publish()["state"], "sent")
        with patch.object(attention, "MAX_REQUESTS", 1), \
                patch.object(attention.time, "time", return_value=1_000_000 + attention.RETENTION_SECONDS + 1):
            with self.assertRaisesRegex(attention.AttentionError, "capacity"):
                attention.publish(self.home, self.environment, self.request, "another-key", self.deliver, "a" * 64)

    def test_read_input_rejects_duplicate_keys_bad_encoding_and_oversized_json(self):
        for raw in ('{"context":"a","context":"b"}', '{"context":NaN}', '"' + "x" * 8192 + '"', "[" * 1100):
            with self.subTest(raw=raw[:20]), self.assertRaises(attention.AttentionError):
                attention.read_request(io.StringIO(raw))
        self.assertEqual(attention.read_request(io.StringIO(json.dumps(self.request))), self.request)

    def run_cli(self, *extra, session_id="session_attention_fixture"):
        environment = {"JCODE_HOME": str(self.home)}
        if session_id is not None:
            environment["JCODE_SESSION_ID"] = session_id
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, "argv", ["jcode-telegram", "attention", "--key", "example/project:review:revision1", *extra]), \
                patch.object(sys, "stdin", io.StringIO(json.dumps(self.request))), \
                patch.object(app, "api", side_effect=lambda token, method, body: self.deliver(method, body)), \
                contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as errors:
            result = app.cli()
        return result, output.getvalue(), errors.getvalue()

    def test_real_cli_entrypoint_reuses_config_and_reports_sent_duplicate_and_resend(self):
        config = self.home / "config.toml"
        original = '[safety]\ntelegram_enabled = true\ntelegram_bot_token = "test-placeholder"\ntelegram_chat_id = "test-destination"\ntelegram_reply_enabled = true\n[hooks]\nturn_end = ["foreign-hook"]\n'
        config.write_text(original)
        for extra, expected in (((), "sent"), ((), "already_sent"), (("--resend",), "sent")):
            code, output, errors = self.run_cli(*extra)
            self.assertEqual((code, errors), (0, ""))
            self.assertEqual(json.loads(output)["state"], expected)
        self.assertEqual(len(self.deliveries), 2)
        self.assertEqual(config.read_text(), original)
        self.assertEqual(self.deliveries[0][1]["chat_id"], "test-destination")

    def test_cli_attention_succeeds_without_jcode_session_id_and_omits_session_name(self):
        config = self.home / "config.toml"
        config.write_text('[safety]\ntelegram_enabled = true\ntelegram_bot_token = "test-placeholder"\ntelegram_chat_id = "test-destination"\n')
        code, output, errors = self.run_cli(session_id=None)
        self.assertEqual((code, errors), (0, ""))
        self.assertEqual(json.loads(output)["state"], "sent")
        message = self.deliveries[0][1]["text"]
        self.assertIn("A staged rollout needs owner review.", message)
        self.assertIn("Review the proposed change before rollout.", message)
        self.assertNotIn("🏷 Session:", message)
        self.assertNotIn("session_attention_fixture", message)

    def test_disabled_channel_cannot_be_overridden_by_attention(self):
        (self.home / "config.toml").write_text('[safety]\ntelegram_enabled = false\ntelegram_bot_token = "test-placeholder"\ntelegram_chat_id = "test-destination"\n')
        code, output, errors = self.run_cli()
        self.assertEqual((code, output), (1, ""))
        self.assertIn("not linked", errors)
        self.assertNotIn("test-placeholder", errors)
        self.assertEqual(self.deliveries, [])

    def test_interrupted_transport_reports_ambiguous_delivery_without_marking_sent(self):
        (self.home / "config.toml").write_text('[safety]\ntelegram_enabled = true\ntelegram_bot_token = "test-placeholder"\ntelegram_chat_id = "test-destination"\n')
        with patch.object(self, "deliver", side_effect=KeyboardInterrupt):
            code, output, errors = self.run_cli()
        self.assertEqual((code, output), (1, ""))
        self.assertIn("may have arrived", errors)
        self.assertIn("do not retry automatically", errors)
        self.assertFalse((self.home / "notifications" / attention.STATE_FILE).exists())

    def test_public_help_explains_stdin_schema_without_creating_state(self):
        result = subprocess.run([sys.executable, str(Path(app.__file__)), "attention", "--help"],
                                env={**os.environ, "JCODE_HOME": str(self.home)}, capture_output=True, text=True, check=True)
        self.assertIn("needs_you", result.stdout)
        self.assertIn("--resend", result.stdout)
        self.assertIn("JCODE_SESSION_ID", result.stdout)
        self.assertIn("optional", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
