"""Originating-chat identity through real formatter and app entry points, offline."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_format as fmt
import telegram_alerts as app
from test_named_sessions import SESSION, event, saved
from test_readability import bold_fragments


def fallback(sid=SESSION):
    return "chat-" + hashlib.sha256(sid.encode()).hexdigest()[:8]


class ChatIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def identity(self):
        return fmt.chat_identity(self.home, SESSION)

    def journal(self, *records):
        path = self.home / "sessions" / (SESSION + ".journal.jsonl")
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        return path

    def test_saved_title_native_name_and_unnamed_identity(self):
        cases = [
            ({"custom_title": " Storage migration ", "saved": True, "save_label": "Old"}, "Storage migration"),
            ({"custom_title": " ", "saved": True, "save_label": " Saved work "}, "Saved work"),
            ({"title": "Generated summary", "saved": False, "save_label": "Stale"}, ""),
        ]
        for metadata, title in cases:
            with self.subTest(metadata=metadata):
                saved(self.home, short_name="snail", **metadata)
                identity = self.identity()
                self.assertEqual(identity, {"title": title, "short_name": "snail", "session_id": SESSION})
                expected = title + " [snail]" if title else "snail"
                self.assertEqual(fmt.session_label(identity), expected)

    def test_missing_or_malformed_native_names_use_stable_hash_not_session_id(self):
        for name in (None, [], {}, 12, "", "has space", "../private", "éclair", "a" * 33, "_snail"):
            with self.subTest(name=name):
                saved(self.home, short_name=name, title="PRIVATE_GENERATED_TITLE")
                text = fmt.session_label(self.identity())
                self.assertEqual(text, fallback())
                self.assertNotIn(SESSION, text)
                self.assertNotIn("PRIVATE_GENERATED_TITLE", text)
        (self.home / "sessions" / (SESSION + ".json")).unlink()
        self.assertEqual(fmt.session_label(self.identity()), fallback())
        self.assertNotEqual(fallback(), fallback("session_other"))

    def test_native_ascii_boundary_and_known_secret_cannot_be_partially_exported(self):
        for name in ("s", "A0_-", "a" * 32):
            saved(self.home, short_name=name)
            self.assertEqual(fmt.session_label(self.identity()), name)
        saved(self.home, custom_title="Named task", short_name="snail")
        label = fmt.session_label(self.identity(), secrets=("snail",))
        self.assertEqual(label, "Named task [" + fallback() + "]")
        self.assertNotIn("snail", label)

    def test_invalid_session_ids_never_gain_an_identity_label(self):
        for sid in (None, [], {}, "", "../../private", "session_", "session_" + "x" * 181):
            with self.subTest(sid=sid):
                self.assertEqual(fmt.session_label(fmt.chat_identity(self.home, sid)), "")
        for profile in fmt.PROFILES:
            self.assertNotIn("Session:", fmt.render_message(event(), profile)["text"])
            self.assertEqual(fmt.session_label("Legacy", profile), "Legacy")

    def test_journal_rename_clear_and_append_messages_share_one_reader(self):
        saved(self.home, custom_title="Original", short_name="snail", parent_id=None)
        appended = {"id": "a2", "role": "assistant", "content": "Result: Journal result."}
        self.journal({"meta": {"custom_title": "Renamed"}, "append_messages": [appended]})
        self.assertEqual(fmt.session_label(self.identity()), "Renamed [snail]")
        self.assertEqual(fmt.saved_session_name(self.home, SESSION), "Renamed")
        self.assertEqual(fmt.read_session(self.home, SESSION)["messages"][-1], appended)
        self.assertEqual(fmt.session_prompt(self.home, SESSION, appended["content"]), "Improve notification identity.")
        self.journal({"meta": {"custom_title": None, "saved": False, "save_label": None}})
        self.assertEqual(fmt.session_label(self.identity()), "snail")
        self.assertEqual(fmt.saved_session_name(self.home, SESSION), "")

    def test_snapshot_above_old_eight_mib_limit_keeps_identity_and_prompt(self):
        # One bounded padding field exercises the old reader limit without a huge message fixture.
        saved(self.home, custom_title="Large chat", short_name="snail", padding="x" * (8 * 1024 * 1024 + 1))
        self.assertEqual(fmt.session_label(self.identity()), "Large chat [snail]")
        self.assertEqual(fmt.session_prompt(self.home, SESSION, "Result: Updated alerts."), "Improve notification identity.")

    def test_unsafe_snapshot_and_journal_fail_closed_without_private_metadata(self):
        path = saved(self.home, custom_title="PRIVATE_TITLE", short_name="snail")
        invalid = [
            '{"id":"' + SESSION + '","messages":[],"custom_title":"PRIVATE_TITLE","custom_title":"other"}',
            '{"id":"' + SESSION + '","messages":[],"custom_title":"PRIVATE_TITLE","bad":NaN}',
            json.dumps({"id": "session_wrong", "messages": [], "custom_title": "PRIVATE_TITLE"}),
            json.dumps({"id": SESSION, "messages": {}, "custom_title": "PRIVATE_TITLE"}),
            '{"id":',
        ]
        for raw in invalid:
            with self.subTest(raw=raw):
                path.write_text(raw)
                self.assertEqual(fmt.read_session(self.home, SESSION), {})
                self.assertEqual(fmt.session_label(self.identity()), fallback())
        saved(self.home, custom_title="PRIVATE_TITLE", short_name="snail")
        target = self.home / "private.json"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        self.assertEqual(fmt.read_session(self.home, SESSION), {})
        self.assertEqual(fmt.session_label(self.identity()), fallback())
        path.unlink()
        saved(self.home, custom_title="PRIVATE_TITLE", short_name="snail")
        journal = self.journal({"unknown_operation": []})
        self.assertEqual(fmt.read_session(self.home, SESSION), {})
        self.assertEqual(fmt.session_label(self.identity()), fallback())
        journal.unlink()
        journal.symlink_to(target)
        self.assertEqual(fmt.read_session(self.home, SESSION), {})
        journal.unlink()
        for raw in ('{"meta":{"custom_title":"PRIVATE_TITLE","custom_title":"duplicate"}}\n',
                    '{"meta":{"custom_title":"PRIVATE_TITLE","bad":Infinity}}\n',
                    '{"meta":[]}\n', '{"append_messages":{}}\n'):
            with self.subTest(journal=raw):
                journal.write_text(raw)
                self.assertEqual(fmt.read_session(self.home, SESSION), {})
                self.assertEqual(fmt.session_label(self.identity()), fallback())

    def test_symlinked_session_directory_and_hardlink_are_unavailable(self):
        path = saved(self.home, custom_title="PRIVATE_TITLE", short_name="snail")
        os.link(path, self.home / "alias.json")
        self.assertEqual(fmt.read_session(self.home, SESSION), {})
        (self.home / "alias.json").unlink()
        folder = self.home / "sessions"
        folder.rename(self.home / "real-sessions")
        folder.symlink_to(self.home / "real-sessions", target_is_directory=True)
        self.assertEqual(fmt.read_session(self.home, SESSION), {})
        self.assertEqual(fmt.session_label(self.identity()), fallback())

    def test_long_private_unicode_title_keeps_suffix_caps_and_owned_entities(self):
        saved(self.home, custom_title="🚀 Release\n" + "界 " * 2000 + " api_key=CANARY_KEY /private/keys CANARY_TOKEN", short_name="snail")
        for profile, limits in fmt.PROFILES.items():
            for native in ("snail", None):
                with self.subTest(profile=profile, native=native):
                    identity = {**self.identity(), "short_name": native}
                    label = fmt.session_label(identity, profile, secrets=("CANARY_TOKEN",))
                    suffix = " [" + (native or fallback()) + "]"
                    self.assertTrue(label.endswith(suffix), label)
                    self.assertNotIn("\n", label)
                    message = fmt.render_message(event(), profile, session_name=identity, secrets=("CANARY_TOKEN",))
                    self.assertIn(suffix, message["text"])
                    for private in ("CANARY_KEY", "CANARY_TOKEN", "/private/keys"):
                        self.assertNotIn(private, message["text"])
                    self.assertLessEqual(len(message["text"]), limits["chars"])
                    self.assertLessEqual(len(message["text"].split()), limits["words"])
                    self.assertIn("Session:", bold_fragments(message))
                    self.assertIn("Result:", bold_fragments(message))
                    self.assertTrue(fmt.formatting_confirmed(message, message))

    def test_routine_error_lifecycle_and_preview_read_unnamed_identity(self):
        saved(self.home, short_name="snail")
        with patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": str(self.home)}), patch.object(app, "api") as network:
            messages = [app.alert_message(event()), app.preview_message("expanded", SESSION),
                        app.alert_message(event(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current failure"))]
            messages.extend(app.event_message(event(JCODE_HOOK_EVENT=kind))
                            for kind in ("session_start", "turn_start", "session_end"))
            for message in messages:
                self.assertIn("🏷 Session: snail\n", message["text"])
            network.assert_not_called()
