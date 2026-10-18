# ADR 0001: Explicit owner attention without a Jcode fork

Canonical location: `docs/adrs/`. The former path remains a compatibility pointer.

- Date: 2026-10-18
- Status: Accepted for a first-cut trial. This is not approval for unrelated project changes.

## Context

Routine Telegram summaries are useful and should remain quiet and concise. A short reply containing an approval link can be suppressed by the successful-turn duration threshold or completion cooldown. The native turn-end observer also does not guarantee delivery of a link mentioned earlier while a turn is waiting.

Making the agent ask about every implementation choice would undermine the autonomy the owner values. Rewriting a skill alone cannot repair rendering or delivery-policy failures.

## Decision

Keep routine alerts and Jcode core unchanged. Add one explicit `jcode-telegram attention --key REPO:DECISION:REVISION` command, accepting a bounded JSON object on stdin:

- `context`: the goal and why owner input is needed now.
- `needs_you`: the precise action or necessary choice.
- `recommendation`: the preferred option and reason, when applicable.
- `links`: up to three original, independently verified destinations and labels.

The command uses Jcode's runtime session identifier and existing Telegram credentials, URL policy, formatting verification and private storage helpers. It sends a fresh non-silent-requested message outside routine duration/cooldown/card rules, while respecting global disable and session filters. It confirms exact returned text/link entities before recording success. It does not interpret or execute an approval.

Use one stable key for one decision at one reviewed revision. Deduplicate acknowledged keys across sessions sharing the destination; explicit owner-requested `--resend` is the only forced resend. Retain at most 256 private fingerprint-only entries for 30 days, failing closed at active capacity. No automatic delivery retries or reminders.

Add a short prompt-overlay rule: work autonomously within delegated scope, publish before genuinely waiting, check the outcome, and continue independent safe work. Workers report to their coordinator. The command's help and README hold the detailed contract, not a new skill.

## Decisions presented to the owner

Major consequential choices should have a committed, published Proposed ADR in the owning repository, linked to the exact reviewed revision. The agent remains responsible for checking publication, reviewer access and safe disclosure. A local hash is not a remote review link.

For a smaller decision that genuinely requires owner preference, present two or three meaningful options with a recommendation and reason. Multiple available approaches alone are not an escalation trigger. Already-delegated reversible choices should proceed without asking.

An ADR records a decision or proposal. Writing or linking it does not authorize a production change, and documenting a delegated decision does not automatically require a new approval.

## Alternatives not selected

- Lower or disable all routine thresholds: increases noise without expressing owner attention explicitly.
- Depend on keywords in final prose: confuses explanation with an actual request and misses in-progress links.
- Add a local LLM, notification daemon, new reply poller or approval-buttons system: unnecessary for the first cut.
- Patch native Jcode to enforce final handoffs: stronger enforcement, but adds maintenance the owner does not want.

## Consequences and limits

The extension cannot force an agent to invoke the command or prove that an owner read the notification. Telegram and device mute settings still apply. Existing native remote-reply behavior is unchanged, not expanded.

Unsupported sensitive, signed/query/fragment, local/IP or non-443 targets remain rejected. A required rejected link is a visible failure, not silent success with a dead placeholder. Do not strip parameters to bypass this rule. Network timeouts are ambiguous and must not be automatically retried.

Attention fields have fixed size limits and oversized messages fail visibly instead of truncating the decision. Routine verbosity and completion policy remain untouched. Agent wording and key stability still affect the quality of the handoff.

## Trial acceptance and rollback

Exercise actual native Jcode, the installed release and Telegram: fresh short-turn attention, another request inside routine cooldown, duplicate suppression, one explicit resend, exact clickable revision targets, and a normal delegated task that does not ask a question. Validate that native credentials, foreign hooks, reply settings, thresholds and preferences remain unchanged.

To roll back, remove the marked prompt-overlay block and restore the previous released helper through its public hook installer. Do not delete native credentials, change remote-reply policy or modify Jcode core.
