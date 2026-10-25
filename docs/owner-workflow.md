# Owner review workflow

This optional workflow keeps Jcode core and compaction unchanged. The reviewed standing preferences live in [the overlay template](../prompts/owner-workflow.md); the publishing procedure lives in [owner-review](../skills/owner-review/SKILL.md). [ADR 0002](adrs/0002-private-owner-reviews.md) records the link trust boundary.

## Adopt once, not in every repo

Review the overlay and procedure before installing them. Their packaged copies are included under the virtual environment's `share/jcode-telegram-alerts/` directory:

- `prompts/owner-workflow.md` goes to `~/.jcode/prompt-overlay.md`.
- `skills/owner-review/SKILL.md` goes to `~/.jcode/skills/owner-review/SKILL.md`.
- Copy `skills/owner-review/references/inbox.md` beside it at `~/.jcode/skills/owner-review/references/inbox.md`. Preserve the relative layout so the installed procedure works without a repository checkout.

Back up existing files privately. Replace the superseded attention block rather than appending overlapping rules, and preserve unrelated instructions. This companion setup is explicit: package or hook installation does not overwrite agent instructions automatically. Keep the prior release and backups for rollback.

The global overlay owns the make-it-right quality bar and the shared `docs/plans/`, `docs/research/` and `docs/adrs/` layout. Repo `AGENTS.md` supplies project facts and commands, not a competing folder standard. The old `docs/adr/0001-explicit-attention-alerts.md` path remains a compatibility pointer to preserve published links.

For substantive replies, it asks for the practical outcome, why it matters and the main trade-off before implementation detail. It assumes a capable reader without project knowledge, not a beginner who needs every concept simplified. Requested technical depth, uncertainty and risks stay intact. It does not require ELI5 or TL;DR headings, extra explanation on routine completions, or new approval gates. The [approved change and bounded checks](plans/2026-10-20-plain-language-overlay.md) record the evidence and limits.

Normal installed Jcode `v0.98.1` reread an edited overlay in a resumed-session acceptance check. That does not mean every SDK/custom prompt path does so. Skill catalogs can remain cached: use a fresh session for new discovery, or read the installed procedure path if the current catalog cannot load it. Do not reload all unrelated skills or reduce compaction just to find this one.

## Trust only the intended review host

Review-link support is disabled by default. Explicitly configure the exact Tailscale device hostname you intend to publish, verified against that host's own Tailscale status, not copied from an untrusted message:

```sh
jcode-telegram review-host device.tailnet.ts.net
jcode-telegram review-host
```

The hostname above is illustrative. The setting stores one exact ASCII `device.tailnet.ts.net` name, not a wildcard or an entire tailnet. It is private extension state at `~/.jcode/notifications/telegram-review-policy.json`, not a change to native Telegram credentials, Tailscale ACLs or Serve configuration. Disable with `jcode-telegram review-host off`.

For a live native Plannotator review, pass its actual port explicitly:

```sh
jcode-telegram attention --key example/project:decision:reviewed-revision --review-port 19433 < attention.json
```

This port is illustrative too. Read the real HTTPS origin from the owned Plannotator process, verify that the intended document/revision is served, and put that exact URL in `links`. A declared review must include a matching link. The exception allows only that configured host, that declared port from 1024 through 65535, and the HTTPS root origin. It does not authorize paths, signed/query/fragment URLs, IPs, other hosts or automatic trust changes. Routine alert links keep the existing strict policy.

## Present work without turning every task into a question

Plans, research and ADRs are repo Markdown and are presented through Plannotator over Tailscale. A document review is not necessarily a work-stopping approval gate. Continue independent authorized work and ask only for missing owner intent, authority or consequential scope that investigation cannot establish.

Use existing Plannotator question cards for genuine small decisions. They include context, meaningful options or Yes/No, a recommendation with a reason, and comments/Other. No ADR is required for an ordinary small preference. Approved-with-notes feedback is guidance, not a reason to force endless repeat approvals.

The `owner-review` procedure describes the actual CLI invocation, private revision/result receipt, background process, URL verification and feedback checks. `--require-approval` is for an explicitly approval-required scope. For ordinary annotations or question answers, omit it and inspect the structured result: exit `0` alone is not approval. A skipped/unanswered/dismissed card does not settle a choice.

Telegram gets attention. The answer belongs in Plannotator or the GitHub PR, not an uncorrelated Telegram Yes/No. An API acknowledgment is delivery evidence, not evidence the owner read or approved anything. No extra poller or automatic command execution is installed.

## How agents discover Inbox

The overlay makes Inbox the global default for genuine owner-dependent small decisions. The existing `owner-review` skill advertises Inbox questions and loads its [packaged reference](../skills/owner-review/references/inbox.md) on demand. The native `plannotator inbox --help` supplies feature/tool details. No new skill, Jcode core change or large system-prompt manual is needed.

This follows [Plannotator's documented pattern](https://plannotator.ai/docs/reference/inbox/): a tool connection, a short reminder and the agent guide. Jcode uses the generic stdio MCP route, not the Claude Code/Pi/OpenCode native integrations. Its replies require explicit retrieval rather than automatic wake.

## Global native MCP, authorized 2026-10-21

The owner explicitly requested global Inbox enablement on 2026-10-21. This supersedes the earlier pilot's OFF/no-persistent-entry restriction, not unrelated operational holds or the questions-only policy. Installation is not enablement for other adopters: this package still never writes MCP settings or starts Inbox automatically.

Merge this native entry into the existing `servers` object in `~/.jcode/mcp.json`, preserving all other servers. Resolve the actual installed binary path when PATH is unreliable. No wrapper, additional package or custom supervisor is required:

```json
{
  "servers": {
    "plannotator-inbox": {
      "command": "plannotator",
      "args": ["inbox", "mcp"],
      "env": {
        "PLANNOTATOR_INBOX_CONNECT": "0",
        "PLANNOTATOR_UPDATE_CHECK": "0",
        "PLANNOTATOR_BROWSER": "none",
        "PLANNOTATOR_AI": "disabled",
        "PLANNOTATOR_INBOX_TAILSCALE": "1"
      },
      "shared": true,
      "timeout_secs": 30
    }
  }
}
```

Native MCP initialization starts/reuses the machine's background Inbox. The Tailscale environment setting requests native owner-checked publication on startup, not Funnel or a manual proxy. For an already-running local-only Inbox, explicitly use native `plannotator inbox --background --tailscale`. Preserve other Serve mappings. A project opt-out prevents project calls, not global service startup. A machine-wide OFF hold needs its auto-connect entry disabled before discovery.

Fresh Jcode processes read the global entry. An already-running process may have cached its earlier server list: connect only this server with the same native settings, or wait for the next normal Jcode start. Do not restart shared Jcode services for this change. `jcode mcp list` checks configuration; `jcode mcp test plannotator-inbox` performs real initialization/tool discovery and therefore can start Inbox. Do not run it during an Inbox OFF hold. Do not reload unrelated servers.

Pass the originating `agent_session` and absolute `project_path` on every applicable call. Do not freeze one project or session in a shared server environment. Keep **Questions only**: routine progress and completed-work summaries stay outside Inbox. Approval-required reviews retain the existing document-review or GitHub route.

For a genuine question, follow the reference's context/choices/recommendation, configured exact review host, verified HTTPS root and checked Telegram attention handoff. Never forward a localhost URL or thread fragment. Save thread/message IDs, question revision, cursor and idempotency key privately. Tell the owner to press **Send**, then return to the originating chat with **check my Inbox reply** if its turn ended.

Use `wait_for_reply` with saved IDs and `timeout_seconds=25` at useful boundaries; do not poll continuously. No automatic wake is available in generic Jcode MCP. Read actual reply text and match the exact question/revision. Acknowledged, skipped, empty or stale replies are not approval. Leave the shared Inbox available after resolution rather than stopping it after each question.

The [bounded pilot](plans/2026-10-20-remote-first-inbox-pilot.md) remains archived, including the owner's actual Questions-only answer. Global enablement does not reopen its messages. To roll back this setup, remove only the Inbox MCP entry and restore the matching private guidance backup. Stop the shared service only with authority and after checking other users; never reset unrelated Serve mappings.

### Observed setup checks, 2026-10-21

| Requirement | Actual check and result |
| --- | --- |
| Global native configuration | `jcode mcp list` recognized Inbox; all five preexisting server definitions remained identical. |
| Working tool connection | `jcode mcp test plannotator-inbox` initialized, discovered eight tools and disconnected cleanly. The current session connected separately and completed `list_decisions` with explicit originating session/project. |
| Remote-first availability | Native startup published its owner-checked Tailscale endpoint. An HTTPS GET returned the Inbox UI with status 200 on the configured exact review host; all preexisting Serve mappings were preserved. |
| Discoverable installed guidance | Real wheel, source archive and fresh installation contained three byte-exact guidance assets. The live copies matched, the relative skill reference resolved, and only `owner-review` was reloaded. |
| Regression and preservation | The 251-test suite passed with one existing skip. Four protected settings files stayed byte-identical; no runtime Python modules or dependencies changed. |

No new owner question, Telegram test message, automatic reply wake or model benchmark was introduced. Another device's access and a new owner reply were not exercised in this setup check. Existing chats may need the scoped connection described above; no shared Jcode restart was performed.

## Boundaries and rollback

Use native `--tailscale`, never Funnel or a replacement mapping on port 443. Keep its remote terminal disabled and preserve existing Serve mappings. The host and review process must remain alive. Native cleanup removes the owned endpoint on normal completion; inspect the exact owned port after interrupted reviews, never reset all Serve configuration.

On failure, report it and preserve the receipt. Do not automatically retry ambiguous attention delivery. To roll back, disable the review host, restore the previous overlay privately, remove only this newly installed procedure if desired, and restore the prior released helper through the public hook installer. Leave credentials, foreign hooks, documents and other tailnet services intact.
