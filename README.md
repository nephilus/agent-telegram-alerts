# Jcode Telegram Alerts

[![CI](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nephilus/jcode-telegram-alerts)](https://github.com/nephilus/jcode-telegram-alerts/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Unofficial event-aware Telegram alerts for [Jcode](https://github.com/1jehuang/jcode).** Get task context, readable results and clickable links. Default alerts need no model call; an optional Clef filter can select which completed turns deserve an update.

> This community extension is not part of, endorsed by, or supported by the Jcode maintainers. It uses Jcode's native lifecycle hook and Telegram credentials. It does not add a remote-command server.

## What it does

- Observes session start, turn start, turn end and normal session closure.
- Sends qualifying completion/error alerts by default, with quiet routine activity, per-session cooldowns and repeated-error suppression.
- Offers an optional editable session status card instead of a stream of routine messages.
- Offers **brief**, **contextual**, and **expanded** profiles. Expanded is the default.
- Uses bold headings, readable section spacing, useful emojis, and compact clickable output links.
- Sends explicit owner handoffs immediately with Context, a precise request, a recommendation and verified links.
- Optionally asks Clef to select completion updates, forwarding the original reply rather than generating another summary. Explicit attention and errors remain independent.
- Links a dedicated bot through a private-chat challenge and hidden terminal token entry.
- Adds/removes its own hook without replacing unrelated hooks or Telegram settings.
- Uses only the Python standard library at runtime. Python **3.11+** and Linux/macOS are supported.

Illustrative expanded alert:

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

Use a dedicated virtual environment. Installation does not access Telegram or change Jcode's configuration until you explicitly register the hook or run setup.

```sh
python3 -m venv "$HOME/.local/share/jcode-telegram-alerts/venv"
. "$HOME/.local/share/jcode-telegram-alerts/venv/bin/activate"
python -m pip install "git+https://github.com/nephilus/jcode-telegram-alerts.git@v0.6.1"
jcode-telegram --version
jcode-telegram preview
jcode-telegram-hook install
```

Alternatively, download the wheel and `SHA256SUMS` from a [GitHub release](https://github.com/nephilus/jcode-telegram-alerts/releases), verify its checksum, and install the local wheel with `python -m pip install /path/to/package.whl`. No PyPI package is published by this repository's automation.

Keep the virtual environment at its installed location: the hook records the executable's absolute path. It does not depend on an interactive shell's PATH or an activated environment after registration. Use `jcode-telegram-hook --help` for an explicit executable path or a custom successful-turn threshold. Do not move/delete the environment before unregistering the hook.

For a manually registered prototype, use explicit migration rather than silently adopting an unowned hook:

```sh
jcode-telegram-hook install --from-command "$HOME/.local/bin/jcode-telegram"
```

Use the actual old executable path. Migration requires one direct legacy `alert` command at that path and refuses ambiguous or shell-wrapped commands. It preserves Moshi and native Telegram credentials. For a manifest-owned 0.1 installation, uninstall its hook before upgrading, then install the new lifecycle hooks. `--events turn_end` selects completion-only registration when needed.

Old installations may have created a group-writable notifications directory. Policy state requires an owner-controlled directory. If necessary, inspect ownership and symlinks first, then use `chmod 700 "$HOME/.jcode/notifications"`. Never upload configuration backups, which can contain credentials.

### Set up Telegram

If Jcode already has a working Telegram channel, skip setup. This helper reuses that channel's native credentials. Avoid running a second `getUpdates` poller beside Jcode's native reply poller.

For a new dedicated bot:

1. Open Telegram's official **@BotFather** and send `/newbot`. Choose an available bot username ending in `bot`.
2. Open your new bot, tap **Start**, and keep the private chat unmuted.
3. In your own terminal, run `jcode-telegram setup`. Paste the bot token only at the hidden prompt, never into an agent conversation or shell argument.
4. Send the exact `/start jcode_...` challenge shown by the helper to your bot. The helper validates your private chat, sends a test, and only then enables the channel.
5. Run `jcode-telegram status`. Let a normal Jcode turn exceed 30 seconds and confirm the notification in your Telegram app. The default completion interval is five minutes per session.

Setup defaults native remote replies to **disabled** and refuses to replace an existing webhook. Do not rerun it casually over an already-linked bot. No tunnel, inbound port, Telegram API application registration, or bot group-admin permission is required.

## Working folder, duration and request context

The `📁` line shows the native session working-folder path rather than guessing a project name from its last component or an arbitrary session name. Your home directory is abbreviated as `~`; long paths are shortened from the left while retaining the leaf. Missing folder metadata is labeled unavailable, never replaced with the observer process's own directory.

This is the session's working folder, **not necessarily the repository a tool last edited**. For example, a session started in one checkout can work on a sibling checkout without changing its native folder. Start Jcode in the intended project if that distinction matters. No repository scanning, tool-output mining or arbitrary-session-name inference is performed.

Durations use minutes and seconds, such as `1m 35s` and `61m 1s`, rounded to the nearest second. Unknown/malformed duration is labeled unavailable.

`Asked` remains useful when a request is safely matched to the successful turn. It is omitted entirely when no usable request context is available, instead of spending space on a context-unavailable placeholder. In brief alerts, the result takes priority over the request excerpt. Request matching is not weakened to fill an empty section.

### Identify the originating chat

Alerts with a valid native session ID show the same `🏷 Session:` line in selected updates, completion/error alerts, enabled lifecycle alerts, saved-session previews and explicit **Needs you** messages:

- Named chat: `Storage migration [snail]`.
- Unnamed chat: its native short name, such as `snail`.
- Unavailable or unsafe metadata: a stable `chat-` identifier derived from the session ID, such as `chat-12ab34cd`. This is a display label, not an argument accepted by Jcode's CLI.

The title follows Jcode's explicit-name precedence: `custom_title`, then `save_label` only when `saved` is true. Generated summaries are not used. The short name identifies the chat even when several agents share a working folder. These are originating-chat labels, not proof of the last repository edited or the current task branch.

Rename through Jcode's normal interface or its native CLI, then preview without sending:

```sh
jcode session rename snail "Storage migration"
jcode-telegram preview --session SESSION_ID
```

Use the full session ID for the preview. Names are read again for each alert, including native journal updates, so renaming or clearing a title needs no helper restart. Snapshot reads are bounded to 128 MiB and journals to 32 MiB. Unreadable, oversized or malformed metadata falls back to the short session-ID label rather than guessing a title.

The line is single-line and redacted before shortening. Brief allows 2 words / 40 characters, contextual 5 / 80, expanded 8 / 120, within the existing whole-alert caps. A title is shortened first so the identifying suffix survives. Paths in titles remain redacted. Avoid confidential titles because this metadata is forwarded to your configured Telegram destination. This display change does not alter Clef's selection rules, cooldowns or explicit-attention delivery.

**Privacy:** the folder line intentionally reveals bounded working-directory metadata to your configured Telegram destination. Home abbreviation is not anonymization. Credential-shaped values are still redacted there, and paths inside request/result text remain redacted. Preview first when folder names themselves are sensitive.

## Clickable output links

Useful links in the current assistant output appear in a compact **🔗 Links** section. Both bare HTTPS URLs and ordinary Markdown links are supported. A GitHub pull request gets a clickable label such as **GitHub PR #42**. Other labels show the destination host and a bounded path, never an arbitrary Markdown label. Telegram preview cards are disabled.

Brief keeps up to one link, contextual two, and expanded three, within the existing whole-alert caps. Complete link labels and result text take priority over optional grouped-count text. The section uses current output only, or the current error on failure. Requests, session names, old successful output and lifecycle-only events do not supply links.

Only conservative ASCII HTTPS destinations are accepted. Query strings, fragments, percent escapes, embedded credentials, IP/local targets, nonstandard ports and credential-shaped targets are omitted. Code fences and secret-redacted lines cannot contribute links. The helper does not fetch destinations, resolve DNS, follow redirects or check repository visibility. A normal-looking hostname or repository path is not proof that its content is public.

**Privacy:** accepted link targets are intentionally sent to your configured Telegram destination, even though URLs remain redacted from ordinary request/result excerpts. Repository names and URL paths can themselves be sensitive. This is a forwarding feature, not a guarantee that a destination is safe or public. Preview first for confidential work.

## Explicit attention when the owner is needed

Routine alerts stay unchanged. When an agent genuinely needs owner input, it can run this command through Jcode's normal bash tool, **before waiting**:

```sh
jcode-telegram attention --key example/project:review:reviewed-head-sha <<'JSON'
{
  "context": "The proposed rollout is ready for owner review.",
  "needs_you": "Review the proposed ADR before the live cutover.",
  "recommendation": "Use a staged cutover because it preserves rollback.",
  "links": [{"label": "Review ADR", "url": "https://github.com/example/project/blob/reviewed-head-sha/docs/adrs/0001-rollout.md"}]
}
JSON
```

This is an illustrative shape, not a real pending request or a verified destination. The agent must supply the actual published revision and verify that the intended reviewer can access it. The command validates URL syntax offline; it does not fetch or prove publication, public visibility or authorization.

The command requires the native `JCODE_SESSION_ID` environment variable and displays the command's current working directory, which may differ from the session's original folder. An explicit saved session name is included when safely readable. Required text fields are `context` (400 characters) and `needs_you` (800); `recommendation` (600) and `links` (up to three exact `label`/`url` objects, labels 80 characters) are optional. Input is one UTF-8 JSON object, at most 8192 bytes, without duplicate/unknown keys. Put URLs in `links`, not text fields. For a smaller necessary decision, the optional owner workflow presents a Plannotator question card; the alert carries its precise request, recommendation and verified link.

Attention uses its own bounded layout, not the routine verbosity profiles. It rejects oversized messages rather than cutting a decision or link. It sends a fresh message with normal notification requested, bypassing routine duration thresholds, completion cooldowns and status-card edits. It still respects a disabled native Telegram channel and session include/exclude filters. It never changes those settings. Telegram/phone mute settings can still prevent a visible or audible notification.

The key identifies one decision at one reviewed revision. Reuse it across continuation turns; include the repository and revision so unrelated work does not collide. Already-acknowledged keys return `already_sent` without contacting Telegram. The same key remains deduplicated across sessions sharing the destination. Only when the owner explicitly asks for another copy, repeat the command with `--resend`. A changed decision or reviewed revision needs a new key. Private fingerprint-only history is bounded to 256 active keys and expires after 30 days; active capacity fails closed. No raw request, URL, key or transcript is saved in that state.

Success prints JSON with `state: sent`, `response_confirmed` and `formatting_confirmed`; duplicates print `state: already_sent`. Failures exit nonzero with a controlled diagnostic. Success requires the Telegram-returned message ID, text and exact bold/link entities. There are no automatic retries: after a timeout or unconfirmed response, delivery may already have occurred. A Telegram acknowledgment is not proof that the owner read or approved anything.

The existing conservative URL rules remain the default. Unsupported private/IP targets, non-443 ports, credential-shaped paths and query/fragment/signed links are rejected visibly, not silently replaced with `[link]`. Do not strip sensitive parameters to manufacture an apparently acceptable destination.

### Optional Plannotator owner workflow

Use the [versioned overlay](prompts/owner-workflow.md) and thin [owner-review skill](skills/owner-review/SKILL.md) for a make-it-right quality bar, one global Markdown folder standard, Plannotator/Tailscale document reviews and necessary small-decision cards. Inbox questions use a [packaged on-demand reference](skills/owner-review/references/inbox.md), not a second skill or an always-on connection. The [adoption guide](docs/owner-workflow.md) explains private backups, installation, cached skills, scoped results and rollback. Wheels package the overlay, skill and reference as opt-in data. Package/hook installation does not overwrite agent instructions or enable/start Inbox.

For native Plannotator's non-443 origin, explicitly configure one exact trusted tailnet host with `jcode-telegram review-host HOST`. Then declare its actual port for each handoff with `attention --review-port PORT`. This attention-only exception accepts only the configured host, declared port and HTTPS root origin. A declared review requires a matching link. Routine output extraction remains unchanged. See [ADR 0002](docs/adrs/0002-private-owner-reviews.md).

Normal installed Jcode `v0.98.1` reloaded an edited overlay in an actual resumed-session check without compaction. Custom SDK prompts and cached skill catalogs differ, so the guide includes an installed-file fallback. Prompt guidance is not a guaranteed tool-call gate.

No native Jcode patch, model, daemon, reply poller or automatic approval execution is added. Existing native remote-reply behavior is unchanged: use Plannotator or GitHub for the answer, not an uncorrelated Telegram reply. [ADR 0001](docs/adrs/0001-explicit-attention-alerts.md) remains the original attention design.

## Choose verbosity

```sh
jcode-telegram verbosity expanded
jcode-telegram verbosity contextual
jcode-telegram verbosity brief
jcode-telegram verbosity
```

| Profile | Whole-alert cap | Content |
| --- | --- | --- |
| brief | 25 words / 320 characters | Status, working folder/duration, result and a request excerpt when space permits |
| contextual | 60 words / 800 characters | More request/result context, stated checks and next action when present |
| expanded | 100 words / 1,400 characters | Fuller request/result excerpts, stated checks and next action when present |

Character caps count Unicode code points, not bytes or visual graphemes. Telegram bold offsets use UTF-16 units separately. Emojis and layout count toward the caps. Brief keeps section content on the label's line; contextual and expanded put it below the label. Failed turns use ❌ and saved-session previews use 👀. The neutral 🔎 does not imply that checks passed.

Clef-selected completions use a separate bounded literal-copy layout, not these excerpt profiles. Long replies are visibly clipped, with complete accepted links retained in a footer. Other alerts keep their existing profiles.

Changing verbosity hot-reloads and preserves native credentials, reply settings, ambient settings, and hook thresholds. The private preference file is `~/.jcode/notifications/telegram-settings.json`. Missing preferences default to expanded; invalid preferences fall back to brief rather than increasing disclosure.

## Choose which events notify

Delivery policy is separate from verbosity. `jcode-telegram policy` queries it without changes. Add a preset name to select the enabled events:

```sh
jcode-telegram policy
jcode-telegram policy balanced
jcode-telegram policy attention
jcode-telegram policy activity
```

| Preset | Enabled event kinds |
| --- | --- |
| balanced, the default | `completion`, `error` |
| attention | `error` only |
| activity | `session_start`, `turn_start`, `completion`, `error`, `session_end` |

Selecting a preset resets event on/off overrides, but preserves other policy settings. Routine lifecycle events are silent by default. Silent means without sound, not absent from the chat or notification tray.

```sh
jcode-telegram policy balanced --cooldown-seconds 300 --error-repeat-seconds 300
jcode-telegram policy --enable session_end --silent session_end
jcode-telegram policy --disable completion
jcode-telegram policy --audible error
```

Without the optional selector, ordinary successful-turn messages must meet the hook duration threshold, 30 seconds by default. Within a session's completion cooldown, further qualifying completions are counted instead of sent. The next eligible completion includes a bounded `Grouped:` count. There is no background timer or delayed digest, so a suppressed final completion is not automatically sent later.

Distinct errors bypass the completion threshold and cooldown. Repeats of the same error are suppressed for the error-repeat interval. A new error reason remains eligible. Cooldowns are per session, not per project or bot. Set an interval to `0` to disable that suppression.

### Optional status card

```sh
jcode-telegram policy activity --status-card on
jcode-telegram policy balanced --status-card off
```

Card mode creates a silent session message, then edits it for enabled lifecycle states. Enabled completions update the card even for short turns or within the ordinary message cooldown, so a working card can return to a finished state. Errors still create fresh attention messages, with a best-effort update of an existing card. A failed edit is not automatically retried or replaced by another routine message. Cards are scoped to a session and the configured destination. Changing destinations does not edit the old destination's card.

`balanced --status-card on` shows completion/error activity only. Enable the activity preset for start/working/closure updates. Cards are best effort: detached hook processes can arrive out of order, and process crashes do not produce a guaranteed closure event.

### Explicit session selection

```sh
jcode-telegram policy --include-session YOUR_SESSION_ID
jcode-telegram policy --exclude-session ANOTHER_SESSION_ID
jcode-telegram policy --clear-session-filters
```

Repeated include/exclude options replace the corresponding list. Exclusion wins. Without the optional selector, there is no automatic root/worker detection. The hook payload has no reliable worker identity, and saved parent IDs also include user-created forks. The selector uses saved metadata conservatively: parented sessions are excluded unless their exact ID is explicitly included. Unavailable context is not guessed.

Policy settings are private local state in `~/.jcode/notifications/telegram-policy.json`. Malformed or unsafe policy/state files fail closed for outgoing alerts rather than reverting to noisier defaults.

### Optional Clef completion filter

The [setup and recovery runbook](docs/plans/2026-10-24-clef-selector-setup.md) covers installing this source into the **actual saved hook runtime**, configuring an existing maintained Clef endpoint and private key file, monitoring the first 100 eligible turns, and rolling back. This feature is not in published v0.6.1; the local source build still reports that version, so check that the saved executable recognizes `selector` rather than relying on `--version` or hook ownership status.

Clef answers one typed YES/NO question for a uniquely matched successful owner-root turn. A YES sends the sanitized original public reply and independently validated original links, bypassing the usual completion duration threshold and cooldown. A NO stays quiet. Known child/automated turns and stale or ambiguous source are excluded. Errors and explicit `attention` are not gated by Clef.

This opt-in mode sends bounded sanitized context to the configured decision service and retains private content for up to 100 eligible turns for review. There is no Qwen rewrite, cloud fallback, automatic retry or unfiltered fallback when selection fails. Read-only `jcode-telegram selector` reports counts, not proof of delivery or usefulness. `jcode-telegram selector off` returns to **quiet completions**, preserving errors, explicit attention and collected evidence. See the [rollout observations and limits](docs/plans/2026-10-24-clef-live-rollout.md).

### Preview and test

```sh
jcode-telegram preview
jcode-telegram preview --verbosity brief
jcode-telegram preview --event turn_start
jcode-telegram preview --event error
jcode-telegram preview --session YOUR_SESSION_ID --verbosity expanded
jcode-telegram test --verbosity expanded
```

`preview` never sends. Without `--session`, it uses illustrative sample text. Saved-session previews are labeled as previews, with a placeholder duration rather than an inferred status. Lifecycle previews contain metadata only, never an earlier turn's prompt or result. Terminal previews show text and spacing; Telegram applies the native bold formatting. `test` deliberately sends a labeled illustrative preview, bypassing the delivery policy. Its explanatory prefix is outside the rendered profile cap. A one-off `--verbosity` override does not change the saved preference.

## Trigger rules and native support

- Default ordinary messages: successful turns lasting **at least 30 seconds** can notify, subject to the five-minute per-session completion interval. Distinct errors can notify regardless of duration.
- A turn is one model response cycle. Without the optional selector, worker/swarm turns can notify too.
- Completion grouping and repeated-error suppression are configurable. There is no focus check. The optional selector adds conservative root-turn eligibility and bypasses completion grouping only for selected updates.
- These profiles affect only this extension's alerts, not native ambient summaries, permission notifications, or inbound replies.
- Jcode's desktop notification thresholds do not throttle this extension.
- Delivery is best effort, with a network timeout and no automatic retry.
- Normal session closure is not a crash or task-success signal. There are no invented needs-input, cancellation or crash events. Native ambient permission/summary notifications remain a separate Jcode route; this extension does not duplicate them.
- `alert` remains a compatibility alias for event dispatch. New managed hooks use the `event` command.

This project was developed against **Jcode v0.98.1**. In that version, a real `jcode run --json` bypassed the turn hook while `--ndjson` invoked it. Use `--ndjson` for scripted notifications. This extension does not patch Jcode itself. Recheck behavior when upgrading Jcode.

## Privacy and security

**Task/result excerpts are intentionally sent to your configured Telegram destination.** Use a private bot you trust. Read [SECURITY.md](SECURITY.md) before enabling this for sensitive work.

Ordinary excerpt formatting reads public text from only the matching saved session, up to 8 MiB. It requires a unique corresponding assistant response before including the request. Missing/ambiguous context is unavailable. Failed turns omit unbound prompt context and use the current error rather than a stale successful response. Reasoning, images, and shell/tool results are not exported as request context.

The optional selector separately reads a bounded native snapshot and journal to recover the complete public final behind the hook excerpt. It sends bounded sanitized task context, the current final and a previous public final to the configured Clef service. Its private `telegram-selector-state.json` retains those inputs and allowed original links for the configured sample, unlike the fingerprint-only routine receipts below. Protect this file and do not publish it. Full limits and the distinction between selection, delivery and human usefulness are in the [selector runbook](docs/plans/2026-10-24-clef-selector-setup.md).

Code fences, paths within request/result text, URLs, email addresses, common credential forms, known bot credentials, and labeled secret values are redacted on a **best-effort basis**. The explicit working-folder metadata line is the intentional path-display exception described above. This is not comprehensive data-loss prevention and does not make arbitrary private prose safe to forward. Preview before using it with confidential projects.

Tokens, configuration/backups, preferences, and diagnostic receipts stay outside this repository. Config/backups and helper state files are written with mode 0600. Backups can contain credentials. Never upload them to issues, pull requests, or build artifacts.

The latest receipt at `~/.jcode/notifications/telegram-last-alert.json` stores state, timestamps, one-way fingerprints, profile/length metadata, and optional server text/bold acknowledgment. It does not store raw message text, bot token, destination, or raw session ID. Later turns can overwrite it. Server acknowledgment does not prove phone notification visibility or that a message was read.

Policy suppression/card state is stored separately in `~/.jcode/notifications/telegram-policy-state.json`. It contains hashed session/destination keys, counters, timestamps, error fingerprints and card message IDs, not message contents. Explicit session filters are intentionally stored in the private policy file. Protect both files and their parent directory.

### Duplicate Moshi registrations

```sh
jcode-telegram-hook dedupe-moshi
```

This removes only exact repeated `moshi-hook jcode-hook` command strings from the four lifecycle arrays, keeping the first occurrence. It never invokes Moshi, changes its settings or removes other commands. A no-op does not create a backup. Actual edits use a private config backup and full semantic checks. Duplicate adapter calls do not establish duplicate phone pushes, so do not use this as a phone-delivery test.

## Update and remove

Before upgrading, check the release notes, then install a chosen tag or verified release wheel into the same environment. No hook change is needed if its executable path and threshold stay the same. To change either, uninstall the registered hook first, then install it with the new options.

```sh
jcode-telegram-hook status
jcode-telegram-hook uninstall
python -m pip uninstall jcode-telegram-alerts
```

Hook removal leaves credentials, verbosity preferences, and native Telegram settings intact. It does not remove other hooks. The separate `jcode-telegram disable` command disables native Telegram flags too, so do not use it when you only want to remove these custom completion alerts.

`JCODE_HOME` is honored for isolated installations and tests. An explicit process-level `JCODE_HOOK_TURN_END` override takes precedence over configured hooks.

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
