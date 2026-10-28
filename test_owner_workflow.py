"""Offline template contracts, not live review/Telegram acceptance tests."""
from pathlib import Path
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
        cls.telegram_skill = (ROOT / "skills/telegram/SKILL.md").read_text()

    def require(self, text, phrases):
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_size_and_frontmatter(self):
        self.assertLessEqual(len(self.overlay.split()), 320)
        self.assertLessEqual(len(self.skill.split()), 1000)
        match = re.match(r'---\nname: owner-review\ndescription: "([^"\n]+)"\n---\n', self.skill)
        self.assertIsNotNone(match)
        description = match.group(1)
        self.assertLessEqual(len(description), 120)
        self.assertTrue(description.startswith("Scoped owner handoffs for ADRs"))
        self.assertIn("Inbox choices", description)
        self.assertLessEqual(len(self.inbox.split()), 600)
        self.assertLessEqual(len(self.telegram_skill.split()), 600)
        match = re.match(r'---\nname: telegram\ndescription: "([^"\n]+)"\n---\n', self.telegram_skill)
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1)), 120)

    def test_adr_policy_and_material_scope(self):
        self.assertIn("Frame ADR decisions as Y-statements", self.overlay)
        self.assertIn("desired qualities and accepted trade-offs", self.overlay)
        self.assertNotIn("<use case/user story>", self.overlay)
        self.assertNotIn("<use case/user story>", self.skill)
        self.require(self.skill, [
            "Use the `adr` companion skill for new or substantively updated material ADR content",
            "including its decision statement, status, alternatives and supporting evidence",
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
        self.require(self.skill, ["new, nonexistent result target", "completion notification when supported",
                                  "Add `--require-approval` only", "not ordinary document feedback or question answers"])

    def test_handoff_trust_and_result_contract(self):
        self.require(self.skill, [
            "originating agent/session", "available commit/revision identifier",
            "SHA-256 of the exact file", "background job identifier, result path",
            "configured attention integration for the trusted exact review host",
            "never silently trust/configure", "1024..65535", "GET only", "`/api/plan`",
            "expected document and exact snapshot", "Do not self-submit feedback",
            "do not use Funnel, remote terminals, or reset other mappings",
            "stable decision/revision key",
            "verified actual review URL and declared review port",
            "`telegram` owns command syntax, payload and delivery mechanics",
            "durable revision fallback for material ADRs",
            "Exit 0, delivery receipts and API acknowledgements are not approval",
            "An `annotated` answer may resolve its matching question; it cannot approve a plan",
            "Skipped, dismissed or empty responses remain unresolved",
            "reject stale results on mismatch", "without automatic re-review loops or broadened authority",
            "removed only the owned endpoint", "preserved all other mappings",
            ":::question", "Recommended:", "Reason:", "**Send answers**",
            "**Send feedback**", "**Approve** alone does not submit",
        ])

    def test_telegram_skill_describes_generic_attention_and_inbox_rewrites(self):
        self.require(self.telegram_skill, [
            "telegram-alerts attention", "does not require a Jcode session", "matching optional `JCODE_SESSION_ID`",
            "TELEGRAM_ALERTS_HOME", "registered `port` and `tailscale.url`",
            "http://localhost:<registered-port>", "http://127.0.0.1:<registered-port>",
            "path, query, and fragment", "TELEGRAM_ALERTS_INBOX_REGISTRY",
            "TELEGRAM_ALERTS_INBOX_BASE_URL", "omitted with a warning",
            "Do not automatically retry", "Use `--resend` only after an explicit owner request",
            "Put URLs only in `links`",
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
            "Read [references/inbox.md](references/inbox.md) before using Inbox",
            "configured and permitted by applicable instructions",
            "without a project opt-out or operational hold",
            "Reuse the configured `plannotator-inbox` MCP server; never duplicate servers",
            "`plannotator inbox --help`", "does not send progress/completion summaries",
            "assume automatic wake", "Keep approval-required actions on the existing review route",
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

    def test_inbox_reference_preserves_opt_in_and_safe_discovery(self):
        self.require(self.inbox, [
            "optional configured integration, not an assumed global grant",
            "Explicit project opt-outs forbid that project's calls",
            "Operational holds retain their scope",
            "Use the current agent's named MCP connection facility for the existing server",
            "Initialization/tool listing can start Inbox",
            "A machine-wide OFF hold",
            "Never test or connect an OFF service to check it",
            "Pass the actual originating `agent_session` and absolute `project_path` explicitly",
            "Do not pin one project/session in shared environment settings",
            "Do not assume the current MCP client supports automatic wake",
            "`timeout_seconds=25`", "Do not poll continuously",
            "actual returned reply text", "exact question/revision",
            "Acknowledged, skipped, empty or stale", "Workers report to their coordinator",
            "never stop it or remove its publication",
            "Clean up only owned temporary document-review resources",
        ])

    def test_inbox_connection_uses_configured_server_and_explicit_attribution(self):
        self.require(self.inbox, [
            "Reuse the configured `plannotator-inbox` MCP server",
            "the installed `plannotator inbox mcp`",
            "PLANNOTATOR_INBOX_CONNECT=0", "PLANNOTATOR_UPDATE_CHECK=0",
            "PLANNOTATOR_BROWSER=none", "PLANNOTATOR_AI=disabled",
            "PLANNOTATOR_INBOX_TAILSCALE=1",
            "Use the current agent's named MCP connection facility",
            "Pass the actual originating `agent_session` and absolute `project_path` explicitly",
            "Do not pin one project/session in shared environment settings",
        ])
        self.assertNotIn('"action": "connect"', self.inbox)

    def test_installed_skill_reference_is_declared_as_a_package_asset(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text())
        assets = config["tool"]["setuptools"]["data-files"]
        destination = "share/telegram-alerts/skills/owner-review/references"
        reference = "skills/owner-review/references/inbox.md"
        telegram_skill = "skills/telegram/SKILL.md"
        self.assertEqual(assets[destination], [reference])
        self.assertEqual(assets["share/telegram-alerts/skills/telegram"], [telegram_skill])
        self.assertTrue((ROOT / reference).is_file())
        self.assertTrue((ROOT / telegram_skill).is_file())
        self.assertIn("~/.jcode/skills/owner-review/references/inbox.md", self.workflow)
        packaged_reference = (ROOT / reference).read_text()
        self.assertIn("Initialization/tool listing can start Inbox", packaged_reference)
        self.assertIn("Never test or connect an OFF service to check it", packaged_reference)


if __name__ == "__main__":
    unittest.main()
