# Plain-language overlay: explain what the decision means for you

**Status: Approved and installed.** Prepared October 20, 2026, local time (+08:00). The owner merged [proposal PR #20](https://github.com/nephilus/jcode-telegram-alerts/pull/20), then separately requested installation on October 19, 2026 at 20:19:42 UTC. The exact block below is now the live global overlay and source template. The comparisons below describe the earlier proposal, not a new approval request.

## Recommendation

Replace the current overlay with the block below. Keep the assistant autonomous, but ask it to explain the practical outcome, why it matters and the important trade-off before discussing implementation. Explain unfamiliar components by what they do. Do not require an ELI5 or TL;DR heading on every reply.

For example, “approval requests should reach you even while routine progress updates are temporarily silenced” explains the purpose better than “explicit attention bypasses session cooldown suppression.” This is an illustrative wording change, not a claim that any particular alert was delivered.

The current overlay has not been shown to make answers generally worse. Its gap is more specific: “keep chat concise” does not tell the assistant what background knowledge to assume. The proposed change targets that gap, not just length.

## Comparison with the base and current overlay

The installed CLI is **Jcode v0.99.0, `774613c90751b6a26ae9eb6a27be6aff3f210062`**. Its [base prompt][base] already calls for autonomy, sparse questions and summaries under five lines. Its [assembler][assembler] adds an overlay without replacing that base. No Jcode code change is needed.

| Concern | Current behavior | Proposed change |
| --- | --- | --- |
| Explanation level | Base requires brevity; current overlay adds brief context | Address a capable reader without project knowledge. Explain consequences and unfamiliar components, not just internal labels |
| Quality and autonomy | Current overlay adds correctness, maintainability, reversible defaults and a threshold for questions | Keep these boundaries, trim repeated wording |
| Documents | Plans/research/ADRs, Y-statements, GitHub and private Plannotator reviews | Preserve them. Clarify that presenting a document does not create a blanket approval gate |
| Owner decisions | Small choice cards and published Proposed ADRs for major decisions | Preserve meaningful choices, recommendation, comments and decision thresholds |
| Attention | Verified action links, scoped revisions, delivery receipts and no automatic ambiguous retry | Preserve these safeguards. Keep command mechanics in the owner-review skill |
| Technical requests | Precise detail remains available | Explicitly match requested depth rather than force a beginner explanation |

I recommend one coherent replacement for ease of maintenance, not because testing proved that rewriting beats appending a paragraph. The append-only variant performed comparably. No new skill, summarizer, service, context-compaction setting or core fork is proposed.

## Exact approved overlay

**307 words**, compared with the previous 297. Installation replaced only the overlay. The base prompt and existing owner-review skill remain in place.

```text
Make it right: deliver correct, maintainable, well-integrated work with the smallest coherent solution. Reuse suitable code, repair or replace it when needed, and avoid speculative features. Verify outcomes and state material limits.

Explain substantive replies to a capable reader who does not know this system. Lead with the practical outcome or recommendation, why it matters, and the main trade-off. Describe what unfamiliar components do before naming them. Prefer concrete everyday language to internal labels, acronyms and implementation steps; add technical detail when requested or necessary for the decision. Preserve risks and uncertainty, and stay concise.

Investigate factual uncertainty. Choose sensible reversible defaults and continue. Ask only when material intent, authority, scope or consequences remain unresolved. Continue independently authorized work while feedback is pending.

Keep durable documents in docs/plans/YYYY-MM-DD-topic.md, docs/research/YYYY-MM-DD-topic.md and docs/adrs/NNNN-topic.md. Frame ADR decisions as Y-statements with desired qualities and accepted trade-offs. Present documents that warrant owner review through Plannotator over Tailscale. Presentation is not a blanket approval gate. Do not manufacture documents for routine work or open side panels unless asked. GitHub holds durable artifacts and PR decisions.

When a small decision genuinely needs the owner, use a Plannotator question card with brief context, meaningful choices or Yes/No, a recommendation with why, and room for comments. Do not turn ordinary uncertainty into an interview. Major decisions need a committed, published Proposed ADR reviewed in Plannotator.

Before waiting for owner action, publish jcode-telegram attention with the exact request and a verified relevant action/review link. Match responses to the decision and reviewed revision; delivery, annotations and sign-in are not blanket approval. Check receipt/failure; use a stable key per reviewed decision/revision. Use --resend only on explicit owner request; never automatically retry ambiguous failure. Workers report to their coordinator, not duplicate owner requests. Use owner-review (~/.jcode/skills/owner-review/SKILL.md) for publishing and feedback mechanics; read that file if unavailable in the skill catalog.
```

This is guidance for substantive explanations, not compulsory headings or a reason to pad a routine completion message.

## What the tests actually showed

Two bounded comparisons used the actual installed Jcode CLI with OpenAI / `gpt-6.1-sol`, isolated temporary homes and the same skill setup. Writing cases supplied facts and prohibited invented actions. An independent model reviewer saw randomized reply labels, not the variants. These were real model calls, not canned replies.

| Comparison | Observed result |
| --- | --- |
| First draft: current overlay, append-only, coherent rewrite | 36 writing replies. The blinded reviewer preferred the rewrite over current in 5 of 12 comparisons, tied 6 and preferred current once. Append-only was comparable. Some jargon remained, so this draft was not adopted as final |
| Exact final block above versus base with no overlay | 12 writing replies. The reviewer preferred final in 3 of 6 pairs and tied the other 3, including the precise-code request. No factual or authority error was flagged in these six pairs |
| Already-authorized edit, check and commit | All five tested variants across both rounds corrected the actual file, passed the repository's check, committed only that file and left a clean worktree |
| Preservation | Live configuration, overlay, owner-review skill, packaged prompt and protected notification files were unchanged. Temporary authentication copies were removed |

The first rewrite's writing replies totalled 1,568 words versus current's 1,538 and append-only's 1,539. The final follow-up totalled 718 versus base's 733. These small differences are not evidence of better understanding, and the two rounds must not be treated as one paired length comparison.

### Requirements checked against actual replies

| Case | What was observed with the final block |
| --- | --- |
| Missed approval alert | Distinguished approval requests from routine updates, recommended the existing targeted publisher and retained uncertainty about the missed alert's cause |
| Application cannot start | Explained the blocked download before the network exception, kept permission limited to test workers and one endpoint, and said startup remained unverified |
| Backup choice | Kept the potential loss of recent records, unmet five-minute requirement, job-maintenance burden and unproven storage-only recovery |
| Green checks, unavailable sign-in | Opened “Not yet,” distinguished checked code from a live service and named the separate go-live review without inventing a link |
| Temporary versus permanent review service | Recommended the existing workflow while retaining its process-lifetime limit and the maintenance burden of a permanent service |
| Explicit technical request | Gave Python after the stated validation precondition, rechecked secrets in the normalized URL and retained exact confirmation. It did not substitute an ELI5 preamble |
| Real edit workflow | Corrected the README, ran the existing check and committed. Its final update stayed four lines without an artificial trade-off section |

The initial reviewer flagged a technical fragment's copyability and an unnecessarily large example. The fragment's prose did state its validation precondition; this was a presentation concern, not a demonstrated unsafe execution. The final follow-up retained that precondition and used a smaller example. No production code was patched in either writing case.

**Limits:** this is a small, single-model, supplied-fact study, not a human comprehension test or a statistically established improvement. It does not test long-running infrastructure work, compaction, unattended recovery or production alert delivery. The edit task explicitly excluded new approvals, so it does not prove the overlay will never over-ask. Some terms still appeared before a full explanation of their role. Your judgment of the explanation level remains the important check.

## Review scope and installation

The original review asked whether the wording and examples gave enough context to decide without decoding the machinery. Its approval covered the wording, not installation, deployment, a new service or infrastructure actions. Installation followed the owner's separate request after merging PR #20.

The approved block was installed on October 19, 2026 at 20:23:43 UTC, after keeping a private rollback copy. Its SHA-256 is `64888f8092127602df949f87dae3de1215e65df35e1b323b4ca9c7547b4c621c`; the live file, source template and block above match exactly.

Two actual Jcode v0.99.0 CLI turns then used the live global configuration, with the second resuming the first session. Neither supplied a custom system prompt. The first explained that a blocked image download prevented startup, described the narrow test-machine access being considered, and explicitly said no rule had been applied or startup verified. The resumed turn answered a precise Python request with the validation precondition, a secret check after URL normalization and exact echo comparison. These observed replies support the intended explanation level and retained technical depth, not a claim of universal comprehension or correctness.

All 246 regression tests completed successfully with one skip. Locally built wheel and source archives contain the exact approved guidance asset. These are packaging checks, not a new published release. The two live checks disabled hooks for those child processes, so they did not send Telegram messages or exercise delivery. No core, compaction, skill, native Telegram or review-procedure change was needed.

[base]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/prompt/system_prompt.md
[assembler]: https://github.com/1jehuang/jcode/blob/774613c90751b6a26ae9eb6a27be6aff3f210062/crates/jcode-base/src/prompt.rs#L481-L544
