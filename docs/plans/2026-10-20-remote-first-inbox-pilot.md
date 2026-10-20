# Remote-first handoffs: a small Inbox pilot

**Status: Approved; pilot awaiting the owner round trip.** October 20, 2026 (+08:00). The owner approved [the original execution revision][approved-revision]. The scope below is retained; observed results and remaining checks are recorded at the end.

## Outcome and approval scope

You should receive a useful Telegram link, open the question on your own device, choose an answer or leave a comment, and have Jcode retrieve the right response without confusing it with permission for other work.

**Approve authorizes the three stages below:** the exact remote-first sentence, a bounded Inbox pilot for this repository on the existing host, and the small procedure/documentation updates needed to use that pilot. It includes one real owner question and its checked Telegram handoff. It does **not** authorize merging PRs, deployments, infrastructure changes, connecting other agent products, a permanent background service, automatic session wake or making Inbox the default across projects. The owner need not approve every reversible implementation detail again.

## 1. State the preference, preserve autonomy

Add this sentence to the document-presentation paragraph of `prompts/owner-workflow.md` and the live overlay, after keeping a private rollback copy:

> Treat owner handoffs as remote-first, preferring verified action links over host-local windows.

This takes the current overlay from 307 to 319 words, within the existing 320-word check. Change nothing else about its explanation level, autonomous work or question threshold. Browser tools remain available for investigation. Remote desktop is an explained fallback, not the normal owner handoff.

Check the exact source/live match, existing guidance tests and archive packaging. Exercise an actual fresh and resumed Jcode session: present a supplied verified action link without opening a local window for the owner, then complete an authorized small edit without asking an unnecessary question. Keep notifications disabled for these isolated checks.

## 2. Prove one Inbox round trip

Use `jcode-telegram-alerts` as the pilot project, not the lab infrastructure repositories.

1. Record installed versions, existing Inbox ownership, protected settings and Tailscale Serve mappings privately. Reuse a compatible existing Inbox rather than starting a conflicting one; never stop one this pilot does not own.
2. Connect the installed `plannotator inbox mcp` through Jcode's supported on-demand tool connection. Verify tool discovery before adding any permanent configuration. Set `PLANNOTATOR_INBOX_CONNECT=0` and the project working directory explicitly. Do not let Inbox connect other agents or add instructions to their files. [inbox]
3. Publish through native `inbox --background --tailscale`, with auto-connect still disabled. Verify the actual emitted HTTPS root, intended project/thread and native permitted-login boundary. Keep control tools local, remote terminals off, existing host trust unchanged and other Serve mappings intact. No proxy, Funnel, port-443 takeover or broader allowlist. If native publication cannot satisfy those boundaries, retain the existing review route rather than weaken them. [tailnet]
4. Post one question with choices, a recommendation and room for a note: **Should this pilot put only questions in Inbox, or also substantial completed-work summaries?** Recommend questions only initially to keep noise low. This is a presentation preference, not approval for production work, and unrelated work continues while it is unanswered.
5. Pass explicit originating `agent_session` and `project_path`. Keep thread/message IDs, cursor, stable idempotency key and the question/revision binding in a private receipt. These fields correlate messages; they are not isolation between local agents. Attach only the relevant non-sensitive project document.
6. Before handoff, query `jcode-telegram review-host` and require the emitted Inbox HTTPS root to match that configured exact host and the declared `--review-port`. If trust is unset or mismatched, stop rather than configure it implicitly. Send one Telegram attention message with the verified root, clear project/question label and stable revision key. Keep thread fragments out of the URL. Check acknowledgement; do not automatically retry an ambiguous delivery.
7. The owner opens the link on another tailnet device, selects an option, optionally adds a note and presses **Send**. Jcode retrieves both through the supported tools and applies only that preference. A saved pick, acknowledgment, empty response or skipped question is not the answer. [inbox-source]

### How replies reach Jcode

While Jcode is working, read at a useful task boundary or use a **25-second** `wait_for_reply`. A timeout means pending, not permission or failure. Avoid continuous polling. If the turn has ended, the owner can resume it with “check my Inbox reply”; Jcode reads the saved thread using its receipt. No automatic wake is promised. Keep the existing per-document review for decisions that must reliably return before work proceeds. [inbox-source] [mcp-timeout]

## 3. Keep only what passes

Run the acceptance checks below on the real installed interfaces. Record results, including failures, in this plan after execution. Add a short optional-Inbox section to the existing `owner-review` procedure and `docs/owner-workflow.md` only once the return path works. Keep the broader `plannotator` skill as a reference and `headless-links` for authentication. No new skill, command wrapper, router, summarizer or compaction change is planned.

| Check | Required observation |
| --- | --- |
| Remote access | Owner sees the intended project and question on another device without remote desktop. Agent-side HTTP 200 alone is insufficient. |
| Answer and note | Actual submitted choice and note return unchanged to the originating Jcode session. |
| Pending and resume | A bounded no-answer wait returns pending; the same saved thread can be read after an actual session resume without another question. |
| No duplicates | Repeating the same Inbox idempotency key returns the same message, not a second card. No second Telegram send is needed for this check. |
| Scope and stale replies | Check question/message/revision before acting. A different session, superseded question, skipped answer or acknowledgment cannot authorize this action. Use disposable pilot records, never another project's messages. |
| Safe publication and rollback | Check remote control routes are not exposed and existing settings/mappings remain intact. Test a denied login only if a distinct test identity is actually available; do not infer it from a successful owner login. |
| No approval spam | Actual reversible work completes without creating an Inbox question. Only the explicit pilot question is expected. |

**Stop or fall back** if response correlation, reachability or privacy fails. Disconnect only the pilot connection, stop only its owned process/publication, and restore only this change's overlay/procedure edits if necessary. Preserve messages, private receipts, credentials and unrelated mappings. Use the existing document review/GitHub links meanwhile.

**Expansion is separate:** a successful pilot may remain opt-in, with explicit retrieval. A persistent primary Inbox or automatic wake would revisit [ADR 0002][adr] and needs its own decision, not a larger implementation hidden inside this plan.

## Evidence to retain

Before implementation: exact reviewed commit/hash, scope and private backups. After implementation: changed-file checks, guidance/package results, real fresh/resumed Jcode observations, owner-device/choice-note evidence, returned IDs and cleanup comparison. Missing owner interaction remains unverified, not replaced by a fabricated reply or mock test.

## Execution record, October 20, 2026

The approved 12-word sentence is installed. Source and live overlay match at 319 words; the rest of the overlay is byte-identical to its previous revision. A private rollback copy is retained. The Inbox is a temporary, run-only pilot with an on-demand MCP connection, not a new permanent service or cross-project default.

| Requirement or output | Actual observation | Status |
| --- | --- | --- |
| Preserve the lean overlay and its other rules | All 246 repository tests passed, with one preexisting skip. The real wheel and source archive contain the byte-exact updated overlay. | Passed |
| Remote-first handoff | A fresh installed Jcode session retained the supplied verified GitHub plan link without a host-local handoff. | Passed for this bounded case, not a general model-quality claim |
| Autonomous reversible work | The same actual native session resumed, repaired a disposable duration formatter and passed its project's three tests without asking an owner question. Child notification hooks were disabled. | Passed |
| Native publication boundary | Real HTTPS root returned 200. MCP, connection, bridge, device and agent-configuration routes returned 403 through that same endpoint. The second loopback listener rejected a missing login; a cross-site request was rejected. Existing Serve mappings were preserved, with no Funnel or manual proxy. | Passed; a distinct denied tailnet account was unavailable |
| One question, not duplicate cards | The real native send created one question and attachment. Repeating the exact idempotency key returned the same thread; readback reported one message and no person reply. | Passed |
| Pending without implied approval | The actual 25-second wait returned pending with a saved cursor. No answer was inferred. | Passed |
| Useful action link | Chrome over the actual tailnet URL displayed this project, the question, both choices, recommendation, note composer and Send. No choice, note, acknowledgment or answer was submitted by the agent. One Telegram attention message was acknowledged with matching formatting. | Passed on the agent host; owner-device access still pending |
| Owner choice and optional note | The real question is open. No fabricated reply or synthetic fixture replaces this check. | Pending owner interaction |
| Reply after session resume | Exact originating session, project, thread/message, revision and cursor are retained privately for retrieval. A new owner reply after a real session resume has not yet been observed. | Pending |
| Stale or unrelated responses | The question's authority is limited to this repository's presentation preference. No merge, deployment or production permission is inferred. Skipped, acknowledged or mismatched replies must not resolve it. | Return-path checks remain pending |
| Minimal procedure update | No broader Inbox instructions or new skill have been installed before the real return path works. | Deliberately deferred |
| Owned cleanup | Keep this temporary publication available while the question is open. Remove only the owned endpoint/process after resolution, retaining messages and comparing saved mappings. | Pending, not claimed complete |

**Observed integration caveat:** this Jcode client currently displays `read_thread`'s count summary rather than its structured message content. The native `wait_for_reply` text includes the actual reply body, so the pilot uses that supported tool with its saved thread and cursor. Automatic wake is still not provided.

**Settings qualification:** native first use added only Plannotator's version-specific sound-dialog marker. Removing that marker reconstructs the exact pre-pilot config hash, consistent with the pinned server's first-run code. A concurrent Jcode config byte change was also observed and preserved, not rolled back or attributed to this pilot. A contemporaneous before/after comparison around the native acceptance run showed identical parsed config, including hooks, notifications, safety and ambient settings, with no persistent pilot MCP entry. Do not interpret this as equality to every earlier baseline byte.

The pilot is **not yet an end-to-end success**. Owner-device access, submitted choice/comment, resumed retrieval and final cleanup remain real acceptance conditions. Private receipts contain the live action URL and recovery instructions; no private host, session, token or receipt is published here.

[approved-revision]: https://github.com/nephilus/jcode-telegram-alerts/blob/a9aa62e98aa0a31432e03f08aaee86e3b2805b2b/docs/plans/2026-10-20-remote-first-inbox-pilot.md
[assessment]: ../research/2026-10-20-remote-first-inbox-assessment.md
[adr]: ../adrs/0002-private-owner-reviews.md
[inbox]: https://plannotator.ai/docs/reference/inbox/
[inbox-source]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-mcp.ts
[tailnet]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-tailscale.ts
[mcp-timeout]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/mcp/client.rs#L47-L58
