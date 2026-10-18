# ADR 0002: Private owner reviews without a core fork

- Date: 2026-10-18
- Status: Proposed record of the implementation authorized by the owner after reviewing assessment `65d18aa`. Review this document through Plannotator over Tailscale. This does not authorize unrelated infrastructure changes.
- Supersedes ADR 0001 only for its blanket non-443 attention-link restriction and absence of an operational review skill.

## Context

The real assessment review returned feedback to the originating Jcode session and cleaned up its owned Serve mapping. Telegram attention could not deliver its non-443 review URL. Routine summaries must remain quiet, while explicit handoffs need a usable action link. Native Telegram replies do not route to ordinary sessions.

The owner wants a make-it-right minimum, one cross-repo document standard and selective questions, not the least disruptive patch at any cost or a mandatory interview.

## Decision

Keep Jcode core, compaction, native reply settings and routine output-link policy unchanged. Use one short global overlay for standing preferences and `owner-review` for the publishing procedure. Plans, research and ADRs use `docs/plans/`, `docs/research/` and `docs/adrs/`, with the same naming convention across repos. Repository `AGENTS.md` supplies project facts, not alternate folder rules. Preserve old published ADR links with a pointer rather than deleting their destination.

Add an **attention-only**, disabled-by-default review-link exception:

1. `jcode-telegram review-host HOST` explicitly stores one exact ASCII `device.tailnet.ts.net` hostname in private local extension settings. No wildcard, IP, scheme, port or path is a trusted host. `review-host` queries; `review-host off` disables.
2. Every non-443 handoff declares `attention --review-port PORT`, an integer from 1024 through 65535. Its URL must be the HTTPS root origin of that exact host and port. A declared review must contain that matching link.
3. Preserve credential, known-secret, control/Unicode, escape, query, fragment and length restrictions. Other GitHub links may accompany a review. Routine extraction and `safe_url` do not inherit this exception.
4. Validation remains offline. The agent separately verifies the actual URL and exact document snapshot issued by native Plannotator; syntax acceptance is not reachability or approval.

Use native `plannotator annotate --tailscale`, an owned background process and private revision/result receipt. Explicitly keep the remote terminal disabled. Preserve other Serve mappings. Capture its actual URL, verify HTTPS and `/api/plan`, then publish attention and check confirmation. Keep the host alive. No Funnel, second Telegram poller, generic command router, local summarizer or Inbox integration is added.

A genuinely owner-dependent small choice uses the existing question cards with context, options, recommendation/reason and comments. Ordinary facts are investigated and authorized reversible work continues. Document presentation does not make every document a blocking approval gate. Required approvals remain bound to the reviewed revision and exact scope.

## Alternatives

- Allow all private hosts or ports globally: unnecessarily broadens routine disclosure and hides the handoff boundary.
- Take over HTTPS 443: may replace unrelated serving configuration and is not needed.
- Add a wake/router/Inbox framework: deferred until a demonstrated asynchronous need justifies it.

## Checks and rollback

Test hostile URLs, malformed/private settings, explicit-port mismatch, missing links and the unchanged routine filter. Run the full suite and actual installed CLIs. Exercise native Jcode autonomous work, skill discovery and a real Plannotator/Telegram handoff. Record owner-device/answer return separately from API acknowledgment.

Rollback by disabling `review-host`, restoring the private overlay backup and prior released launchers/hooks, and removing only this newly installed skill if needed. Preserve credentials, foreign hooks, documents, results and unrelated Serve mappings.
