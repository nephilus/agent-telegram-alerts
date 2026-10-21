---
name: owner-review
description: "ADR writing, doc reviews and owner-dependent choices: Inbox questions, scoped reviews and correlated feedback."
---

# Owner review

The global overlay supplies policy and triggers. This skill supplies mechanics, not a second policy copy. Reuse the installed Plannotator reference for uncommon flags and result/question schemas. Do not introduce a router or permanent service.

## Prepare the scoped revision

Identify document feedback, a question, or a specific approval-required action. State exactly what a response authorizes and what remains outside scope. For material decisions, commit and publish the Proposed ADR first, retaining a durable GitHub revision link as fallback alongside the live review URL. Do not guess either link.

### ADR decision statement

For new or substantively updated material ADRs, open **Decision** with the long-form Y-statement:

> In the context of <use case/user story>, facing <concern>, we decided for <option> and neglected <other options>, to achieve <system qualities/desired consequences>, accepting <downside/undesired consequences>, because <additional rationale>.

Keep **Status** and useful supporting context/evidence. Name rejected alternatives and explain why; replace every placeholder with concrete project facts. Preserve historical ADRs unless a substantive change already calls for updating them. Routine reversible choices remain implementation details, not new ADRs or approval gates.

### Review receipt and small choices

Record the originating Jcode session, repository, document path, commit, SHA-256 of the exact file, review scope and stable decision/revision key in a private receipt. Retain the eventual actual URL, background job identifier, result path and delivery outcome there. Keep credentials and private receipt content out of repository documents.

For a small choice, include context, meaningful alternatives, recommendation/reason and room for comments in the relevant note. Native question syntax:

```markdown
:::question
Which approach should this scoped change use?

Context: Only the owner can decide this preference. Comments are welcome.

- [ ] A: Preserve the current behavior
- [ ] B: Adopt the proposed behavior

Recommended: A: Preserve the current behavior
Reason: It avoids changing the established workflow.
:::
```

## Host and verify

Create a private existing result directory and choose a new, nonexistent result target. Start the installed command through Jcode's background execution with completion wake support, without a fixed timeout that kills a pending review:

```sh
env -u PLANNOTATOR_PORT -u PLANNOTATOR_AGENT_TERMINAL_REMOTE PLANNOTATOR_BROWSER=none PLANNOTATOR_UPDATE_CHECK=0 PLANNOTATOR_AI=disabled \
  plannotator annotate FILE --tailscale --gate --json --result-file NEW_PRIVATE_RESULT
```

Never prefix `--browser` before `annotate`: that parser combination is broken. Add `--require-approval` only for the explicitly scoped approval-required action, not ordinary document feedback or question answers. Keep host and process alive, use native background wait/wake, and continue independent authorized work.

Capture the actual HTTPS URL printed by this job. Query `jcode-telegram review-host` for the configured exact host. If unset/off or mismatched, stop this handoff and report the trust prerequisite; never silently trust/configure each observed URL host. Check the root-origin HTTPS URL has that exact `device.tailnet.ts.net` host and the declared port in 1024..65535. Preserve the actual URL verbatim, including any query rather than guessing or stripping it. If incompatible with attention validation, report failure rather than rewrite it.

Before handoff, use GET only to verify real HTTPS `/api/plan` serves the expected document and exact snapshot. Do not self-submit feedback. Native Tailscale Serve trusts permitted tailnet peers; do not use Funnel, remote terminals, or reset other mappings. Record preexisting mappings for cleanup comparison.

## Notify and resolve

Send `jcode-telegram attention` using the reviewed revision's stable `--key` and per-send `--review-port PORT`. Its JSON contains only `context`, `needs_you`, optional `recommendation`, and `links` entries with `label` and `url`. Include the actual review link and, for material ADRs, the durable GitHub fallback. Check the receipt/failure, not just command launch. Follow the overlay's retry and coordinator guardrails.

For question answers or annotations, tell the owner to use **Send answers** or **Send feedback** as applicable; **Approve** alone does not submit those responses.

Read this job's actual returned decision/answer and atomically published private result, checking exit status and publication success too. Exit 0, delivery receipts and API acknowledgements are not approval. An `annotated` answer may resolve its matching question but cannot approve a plan. Skipped, dismissed or empty responses remain unresolved. Strict actions require an explicit `approved` result for that exact scope/revision. A plan approval does not authorize merging, deployment or destructive actions.

Before applying feedback, recompute the file hash and reject stale results on mismatch. Apply approved-with-notes clarifications without automatic re-review loops; changed material scope requires its own decision. Persist outcome and unresolved dependencies for the originating session. After completion verify native cleanup removed only the owned endpoint and preserved all other mappings. Report cleanup failures without broad reset commands.

## Inbox questions

For owner-enabled projects, read [references/inbox.md](references/inbox.md) before connecting or retrieving replies. Read `plannotator inbox --help` for features. Questions only, not progress/completion summaries. Keep approval-required actions on the existing review route. No permanent service, automatic wake or cross-project default. Closed or held Inboxes stay off.
