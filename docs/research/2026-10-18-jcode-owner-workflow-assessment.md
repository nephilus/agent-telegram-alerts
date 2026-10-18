# Jcode prompts, skills and remote owner review

**Assessment, not applied configuration.** Researched October 18, 2026 UTC. Verified installed Jcode `v0.98.1` against commit `1c7426eb1925a1167eb56011fa479ad707cc28b6`, Plannotator `0.28.23`, Tailscale `1.102.4` and the installed Telegram helper `0.5.0`.

**Review scope:** comments or approval here concern this assessment only. They do not authorize changing the overlay, deleting skills, broadening URL policy, merging PRs or deploying anything. Use annotations to suggest changes.

## Recommendation

**Keep Jcode's base prompt. Add a lean preference overlay, retain operational skills on demand, and make Telegram the attention channel, not the approval engine.**

1. Put the everyday nuances of ponytail, selective clarification and repo-based presentation into one short overlay. Do not paste entire skills into it.
2. Keep deep grilling opt-in. Keep headless authentication and Plannotator procedures separate. Move habitual PR formatting into repository templates/conventions where practical.
3. Use committed Markdown as the source of truth, Plannotator for review/question cards, and GitHub for durable links and PR approval. Stop opening side panels unless requested.
4. Pilot one document review over Tailscale before deleting skills or adding an asynchronous Inbox. There is one concrete Telegram URL compatibility gap to fix.
5. Leave compaction alone initially. It does not make tool invocation or approval correlation reliable.

No core patch, new summarizer, generic Telegram command router or mandatory interview framework is justified for this first step.

## 1. What Jcode already does

### Autonomy and presentation

The small base prompt already favors autonomous completion, sparse blocking questions and caution around irreversible actions. Ponytail's useful addition is mainly the **smallest complete solution**, reuse and avoidance of speculative machinery, not another instruction to be proactive. [base]

There is **no side-panel preference in the base prompt** at this commit. Panel behavior is described in `crates/jcode-app-core/src/tool/panel.rs:37-51`; the legacy `side_panel` tool merely prefers the newer `panel` API. Earlier use of panels was an agent presentation choice, not a base-prompt requirement. A preference such as “do not open side panels unless I ask” is sufficient to steer normal behavior. For a stricter per-run boundary, the installed CLI supports `--disabled-tools panel,side_panel`; this hides agent tools, not the client widget itself. [panel] [legacy-panel]

Keep the built-in base. Replacing `.jcode/system-prompt.md` would throw away useful defaults unnecessarily; `.jcode/prompt-overlay.md` is the additive mechanism. [assembly]

### Important correction: overlays do reload

Bundled `SYSTEM_PROMPT_CONFIG.md` says existing sessions retain their startup prompt. The actual ordinary Agent path rebuilds prompt parts before provider requests and rereads base/overlay/preferred-tool files. An explicit SDK/session `system_prompt` override bypasses that path. Agent AGENTS/advertised-skill snapshots are separate, and not every harness shares identical snapshot behavior. [prompt-doc] [request-loop] [prompt-build] [assembly] [agent-snapshots]

**Real installed-path check:** in a new scratch project, a tool-free native turn reported a marker known only through its project overlay. After editing that isolated overlay, the same native session was resumed and reported the new marker. No compaction was involved. Notification hooks were disabled and no real/global project instructions changed.

This corrects the earlier blanket advice that an overlay change requires a new session. The source and observed normal CLI behavior support reloading; this is not a claim that every SDK override or client path reloads everything.

### Skills and compaction

The advertised skill catalog contains short descriptions, not every complete skill body. Thus having installed skills is not equivalent to putting all their instructions into the system prompt. Full bodies become relevant when selected or loaded. [skill-catalog]

There is also a meaningful distinction:

- A slash-selected `active_skill` is dynamically included in ordinary Agent requests while that selection remains active.
- `skill_manage load` returns text as a tool result; it does **not** set `Agent.active_skill`. That text can later be summarized with conversation history. Do not equate a load receipt with a permanently pinned system instruction. [skill-tool] [active-skill]
- Global skill content is cached. A missing on-disk directory can still be readable through the current registry. A reload may remove it or reveal another same-name source; existing advertised catalogs and transcript text are separate. Archive/remove only after checking the effective registry and a fresh session. No reload or deletion was performed during this assessment. [skill-cache] [skill-reload]

Jcode-managed compaction normally targets 80% usage, with critical recovery at 95%. A separate OpenAI-native automatic compaction path has its own threshold, so there is not one universal percentage knob. Static system instructions are passed separately from compacted conversation messages. Earlier compaction may reduce old conversation load, but adds summarization and possible information loss; it does not enforce attention calls or route replies. Keep defaults first, checkpoint decisions in repo files, and investigate measured drift before tuning provider-specific settings. [compaction] [compact-output] [compaction-config] [openai-compaction]

## 2. What to keep, retire or move

These are recommendations, not changes already made.

| Item | Pragmatic treatment |
| --- | --- |
| **Ponytail** | Extract the few everyday principles into the overlay. Trial them, then archive the personal skill if its explicit lite/full/ultra modes are no longer useful. |
| **Headless-links** | Retain for authentication/device-code workflows, with their real URL, expiry, browser and ambiguous-result safety rules. Do not treat it as a Telegram delivery mechanism. |
| **PR skill** | Put the habitual summary/evidence/risk contract in each repo's existing PR template/conventions. Keep the visual-rich skill optional, or archive it after equivalent coverage exists. Do not copy its complete template globally. |
| **Grill-me / grilling** | Retain as an explicit design stress-test. Do not globally import the requirement to interview through every decision branch before acting. Extract only investigate-first, material questions, meaningful options and a recommendation. |
| **Plannotator** | Reuse the installed procedures on demand. Add only a short Jcode-specific handoff procedure if the pilot exposes a gap, not another general orchestration framework. |

Local inspected bodies were 592 words for ponytail, 1,045 for headless-links, 568 for PR and 3,951 for Plannotator. Those procedures belong on demand, not in an always-present overlay. The exposed grilling text explicitly treats all decisions as the owner's and waits for a fully resolved design tree, which conflicts with the desired everyday autonomy. Its upstream entry point is an alias to that workflow. [grilling]

### Candidate overlay, not installed

```text
Prefer the smallest complete solution that fits the existing code and conventions. Reuse what exists; avoid speculative features, abstractions and dependencies. Verify the result, and state material limits.

Resolve factual uncertainty by investigation. Choose sensible reversible implementation defaults and continue. Ask only when material intent, authority, scope or consequences remain unresolved. Give brief context, meaningful options when useful, and a recommendation with why. Continue independently authorized work.

Keep substantial plans, research and decisions as Markdown in the owning repo, following its conventions. Do not open side panels unless asked. Use Plannotator for requested document/question review and GitHub for PRs and durable artifacts. Keep chat concise.

Before genuinely needing owner action, publish jcode-telegram attention with the exact request and a verified relevant action/review link. Major decisions need a committed Proposed ADR. Match any answer to its decision and reviewed revision; delivery, annotations and sign-in are not blanket approval. Keep tool-specific procedures in skills, not this overlay.
```

This would **replace and streamline** the current attention block after agreement, not accumulate another overlapping block. Full grilling remains available when explicitly requested.

### Repository structure

Follow an existing convention first. Where none exists, create only directories actually needed:

```text
docs/
  plans/YYYY-MM-DD-topic.md
  research/YYYY-MM-DD-topic.md
  adrs/NNNN-decision.md
```

This repository already uses `docs/adr/`, so keep that singular spelling rather than renaming it for aesthetics. A small reversible change does not need a plan, research note and ADR. Significant decisions get a Proposed ADR with context, options, recommendation, consequences and the exact scope needing approval.

## 3. The smallest useful owner-review loop

**Repo artifact -> Plannotator review -> Telegram attention with the real link -> correlated feedback -> same agent -> update the artifact.**

### Significant decisions and plan approval

1. Write the plan or Proposed ADR in the owning repo. Commit/publish significant decision records so there is a durable fallback link tied to a revision.
2. Start one background-hosted invocation of the installed CLI, suppressing automatic browser launch:

```sh
PLANNOTATOR_BROWSER=none plannotator annotate docs/adr/NNNN-decision.md \
  --tailscale --gate --json --require-approval \
  --result-file /existing/private/directory/NEW-result.json
```

3. Capture the **actual HTTPS URL printed to stderr**, not a guessed host/port or old link. Publish attention immediately with concise Context, Needs you, recommendation and this link, plus the committed ADR/PR fallback. Include the reviewed revision in the stable attention key.
4. Keep the hosting process alive while review is pending, continue unrelated authorized work, and read that process's result. Under strict mode, proceed only with exit `0`, an `approved` decision, successful result publication and the matching reviewed revision/scope. Annotation-only or dismissed results are not approval. Cancellation/publication failure is not approval either. [gate-source] [tailscale]

The result-file parent must already exist and the target must be new. The CLI publishes atomically without overwriting. A printed approved JSON followed by exit `2` can mean result publication failed, so do not check stdout alone. Tailnet annotation disables the local abandonment lease; the URL still requires the host/process to remain alive and normal cleanup. It is not a permanent GitHub-style artifact. [gate-source] [annotate-source]

A Plannotator plan approval does not automatically authorize a PR merge, deployment or destructive command. For an actual GitHub PR decision, send the PR link and let its normal review/merge controls remain authoritative.

### Small decisions: use the existing question cards

Plannotator already supports single choice, multiple choice and free text in Markdown. Yes/No is simply a two-choice question; an explicit recommendation can be shown with its reason. The reviewer can add a note or another answer. Do not build a replacement for OMP ask cards. [questions]

Illustrative syntax, not a pending owner request:

```markdown
:::question
Which destination should receive this new integration's sensitive notices?

This is an owner visibility preference, not a fact the code can establish.

- [ ] A: Existing restricted operations channel
- [ ] B: A separate owner-only channel

Recommended: A: Existing restricted operations channel
Reason: It preserves the current access and on-call visibility model.
:::
```

For a **question-only** handoff, use annotation/question feedback, not a strict approval requirement. Inspect the returned answer for that question/revision. Sending answers is different from approving a plan; unanswered/skipped or merely dismissed cards settle nothing. Do not force an extra approval click for a small choice. Ask only questions that materially need the owner, not every implementation detail. [questions] [gate-source]

### Two concrete gaps, not prompt problems

**Private review URL delivery:** an offline probe of the actual installed helper accepted ordinary GitHub URLs and default-443 synthetic `ts.net` origins, but rejected a `ts.net:19433` URL. Plannotator's normal Serve URL uses its session port. Therefore the desired clickable Telegram path does not work unchanged. A local `http://localhost:...#thread=...` Inbox tool URL is also not a remote review link. [link-policy] [tailscale]

The smallest proposed fix is an **attention-only** exception for an explicitly trusted exact tailnet host and declared review port, preserving HTTPS and credential/query/fragment restrictions. Leave ordinary output-link extraction unchanged. Do not permit every private address or every `ts.net` host, remove all port validation, take over an existing 443 mapping or reset unrelated Serve entries. A static 443 route is an alternative only if separately designed and owned, not an assumed shortcut. Syntax acceptance does not prove reachability.

**Delivery is not a durable decision inbox:** current attention stores outbound confirmation/deduplication metadata, not a routed inbound question record. It also permits an empty links list. Prompt wording alone cannot guarantee that every handoff is sent, contains a usable action link, or receives an answer. A future review-publishing path should reject a missing/unusable action link and report delivery failure visibly, while existing generic notices need not become a new workflow engine. [attention]

## 4. Can I just answer Yes/No in Telegram?

**Not reliably for the ordinary session that sent an attention alert.** In this Jcode version, native free-text Telegram replies enter the ambient runner. The native decoder/poller does not correlate reply-to message IDs, attention keys or option callbacks to an ordinary session. Its special permission reply path needs an explicit permission request ID and belongs to ambient safety handling. A bare Yes/No is not approval of the corresponding attention request. The helper has no inbound receiver. [telegram] [ambient-ingress] [telegram-types] [attention]

Recommended first cut: **Telegram gets your attention; answer in Plannotator or the GitHub PR.** This supplies real question cards and contextual decisions without introducing another Telegram consumer/router. Do not enable a second competing poller or infer broad permission from an uncorrelated reply.

### Optional later: asynchronous Plannotator Inbox

The installed version supports Inbox over Tailscale and its MCP server. Inbox has session/thread/message/cursor identifiers and question cards. Its native tailnet publication is owner-login/allowlist restricted with agent-control routes local-only; standalone annotation instead trusts every tailnet peer permitted by access rules. Use native publication, not a manual direct proxy to Inbox's main listener. [inbox] [inbox-source]

For generic MCP clients such as Jcode, replies do **not** automatically wake the original session. Supply the actual Jcode session and project identity, persist returned thread/message/cursor identifiers, then read or wait for that thread. Inbox's wait defaults to 50 seconds; Jcode's default tool timeout is 30. A 25-second wait is the minimal initial fit without changing global timeouts. After a turn/session ends, an explicit resume-and-read is still needed unless an independently validated wake integration is added. [inbox-mcp] [mcp-timeout]

Inbox is worthwhile if holding a per-document gate open becomes inconvenient. It is not needed to prove the first review, and an asynchronous message is not itself a strict approval gate. For Telegram, use the verified published tailnet origin, not the local fragment-bearing MCP thread URL. No Inbox server or connection was started here.

## 5. Proposed rollout and acceptance

| Stage | Change | Acceptance before expanding |
| --- | --- | --- |
| **A. Preferences** | One lean overlay, repo Markdown, no unsolicited panels. Leave compaction and skills installed. | A normal task proceeds without unnecessary questions. A genuinely material ambiguity gets context/options/recommendation. An existing session observes the intended overlay. |
| **B. One real review** | Reuse Plannotator CLI/question blocks and make the narrow explicit-attention URL fix. | From the owner's tailnet device: open the exact Telegram link, answer a question, approve/request changes/close, verify the correct originating session consumes only the intended result, reject stale revision/failed publication, and clean up only the owned mapping. Keep the host alive during the test. |
| **C. Consolidate** | Archive duplicate personal skills after checking effective registry/fresh-session behavior. Add Inbox MCP only if asynchronous questions are actually needed. | Explicit thread/session correlation, timeout behavior and stopped/resumed-session handling are demonstrated, not inferred. |

No lower compaction threshold, forced interview, core fork, local LLM summarizer or new generic approval/command router is recommended now. When implementation is authorized, the material trust-boundary change should itself be recorded as a committed Proposed ADR rather than quietly widening URL policy.

## Verification and remaining limits

**Observed:** exact-version source inspection, current installed CLI help/versions, privacy-safe Tailscale status reporting Running/online/DNS available, existing Serve mappings left untouched, installed helper URL-policy results, and two real native same-session overlay turns. The overlay probe used only a new scratch fixture, no tools in the child, and disabled notification hooks.

**Assessment-time limits:** before the owner's subsequent request to host this document, phone access, HTTPS certificate consent, live Plannotator approval/question return, mapping cleanup, Inbox MCP registration/wake, live Telegram replies and native compaction were not exercised. No actual approval or remote review URL was invented. Configuration, global overlay, skills, native core, credentials, polling and existing network mappings were not changed during research. The integration catalog was unavailable when recording the two already-installed tools, so inspection used their existing CLIs and primary sources instead. The separately requested document review may add an owned temporary Serve mapping, but does not apply these proposals.

Source-backed assessment is sufficient to recommend the pilot, not to claim the complete remote review workflow is already operational.

## Sources

Jcode links pin the installed commit; Plannotator source links pin the installed release. Local skill body observations came from the exposed registry and existing files, not a claim that today's upstream copies match every local customization.

[base]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/prompt/system_prompt.md
[panel]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/tool/panel.rs#L37-L51
[legacy-panel]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/tool/side_panel.rs#L34-L42
[assembly]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/prompt.rs#L563-L670
[prompt-doc]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/docs/SYSTEM_PROMPT_CONFIG.md#L45-L54
[request-loop]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/agent/turn_streaming_mpsc.rs#L108-L145
[prompt-build]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/agent/prompting.rs#L148-L193
[agent-snapshots]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/agent.rs#L341-L410
[skill-catalog]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/prompt.rs#L249-L282
[skill-tool]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/tool/skill.rs#L112-L160
[active-skill]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/agent.rs#L747-L776
[skill-cache]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/skill.rs#L14-L109
[skill-reload]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/skill.rs#L587-L653
[compaction]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-compaction-core/src/lib.rs#L5-L22
[compact-output]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/compaction.rs#L1310-L1346
[compaction-config]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-config-types/src/lib.rs#L358-L418
[openai-compaction]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-provider-openai-runtime/src/lib.rs#L1142-L1153
[grilling]: https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md
[gate-source]: https://github.com/backnotprop/plannotator/blob/v0.28.23/apps/hook/server/strict-annotate-result.ts
[annotate-source]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/annotate.ts
[tailscale]: https://docs.plannotator.ai/open-source/tailscale
[questions]: https://docs.plannotator.ai/open-source/workflows/questions
[link-policy]: https://github.com/nephilus/jcode-telegram-alerts/blob/b4aa970eb170696ba8b6170be90876386d574272/alert_links.py#L34-L89
[attention]: https://github.com/nephilus/jcode-telegram-alerts/blob/b4aa970eb170696ba8b6170be90876386d574272/alert_attention.py
[telegram]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/channel.rs#L185-L264
[ambient-ingress]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-app-core/src/ambient/runner.rs#L103-L135
[telegram-types]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/telegram.rs#L14-L98
[inbox]: https://docs.plannotator.ai/open-source/inbox
[inbox-source]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-tailscale.ts
[inbox-mcp]: https://github.com/backnotprop/plannotator/blob/v0.28.23/packages/server/inbox-mcp.ts
[mcp-timeout]: https://github.com/1jehuang/jcode/blob/1c7426eb1925a1167eb56011fa479ad707cc28b6/crates/jcode-base/src/mcp/client.rs#L52-L64
