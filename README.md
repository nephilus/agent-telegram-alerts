# Agent Telegram Alerts

[![CI](https://github.com/nephilus/agent-telegram-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/nephilus/agent-telegram-alerts/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nephilus/agent-telegram-alerts)](https://github.com/nephilus/agent-telegram-alerts/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Generic Telegram delivery for agent updates and owner handoffs.** Use `telegram-alerts update` for a routine candidate that must pass Clef selection, or `telegram-alerts attention` for an explicitly requested direct send. Neither requires Jcode session state or hooks. The approved generic prompt resource is not yet packaged on this branch, so routine updates intentionally fail closed until owner vet and integration.

> The generic CLI and `/telegram` skill do not read native sessions or install/invoke lifecycle hooks. `jcode-telegram` remains a thin deprecated alias for the same generic CLI; legacy event, selector, and saved-session preview behavior is isolated in the separately invoked `telegram-alerts-jcode` adapter. No remote-command server is added.

## What it does

- Accepts concise, caller-written generic update candidates; a versioned Clef YES/NO gate sends the unchanged sanitized summary only on YES. The owner-vetted production prompt resource is a separate pending integration.
- Sends explicit owner handoffs immediately through the generic CLI and `/telegram` skill, bypassing Clef by deliberate command choice.
- Keeps the deprecated native-session lifecycle, selector, and event-policy features behind the separate, explicit `telegram-alerts-jcode` adapter; the generic CLI never dispatches `JCODE_HOOK_*` events.
- Legacy event mode offers an optional editable session status card instead of a stream of routine messages.
- Legacy event mode offers **brief**, **contextual**, and **expanded** profiles. Expanded is the default.
- Uses bold headings, readable section spacing, useful emojis, and compact clickable output links.
- Generic `update` never asks a model to summarize; `attention` remains a separate explicit send. The optional Jcode adapter's completion selector remains isolated and back-compatible.
- Links a dedicated bot through a private-chat challenge and hidden terminal token entry.
- Keeps a deprecated Jcode hook adapter for existing installations; generic attention does not install or require hooks.
- Uses only the Python standard library at runtime. Python **3.11+** and Linux/macOS are supported.

Illustrative legacy Jcode event alert:

> ✅ **Jcode turn finished**<br>
> 🏷 **Session:** Storage migration [snail]<br>
> 📁 ~/workspace/example-project · 1m 35s
>
> 💬 **Asked:**<br>
> Make the notification easier to scan.
>
> 📝 **Result:**<br>
> Added readable headings and section spacing.
>
> 🔎 **Checked:**<br>
> Formatter tests passed.
>
> 👉 **Needs you:**<br>
> Review the next alert.

The example is not a claim about a particular task. Check statements are copied from the assistant's public response, not independently verified by the formatter. A finished turn does not mean the entire user goal is complete.

## Install

Use a dedicated virtual environment. Installation does not access Telegram, copy credentials, or register any Jcode hook.

```sh
python3 -m venv "$HOME/.local/share/agent-telegram-alerts/venv"
. "$HOME/.local/share/agent-telegram-alerts/venv/bin/activate"
python -m pip install "git+https://github.com/nephilus/agent-telegram-alerts.git@main"
telegram-alerts --version
telegram-alerts preview
telegram-alerts update --help
telegram-alerts clef status
telegram-alerts attention --help
```

Alternatively, download the wheel and `SHA256SUMS` from a [GitHub release](https://github.com/nephilus/agent-telegram-alerts/releases), verify its checksum, and install the local wheel with `python -m pip install /path/to/package.whl`. No PyPI package is published by this repository's automation.

Keep the virtual environment at its installed location. Generic installation never registers hooks. The wheel installs `jcode-telegram` only as a deprecated generic alias to `telegram-alerts`; it forwards the same arguments and uses the exact same home resolution. It does not support legacy `alert`, `event`, `selector`, or saved-session preview commands. Existing event hooks must be retired or deliberately reinstalled to call the separate `telegram-alerts-jcode` adapter. The `telegram-alerts-hook`/`jcode-telegram-hook` tools are deprecated, opt-in maintenance tools; they require an explicit `TELEGRAM_ALERTS_HOME` (or deprecated `JCODE_HOME`) and install only the explicit adapter command.

The legacy adapter and hook installer remain only for deliberate maintenance of an existing Jcode integration. They are not prerequisites for `telegram-alerts attention` and are never invoked by the generic CLI or skill. Generic package installation does not rewrite native configuration. Never upload configuration backups, which can contain credentials.

## Profile home and migration

The writable profile defaults to `~/.config/telegram-alerts`. `TELEGRAM_ALERTS_HOME` overrides it; deprecated `JCODE_HOME` is honored only when the new variable is unset. This profile stores Telegram credentials and alert settings, not Jcode session state.

For an existing installation with no usable Telegram credentials in the default generic home, the CLI reads only the Telegram safety fields from `~/.jcode/config.toml` in read-only compatibility mode and prints a notice. New configuration, policy, receipts and dedup state are written under the selected generic home. Legacy policy and attention-dedup files are consulted read-only when the corresponding generic file is absent; they are not copied. Generic Clef configuration is read only from the selected generic home; old Jcode selector endpoints/keys are never inherited or migrated. Review-host trust, selector data and preferences are not migrated automatically. An explicit home override disables the Telegram fallback.

To move a profile, use `telegram-alerts setup` in your own terminal or manually create a generic config containing only the intended Telegram safety fields. Do not copy the whole Jcode `config.toml`, which contains unrelated native settings. A fallback directory named `.jcode` is a compatibility source, not a runtime dependency.

### Set up Telegram

If the selected Alerts home already has a Telegram profile, skip setup. The generic CLI stores only Telegram credentials and alert settings. A legacy fallback reads only Telegram fields from `~/.jcode`; it does not read session state. This sender does not poll for replies.

For a new dedicated bot:

1. Open Telegram's official **@BotFather** and send `/newbot`. Choose an available bot username ending in `bot`.
2. Open your new bot, tap **Start**, and keep the private chat unmuted.
3. In your own terminal, run `telegram-alerts setup`. Paste the bot token only at the hidden prompt, never into an agent conversation or shell argument.
4. Send the exact `/start telegram_alerts_...` challenge shown by the helper to your bot. The helper validates your private chat, sends a test, and only then enables the channel.
5. Run `telegram-alerts status`; setup already sent its labeled test. For a separate authorized check, `telegram-alerts test` sends an illustrative message.

Setup defaults remote replies to **disabled** and refuses to replace an existing webhook. Do not rerun it casually over an already-linked bot. No tunnel, inbound port, Telegram API application registration, or bot group-admin permission is required.

## Legacy Jcode event adapter (explicit opt-in, deprecated)

The following event/formatting features are available only through `telegram-alerts-jcode`, a separate external adapter. The generic `telegram-alerts` CLI, its `jcode-telegram` alias, and `/telegram` skill neither read native Jcode sessions nor emit lifecycle alerts. Generic `alert`, `event`, `policy`, `selector`, and native-session preview commands are intentionally absent from that core CLI. `JCODE_HOOK_*` values are consumed only when the explicit adapter's `event` or `alert` command is invoked.

The adapter is not installed into native configuration by default. For a fresh opt-in, select the native home and invoke the deprecated hook installer; it registers the separate adapter executable, not the generic alias:

```sh
TELEGRAM_ALERTS_HOME="$HOME/.jcode" telegram-alerts-hook install
TELEGRAM_ALERTS_HOME="$HOME/.jcode" telegram-alerts-hook status
```

To retire the managed integration instead, run `TELEGRAM_ALERTS_HOME="$HOME/.jcode" telegram-alerts-hook uninstall`. If an existing managed registration points to the former `telegram-alerts` executable, inspect its ownership and uninstall it before reinstalling with the explicit adapter: the installer refuses to change an already-owned command in place. It removes only manifest-owned hooks and preserves foreign entries. Existing manual event hooks that call `jcode-telegram alert|event` must be removed or explicitly migrated to `telegram-alerts-jcode`; do not leave them pointed at the generic alias.

The generic alias continues to use the same home resolution as `telegram-alerts`, including `TELEGRAM_ALERTS_HOME > JCODE_HOME > ~/.config/telegram-alerts`; it never loads native session data.

## Legacy event working folder, duration and request context

In legacy Jcode event alerts, the `📁` line shows the native session working-folder path rather than guessing a project name from its last component or an arbitrary session name. Generic `update` displays only the caller-supplied explicit project; generic `attention` displays no project or invocation CWD. In event alerts, your home directory is abbreviated as `~`; long paths are shortened from the left while retaining the leaf. Missing folder metadata is labeled unavailable, never replaced with the observer process's own directory.

This is the session's working folder, **not necessarily the repository a tool last edited**. For example, a session started in one checkout can work on a sibling checkout without changing its native folder. Start Jcode in the intended project if that distinction matters. No repository scanning, tool-output mining or arbitrary-session-name inference is performed.

Durations use minutes and seconds, such as `1m 35s` and `61m 1s`, rounded to the nearest second. Unknown/malformed duration is labeled unavailable.

`Asked` remains useful when a request is safely matched to the successful turn. It is omitted entirely when no usable request context is available, instead of spending space on a context-unavailable placeholder. In brief alerts, the result takes priority over the request excerpt. Request matching is not weakened to fill an empty section.

### Originating-chat labels in legacy event alerts

Legacy Jcode event alerts and saved-session previews may show a `🏷 Session:` line when a native session ID is available. Generic explicit attention deliberately never displays a session ID or saved session name. The legacy line contains:

- Named chat: `Storage migration [snail]`.
- Unnamed chat: its native short name, such as `snail`.
- Unavailable or unsafe metadata: a stable `chat-` identifier derived from the session ID, such as `chat-12ab34cd`. This is a display label, not an argument accepted by Jcode's CLI.

The title follows Jcode's explicit-name precedence: `custom_title`, then `save_label` only when `saved` is true. Generated summaries are not used. The short name identifies the chat even when several agents share a working folder. These are originating-chat labels, not proof of the last repository edited or the current task branch.

Rename through Jcode's normal interface or its native CLI, then preview without sending:

```sh
jcode session rename snail "Storage migration"
telegram-alerts-jcode preview --session SESSION_ID
```

Use the full session ID for the preview. Names are read again for each alert, including native journal updates, so renaming or clearing a title needs no helper restart. Snapshot reads are bounded to 128 MiB and journals to 32 MiB. Unreadable, oversized or malformed metadata falls back to the short session-ID label rather than guessing a title.

The line is single-line and redacted before shortening. Brief allows 2 words / 40 characters, contextual 5 / 80, expanded 8 / 120, within the existing whole-alert caps. A title is shortened first so the identifying suffix survives. Paths in titles remain redacted. Avoid confidential titles because this metadata is forwarded to your configured Telegram destination. This display change does not alter Clef's selection rules, cooldowns or explicit-attention delivery.

**Privacy:** the legacy event folder line intentionally reveals bounded working-directory metadata to your configured Telegram destination. Generic updates show a project only when the caller explicitly supplies it. Home abbreviation is not anonymization. Credential-shaped values are still redacted there, and paths inside request/result text remain redacted. Preview first when folder names themselves are sensitive.

## Legacy event output links

This section applies only to the deprecated Jcode event adapter. Generic attention and Clef-gated update candidates accept explicit `links[].url` values and use the Inbox rewrite documented above.

Useful links in the current assistant output appear in a compact **🔗 Links** section. Both bare HTTPS URLs and ordinary Markdown links are supported. A GitHub pull request gets a clickable label such as **GitHub PR #42**. Other labels show the destination host and a bounded path, never an arbitrary Markdown label. Telegram preview cards are disabled.

Brief keeps up to one link, contextual two, and expanded three, within the existing whole-alert caps. Complete link labels and result text take priority over optional grouped-count text. The section uses current output only, or the current error on failure. Requests, session names, old successful output and lifecycle-only events do not supply links.

Only conservative ASCII HTTPS destinations are accepted. Query strings, fragments, percent escapes, embedded credentials, IP/local targets, nonstandard ports and credential-shaped targets are omitted. Code fences and secret-redacted lines cannot contribute links. The helper does not fetch destinations, resolve DNS, follow redirects or check repository visibility. A normal-looking hostname or repository path is not proof that its content is public.

**Privacy:** accepted link targets are intentionally sent to your configured Telegram destination, even though URLs remain redacted from ordinary request/result excerpts. Repository names and URL paths can themselves be sensitive. This is a forwarding feature, not a guarantee that a destination is safe or public. Preview first for confidential work.

## Routine Clef-gated updates

Submit a single concise candidate only when a material change is worth considering; do not narrate each tool call or ask a model to rewrite/summarize the update. The CLI sends a fixed YES/NO request to the configured versioned Clef resource. The caller's original sanitized `summary` is sent only on YES; NO is silent. Candidate text is untrusted data, not instructions. Clef receives only `summary`, optional `context`, and optional `project`; validated links are not relevance evidence and are not sent to the selector.

```sh
telegram-alerts update --key example/project:milestone:revision-42 <<'JSON'
{
  "summary": "The requested import flow now works; its verified limit is 20 MB.",
  "context": "The owner asked for a verified size limit before the rollout decision.",
  "project": "example/importer",
  "links": [{"label": "Details", "url": "https://github.com/example/importer/pull/42"}]
}
JSON
```

`summary` is required (≤400 characters); `context` is optional gate-only background (≤3,000), `project` is optional explicit display context (≤120), and `links` has up to three exact `label`/`url` objects. Project is never inferred from the shell's working directory. The complete UTF-8 JSON input is bounded to 8,192 bytes and rejects duplicate/unknown keys. Keep detailed evidence in the authorized Plannotator Inbox or review page and pass its exact URL under `links`; do not put transcripts or private source in `context`. Inbox rewriting is described below and preserves the outgoing URL bytes.

Configure Clef only in the selected generic home, with explicitly supplied endpoint/model and a private key file; no Jcode selector settings or key are inherited:

```sh
telegram-alerts clef status
telegram-alerts clef configure --endpoint https://decision.example --key-file /secure/path/clef.key --model model-alias --expected-model response-model
```

The command stores configuration metadata only and does not infer or send. `clef status` reports whether the update route is actually ready and separately reports that explicit `attention` bypasses Clef. This branch ships an empty versioned-resource manifest pending owner vet, so ordinary updates currently return a structured `prompt_unavailable` suppression with a nonzero exit before contacting Clef or Telegram. Missing configuration/key/prompt, busy service, malformed response, or transport failure also fails closed. A completed Clef NO or duplicate candidate returns a successful suppression; fail-closed errors exit nonzero. A selector failure or delivery ambiguity is not a Telegram delivery receipt; no automatic retry is made. Repeating the exact candidate is deduplicated after a decision attempt; changed content/context/project/links is a distinct candidate. Never change the key/content to retry an ambiguous send. The [prompt resource contract](docs/clef-prompt-resources.md) documents the package loader and owner-approval boundary.

A mandatory review/authentication link bypasses routine relevance only when the user/workflow explicitly requests that handoff: invoke the explicit `attention` command below. Neither summary wording nor a link alone auto-classifies a candidate as required. Do not use `attention` as a routine-update fallback just because Clef is unavailable.

## Explicit attention when the owner is needed

Legacy event alerts stay unchanged. For a genuine owner handoff, any agent can run this command from any shell or agent tool, **before waiting**:

```sh
telegram-alerts attention --key example/project:review:reviewed-head-sha <<'JSON'
{
  "context": "The proposed rollout is ready for owner review.",
  "needs_you": "Review the proposed ADR before the live cutover.",
  "recommendation": "Use a staged cutover because it preserves rollback.",
  "links": [{"label": "Review ADR", "url": "https://github.com/example/project/blob/reviewed-head-sha/docs/adrs/0001-rollout.md"}]
}
JSON
```

This is an illustrative shape, not a real pending request or a verified destination. The agent must supply the actual published revision and verify that the intended reviewer can access it. The command validates URL syntax offline; it does not fetch or prove publication, public visibility or authorization.

The command requires no Jcode environment or session ID and displays no inferred project or invocation working directory. A supplied `JCODE_SESSION_ID` is used only by configured legacy compatibility filters; if an include list is active without a matching ID, delivery fails closed. Neither the ID nor a saved session name is displayed. Required compatibility text fields remain `context` (400 characters) and `needs_you` (800); `recommendation` (600) and `links` (up to three exact `label`/`url` objects, labels 80 characters) are optional. Input is one UTF-8 JSON object, at most 8192 bytes, without duplicate/unknown keys. Their values are forwarded as body text under the neutral `🔔 Update` heading, without mandatory `Needs you` or `Context` labels. Put URLs in `links`, not text fields. For a smaller necessary decision, the optional owner workflow presents a Plannotator question card; the explicit attention send carries its precise request, recommendation and verified link.

Attention uses the same single neutral `🔔 Update` renderer as routine updates, not the legacy event verbosity profiles. It rejects oversized messages rather than cutting a decision or link. It sends a fresh message with normal notification requested, bypassing Clef relevance selection, routine duration thresholds, completion cooldowns and status-card edits. It respects a disabled Telegram profile and any configured compatibility session include/exclude filters, but never changes them. Telegram/phone mute settings can still prevent a visible or audible notification.

The key identifies one decision at one reviewed revision. Reuse it across continuation turns; include the repository and revision so unrelated work does not collide. Already-acknowledged keys return `already_sent` without contacting Telegram. The same key remains deduplicated across sessions sharing the destination. Only when the owner explicitly asks for another copy, repeat the command with `--resend`. A changed decision or reviewed revision needs a new key. Private fingerprint-only history is bounded to 256 active keys and expires after 30 days; active capacity fails closed. No raw request, URL, key or transcript is saved in that state.

Success prints JSON with `state: sent`, `response_confirmed` and `formatting_confirmed`; if an Inbox URL was rewritten, `url_rewrites` reports only the source and destination origins, not the path/query/fragment. An unavailable mapping is reported in `url_rewrite_warnings`. Duplicates print `state: already_sent`. Failures exit nonzero with a controlled diagnostic. Success requires the Telegram-returned message ID, text and exact bold/link entities. There are no automatic retries: after a timeout or unconfirmed response, delivery may already have occurred. A Telegram acknowledgment is not proof that the owner read or approved anything.

The existing conservative HTTPS URL rules remain the default. Plannotator Inbox URLs are the sole exception: for the exact registered loopback port, a read-only `~/.plannotator/inbox/inbox.json` supplies `tailscale.url`; the CLI rewrites only `http://localhost:<port>` and `http://127.0.0.1:<port>` links at send time. It preserves path/query/fragment bytes and never mutates the request. Set `TELEGRAM_ALERTS_INBOX_REGISTRY` to override the registry path or `TELEGRAM_ALERTS_INBOX_BASE_URL` to explicitly override the published base. If no trusted mapping exists, the local link is omitted with a warning and the alert still sends; no replacement is guessed. Other loopback URLs are not rewritten. Unsupported private/IP targets, non-443 ports, credential-shaped paths and query/fragment/signed links are rejected visibly, not silently replaced with `[link]`. Do not strip sensitive parameters to manufacture an apparently acceptable destination.

### Optional Plannotator owner workflow

Use the [versioned overlay](prompts/owner-workflow.md) and thin [owner-review skill](skills/owner-review/SKILL.md) for a make-it-right quality bar, one global Markdown folder standard, Plannotator/Tailscale document reviews and necessary small-decision cards. Inbox questions use a [packaged on-demand reference](skills/owner-review/references/inbox.md), not a second skill or an always-on connection. The [adoption guide](docs/owner-workflow.md) explains private backups, installation, cached skills, scoped results and rollback. Wheels include the `/telegram` skill plus the optional owner-review overlay, skill, and reference as data files. Package/hook installation does not overwrite agent instructions or enable/start Inbox.

For a separate non-Inbox review origin, explicitly configure one exact trusted tailnet host with `telegram-alerts review-host HOST`, then declare its actual port with `attention --review-port PORT`. This exception accepts only that configured host, declared port and HTTPS root origin. A declared review requires a matching link. It is not needed for URLs rewritten from the Plannotator Inbox registry. See [ADR 0002](docs/adrs/0002-private-owner-reviews.md).

Normal installed Jcode `v0.98.1` reloaded an edited overlay in an actual resumed-session check without compaction. Custom SDK prompts and cached skill catalogs differ, so the guide includes an installed-file fallback. Prompt guidance is not a guaranteed tool-call gate.

No native Jcode patch, model, daemon, reply poller or automatic approval execution is added. Existing native remote-reply behavior is unchanged: use Plannotator or GitHub for the answer, not an uncorrelated Telegram reply. [ADR 0001](docs/adrs/0001-explicit-attention-alerts.md) remains the original attention design.

## Legacy event verbosity

These profiles affect only optional legacy event messages; explicit attention uses its own bounded layout.

```sh
telegram-alerts-jcode verbosity expanded
telegram-alerts-jcode verbosity contextual
telegram-alerts-jcode verbosity brief
telegram-alerts-jcode verbosity
```

| Profile | Whole-alert cap | Content |
| --- | --- | --- |
| brief | 25 words / 320 characters | Status, working folder/duration, result and a request excerpt when space permits |
| contextual | 60 words / 800 characters | More request/result context, stated checks and next action when present |
| expanded | 100 words / 1,400 characters | Fuller request/result excerpts, stated checks and next action when present |

Character caps count Unicode code points, not bytes or visual graphemes. Telegram bold offsets use UTF-16 units separately. Emojis and layout count toward the caps. Brief keeps section content on the label's line; contextual and expanded put it below the label. Failed turns use ❌ and saved-session previews use 👀. The neutral 🔎 does not imply that checks passed.

Clef-selected completions use a separate bounded literal-copy layout, not these excerpt profiles. Long replies are visibly clipped, with complete accepted links retained in a footer. Other alerts keep their existing profiles.

Changing verbosity hot-reloads and preserves native credentials, reply settings, ambient settings, and hook thresholds. The private preference file is `~/.config/telegram-alerts/notifications/telegram-settings.json`. Missing preferences default to expanded; invalid preferences fall back to brief rather than increasing disclosure.

## Legacy event notification policy

This policy controls the optional legacy Jcode event adapter. Delivery policy is separate from verbosity. `telegram-alerts-jcode policy` queries it without changes. Add a preset name to select the enabled events:

```sh
telegram-alerts-jcode policy
telegram-alerts-jcode policy balanced
telegram-alerts-jcode policy attention
telegram-alerts-jcode policy activity
```

| Preset | Enabled event kinds |
| --- | --- |
| balanced, the default | `completion`, `error` |
| attention | `error` only |
| activity | `session_start`, `turn_start`, `completion`, `error`, `session_end` |

Selecting a preset resets event on/off overrides, but preserves other policy settings. Routine lifecycle events are silent by default. Silent means without sound, not absent from the chat or notification tray.

```sh
telegram-alerts-jcode policy balanced --cooldown-seconds 300 --error-repeat-seconds 300
telegram-alerts-jcode policy --enable session_end --silent session_end
telegram-alerts-jcode policy --disable completion
telegram-alerts-jcode policy --audible error
```

Without the optional selector, ordinary successful-turn messages must meet the hook duration threshold, 30 seconds by default. Within a session's completion cooldown, further qualifying completions are counted instead of sent. The next eligible completion includes a bounded `Grouped:` count. There is no background timer or delayed digest, so a suppressed final completion is not automatically sent later.

Distinct errors bypass the completion threshold and cooldown. Repeats of the same error are suppressed for the error-repeat interval. A new error reason remains eligible. Cooldowns are per session, not per project or bot. Set an interval to `0` to disable that suppression.

### Legacy status card

```sh
telegram-alerts-jcode policy activity --status-card on
telegram-alerts-jcode policy balanced --status-card off
```

Card mode creates a silent session message, then edits it for enabled lifecycle states. Enabled completions update the card even for short turns or within the ordinary message cooldown, so a working card can return to a finished state. Errors still create fresh attention messages, with a best-effort update of an existing card. A failed edit is not automatically retried or replaced by another routine message. Cards are scoped to a session and the configured destination. Changing destinations does not edit the old destination's card.

`balanced --status-card on` shows completion/error activity only. Enable the activity preset for start/working/closure updates. Cards are best effort: detached hook processes can arrive out of order, and process crashes do not produce a guaranteed closure event.

### Legacy session selection

These filters apply to the external Jcode event adapter. On generic attention, a supplied JCODE_SESSION_ID is optional context for these filters only; no session name or ID is rendered.

```sh
telegram-alerts-jcode policy --include-session YOUR_SESSION_ID
telegram-alerts-jcode policy --exclude-session ANOTHER_SESSION_ID
telegram-alerts-jcode policy --clear-session-filters
```

Repeated include/exclude options replace the corresponding list. Exclusion wins. Without the optional selector, there is no automatic root/worker detection. The hook payload has no reliable worker identity, and saved parent IDs also include user-created forks. The selector uses saved metadata conservatively: parented sessions are excluded unless their exact ID is explicitly included. Unavailable context is not guessed.

Policy settings are private local state in `~/.config/telegram-alerts/notifications/telegram-policy.json`. Malformed or unsafe policy/state files fail closed for outgoing alerts rather than reverting to noisier defaults.

### Legacy Clef completion filter (deprecated)

The [legacy Jcode selector runbook](docs/plans/2026-10-24-clef-selector-setup.md) covers the optional Clef event adapter for existing hook installations. It is not needed by generic attention, and the generic home does not include Jcode session data.

Clef answers one typed YES/NO question for a uniquely matched successful owner-root turn. A YES sends the sanitized original public reply and independently validated original links, bypassing the usual completion duration threshold and cooldown. A NO stays quiet. Known child/automated turns and stale or ambiguous source are excluded. Errors and explicit `attention` are not gated by Clef.

This opt-in mode sends bounded sanitized context to the configured decision service and retains private content for up to 100 eligible turns for review. There is no Qwen rewrite, cloud fallback, automatic retry or unfiltered fallback when selection fails. Read-only `telegram-alerts-jcode selector` reports counts, not proof of delivery or usefulness. `telegram-alerts-jcode selector off` returns to **quiet completions**, preserving errors, explicit attention and collected evidence. See the [rollout observations and limits](docs/plans/2026-10-24-clef-live-rollout.md).

### Preview and test

These commands preview or deliberately send legacy event-format examples; they are not required for generic owner handoffs. `telegram-alerts attention --help` documents the generic request schema without sending.

```sh
telegram-alerts-jcode preview
telegram-alerts-jcode preview --verbosity brief
telegram-alerts-jcode preview --event turn_start
telegram-alerts-jcode preview --event error
telegram-alerts-jcode preview --session YOUR_SESSION_ID --verbosity expanded
```

`telegram-alerts-jcode preview` never sends. Without `--session`, it uses illustrative legacy event text. Saved-session previews are labeled as previews, with a placeholder duration rather than an inferred status. Lifecycle previews contain metadata only, never an earlier turn's prompt or result. Terminal previews show text and spacing; Telegram applies the native bold formatting. The generic `telegram-alerts preview` instead shows a neutral update example without live selection, and generic `telegram-alerts test` deliberately sends that labeled example without reading native session state. A one-off adapter `--verbosity` override does not change the saved preference.

## Legacy Jcode trigger rules

- Default ordinary messages: successful turns lasting **at least 30 seconds** can notify, subject to the five-minute per-session completion interval. Distinct errors can notify regardless of duration.
- A turn is one model response cycle. Without the optional selector, worker/swarm turns can notify too.
- Completion grouping and repeated-error suppression are configurable. There is no focus check. The optional selector adds conservative root-turn eligibility and bypasses completion grouping only for selected updates.
- These profiles affect only this extension's alerts, not native ambient summaries, permission notifications, or inbound replies.
- Jcode's desktop notification thresholds do not throttle this extension.
- Delivery is best effort, with a network timeout and no automatic retry.
- Normal session closure is not a crash or task-success signal. There are no invented needs-input, cancellation or crash events. Native ambient permission/summary notifications remain a separate Jcode route; this extension does not duplicate them.
- `telegram-alerts-jcode alert` remains an alias for event dispatch within the explicit adapter. New managed hooks use `telegram-alerts-jcode event`; generic `jcode-telegram alert|event` is no longer supported.

This project was developed against **Jcode v0.98.1**. In that version, a real `jcode run --json` bypassed the turn hook while `--ndjson` invoked it. Use `--ndjson` for scripted notifications. This extension does not patch Jcode itself. Recheck behavior when upgrading Jcode.

## Privacy and security

**Task/result excerpts are intentionally sent to your configured Telegram destination.** Use a private bot you trust. Read [SECURITY.md](SECURITY.md) before enabling this for sensitive work.

Only the explicit legacy adapter's excerpt formatting reads public text from a matching saved session. It requires a unique corresponding assistant response before including the request. Missing/ambiguous context is unavailable. Failed turns omit unbound prompt context and use the current error rather than a stale successful response. Reasoning, images, and shell/tool results are not exported as request context. The generic CLI and skill do not perform these reads.

The optional selector separately reads a bounded native snapshot and journal to recover the complete public final behind the hook excerpt. It sends bounded sanitized task context, the current final and a previous public final to the configured Clef service. Its private `telegram-selector-state.json` retains those inputs and allowed original links for the configured sample, unlike the fingerprint-only routine receipts below. Protect this file and do not publish it. Full limits and the distinction between selection, delivery and human usefulness are in the [selector runbook](docs/plans/2026-10-24-clef-selector-setup.md).

Code fences, paths within request/result text, URLs, email addresses, common credential forms, known bot credentials, and labeled secret values are redacted on a **best-effort basis**. The explicit working-folder metadata line is the intentional path-display exception described above. This is not comprehensive data-loss prevention and does not make arbitrary private prose safe to forward. Preview before using it with confidential projects.

Tokens, configuration/backups, preferences, and diagnostic receipts stay outside this repository. Config/backups and helper state files are written with mode 0600. Backups can contain credentials. Never upload them to issues, pull requests, or build artifacts.

When the explicit adapter runs, its latest receipt at the selected home (`notifications/telegram-last-alert.json`) stores state, timestamps, one-way fingerprints, profile/length metadata, and optional server text/bold acknowledgment. It does not store raw message text, bot token, destination, or raw session ID. Later turns can overwrite it. The generic CLI does not read this legacy event receipt. Server acknowledgment does not prove phone notification visibility or that a message was read.

Policy suppression/card state is stored separately in `~/.config/telegram-alerts/notifications/telegram-policy-state.json`. It contains hashed session/destination keys, counters, timestamps, error fingerprints and card message IDs, not message contents. Explicit session filters are intentionally stored in the private policy file. Protect both files and their parent directory.

### Legacy hook adapter and duplicate Moshi registrations

`telegram-alerts-hook` is a deprecated Jcode-only maintenance tool, not part of the generic owner-handoff flow. It requires an explicit home selection so it cannot edit the generic Alerts profile by accident:

```sh
TELEGRAM_ALERTS_HOME="$HOME/.jcode" telegram-alerts-hook dedupe-moshi
```

The helper removes only exact repeated `moshi-hook jcode-hook` command strings from the four lifecycle arrays, keeping the first occurrence. It never invokes Moshi, changes its settings or removes other commands. A no-op does not create a backup. Actual edits use a private config backup and full semantic checks. Duplicate adapter calls do not establish duplicate phone pushes, so do not use this as a phone-delivery test.

## Update and remove

Before upgrading, check the release notes and install a chosen tag or verified release wheel into the same generic Alerts environment. New installations do not register Jcode hooks. The `jcode-telegram` alias now accepts only the generic CLI, so old lifecycle registrations that call it must be removed or deliberately reinstalled through `telegram-alerts-hook` to invoke `telegram-alerts-jcode`. The alias still uses the same home resolver. The hook installer requires an explicit home and is not recommended for new workflows.

```sh
telegram-alerts --version
TELEGRAM_ALERTS_HOME="$HOME/.jcode" telegram-alerts-hook status
python -m pip uninstall agent-telegram-alerts
```

Hook removal leaves unrelated hooks untouched. `telegram-alerts disable` disables only the selected Telegram Alerts profile; it does not modify Jcode's native settings unless the operator explicitly sets `TELEGRAM_ALERTS_HOME` to a native Jcode home.

`TELEGRAM_ALERTS_HOME` selects the writable profile; deprecated `JCODE_HOME` is honored only when it is unset. A process-level `JCODE_HOOK_TURN_END` override remains an external input for the optional legacy Jcode event adapter.

## Development and releases

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python -m build
```

Tests use synthetic data and temporary Jcode homes, not maintainer credentials. CI also builds and installs the actual wheel and exercises public commands. See [CONTRIBUTING.md](CONTRIBUTING.md), [release management](docs/RELEASING.md), and [verification](docs/VERIFICATION.md).

Conventional Commit titles drive version/changelog PRs. Merging a passing release PR creates a versioned GitHub release with wheel/source archives and checksums. Dependabot maintains GitHub Actions and build-tool dependencies. Runtime dependencies remain empty.

## References

- [Jcode source](https://github.com/1jehuang/jcode)
- [Version-matched lifecycle hook documentation](https://github.com/1jehuang/jcode/blob/1c7426eb1/docs/HOOKS.md)
- [Telegram bot tutorial](https://core.telegram.org/bots/tutorial)
- [Telegram sendMessage and entities](https://core.telegram.org/bots/api#sendmessage)

MIT licensed. See [LICENSE](LICENSE).
