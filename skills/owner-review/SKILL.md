---
name: owner-review
description: "Scoped owner handoffs for ADRs, document reviews and owner-dependent Inbox choices, with exact-revision correlation."
---

# Owner review

The applicable project and user instructions supply policy and triggers. This skill owns review policy, scope and exact-revision correlation, not a second copy of those instructions. Use the `abstract` companion skill for summary writing, `adr` for ADR content, `plannotator-annotate` for document UI mechanics and `telegram` for attention delivery. Skill names identify companion instructions; use the current agent's skill-loading mechanism. The commands below are for an optional configured Plannotator/Tailscale integration. Its generic vendor advice does not override these scope and authorization boundaries. Reuse the installed Plannotator reference for uncommon flags and result/question schemas. Do not introduce a router or custom service.

## Prepare the scoped revision

Identify document feedback, a question, or a specific approval-required action. State exactly what a response authorizes and what remains outside scope. For material decisions, retain a durable published revision link for the Proposed ADR as fallback alongside the live review URL, using the repository's authorized publication workflow. If publication is not authorized, report that prerequisite rather than publishing or claiming the handoff is complete. GitHub is an optional configured hosting integration, not a requirement. Do not guess either link.

### ADR content

Use the `adr` companion skill for new or substantively updated material ADR content, including its decision statement, status, alternatives and supporting evidence. Routine reversible choices remain implementation details, not new ADRs or approval gates.

### Review receipt and small choices

Record the originating agent/session, repository, document path, available commit/revision identifier, SHA-256 of the exact file, review scope and stable decision/revision key in a private receipt. Retain the eventual actual URL, background job identifier, result path and delivery outcome there. Keep credentials and private receipt content out of repository documents.

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

Use the `plannotator-annotate` companion skill for the document UI, subject to the hosting, trust and exact-revision safeguards below. Preserve this job's actual stdout URL and result correlation.

Create a private existing result directory and choose a new, nonexistent result target. Start the installed command through the current agent's background execution facility, using completion notification when supported, without a fixed timeout that kills a pending review:

```sh
env -u PLANNOTATOR_PORT -u PLANNOTATOR_AGENT_TERMINAL_REMOTE PLANNOTATOR_BROWSER=none PLANNOTATOR_UPDATE_CHECK=0 PLANNOTATOR_AI=disabled \
  plannotator annotate FILE --tailscale --gate --json --result-file NEW_PRIVATE_RESULT
```

Never prefix `--browser` before `annotate`: that parser combination is broken in the referenced integration. Check installed help for version-specific syntax. Add `--require-approval` only for the explicitly scoped approval-required action, not ordinary document feedback or question answers. Keep host and process alive, use supported background wait/notification facilities, and continue independent authorized work. Do not promise automatic wake when unavailable.

Capture the actual HTTPS URL printed by this job. Query the configured attention integration for the trusted exact review host. If unset/off or mismatched, stop this handoff and report the trust prerequisite; never silently trust/configure each observed URL host. For the configured Tailscale integration, check the root-origin HTTPS URL has that exact `device.tailnet.ts.net` host and the declared port in 1024..65535. Preserve the actual URL verbatim, including any query rather than guessing or stripping it. If incompatible with attention validation, report failure rather than rewrite it.

Before handoff, use GET only to verify real HTTPS `/api/plan` serves the expected document and exact snapshot. Do not self-submit feedback. Native Tailscale Serve trusts permitted tailnet peers; do not use Funnel, remote terminals, or reset other mappings. Record preexisting mappings for cleanup comparison.

## Notify and resolve

Use the `abstract` companion skill to write the handoff summary and `telegram` to deliver attention through the configured notification integration with the reviewed revision's stable decision/revision key, verified actual review URL and declared review port. Include the durable revision fallback for material ADRs. `telegram` owns command syntax, payload and delivery mechanics; follow its installed CLI reference rather than duplicating it here. Retain the actual receipt or failure in the private review receipt, not just command launch. Follow `telegram`'s retry guardrails. Workers report to their coordinator rather than duplicating owner requests.

For question answers or annotations, tell the owner to use **Send answers** or **Send feedback** as applicable; **Approve** alone does not submit those responses.

Read this job's actual returned decision/answer and atomically published private result, checking exit status and publication success too. Exit 0, delivery receipts and API acknowledgements are not approval. An `annotated` answer may resolve its matching question; it cannot approve a plan. Skipped, dismissed or empty responses remain unresolved. Strict actions require an explicit `approved` result for that exact scope/revision. A plan approval does not authorize merging, deployment or destructive actions.

Before applying feedback, recompute the file hash and reject stale results on mismatch. Approved notes may be incorporated when they request a scoped clarification, without automatic re-review loops or broadened authority; changed material scope requires its own decision. Persist outcome and unresolved dependencies for the originating session. After completion verify native cleanup removed only the owned endpoint and preserved all other mappings. Report cleanup failures without broad reset commands.

## Inbox questions

Read [references/inbox.md](references/inbox.md) before using Inbox. Use it only when configured and permitted by applicable instructions, without a project opt-out or operational hold. Reuse the configured `plannotator-inbox` MCP server; never duplicate servers. Read `plannotator inbox --help` for the installed optional integration. This question workflow does not send progress/completion summaries or assume automatic wake. Keep approval-required actions on the existing review route.
