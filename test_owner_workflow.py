"""Offline template contracts, not live review/Telegram acceptance tests."""
from pathlib import Path
import json
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent


class OwnerWorkflowTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / "prompts/owner-workflow.md").read_text()
        cls.skill = (ROOT / "skills/owner-review/SKILL.md").read_text()
        cls.workflow = (ROOT / "docs/owner-workflow.md").read_text()
        cls.inbox = (ROOT / "skills/owner-review/references/inbox.md").read_text()

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
        self.assertTrue(description.startswith("ADR writing, doc reviews and owner-dependent choices:"))
        self.assertIn("Inbox questions", description)
        self.assertLessEqual(len(self.inbox.split()), 600)

    def test_adr_y_statement_and_material_scope(self):
        self.assertIn("Frame ADR decisions as Y-statements", self.overlay)
        self.assertIn("desired qualities and accepted trade-offs", self.overlay)
        self.assertNotIn("<use case/user story>", self.overlay)
        statement = (
            "> In the context of <use case/user story>, facing <concern>, "
            "we decided for <option> and neglected <other options>, "
            "to achieve <system qualities/desired consequences>, "
            "accepting <downside/undesired consequences>, because <additional rationale>."
        )
        self.assertIn(statement, self.skill)
        self.require(self.skill, [
            "new or substantively updated material ADRs", "open **Decision**",
            "Keep **Status**", "supporting context/evidence",
            "Name rejected alternatives and explain why", "replace every placeholder",
            "Preserve historical ADRs unless a substantive change",
            "Routine reversible choices remain implementation details",
            "not new ADRs or approval gates",
        ])

    def test_global_policy_and_preserved_attention_guardrails(self):
        self.require(self.overlay, [
            "Make it right:", "Reuse suitable code",
            "repair or replace", "smallest coherent solution", "material intent, authority, scope",
            "docs/plans/YYYY-MM-DD-topic.md", "docs/research/YYYY-MM-DD-topic.md",
            "docs/adrs/NNNN-topic.md", "Present documents that warrant owner review through Plannotator over Tailscale",
            "Presentation is not a blanket approval gate",
            "side panels unless asked", "meaningful choices or Yes/No", "recommendation with why",
            "room for comments", "independently authorized work", "committed, published Proposed ADR",
            "Check receipt/failure", "stable key per reviewed decision/revision",
            "--resend only on explicit owner request", "never automatically retry ambiguous failure",
            "Workers report to their coordinator", "~/.jcode/skills/owner-review/SKILL.md",
            "read that file if unavailable in the skill catalog",
            "Treat owner handoffs as remote-first, preferring verified action links over host-local windows.",
        ])
        self.assertNotIn("plannotator annotate", self.overlay)
        self.assertNotIn("--result-file", self.overlay)

    def test_plain_language_preserves_depth_and_autonomy(self):
        self.require(self.overlay, [
            "Explain substantive replies to a capable reader who does not know this system",
            "practical outcome or recommendation, why it matters, and the main trade-off",
            "Describe what unfamiliar components do before naming them",
            "concrete everyday language", "technical detail when requested or necessary",
            "Preserve risks and uncertainty, and stay concise",
            "Choose sensible reversible defaults and continue",
            "Ask only when material intent, authority, scope or consequences remain unresolved",
        ])
        self.assertNotIn("ELI5", self.overlay)
        self.assertNotIn("TL;DR", self.overlay)

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
        for text in (self.overlay, self.skill, self.inbox):
            self.assertNotRegex(text, r"/(?:home|Users|tmp)/")
            self.assertNotRegex(text, r"https?://")
            hosts = re.findall(r"[\w.-]+\.ts\.net", text)
            self.assertTrue(all(host == "device.tailnet.ts.net" for host in hosts))
            self.assertNotIn("\u2014", text)

    def test_inbox_discovery_preserves_questions_only_opt_in(self):
        self.assertIn("prefer Plannotator Inbox when enabled, otherwise a question card", self.overlay)
        self.require(self.skill, [
            "owner-enabled projects", "[references/inbox.md](references/inbox.md)",
            "`plannotator inbox --help`", "Questions only, not progress/completion summaries",
            "approval-required actions on the existing review route",
            "No permanent service, automatic wake or cross-project default",
            "Closed or held Inboxes stay off",
        ])
        self.assertNotIn("repository checkout's", self.skill)
        self.require(self.workflow, [
            "**Questions only**", "completed-work summaries stay outside Inbox",
            "on-demand stdio", "PLANNOTATOR_INBOX_CONNECT=0", "PLANNOTATOR_CWD",
            "`agent_session`", "`project_path`", "configured exact review host",
            "localhost URL or thread fragment", "question revision, cursor and idempotency key",
            "**Send**", "**check my Inbox reply**", "`timeout_seconds=25`",
            "do not poll continuously", "exact question/revision",
            "Acknowledged, skipped, empty or stale", "No automatic wake",
            "Never stop a reused service this pilot does not own",
            "Installation is not enablement", "without a discovery smoke test",
        ])

    def test_inbox_reference_does_not_start_discovery_during_hold(self):
        self.require(self.inbox, [
            "owner or project instructions explicitly permit Inbox use and startup",
            "An installed binary, visible tool or this skill alone is not permission",
            "operational hold stays off until explicitly released",
            "Do not connect, run `jcode mcp test`",
            "even MCP initialization and tool listing start it",
            "Do not add permanent MCP configuration",
            "actual originating `agent_session` and absolute `project_path`",
            "**no automatic wake**", "`timeout_seconds=25`", "Do not poll continuously",
            "actual returned reply text", "exact question/revision",
            "Acknowledged, skipped, empty or stale", "Workers report to their coordinator",
            "Never stop a reused service you do not own",
        ])

    def test_inbox_connection_example_is_on_demand_and_project_explicit(self):
        example = re.search(r"```json\n(.*?)\n```", self.inbox, re.S).group(1)
        connection = json.loads(example)
        self.assertEqual(connection["action"], "connect")
        self.assertEqual(connection["args"], ["inbox", "mcp"])
        self.assertEqual(connection["env"]["PLANNOTATOR_INBOX_CONNECT"], "0")
        self.assertEqual(connection["env"]["PLANNOTATOR_CWD"], "ABSOLUTE_PROJECT_PATH")
        self.assertEqual(connection["env"]["PLANNOTATOR_AI"], "disabled")
        self.assertNotIn("url", connection)

    def test_installed_skill_reference_is_declared_as_a_package_asset(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text())
        assets = config["tool"]["setuptools"]["data-files"]
        destination = "share/jcode-telegram-alerts/skills/owner-review/references"
        reference = "skills/owner-review/references/inbox.md"
        self.assertEqual(assets[destination], [reference])
        self.assertTrue((ROOT / reference).is_file())
        self.assertIn("~/.jcode/skills/owner-review/references/inbox.md", self.workflow)


if __name__ == "__main__":
    unittest.main()
