"""Offline template contracts, not live review/Telegram acceptance tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


class OwnerWorkflowTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / "prompts/owner-workflow.md").read_text()
        cls.skill = (ROOT / "skills/owner-review/SKILL.md").read_text()

    def require(self, text, phrases):
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_size_and_frontmatter(self):
        self.assertLessEqual(len(self.overlay.split()), 320)
        self.assertLessEqual(len(self.skill.split()), 800)
        match = re.match(r'---\nname: owner-review\ndescription: "([^"\n]+)"\n---\n', self.skill)
        self.assertIsNotNone(match)
        description = match.group(1)
        self.assertLessEqual(len(description), 120)
        self.assertTrue(description.startswith("Doc reviews and genuine owner-dependent choices:"))

    def test_global_policy_and_preserved_attention_guardrails(self):
        self.require(self.overlay, [
            "Make it right is the minimum", "Reuse existing code only when suitable",
            "repair or replace", "smallest coherent solution", "material intent, authority, scope",
            "docs/plans/YYYY-MM-DD-topic.md", "docs/research/YYYY-MM-DD-topic.md",
            "docs/adrs/NNNN-topic.md", "plans, research and ADRs for review through Plannotator over Tailscale",
            "side panels unless asked", "meaningful choices or Yes/No", "recommendation with why",
            "room for comments", "independently authorized work", "committed, published Proposed ADR",
            "Check receipt/failure", "stable key per reviewed decision/revision",
            "--resend only on explicit owner request", "never automatically retry ambiguous failure",
            "Workers report to their coordinator", "~/.jcode/skills/owner-review/SKILL.md",
            "read that file if unavailable in the skill catalog",
        ])
        self.assertNotIn("plannotator annotate", self.overlay)
        self.assertNotIn("--result-file", self.overlay)

    def test_native_command_is_non_strict_by_default(self):
        shell = re.search(r"```sh\n(.*?)\n```", self.skill, re.S).group(1)
        self.require(shell, ["env -u PLANNOTATOR_PORT", "-u PLANNOTATOR_AGENT_TERMINAL_REMOTE", "PLANNOTATOR_BROWSER=none",
                             "PLANNOTATOR_UPDATE_CHECK=0", "PLANNOTATOR_AI=disabled",
                             "plannotator annotate FILE --tailscale --gate --json --result-file NEW_PRIVATE_RESULT"])
        self.assertNotIn("--browser", shell)
        self.assertNotIn("--require-approval", shell)
        self.assertNotIn("timeout", shell)
        self.require(self.skill, ["new, nonexistent result target", "completion wake support",
                                  "--require-approval` only", "not ordinary document feedback or question answers"])

    def test_handoff_trust_and_result_contract(self):
        self.require(self.skill, [
            "originating Jcode session", "repository, document path, commit, SHA-256",
            "background job identifier, result path", "jcode-telegram review-host",
            "never silently trust/configure", "1024..65535", "GET only", "`/api/plan`",
            "expected document and exact snapshot", "Do not self-submit", "do not use Funnel",
            "--review-port PORT", "`context`, `needs_you`, optional `recommendation`",
            "`links` entries with `label` and `url`", "durable GitHub fallback",
            "Exit 0, delivery receipts and API acknowledgements are not approval",
            "cannot approve a plan", "Skipped, dismissed or empty", "reject stale results",
            "without automatic re-review loops", "removed only the owned endpoint",
            "preserved all other mappings", ":::question", "Recommended:", "Reason:",
            "**Send answers**", "**Send feedback**", "**Approve** alone does not submit",
        ])

    def test_templates_have_no_private_paths_or_real_hosts(self):
        for text in (self.overlay, self.skill):
            self.assertNotRegex(text, r"/(?:home|Users|tmp)/")
            self.assertNotRegex(text, r"https?://")
            hosts = re.findall(r"[\w.-]+\.ts\.net", text)
            self.assertTrue(all(host == "device.tailnet.ts.net" for host in hosts))
            self.assertNotIn("\u2014", text)


if __name__ == "__main__":
    unittest.main()
