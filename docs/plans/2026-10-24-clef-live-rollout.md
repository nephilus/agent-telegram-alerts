# Live Clef update selector and 100-turn post-implementation review

## Authorized outcome

On October 24, 2026, the owner authorized enabling the tested Clef selector for ordinary turn-finished updates instead of leaving all completion pushes disabled. Explicit `attention` / “Jcode needs you” remains independent. Collect the next 100 eligible turns privately and quietly for a post-implementation review (PIR).

Task branch: `feat/clef-live-update-filter-20261024`. This is a local implementation and installation, not authorization to push, open a PR, merge or publish a release.

## Delivery contract

- Use the frozen E yes/no Choice prompt from `docs/research/2026-10-24-clef-notification-safety-net.md`. The model selects a label. It cannot write the notification, supply a destination or execute a requested action.
- Read the complete public final from the native session snapshot and append-only journal, binding it to the hook's exact 4000-character excerpt. Read only public text blocks, not reasoning or tool results.
- Consider successful owner-root turns. Exclude known child sessions, stale/ambiguous source matches and automated coordination-only turns. A user-created fork also has a parent, so it is conservatively excluded unless its exact session ID is explicitly included in the existing delivery policy.
- A YES permits one new ordinary Telegram update. Preserve the original ELIF/public reply with existing secret and Markdown cleanup. Include only independently validated original links. No Qwen rewriting.
- Selected updates bypass the old 30-second minimum and 300-second grouping window. Otherwise a short approval request or a follow-up link could be lost again. Existing include/exclude filters still apply. Errors retain their existing enabled state and repeat suppression.
- Keep selected text within Telegram's UTF-16 limit. Long bodies are visibly clipped, with complete allowed link labels and destinations retained in a separate footer. This is a bounded literal copy, not a claim that every long output fits Telegram.
- Never infer that another notification delivered a request. The frozen selector state uses `attention_state: unknown` and `last_published_update: null`. Existing explicit attention is neither filtered nor disabled. Cross-channel semantic deduplication is not established.

## Failure and concurrency contract

Use one finite HTTPS request to the configured maintained local decision origin. Require the configured response model and strict typed yes/no result. Reject invalid, oversized, redirected, failed or timed-out responses. Do not retry, call Qwen or fall back to a cloud model or unfiltered completion delivery.

Claim a unique source turn before external work. Repeating an event after an uncertain send must not resend it. Bound retained claim history and model concurrency. Record busy/failure outcomes instead of treating them as NO judgments. Recheck the live policy immediately before a send. Turning the selector off must leave ordinary completion pushes off, not restore the old flood.

Explicit attention, errors, native credentials, reply settings, foreign hooks, global prompt guidance and review-host trust are outside this change.

## Private next-100-turn collection

Store sanitized selector inputs, original allowed links, prompt identity, timing, typed choice and actual delivery outcome in owner-only local files. Limit content retention to 100 unique eligible turns. Continue filtering afterward without collecting further turn content. Read-only status exposes counts and readiness, not credentials or conversation text.

This is an observational collection, not a claim of proven precision or recall. The PIR must review both YES and NO examples, separate invalid/busy/delivery failures, identify acceptance-test turns, and inspect possible missed owner actions. Distinguish notification quality from an authoritative approval decision. No per-turn collection notices or extra Telegram summaries are needed.

At 100 records, report collection readiness in local status. A subsequent PIR reads those exact records without silently changing the prompt or delivery policy. Human usefulness ratings remain different from model or agent labels.

## Public operator interface

Configure the existing origin and existing key file through the installed CLI. Credentials remain in the referenced private file, not command arguments or the source repository:

```sh
jcode-telegram selector on \
  --endpoint https://decision.example.ts.net:9105 \
  --key-file /absolute/private/decision.key \
  --model maintained-decision-alias \
  --response-model exact-clef-backend \
  --pir-turns 100
jcode-telegram selector
jcode-telegram policy
```

The hostname, paths and model names above are placeholders, not deployment configuration. Configuration alone does not prove reachability. Re-enabling the same selector must preserve the existing journal rather than restart the sample.

Rollback to quiet completions, preserving errors, explicit attention and collected evidence:

```sh
jcode-telegram selector off
```

## Acceptance mapping

| Requirement | Concrete acceptance observation |
| --- | --- |
| Tested prompt, not another rewrite | Exact E instructions/criteria fingerprint and strict single Choice response tests |
| Complete native source | Snapshot plus journal, 4000-character prefix recovery, duplicate/stale/tool/child/automation rejection tests and a real native turn |
| Useful short updates can reach the owner | Offline YES integration and a separate real Telegram formatter check passed. Three short native turns reached Clef through a child-only witness, but all returned NO. Automatic production YES-to-Telegram remains unobserved. |
| NO does not send | Actual maintained Clef NO on a native routine response with a quiet observer receipt |
| No model-generated notification or links | Exact sanitized source text and original verified URL entity comparison |
| Explicit attention and errors remain independent | Existing attention tests plus selector-enabled observer error and repeated-error tests, no redundant owner-action send needed |
| Unavailable or malformed selector stays quiet | Finite transport/deadline and strict response rejection tests, no-send outcomes clearly distinguished from semantic NO |
| No duplicate retry | Pre-transport claim, concurrent/busy tests and uncertain-delivery replay checks |
| 100-turn retention bound | Concurrent/restarted collection, 100-record content cap and post-cap filtering tests |
| No private-data publication or unrelated changes | Secret checks, owner-only evidence modes, protected-setting hashes and independent branch diff/build |
| Safe rollback | Installed public `selector off` check in an isolated home, preserving errors, native settings and the journal |

Passing synthetic transport tests is not evidence of actual Telegram delivery. The installation receipt must separately identify real API, native-hook and Telegram observations, any unexercised boundaries, and the local build's exact source identity.

## Observed installation on October 24, 2026

The selector policy was enabled locally at 12:55 UTC. The initially installed runtime came from independent task-branch revision `ef6bab9296974f57ec711a6ec2ebe7e43d4a34be`, not the combined workspace. Its wheel SHA-256 is `0f53520da6549c1d55c8887bf76b56e45e46203b9c1d648f1ee7226b3bc045c2`. All seven installed Python modules matched that wheel. This is an unpublished local build, not a new public release. **That initial check did not establish production hook routing.**

### Hook-runtime correction at 13:19 UTC

After the owner reported missing notifications, inspection found that all four saved Jcode observers still invoked the previous installation, not the newly updated stable wrapper. The actual saved executable did not support `selector`, and normal completion diagnostics reported `invalid_policy`. The three earlier native checks had used a child-only witness that called the new wrapper. Calling the hook installer `status` had established ownership, not that the saved executable contained the new feature. The initial production-readiness claim was therefore overstated.

The complete previous owned runtime was backed up privately. The same tested independent wheel was then installed into the exact runtime the saved observers already invoke. Both installed runtimes now have seven byte-exact matching modules. Native configuration, foreign hooks, global guidance, selector policy, selector evidence and stable wrappers remained unchanged, so existing cached hook paths need no daemon restart.

The exact saved `turn_end` command was exercised using an already-claimed NO event. It produced `quiet` / `duplicate`, with unchanged counters and no additional classification or notification. This checks the actual configured executable without forcing a YES. New natural-turn ingress and automatic YES delivery still require observation after this correction.

### Earlier checks and their limits

- The combined workspace ran a successful 297-test suite, with one existing skip. The independent branch ran 287 tests successfully, with the same skip, and built both wheel and source archives. Installed public query/on/off, repeated configuration, three previews and quiet rollback passed in isolated homes.
- Three actual native turns in a fresh, then resumed session reached the maintained Clef API. Child-only hook witnesses invoked the real installed observer, without editing native hooks. Decisions were **NO, NO, NO**, taking approximately 0.16, 0.20 and 0.23 seconds. All turns were below the old 30-second completion threshold. No tool was called by these native writing turns.
- The routine acknowledgment was correctly kept quiet. The useful installation notice and the follow-up limitation finding were also kept quiet. These are potential missed updates according to the agent's expectations, not owner usefulness labels. Keep them in the evidence instead of silently adjusting the frozen prompt to obtain a YES.
- **An automatic native YES-to-Telegram delivery has not yet been observed.** Separately, one visibly labeled formatter check sent the original native reply through the installed notification renderer and real Telegram transport. Telegram acknowledged the exact text, trusted bold ranges and original clickable repository target. This checked that delivery boundary, not the classifier's judgment.
- Native configuration, global overlay, saved verbosity, review-host trust, maintained API reference and credential remained unchanged. Only the two stable helper wrappers and selected-completion policy changed. Errors and explicit attention stayed independent. Selector configuration and evidence are owner-only, and exact known credentials and the private home path were absent from collected inputs.

At 13:21 UTC the counter still contained only the three marked acceptance turns, not observed natural production traffic. Preserve their identities privately and exclude them from any natural-usefulness rate. Collection stops retaining content at 100 records, while filtering continues. No production precision, recall or owner benefit has been established by these installation checks.

## PIR reading rules

Review both sent and skipped examples, not just the send rate. Separate semantic NO from failed, oversized, busy and uncertain-delivery outcomes. Inspect retained late owner actions and original links, check observed automatic YES delivery when it occurs, and report request/delivery latency separately. Distinguish owner labels from agent expectations and exclude marked acceptance cases from natural-usefulness statistics.

The completion counter is for eligible, source-bound root turns, not every worker, automation or unavailable-source hook. Do not present it as exhaustive coverage of all Jcode activity. Keep the prompt and live policy unchanged during collection unless a new owner instruction or a material safety issue requires action. At the collection limit, produce the PIR from the retained records. No additional inference, Telegram test or repeated progress messages are needed to collect them.
