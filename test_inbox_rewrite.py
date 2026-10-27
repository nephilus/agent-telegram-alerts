import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import alert_attention as attention
import telegram_alerts as app


class InboxRewriteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.registry = self.root / "inbox.json"
        self.environment = {
            "TELEGRAM_ALERTS_CWD": "sample-project",
            attention.INBOX_REGISTRY_ENV: str(self.registry),
        }
        self.request = {
            "context": "A Plannotator review is ready.",
            "needs_you": "Review the linked Inbox thread.",
            "links": [{"label": "Inbox thread", "url": "http://localhost:44529/inbox/review%2Fsub?mode=compact%2Ffull#thread=alpha"}],
        }
        self.deliveries = []

    def registry_data(self, *, port=44529, tailscale_url="https://device.tailnet.ts.net:44529/"):
        value = {"v": 1, "port": port, "url": f"http://localhost:{port}/", "tailscale": {}}
        if tailscale_url is not None:
            value["tailscale"]["url"] = tailscale_url
        self.registry.write_text(json.dumps(value))
        self.registry.chmod(0o600)
        return self.registry.read_bytes()

    def deliver(self, method, body):
        self.deliveries.append((method, copy.deepcopy(body)))
        return {"message_id": 42, **copy.deepcopy(body)}

    def publish(self, **kwargs):
        return attention.publish(self.home, self.environment, self.request,
                                 "example/project:inbox-review:revision1", self.deliver,
                                 "a" * 64, **kwargs)

    @staticmethod
    def link_urls(message):
        return [entity["url"] for entity in message["entities"] if entity["type"] == "text_link"]

    def test_registry_rewrite_preserves_path_query_fragment_without_mutating_input(self):
        registry_before = self.registry_data()
        request_before = copy.deepcopy(self.request)
        receipt = self.publish()
        self.assertEqual(receipt["state"], "sent")
        self.assertEqual(self.deliveries[0][0], "sendMessage")
        message = self.deliveries[0][1]
        self.assertEqual(self.link_urls(message), [
            "https://device.tailnet.ts.net:44529/inbox/review%2Fsub?mode=compact%2Ffull#thread=alpha"
        ])
        self.assertEqual(self.request, request_before)
        self.assertEqual(self.registry.read_bytes(), registry_before)
        self.assertEqual(receipt["url_rewrites"], [{
            "from": "http://localhost:44529",
            "to": "https://device.tailnet.ts.net:44529/",
            "count": 1,
        }])
        self.assertNotIn("thread=alpha", json.dumps(receipt))
        self.assertNotIn("mode=compact", json.dumps(receipt))
        self.assertTrue(receipt["response_confirmed"])
        self.assertTrue(receipt["formatting_confirmed"])

    def test_default_registry_is_under_the_plannotator_inbox_home(self):
        request = {"links": [{"url": "http://localhost:44529/"}]}
        base = "https://device.tailnet.ts.net:44529/"
        with patch.object(Path, "home", return_value=self.root), \
                patch.object(attention, "_read_inbox_registry", return_value=(44529, base)) as read:
            mapping = attention._inbox_mapping({}, request)
        self.assertEqual(mapping["base"], "https://device.tailnet.ts.net:44529")
        read.assert_called_once_with(str(self.root / ".plannotator" / "inbox" / "inbox.json"))

    def test_both_exact_loopback_hosts_rewrite_but_other_ports_and_hosts_do_not(self):
        self.registry_data()
        mapping = attention._inbox_mapping(self.environment, self.request)
        for value in ("http://localhost:44528/", "http://localhost:44529evil/",
                      "http://127.0.0.2:44529/", "http://127.0.0.1:44528/"):
            with self.subTest(value=value):
                self.assertEqual(attention._rewrite_inbox_url(value, mapping), (None, None, False))
        for host in ("localhost", "127.0.0.1"):
            value = f"http://{host}:44529/#thread=test"
            rewritten, prefix, missing = attention._rewrite_inbox_url(value, mapping)
            self.assertEqual(prefix, f"http://{host}:44529")
            self.assertFalse(missing)
            self.assertEqual(rewritten, "https://device.tailnet.ts.net:44529/#thread=test")

    def test_explicit_base_override_and_registry_path_are_honored(self):
        registry_before = self.registry_data(tailscale_url="https://registry.tailnet.ts.net:44529/")
        self.environment[attention.INBOX_BASE_ENV] = "https://override.tailnet.example.net:44529/"
        self.request["links"][0]["url"] = "http://127.0.0.1:44529/"
        receipt = self.publish()
        self.assertEqual(self.link_urls(self.deliveries[0][1]), ["https://override.tailnet.example.net:44529/"])
        self.assertEqual(receipt["url_rewrites"][0]["to"], "https://override.tailnet.example.net:44529/")
        self.assertEqual(self.registry.read_bytes(), registry_before)

    def test_other_loopback_ports_and_sensitive_suffixes_keep_rejecting(self):
        self.registry_data()
        for url in ("http://localhost:44528/", "http://127.0.0.2:44529/",
                    "http://localhost:44529/?token=private"):
            with self.subTest(url=url), self.assertRaises(attention.AttentionError):
                self.request["links"][0]["url"] = url
                self.publish()
        self.assertEqual(self.deliveries, [])

    def test_missing_tailnet_mapping_warns_and_sends_without_the_local_link(self):
        self.registry_data(tailscale_url=None)
        request_before = copy.deepcopy(self.request)
        receipt = self.publish()
        self.assertEqual(receipt["state"], "sent")
        self.assertEqual(self.link_urls(self.deliveries[0][1]), [])
        self.assertNotIn("Links:", self.deliveries[0][1]["text"])
        self.assertIn("url_rewrite_warnings", receipt)
        self.assertIn("omitted", receipt["url_rewrite_warnings"][0])
        self.assertEqual(self.request, request_before)

    def test_missing_registry_warns_and_does_not_invent_a_mapping(self):
        self.request["links"][0]["url"] = "http://127.0.0.1:44529/"
        receipt = self.publish()
        self.assertEqual(receipt["state"], "sent")
        self.assertEqual(self.link_urls(self.deliveries[0][1]), [])
        self.assertTrue(receipt["url_rewrite_warnings"])
        self.assertNotIn("url_rewrites", receipt)

    def test_cli_prints_unmapped_link_warning_and_receipt(self):
        self.registry_data(tailscale_url=None)
        self.home.mkdir()
        payload = json.dumps(self.request)
        with patch.dict(os.environ, {"TELEGRAM_ALERTS_HOME": str(self.home),
                                     attention.INBOX_REGISTRY_ENV: str(self.registry)}, clear=True), \
                patch.object(app.sys, "argv", ["telegram-alerts", "attention", "--key",
                                                "example/project:inbox-review:revision2"]), \
                patch.object(app.sys, "stdin", io.StringIO(payload)), \
                patch.object(app, "credentials", return_value=("synthetic-token", "42")), \
                patch.object(app, "api", side_effect=lambda token, method, body: self.deliver(method, body)), \
                patch("sys.stdout", new_callable=io.StringIO) as output, \
                patch("sys.stderr", new_callable=io.StringIO) as errors:
            app.main()
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["state"], "sent")
        self.assertIn("Warning:", errors.getvalue())
        self.assertIn("omitted", errors.getvalue())

    def test_non_loopback_https_link_is_unchanged(self):
        self.request["links"][0]["url"] = "https://github.com/example/project/pull/123"
        receipt = self.publish()
        self.assertEqual(self.link_urls(self.deliveries[0][1]), [self.request["links"][0]["url"]])
        self.assertNotIn("url_rewrites", receipt)


if __name__ == "__main__":
    unittest.main()
