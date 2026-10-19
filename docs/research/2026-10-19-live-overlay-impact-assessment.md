# Did the earlier live Jcode overlay make explanations worse?

Assessed October 19, 2026 UTC. **Research only: no live instructions were changed.**

## Bottom line

**This study did not find convincing evidence that the installed overlay caused an overall regression.** Replies were very similar across three instruction variants. The live overlay produced about 3% more words, not the 25% increase from a different, never-installed wording experiment.

This does not prove the overlay is harmless or that explanations are easy to understand. The owner's difficulty remains a real usability problem; this study does not locate its cause. The overlay's main weakness is a mismatch with that complaint: it specifies working and review procedures much more clearly than how to explain a decision in plain language.

## What was compared

The installed Jcode CLI was `v0.98.1`, commit `1c7426eb1925a1167eb56011fa479ad707cc28b6`. Only the custom global overlay varied:

| Variant | Overlay words | Provenance |
| --- | ---: | --- |
| Base, no custom overlay | 0 | Normal built-in prompt, with the same other experimental inputs |
| Previous attention-only overlay | 134 | Exact private backup made before the broader owner-workflow installation; its instruction body matches the earlier [published attention guidance][previous] |
| Current live owner-workflow overlay | 297 | Byte-identical to [the published template][live], including Y-statement ADR guidance |

The current overlay's SHA-256 was `dc46bbcb8de3540cf8483b34e425b4f194849fcf8718761e107b6aa8972e4281`. The predecessor's was `d716e85ba1f84caf01c0352f1dd91a371ce96a570439e810a4c795fcb1128e0d`.

Five supplied-fact writing tasks were run twice per variant: **30 fresh real Jcode sessions**, not mocked model responses. All used actual OpenAI `gpt-6.1-sol` through `jcode run --ndjson --tool-profile none`, separate temporary homes and working directories, the same account model catalog and the same available owner-review skill. Scheduling rotated variant order with two concurrent processes. Only final `done.text` records were evaluated. The model's generation seed was not controlled.

The tasks covered a completed release update, a missed approval alert, an already-authorized typo correction, a material remote-review architecture choice, and an ordinary completed research finding. The typo and completed-research cases were hypothetical boundary checks, not actual edits or newly completed research. Prompt facts and capability restrictions were identical within each comparison; no answer format was prescribed.

## Observed output

| Task | Base mean words | Previous mean words | Live mean words |
| --- | ---: | ---: | ---: |
| Completed release | 86 | 86 | 84.5 |
| Missed approval alert | 84 | 85.5 | 97 |
| Authorized typo | 27 | 26 | 26 |
| Material review decision | 120.5 | 119.5 | 121.5 |
| Completed research | 66 | 67.5 | 66.5 |
| **Total, ten replies per variant** | **767** | **769** | **791** |

The live total was **3.13% above base** and **2.86% above the predecessor**. That is an observed difference in this small sample, not a statistically established effect. It averaged about two additional words per reply compared with the predecessor.

Concrete findings:

- **No new gate in the routine examples.** All six typo replies described fixing, checking and committing without another approval. None claimed to have performed those actions. All six completed-research replies said no owner decision or configuration change was needed. This checks stated next steps, not tool execution.
- **Much of the writing was nearly identical.** The release replies in all variants led with the installed version and package verification, then described the URL fix and unresolved live delivery. The technical-first pattern was not unique to the live overlay.
- **The largest length increase was localized.** In the missed-alert case, the live replies added explanation or caution. One explicitly distinguished a likely routing/formatting gap from proof that thresholds caused the miss. Extra words are not automatically harmful when they preserve a useful uncertainty.
- **Material advice stayed pragmatic.** Every remote-review answer preferred the demonstrated temporary-page workflow over building an unneeded always-on service, while retaining the process-lifetime trade-off.

## Independent blinded review

A separate model reviewer saw only the requests and anonymized A/B/C final replies, not the variant key or experiment script. Six of ten triads were entirely tied. The other four showed limited differences in useful qualification, next steps or trade-off framing. Decoding the completed judgments gave:

| Pairwise model preference | Live preferred | Comparator preferred | Tied |
| --- | ---: | ---: | ---: |
| Live versus base | 3 | 0 | 7 |
| Live versus predecessor | 2 | 1 | 7 |

The reviewer found no meaningful factual/authority errors or unnecessary blocking gates. These are qualitative model judgments, not human comprehension scores or statistically established gains. In particular, this does not demonstrate that the live overlay meaningfully improved usability either.

## Check against actual history

A separate read-only audit selected seven substantive human-facing finals in one continuing workstream: two before the broader overlay installation around October 18 at 17:42 UTC, and five after installation and the later Y-statement addition. The sample spanned October 18 at 12:29 UTC through October 19 at 05:05 UTC.

Both periods contained outcome-first updates and explicit operational limits. No unnecessary owner-approval or Plannotator gate was observed in that targeted sample. Earlier missing-alert/link complaints predated the broader overlay and cannot be attributed to it merely because they remained part of the conversation.

This was a targeted sample, not a random cohort. Task stages, conversation length, model use and workflow details were not held constant. Automation prompts, worker messages, tool receipts and repeated automation-triggered finals were excluded from the readability judgments. That traffic can otherwise distort raw message counts. Private transcript excerpts, identities and infrastructure details are intentionally not published here.

## Interpretation and recommendation

The [base prompt][base] already calls for autonomy, sparse blocking questions and summaries under five lines. The overlay adds valuable owner-specific safeguards, but repeats some existing principles and devotes much of its space to artifact placement, review mechanics and approval scope. These are not, by themselves, instructions to explain technical work at the owner's level.

The broad instruction to present plans, research and ADRs in Plannotator is a possible source of ceremony if interpreted as a universal blocking gate. Other overlay language and the [accepted workflow decision][adr] explicitly oppose unnecessary questions and distinguish presentation from approval. The present study did **not** demonstrate that this potential misreading actually occurred.

**Do not roll back the whole overlay on the evidence available.** Keep autonomy, truthful verification, explicit attention and scoped-approval safeguards. If presentation guidance is later changed, make the change small: favor a short practical outcome/recommendation and its main consequence before mechanics, preserve material risks, and retain an explicit brevity constraint. Keep operational procedures in the on-demand skill rather than adding another mandatory reply template.

This is a recommendation, not an applied instruction or a request for a new approval. The earlier 25% result concerns a different decision-first candidate and must not be presented as an effect of the installed overlay.

## Limits and preservation

This exercised the real public CLI and real model, but only its writing path. It did not test long tool-using sessions, compaction, actual coding quality, real editing, live review latency, Telegram receipt, other models, or the owner's comprehension and informed approval. Supplied facts may dominate some prompt effects. Holding the skill catalog constant isolates the overlay, not the net effect of every customization installed over time.

Before/after hashes matched for production config, overlay, owner-review skill, Telegram preferences, policy, hook ownership, trust and attention state. Experimental child processes had notification hooks disabled. No Telegram-send or review-service commands were invoked for the assessment, and no production settings, local-model/GPU workloads or infrastructure operations were changed. This is not a claim about unrelated automatic notifications elsewhere. Temporary credential-store copies were removed and the private trial artifacts contained no exact known authentication values.

Private evidence retains the manifest, all thirty native final records, word counts, variant mapping and preservation receipt. Publishing this note does not publish real transcripts or credentials.

[base]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/prompt/system_prompt.md
[previous]: https://github.com/nephilus/jcode-telegram-alerts/blob/148184aa51bc695676f3560c3446ac67520be7b2/README.md
[live]: https://github.com/nephilus/jcode-telegram-alerts/blob/ae9c61e3af8866131f69258f36e85f89b29ee89c/prompts/owner-workflow.md
[adr]: ../adrs/0002-private-owner-reviews.md
