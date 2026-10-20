# Remote-first handoffs: a small Inbox pilot

**Status: Proposed execution plan.** October 20, 2026 (+08:00). Builds on the [approved assessment][assessment]. Nothing below has been installed or enabled by preparing this plan.

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

[assessment]: ../research/2026-10-20-remote-first-inbox-assessment.md
[adr]: ../adrs/0002-private-owner-reviews.md
[inbox]: https://plannotator.ai/docs/reference/inbox/
[inbox-source]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-mcp.ts
[tailnet]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-tailscale.ts
[mcp-timeout]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/mcp/client.rs#L47-L58
