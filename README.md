# Jcode Telegram Alerts

[![CI](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml/badge.svg)](https://github.com/nephilus/jcode-telegram-alerts/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nephilus/jcode-telegram-alerts)](https://github.com/nephilus/jcode-telegram-alerts/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Unofficial Telegram completion alerts for [Jcode](https://github.com/1jehuang/jcode).** Get concise task context and readable results without exporting an entire transcript or making another model call.

> This community extension is not part of, endorsed by, or supported by the Jcode maintainers. It uses Jcode's native lifecycle hook and Telegram credentials. It does not add a remote-command server.

## What it does

- Sends completion/error alerts from Jcode's built-in `turn_end` hook.
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
python -m pip install "git+https://github.com/nephilus/jcode-telegram-alerts.git@v0.1.0"
jcode-telegram --version
jcode-telegram preview
jcode-telegram-hook install
```

Alternatively, download the wheel and `SHA256SUMS` from a [GitHub release](https://github.com/nephilus/jcode-telegram-alerts/releases), verify its checksum, and install the local wheel with `python -m pip install /path/to/package.whl`. No PyPI package is published by this repository's automation.

Keep the virtual environment at its installed location: the hook records the executable's absolute path. It does not depend on an interactive shell's PATH or an activated environment after registration. Use `jcode-telegram-hook --help` for an explicit executable path or a custom successful-turn threshold. Do not move/delete the environment before unregistering the hook.

### Set up Telegram

If Jcode already has a working Telegram channel, skip setup. This helper reuses that channel's native credentials. Avoid running a second `getUpdates` poller beside Jcode's native reply poller.

For a new dedicated bot:

1. Open Telegram's official **@BotFather** and send `/newbot`. Choose an available bot username ending in `bot`.
2. Open your new bot, tap **Start**, and keep the private chat unmuted.
3. In your own terminal, run `jcode-telegram setup`. Paste the bot token only at the hidden prompt, never into an agent conversation or shell argument.
4. Send the exact `/start jcode_...` challenge shown by the helper to your bot. The helper validates your private chat, sends a test, and only then enables the channel.
5. Run `jcode-telegram status`. Let a normal Jcode turn exceed 30 seconds and confirm the notification in your Telegram app.

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

Emojis and layout count toward the caps. Brief keeps section content on the label's line; contextual and expanded put it below the label. Failed turns use ❌ and saved-session previews use 👀. The neutral 🔎 does not imply that checks passed.

Changing verbosity hot-reloads and preserves native credentials, reply settings, ambient settings, and hook thresholds. The private preference file is `~/.jcode/notifications/telegram-settings.json`. Missing preferences default to expanded; invalid preferences fall back to brief rather than increasing disclosure.

### Preview and test

```sh
jcode-telegram preview
jcode-telegram preview --verbosity brief
jcode-telegram preview --session YOUR_SESSION_ID --verbosity expanded
jcode-telegram test --verbosity expanded
```

`preview` never sends. Without `--session`, it uses illustrative sample text. Saved-session previews are labeled as previews, with a placeholder duration rather than an inferred status. Terminal previews show text and spacing; Telegram applies the native bold formatting. `test` deliberately sends a labeled illustrative preview. Its explanatory prefix is outside the rendered profile cap. A one-off `--verbosity` override does not change the saved preference.

## Trigger rules and native support

- Successful turns lasting **at least 30 seconds** notify. All failed turns notify, regardless of duration.
- A turn is one model response cycle. Worker/swarm turns can notify too.
- There is no cooldown, deduplication, focus check, or root-only filter.
- These profiles affect only this extension's completion/error alerts, not native ambient summaries, permission notifications, or inbound replies.
- Jcode's desktop notification thresholds do not throttle this extension.
- Delivery is best effort, with a network timeout and no automatic retry.

This project was developed against **Jcode v0.98.1**. In that version, a real `jcode run --json` bypassed the turn hook while `--ndjson` invoked it. Use `--ndjson` for scripted notifications. This extension does not patch Jcode itself. Recheck behavior when upgrading Jcode.

## Privacy and security

**Task/result excerpts are intentionally sent to your configured Telegram destination.** Use a private bot you trust. Read [SECURITY.md](SECURITY.md) before enabling this for sensitive work.

The helper reads public text from only the matching saved session, up to 8 MiB. It requires a unique corresponding assistant response before including the request. Missing/ambiguous context is unavailable. Failed turns omit unbound prompt context and use the current error rather than a stale successful response. Reasoning, images, and shell/tool results are not exported as request context.

Code fences, paths, URLs, email addresses, common credential forms, known bot credentials, and labeled secret values are redacted on a **best-effort basis**. This is not comprehensive data-loss prevention and does not make arbitrary private prose safe to forward. Preview before using it with confidential projects.

Tokens, configuration/backups, preferences, and diagnostic receipts stay outside this repository. Config/backups and helper state files are written with mode 0600. Backups can contain credentials. Never upload them to issues, pull requests, or build artifacts.

The latest receipt at `~/.jcode/notifications/telegram-last-alert.json` stores state, timestamps, one-way fingerprints, profile/length metadata, and optional server text/bold acknowledgment. It does not store raw message text, bot token, destination, or raw session ID. Later turns can overwrite it. Server acknowledgment does not prove phone notification visibility or that a message was read.

## Update and remove

Before upgrading, check the release notes, then install a chosen tag or verified release wheel into the same environment. Re-register only if the executable path or threshold changes.

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
