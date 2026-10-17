# Jcode Telegram Alerts

[![CI](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nephilus/jcode-telegram-alerts)](https://github.com/nephilus/jcode-telegram-alerts/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Unofficial event-aware Telegram alerts for [Jcode](https://github.com/1jehuang/jcode).** Get concise task context and readable results without exporting an entire transcript or making another model call.

> This community extension is not part of, endorsed by, or supported by the Jcode maintainers. It uses Jcode's native lifecycle hook and Telegram credentials. It does not add a remote-command server.

## What it does

- Observes session start, turn start, turn end and normal session closure.
- Sends qualifying completion/error alerts by default, with quiet routine activity, per-session cooldowns and repeated-error suppression.
- Offers an optional editable session status card instead of a stream of routine messages.
- Offers **brief**, **contextual**, and **expanded** profiles. Expanded is the default.
- Uses bold headings, readable section spacing, and useful emojis.
- Links a dedicated bot through a private-chat challenge and hidden terminal token entry.
- Adds/removes its own hook without replacing unrelated hooks or Telegram settings.
- Uses only the Python standard library at runtime. Python **3.11+** and Linux/macOS are supported.

Illustrative expanded alert:

> ✅ **Jcode turn finished**<br>
> example-project · 95s
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
python -m pip install "git+https://github.com/nephilus/jcode-telegram-alerts.git@v0.2.0"
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

## Choose verbosity

```sh
jcode-telegram verbosity expanded
jcode-telegram verbosity contextual
jcode-telegram verbosity brief
jcode-telegram verbosity
```

| Profile | Whole-alert cap | Content |
| --- | --- | --- |
| brief | 25 words / 320 characters | Status, project/duration, short request and result |
| contextual | 60 words / 800 characters | More request/result context, stated checks and next action when present |
| expanded | 100 words / 1,400 characters | Fuller request/result excerpts, stated checks and next action when present |

Character caps count Unicode code points, not bytes or visual graphemes. Telegram bold offsets use UTF-16 units separately. Emojis and layout count toward the caps. Brief keeps section content on the label's line; contextual and expanded put it below the label. Failed turns use ❌ and saved-session previews use 👀. The neutral 🔎 does not imply that checks passed.

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

In ordinary message mode, successful turns still need to meet the hook duration threshold, 30 seconds by default. Within a session's completion cooldown, further qualifying completions are counted instead of sent. The next eligible completion includes a bounded `Grouped:` count. There is no background timer or delayed digest, so a suppressed final completion is not automatically sent later.

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

Repeated include/exclude options replace the corresponding list. Exclusion wins. These are explicit choices, not automatic root/worker detection. The hook payload has no reliable worker identity, and saved parent IDs also include user-created forks. Unavailable context is not guessed.

Policy settings are private local state in `~/.jcode/notifications/telegram-policy.json`. Malformed or unsafe policy/state files fail closed for outgoing alerts rather than reverting to noisier defaults.

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
- A turn is one model response cycle. Worker/swarm turns can notify too.
- Completion grouping and repeated-error suppression are configurable. There is no focus check or automatic root-only filter.
- These profiles affect only this extension's alerts, not native ambient summaries, permission notifications, or inbound replies.
- Jcode's desktop notification thresholds do not throttle this extension.
- Delivery is best effort, with a network timeout and no automatic retry.
- Normal session closure is not a crash or task-success signal. There are no invented needs-input, cancellation or crash events. Native ambient permission/summary notifications remain a separate Jcode route; this extension does not duplicate them.
- `alert` remains a compatibility alias for event dispatch. New managed hooks use the `event` command.

This project was developed against **Jcode v0.98.1**. In that version, a real `jcode run --json` bypassed the turn hook while `--ndjson` invoked it. Use `--ndjson` for scripted notifications. This extension does not patch Jcode itself. Recheck behavior when upgrading Jcode.

## Privacy and security

**Task/result excerpts are intentionally sent to your configured Telegram destination.** Use a private bot you trust. Read [SECURITY.md](SECURITY.md) before enabling this for sensitive work.

The helper reads public text from only the matching saved session, up to 8 MiB. It requires a unique corresponding assistant response before including the request. Missing/ambiguous context is unavailable. Failed turns omit unbound prompt context and use the current error rather than a stale successful response. Reasoning, images, and shell/tool results are not exported as request context.

Code fences, paths, URLs, email addresses, common credential forms, known bot credentials, and labeled secret values are redacted on a **best-effort basis**. This is not comprehensive data-loss prevention and does not make arbitrary private prose safe to forward. Preview before using it with confidential projects.

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
