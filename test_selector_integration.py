"""Native source, public CLI and delivery-boundary checks for selected updates.

All transports are synthetic in this file. The rollout separately exercises the
installed observer against the maintained decision API and real Telegram.
"""
import copy
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import alert_format as fmt
import alert_policy as policy
import alert_selector as selector
import jcode_telegram as app


class SelectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.sid = "session_selector_test"
        self.environment = {
            "JCODE_HOME": str(self.home), "JCODE_SESSION_ID": self.sid,
            "JCODE_HOOK_SESSION_ID": self.sid, "JCODE_HOOK_EVENT": "turn_end",
            "JCODE_HOOK_STATUS": "ok", "JCODE_HOOK_DURATION_MS": "500",
            "JCODE_HOOK_CWD": "/sample/project",
        }
        self.token = "synthetic-bot-credential"
        self.chat = "synthetic-destination"
        self.key = self.home / "decision.key"
        self.key.write_text("synthetic-decision-credential")
        self.key.chmod(0o600)
        (self.home / "config.toml").write_text(
            '[safety]\ntelegram_enabled = true\ntelegram_bot_token = "' + self.token
            + '"\ntelegram_chat_id = "' + self.chat + '"\ntelegram_reply_enabled = false\n')
        (self.home / "sessions").mkdir()
        self.messages = [self.message("u1", "user", "Make the service usable and report its measured limits.")]
        self.source = {"id": self.sid, "parent_id": None, "working_dir": "/sample/project",
                       "short_name": "automatic-animal", "messages": self.messages}
        self.response = "**ELIF:** The service is now usable. Its actual sign-in test passed, but the upload limit is still 10 MB."
        self.publish(self.response)
        self.calls, self.requests = [], []

    @staticmethod
    def message(mid, role, text):
        return {"id": mid, "role": role, "content": [{"type": "text", "text": text}]}

    def write_source(self):
        (self.home / "sessions" / (self.sid + ".json")).write_text(json.dumps(self.source))

    def publish(self, response, mid="a1"):
        self.messages.append(self.message(mid, "assistant", response))
        self.write_source()
        self.environment["JCODE_HOOK_LAST_ASSISTANT_TEXT"] = response[:4000]

    def enable(self):
        selector.configure(self.home, endpoint="https://decision.example.test:9105", key_file=str(self.key),
                           model="test-alias", expected_model="test-clef", pir_turns=100)
        policy.save_policy(self.home, {"completion_selector": "clef", "events": {"completion": True}})

    @staticmethod
    def answer(keep=True):
        return {"model": "test-clef", "usage": {"input_tokens": 100, "output_tokens": 0},
                "answers": {"publish": {"type": "choice", "choice": "yes" if keep else "no",
                    "probabilities": {"yes": .9 if keep else .1, "no": .1 if keep else .9}, "confidence": .8}}}

    def observe(self, keep=True, request=None):
        real_process = selector.process

        def fake_request(config, payload, key):
            self.requests.append(copy.deepcopy(payload))
            return request(config, payload, key) if request else self.answer(keep)

        def process(home, turn, deliver, **kwargs):
            return real_process(home, turn, deliver, request=fake_request, **kwargs)

        def telegram(token, method, body):
            self.calls.append((method, copy.deepcopy(body)))
            return {**body, "message_id": len(self.calls)}

        with patch.dict(os.environ, self.environment), patch.object(selector, "process", side_effect=process), patch.object(app, "api", side_effect=telegram):
            app.observe_event(self.environment, min_seconds=30)
        kind = "error" if self.environment.get("JCODE_HOOK_STATUS") == "error" else "completion"
        return json.loads((self.home / ("notifications/telegram-last-" + kind + ".json")).read_text())

    def test_native_snapshot_and_journal_bind_full_final_and_rename(self):
        long = "**ELIF:** " + "Useful result. " * 310 + "\n\nNeeds you: review the actual PR.\nhttps://github.com/example/repo/pull/42"
        self.source["messages"] = self.messages[:1]
        self.write_source()
        journal = {"meta": {"custom_title": "Meaningful work"}, "append_messages": [self.message("a2", "assistant", long)]}
        (self.home / "sessions" / (self.sid + ".journal.jsonl")).write_text(json.dumps(journal) + "\n")
        self.environment["JCODE_HOOK_LAST_ASSISTANT_TEXT"] = long[:4000]
        context = fmt.selector_context(self.home, self.environment)
        self.assertIn("Needs you: review", context["turn"]["current_public_final"])
        self.assertEqual(context["session_name"], {"title": "Meaningful work", "short_name": "automatic-animal", "session_id": self.sid})
        self.assertNotIn("session_name", context["turn"])
        self.assertNotIn("short_name", context["turn"])
        self.assertNotIn("custom_title", context["turn"])
        self.assertEqual(context["turn"]["links"][0]["url"], "https://github.com/example/repo/pull/42")
        self.assertEqual(context["environment"]["JCODE_HOOK_LAST_ASSISTANT_TEXT"], long)

    def test_source_mismatch_duplicate_newer_or_tool_final_is_quiet(self):
        original = copy.deepcopy(self.source)
        for replacement in ("Not the hook response", self.response):
            self.source = copy.deepcopy(original)
            self.source["messages"].append(self.message("a2", "assistant", replacement))
            self.write_source()
            with self.assertRaises(ValueError):
                fmt.selector_context(self.home, self.environment)
        self.source = copy.deepcopy(original)
        self.source["messages"][-1]["content"].append({"type": "tool_use", "name": "tool", "input": {}})
        self.write_source()
        with self.assertRaises(ValueError):
            fmt.selector_context(self.home, self.environment)

    def test_known_children_and_automation_are_not_owner_turns(self):
        self.source["parent_id"] = "session_parent"
        self.write_source()
        with self.assertRaisesRegex(ValueError, "internal_session"):
            fmt.selector_context(self.home, self.environment)
        self.assertEqual(fmt.selector_context(self.home, self.environment, allow_fork=True)["turn"]["session_id"], self.sid)
        self.source["parent_id"] = None
        for request in ("[auto] Keep checking tests", "Cross-swarm DM from someone: ACK", "You have 3 incomplete todos. Continue working.", "<system-reminder>tools finished</system-reminder>"):
            self.source["messages"][0]["content"][0]["text"] = request
            self.write_source()
            with self.assertRaisesRegex(ValueError, "internal_turn"):
                fmt.selector_context(self.home, self.environment)

    def test_unknown_journal_operation_and_symlink_fail_closed(self):
        journal = self.home / "sessions" / (self.sid + ".journal.jsonl")
        journal.write_text(json.dumps({"replace_messages": []}) + "\n")
        with self.assertRaises(ValueError):
            fmt.selector_context(self.home, self.environment)
        journal.unlink()
        journal.symlink_to(self.home / "config.toml")
        with self.assertRaises(OSError):
            fmt.selector_context(self.home, self.environment)

    def test_yes_sends_literal_elif_and_verified_link_beyond_old_excerpt(self):
        self.enable()
        self.source["custom_title"] = "Service rollout"
        self.messages.pop()
        response = ("**ELIF:** The service now works for your team. " + "Its measured limit is unchanged. " * 14
                    + "\n\nNeeds you: review PR42 before activation.\n[Review PR42](https://github.com/example/repo/pull/42)")
        self.publish(response)
        result = self.observe()
        self.assertEqual(result["state"], "sent")
        self.assertTrue(result["response_confirmed"])
        self.assertTrue(result["formatting_confirmed"])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.calls), 1)
        body = self.calls[0][1]
        self.assertIn(fmt.sanitize(response), body["text"])
        self.assertIn("Service rollout", body["text"])
        self.assertIn("Service rollout [automatic-animal]", body["text"])
        self.assertEqual([e["url"] for e in body["entities"] if e["type"] == "text_link"], ["https://github.com/example/repo/pull/42"])
        self.assertTrue(body["link_preview_options"]["is_disabled"])

    def test_no_and_invalid_model_are_quiet(self):
        self.enable()
        self.observe(False)
        self.assertEqual(self.calls, [])
        self.messages.append(self.message("u2", "user", "Any further useful result?"))
        self.publish("ELIF: A different actual result.", "a2")
        self.observe(request=lambda *_: {"model": "wrong"})
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.requests), 2)

    def test_linkless_selected_update_has_confirmed_heading_formatting(self):
        self.enable()
        result = self.observe()
        self.assertEqual(result["state"], "sent")
        self.assertTrue(result["response_confirmed"])
        self.assertTrue(result["formatting_confirmed"])
        self.assertEqual(result["link_entities"], 0)
        self.assertEqual(result["bold_entities"], 1)
        self.assertIn("🏷 Session: automatic-animal\n", self.calls[0][1]["text"])

    def test_selected_success_bypasses_old_duration_and_cooldown_only_for_completions(self):
        self.enable()
        self.assertEqual(self.observe()["state"], "sent")
        self.messages.append(self.message("u2", "user", "What is the next measured result?"))
        self.publish("ELIF: The second measured milestone is now ready, with its limit verified.", "a2")
        self.assertEqual(self.observe()["state"], "sent")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(policy.load_policy(self.home)["cooldown_seconds"], 300)
        self.assertNotIn("Grouped:", self.calls[-1][1]["text"])

    def test_direct_policy_cannot_accidentally_send_without_selector(self):
        self.enable()
        result = policy.notify(self.home, self.environment, lambda: {"text": "bypass"},
                               lambda *_: self.fail("Unclassified send"), "destination", min_seconds=0)
        self.assertEqual(result["state"], "selector_required")

    def test_policy_off_during_decision_prevents_send(self):
        self.enable()
        def turn_off(*_):
            policy.save_policy(self.home, {"completion_selector": "off", "events": {"completion": False}})
            return self.answer()
        self.observe(request=turn_off)
        self.assertEqual(self.calls, [])

    def test_selected_output_is_utf16_bounded_and_keeps_whole_original_targets(self):
        raw = "**ELIF:** " + "😀 useful fact " * 650 + "\n[Review](https://github.com/example/repo/pull/42)"
        environment = {**self.environment, "JCODE_HOOK_LAST_ASSISTANT_TEXT": raw}
        rendered = fmt.render_selected_message(environment)
        message = policy._message(rendered, "expanded", 0, selected=True)
        self.assertLessEqual(fmt.utf16_length(message["text"]), 4096)
        self.assertIn("…", message["text"])
        self.assertEqual([e["url"] for e in message["entities"] if e["type"] == "text_link"], ["https://github.com/example/repo/pull/42"])

    def test_errors_bypass_model_and_keep_existing_repeat_behavior(self):
        self.enable()
        self.environment.update(JCODE_HOOK_STATUS="error", JCODE_HOOK_ERROR="Current bounded test failure")
        self.observe()
        self.observe()
        self.assertEqual(self.requests, [])
        self.assertEqual(len(self.calls), 1)

    def test_explicit_attention_bypasses_clef_even_with_completions_disabled(self):
        self.enable()
        policy.save_policy(self.home, {"events": {"completion": False}})
        request = {"context": "One genuine owner choice remains.",
                   "needs_you": "Choose option A or B for this reviewed change.",
                   "recommendation": "A is recommended because it preserves the existing setup.",
                   "links": [{"label": "Review PR42", "url": "https://github.com/example/repo/pull/42"}]}
        def telegram(token, method, body):
            self.calls.append((method, body))
            return {**body, "message_id": 42}
        with patch.dict(os.environ, self.environment), patch.object(app.sys, "argv", ["jcode-telegram", "attention", "--key", "test:choice:revision1"]), patch.object(app.sys, "stdin", io.StringIO(json.dumps(request))), patch.object(app.sys, "stdout", io.StringIO()), patch.object(app, "api", side_effect=telegram), patch.object(selector, "process", side_effect=AssertionError("Attention must bypass Clef")):
            app.main()
        self.assertEqual(len(self.calls), 1)
        self.assertIn("Choose option A or B", self.calls[0][1]["text"])
        self.assertIn("🏷 Session: automatic-animal\n", self.calls[0][1]["text"])

    def test_selector_cli_queries_read_only_and_off_never_restores_unfiltered_pushes(self):
        self.enable()
        config_before = (self.home / "config.toml").read_bytes()
        command = [sys.executable, "-B", str(Path(app.__file__))]
        environment = {**os.environ, "JCODE_HOME": str(self.home)}
        queried = subprocess.run(command + ["selector"], env=environment, capture_output=True, text=True, check=True)
        result = json.loads(queried.stdout)
        self.assertEqual(result["mode"], "clef")
        self.assertNotIn("synthetic-decision-credential", queried.stdout)
        subprocess.run(command + ["selector", "off"], env=environment, capture_output=True, check=True)
        result = policy.load_policy(self.home)
        self.assertFalse(result["events"]["completion"])
        self.assertTrue(result["events"]["error"])
        self.assertEqual(result["completion_selector"], "off")
        self.assertEqual((self.home / "config.toml").read_bytes(), config_before)
        for arguments in (["selector", "--endpoint", "https://wrong.example"], ["policy", "--key-file", "x"], ["selector", "on"], ["selector", "off", "--min-seconds", "0"]):
            value = subprocess.run(command + arguments, env=environment, capture_output=True, text=True)
            self.assertEqual(value.returncode, 2)


if __name__ == "__main__":
    unittest.main()
