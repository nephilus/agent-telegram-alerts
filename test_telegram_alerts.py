import io
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import urllib.error

import telegram_alerts as app
import legacy_jcode as legacy

TOKEN = "123456:" + "a" * 35


class TelegramTests(unittest.TestCase):
    def test_preserves_unrelated_settings_and_existing_hooks(self):
        text = '# comment\n[hooks]\nturn_end = ["moshi", "other"]\n[safety]\ntelegram_enabled = false\ndesktop_notifications = true\n[provider]\nmodel = "existing"\n'
        result = app.update_safety(text, {"telegram_enabled": True, "telegram_bot_token": TOKEN, "telegram_chat_id": "42", "telegram_reply_enabled": False})
        old, new = tomllib.loads(text), tomllib.loads(result)
        self.assertEqual(old["hooks"], new["hooks"])
        self.assertEqual(old["provider"], new["provider"])
        self.assertTrue(new["safety"]["desktop_notifications"])
        self.assertFalse(new["safety"]["telegram_reply_enabled"])
        self.assertTrue(result.startswith("# comment"))

    def test_adds_missing_safety_section_and_is_idempotent(self):
        changes = {"telegram_enabled": True, "telegram_bot_token": TOKEN}
        result = app.update_safety('[provider]\nmodel = "keep"\n', changes)
        self.assertEqual(app.update_safety(result, changes), result)
        self.assertEqual(tomllib.loads(result)["provider"]["model"], "keep")
        self.assertTrue(tomllib.loads(app.update_safety("", changes))["safety"]["telegram_enabled"])

    def test_config_and_backup_are_private(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory}):
            path = Path(directory) / "config.toml"
            path.write_text('[safety]\ntelegram_enabled = false\n')
            app.save_safety({"telegram_enabled": True, "telegram_bot_token": TOKEN})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            backups = list(Path(directory).glob("config.toml.telegram-backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
            self.assertFalse(tomllib.loads(backups[0].read_text())["safety"]["telegram_enabled"])

    def test_legacy_telegram_credentials_are_read_only_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".jcode"
            legacy.mkdir()
            legacy_path = legacy / "config.toml"
            original = ('[safety]\ntelegram_enabled = true\ntelegram_bot_token = "' + TOKEN +
                        '"\ntelegram_chat_id = "42"\ntelegram_reply_enabled = false\n')
            legacy_path.write_text(original)
            generic = root / ".config" / "telegram-alerts"
            with patch.object(Path, "home", return_value=root), patch.dict(os.environ, {}, clear=True), \
                    patch.object(app, "_legacy_config_notice_emitted", False), \
                    patch("sys.stderr", new_callable=io.StringIO) as errors:
                self.assertEqual(app.config_path(), generic / "config.toml")
                self.assertEqual(app.credentials(), (TOKEN, "42"))
                self.assertFalse((generic / "config.toml").exists())
                self.assertEqual(legacy_path.read_text(), original)
                self.assertIn("~/.jcode/", errors.getvalue())
                self.assertIn("read-only", errors.getvalue())
                app.save_safety({"telegram_enabled": False})
                self.assertTrue((generic / "config.toml").is_file())
                self.assertEqual(legacy_path.read_text(), original)

    def test_explicit_generic_home_and_disable_do_not_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".jcode"
            legacy.mkdir()
            (legacy / "config.toml").write_text(
                '[safety]\ntelegram_enabled = true\ntelegram_bot_token = "' + TOKEN +
                '"\ntelegram_chat_id = "42"\n')
            generic = root / ".config" / "telegram-alerts"
            generic.mkdir(parents=True)
            (generic / "config.toml").write_text('[safety]\ntelegram_enabled = false\n')
            with patch.object(Path, "home", return_value=root), patch.dict(
                    os.environ, {"TELEGRAM_ALERTS_HOME": str(generic)}, clear=True), \
                    patch.object(app, "_legacy_config_notice_emitted", False), \
                    patch("sys.stderr", new_callable=io.StringIO) as errors:
                self.assertFalse(app.load_config()["safety"]["telegram_enabled"])
                self.assertEqual(errors.getvalue(), "")

    def test_legacy_cli_forwards_to_the_same_cli_without_changing_home(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"TELEGRAM_ALERTS_HOME": directory}, clear=True), \
                patch.object(app, "cli", return_value=7) as run_cli:
            argv = ["jcode-telegram", "attention", "--key", "example/project:review:revision"]
            with patch.object(app.sys, "argv", argv):
                self.assertEqual(app.legacy_cli(), 7)
                self.assertIs(app.sys.argv, argv)
            run_cli.assert_called_once_with()
            self.assertEqual(app.config_path().parent, Path(directory))

    def test_rejects_config_symlink(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory}):
            target = Path(directory) / "real.toml"
            target.write_text("")
            (Path(directory) / "config.toml").symlink_to(target)
            with self.assertRaises(app.SetupError):
                app.save_safety({"telegram_enabled": True})
            self.assertEqual(target.read_text(), "")

    def test_short_success_filtered_boundary_and_failure_allowed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"TELEGRAM_ALERTS_HOME": directory}):
            event = {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok", "JCODE_HOOK_DURATION_MS": "29999"}
            self.assertIsNone(legacy.alert_text(event))
            event["JCODE_HOOK_DURATION_MS"] = "30000"
            self.assertIn("finished", legacy.alert_text(event))
            event.update(JCODE_HOOK_STATUS="error", JCODE_HOOK_DURATION_MS="0")
            self.assertIn("failed", legacy.alert_text(event))
            event["JCODE_HOOK_DURATION_MS"] = "bad"
            self.assertIn("failed", legacy.alert_text(event))

    def test_no_sensitive_event_contents_are_forwarded(self):
        event = {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "error", "JCODE_HOOK_DURATION_MS": "1000", "JCODE_HOOK_LAST_ASSISTANT_TEXT": TOKEN, "JCODE_HOOK_ERROR": TOKEN, "JCODE_HOOK_CWD": "/private/path"}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory}):
            result = legacy.alert_text(event)
            self.assertNotIn(TOKEN, result)
            self.assertIn("📁 /private/path", result)
            event["JCODE_HOOK_EVENT"] = "post_tool"
            self.assertIsNone(legacy.alert_text(event))

    def test_http_failure_never_exposes_token(self):
        error = urllib.error.HTTPError(f"https://api.telegram.org/bot{TOKEN}/getMe", 401, "Unauthorized", {}, None)
        with patch.object(app.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(app.SetupError) as caught:
                app.api(TOKEN, "getMe")
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertIn("401", str(caught.exception))

    def test_api_uses_https_json_and_timeout(self):
        with patch.object(app.urllib.request, "urlopen") as request:
            request.return_value.__enter__.return_value = io.StringIO('{"ok":true,"result":{"id":42}}')
            self.assertEqual(app.api(TOKEN, "getMe"), {"id": 42})
            sent = request.call_args.args[0]
            self.assertTrue(sent.full_url.startswith("https://api.telegram.org/"))
            self.assertEqual(json.loads(sent.data), {})
            self.assertEqual(request.call_args.kwargs["timeout"], 15)

    def test_setup_refuses_non_terminal_token_entry(self):
        with patch.object(app.sys.stdin, "isatty", return_value=False), patch.object(app.getpass, "getpass") as prompt:
            with self.assertRaises(app.SetupError):
                app.setup()
            prompt.assert_not_called()

    def test_setup_refuses_existing_webhook_without_mutation(self):
        with patch.object(app.sys.stdin, "isatty", return_value=True), patch.object(app.getpass, "getpass", return_value=TOKEN), patch.object(app, "api", side_effect=[{"username": "test_bot"}, {"url": "https://existing.invalid"}]), patch.object(app, "save_safety") as save, patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(app.SetupError):
                app.setup()
            save.assert_not_called()

    def test_setup_verifies_private_challenge_and_test_before_save(self):
        challenge = "/start telegram_alerts_fixedchallenge"
        def update(number, kind, text, who=42):
            return {"update_id": number, "message": {"text": text, "chat": {"id": 42, "type": kind}, "from": {"id": who}}}
        updates = [update(1, "private", "/start"), update(2, "group", challenge), update(3, "private", challenge, 99), update(4, "private", challenge)]
        calls = []
        def fake_api(token, method, values=None, timeout=15):
            calls.append(method)
            return {"getMe": {"username": "test_bot"}, "getWebhookInfo": {"url": ""}, "getUpdates": updates, "sendMessage": {"message_id": 1}}[method]
        def save(changes):
            self.assertEqual(calls[-1], "sendMessage")
            self.assertEqual(changes["telegram_chat_id"], "42")
            self.assertFalse(changes["telegram_reply_enabled"])
        with patch.object(app.sys.stdin, "isatty", return_value=True), patch.object(app.getpass, "getpass", return_value=TOKEN), patch.object(app.secrets, "token_hex", return_value="fixedchallenge"), patch.object(app, "api", side_effect=fake_api), patch.object(app, "save_safety", side_effect=save) as saved, patch("sys.stdout", new_callable=io.StringIO):
            app.setup()
            saved.assert_called_once()

    def test_failed_delivery_never_enables_channel(self):
        update = {"update_id": 1, "message": {"text": "/start telegram_alerts_fixed", "chat": {"id": 42, "type": "private"}, "from": {"id": 42}}}
        with patch.object(app.sys.stdin, "isatty", return_value=True), patch.object(app.getpass, "getpass", return_value=TOKEN), patch.object(app.secrets, "token_hex", return_value="fixed"), patch.object(app, "api", side_effect=[{"username": "test_bot"}, {"url": ""}, [update], app.SetupError("send failed")]), patch.object(app, "save_safety") as save, patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(app.SetupError):
                app.setup()
            save.assert_not_called()

    def test_missing_credentials_do_not_send_alert(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory, "JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "error"}), patch.object(app.sys, "argv", ["telegram-alerts-jcode", "event"]), patch.object(legacy, "api") as send:
            legacy.main()
            send.assert_not_called()
            receipt = json.loads(legacy.receipt_path().read_text())
            self.assertEqual(receipt["state"], "pending_setup")
            self.assertEqual(legacy.receipt_path().stat().st_mode & 0o777, 0o600)

    def test_receipt_does_not_store_raw_session_or_contents(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": directory, "JCODE_HOOK_SESSION_ID": "private-session-id", "JCODE_HOOK_LAST_ASSISTANT_TEXT": TOKEN}):
            legacy.record_receipt("suppressed_short_or_unknown_turn")
            text = legacy.receipt_path().read_text()
            self.assertNotIn("private-session-id", text)
            self.assertNotIn(TOKEN, text)
            self.assertEqual(len(json.loads(text)["session_fingerprint"]), 16)

    def test_receipt_failure_does_not_disrupt_hook(self):
        with patch.object(app, "private_write", side_effect=OSError("read only")):
            legacy.record_receipt("pending_setup")


if __name__ == "__main__":
    unittest.main()
