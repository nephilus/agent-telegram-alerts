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
| Useful short updates can reach the owner | Installed observer/native turn below the old duration threshold, actual Clef YES and Telegram text/entity confirmation |
| NO does not send | Actual maintained Clef NO on a native routine response with a quiet observer receipt |
| No model-generated notification or links | Exact sanitized source text and original verified URL entity comparison |
| Explicit attention and errors remain independent | Existing attention tests plus selector-enabled observer error and repeated-error tests, no redundant owner-action send needed |
| Unavailable or malformed selector stays quiet | Finite transport/deadline and strict response rejection tests, no-send outcomes clearly distinguished from semantic NO |
| No duplicate retry | Pre-transport claim, concurrent/busy tests and uncertain-delivery replay checks |
| 100-turn retention bound | Concurrent/restarted collection, 100-record content cap and post-cap filtering tests |
| No private-data publication or unrelated changes | Secret checks, owner-only evidence modes, protected-setting hashes and independent branch diff/build |
| Safe rollback | Installed public `selector off` check in an isolated home, preserving errors, native settings and the journal |

Passing synthetic transport tests is not evidence of actual Telegram delivery. The installation receipt must separately identify real API, native-hook and Telegram observations, any unexercised boundaries, and the local build's exact source identity.
