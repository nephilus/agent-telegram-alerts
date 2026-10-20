# Owner review workflow

This optional workflow keeps Jcode core and compaction unchanged. The reviewed standing preferences live in [the overlay template](../prompts/owner-workflow.md); the publishing procedure lives in [owner-review](../skills/owner-review/SKILL.md). [ADR 0002](adrs/0002-private-owner-reviews.md) records the link trust boundary.

## Adopt once, not in every repo

Review the two templates before installing them. Their released copies are included under the virtual environment's `share/jcode-telegram-alerts/` directory:

- `prompts/owner-workflow.md` goes to `~/.jcode/prompt-overlay.md`.
- `skills/owner-review/SKILL.md` goes to `~/.jcode/skills/owner-review/SKILL.md`.

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

## Optional Inbox pilot

The owner chose **Questions only** for this repository's [bounded pilot](plans/2026-10-20-remote-first-inbox-pilot.md). Routine progress and completed-work summaries stay outside Inbox. This is not a cross-project default or permission for a permanent service. Approval-required reviews keep the existing document-review or GitHub route. These steps live in the repository checkout, not the wheel; the installed skill points back here.

For an explicitly authorized use:

1. Connect `plannotator inbox mcp` through Jcode's on-demand stdio connection. Set `PLANNOTATOR_INBOX_CONNECT=0` and `PLANNOTATOR_CWD` to this repository. Pass the originating `agent_session` and absolute `project_path` explicitly on message/reply calls. Do not add a persistent MCP entry or connect other agent products.
2. Reuse a compatible Inbox, recording process ownership and existing Serve mappings. Publish with native `inbox --background --tailscale` for this run, not a saved Settings toggle. Require the configured exact review host and declared port, verify the real HTTPS root and intended project/question, then use the existing checked Telegram handoff. Do not forward a returned localhost URL or thread fragment.
3. Ask only a genuine owner-dependent question, with context, choices, recommendation and room for a note. Save thread/message IDs, question revision, cursor and idempotency key privately. Keep working independently. Tell the owner to press **Send**, then resume this chat with **check my Inbox reply** if its turn has ended.
4. Use native `wait_for_reply` with the saved IDs and `timeout_seconds=25` at a useful boundary. Pending is not permission; do not poll continuously. This Jcode client exposes the actual reply in that tool's text, whereas `read_thread` displays counts. Match the exact question/revision before applying its scoped answer. Acknowledged, skipped, empty or stale responses do not settle the question. No automatic wake is available.
5. After resolution, preserve the messages and private receipt. Stop only the owned temporary process/publication, disconnect only the pilot MCP and verify other mappings remain intact. Never stop a reused service this pilot does not own.

## Boundaries and rollback

Use native `--tailscale`, never Funnel or a replacement mapping on port 443. Keep its remote terminal disabled and preserve existing Serve mappings. The host and review process must remain alive. Native cleanup removes the owned endpoint on normal completion; inspect the exact owned port after interrupted reviews, never reset all Serve configuration.

On failure, report it and preserve the receipt. Do not automatically retry ambiguous attention delivery. To roll back, disable the review host, restore the previous overlay privately, remove only this newly installed procedure if desired, and restore the prior released helper through the public hook installer. Leave credentials, foreign hooks, documents and other tailnet services intact.
