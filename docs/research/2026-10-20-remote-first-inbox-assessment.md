# Remote-first handoffs and Plannotator Inbox

**Assessment only.** Prepared October 20, 2026 (+08:00). Checked Jcode v0.99.0 (`774613c90751b6a26ae9eb6a27be6aff3f210062`), installed Plannotator 0.28.23, the current overlay and relevant skills. This review does not authorize Inbox setup, prompt or skill changes, or infrastructure actions.

## Recommendation

**Yes to remote-first handoffs. Yes to an Inbox trial. Not yet to making Inbox the main way Jcode receives instructions.**

The useful preference is “give me a link I can use from my own device,” not “you have no browser.” The agent can still use its browser to investigate and verify work. It should not assume you are watching its Chrome window, side panel or remote desktop.

Inbox could put questions, comments and review files in one place. The important limitation is the return journey: through generic MCP, the local tool connection Jcode can use, an Inbox reply does not automatically wake the originating Jcode session. That makes it promising for asynchronous feedback, but not yet a dependable replacement for the existing blocking-review path. [inbox-mcp]

Keep the roles simple:

| Need | Preferred route |
| --- | --- |
| Get your attention | Telegram, with the relevant verified action link |
| Review a plan, research or ADR | Repo Markdown and the existing private Plannotator review |
| Approve a PR or merge | GitHub, with the exact PR link |
| Answer a genuine small choice | Existing Plannotator question card; trial Inbox when reply retrieval is established |
| Authenticate | Supported service/device link, using `headless-links` |
| Handle an unavoidable desktop-only step | Explain the limitation and offer remote desktop as a fallback, not the default |

## What the session history supports

A bounded review used seven targeted searches, not a random sample or a failure-rate measurement. Automatic reminders, worker messages and tool receipts were excluded from explanation-quality judgments. Exact identifiers remain private rather than publishing transcripts.

- The October 18 owner requests about the missing PR91 alert and the later missing PR link establish a handoff problem worth addressing. They do not, by themselves, establish grouping or cooldown as the cause.
- Later October 18 requests explicitly preferred repo documents and Plannotator over a side panel, then asked for the Markdown review to be exposed through Tailscale. This supports a durable remote-access preference, not just a different summary style.
- Earlier WSLg/Chrome discussions concerned browser visibility and continuity. They are not evidence that browser tools should be removed or forbidden. The present request clarifies that remote desktop is possible but less desirable.
- Prior document reviews did return scoped feedback to this conversation through their background CLI jobs. That is a useful existing path to preserve while evaluating a shared Inbox.

This supports improving the handoff rule. It does not prove that labelling every session “headless” would improve behavior, or that Inbox would have prevented the historical missed alerts.

## Prompt and skills: a small change, not another manual

Jcode's base already favors non-interactive commands and sparse questions. It does not specify where an absent owner should receive a review. The installed overlay already covers linked attention, selective questions and no unsolicited side panels, but does not state the cross-device preference explicitly. [base] [overlay]

A possible addition is:

> Treat owner handoffs as remote-first, preferring verified action links over host-local windows.

This is a proposal, not installed wording. It adds 12 words to the current 307-word overlay, staying within its existing 320-word check. It states the preference without claiming the runtime has no GUI. It should not disable the agent's browser or turn all work into an approval request.

Use the existing skills selectively:

- **`headless-links`:** retain its authentication safeguards, real emitted URL, expiry handling and no repeated login attempts. Its broad references to approvals/cards should not be read as banning the Plannotator review cards you explicitly want.
- **`owner-review`:** keep the Jcode-specific receipt, exact revision, private URL, background completion and answer-scope procedure. Add a short routing note only if an Inbox trial is agreed.
- **`plannotator`:** use as an on-demand reference for Inbox and unusual review features. Its host-specific automatic plan hooks and reply-wake instructions must not be assumed to apply to Jcode.
- **Another skill:** not needed merely to say “remote-first.” An optional short `owner-inbox` procedure would be justified only after a working connection exists and its Jcode-specific retrieval steps prove useful. Do not paste the full reference into every prompt.

No core fork, compaction change or new summary model is needed for this preference.

## What Inbox can do, and what still needs a trial

The installed CLI exposes `plannotator inbox mcp`; its supported reply interface is the MCP tools, not a separate documented `inbox send/read` shell command. Tool discovery in this Jcode session returned no Plannotator tools. That establishes current availability here, not whether another session or machine has configured it.

Inbox supports threaded Markdown, attached review files, answerable questions and reading replies. Native question blocks already support choices, recommendations and free text, so a new questionnaire renderer is unnecessary. Inbox can distinguish genuinely stopped work from a question that only holds up one part of the job. Do not use that distinction to manufacture blockers. [inbox-mcp] [questions]

For a Jcode trial:

- Pass the actual originating `agent_session` and `project_path`. Retain returned thread/message identifiers, cursor and idempotency key. A generic thread name can intentionally join sessions, so do not rely on a vague title as the session boundary. This metadata correlates work; it is not an access-control boundary between your local agents.
- Read after independent work, or use bounded `wait_for_reply` calls when the answer is needed. Inbox defaults to 50 seconds; Jcode's MCP default is 30. A proposed 25-second wait avoids that mismatch without a global timeout change.
- Once a turn has ended, do not promise automatic continuation. A deliberate resume-and-read is required unless a separate wake path is implemented and verified. No new poller/router is recommended for this trial. [inbox-mcp] [mcp-timeout]

The existing per-document CLI review has a different return path: its owned background process ends when feedback is submitted and Jcode can receive that completion. Preserve it for blocking decisions rather than replacing a demonstrated path with an unverified one. [owner-review]

### Remote access and approval boundaries

Use native `inbox --tailscale` publication, never a manual proxy to its main listener. Inbox's native path checks the permitted Tailscale login and keeps MCP/control routes local. It differs from ordinary annotation's broader permitted-tailnet-peer boundary. Do not enable a remote terminal, take over port 443 or broaden the login allowlist casually. The process must stay alive, and stale owned mappings need scoped cleanup after a crash. [inbox-tailnet] [tailnet-checks] [remote-reviews]

The tool returns a local thread URL. That is not a usable remote handoff. The Telegram helper currently accepts a verified private root origin with the declared port, not arbitrary thread fragments. A first trial can link the verified Inbox root and name the project/thread clearly. Exact thread deep links would need a separately reviewed, narrow policy change. [inbox-mcp] [review-adr]

An Inbox acknowledgment or recorded decision is not blanket authorization to merge, deploy or change infrastructure. Keep material decisions in committed Y-statement ADRs and PR decisions in GitHub. Bind any answer to the actual question, revision and scope. Do not copy private login URLs or credentials into persistent Inbox attachments.

## Smallest useful next step

1. Consider the one-sentence preference independently of Inbox setup. Keep the just-approved explanation overlay otherwise stable.
2. If agreed, trial one project and one non-destructive owner question through a supported, on-demand MCP connection and native tailnet publication. Do not automatically connect unrelated agent products.
3. Keep per-document reviews for blocking decisions and GitHub for PR authority. Put only genuine questions or substantial handoffs in Inbox, not routine progress.
4. Expand only after the return path works in actual Jcode use. Adopting a persistent primary Inbox would revisit the deferral in ADR 0002 and merits its own scoped decision. This assessment does not enact it. [review-adr]

### Acceptance checks for that trial

| Requirement | Evidence needed before relying on it |
| --- | --- |
| No remote desktop required | Owner opens the actual HTTPS link on another tailnet device and sees the intended question |
| Useful choices and comments | Owner submits a choice plus a note; originating Jcode reads both unchanged |
| Correct session and revision | A reply is applied only to its intended session, question and scope; shared-thread visibility or stale/superseded questions do not authorize other work |
| Honest waiting and continuation | No reply remains pending; an ended turn requires the documented resume path, not an automatic-wake promise |
| No duplicate requests or approval spam | Reusing the same request key does not duplicate it; ordinary reversible work proceeds without an owner question |
| Safe exposure and fallback | MCP stays local; only the owned mapping is removed; GitHub remains a durable fallback |

**Observed now:** actual installed version/help, current tool availability, bounded session evidence and pinned implementation contracts. **Not performed:** starting or configuring Inbox, sending a trial question, owner-device access or an end-to-end Inbox reply. Those are explicitly future acceptance checks, not results inferred from documentation or synthetic tests.

## Sources

- [Installed Jcode base prompt][base], pinned to the checked CLI commit.
- [Inbox MCP contract][inbox-mcp], Plannotator v0.28.23: routing, questions, waits and return values.
- [Question block implementation][questions], the same version.
- [Inbox native Tailscale publication][inbox-tailnet] and [identity checks][tailnet-checks], the same version.
- [Jcode MCP timeout][mcp-timeout], pinned to the checked CLI commit.
- [Official remote-review guide][remote-reviews]. This page describes the older ordinary-review boundary; the pinned Inbox source takes precedence for Inbox-specific behavior.
- [Existing workflow][owner-review], [overlay][overlay] and [accepted ADR 0002][review-adr].

[base]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/prompt/system_prompt.md
[inbox-mcp]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-mcp.ts
[questions]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/core/question-block.ts
[inbox-tailnet]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-tailscale.ts
[tailnet-checks]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/shared/inbox/tailnet.ts
[mcp-timeout]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/mcp/client.rs#L47-L58
[remote-reviews]: https://docs.plannotator.ai/open-source/tailscale
[owner-review]: ../owner-workflow.md
[overlay]: ../../prompts/owner-workflow.md
[review-adr]: ../adrs/0002-private-owner-reviews.md
