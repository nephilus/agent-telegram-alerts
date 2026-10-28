# Legacy Jcode Clef completion selector: operator runbook

**Status: legacy Jcode event adapter only.** This runbook is retained for existing Jcode hook installations; it is not required for generic `telegram-alerts attention` or the `/telegram` skill, and it is not a recommended new setup. The generic writable home is `~/.config/telegram-alerts`; the read-only `~/.jcode/config.toml` fallback covers Telegram credentials only, not Jcode session files or Clef state. No settings are migrated automatically. `version.txt` is the package version source; verify feature help from the intended source/runtime rather than relying on an old release claim.

## Before you begin

For this legacy selector only, point the process at the existing Jcode profile so it can read session data. This environment setting changes no files:

```sh
export TELEGRAM_ALERTS_HOME="$HOME/.jcode"
```

- Use a source checkout or wheel that contains the selector. This optional legacy adapter is not required or exercised by generic `telegram-alerts attention`.
- Python 3.11 or newer is required. Use an isolated environment and keep it at its installed path.
- This procedure applies only to an existing Jcode event-hook adapter. The generic CLI does not require it. Before running any command in this runbook, explicitly select the Jcode session/profile home with `export TELEGRAM_ALERTS_HOME="$HOME/.jcode"`; the generic default does not contain Jcode session files.
- Confirm that the existing maintained Clef HTTPS origin, request-model alias, exact response backend identity, and API key are available to you. The endpoint is Clef's typed `/v1/systemone` API, not a generic OpenAI-compatible endpoint. This guide does not install a model service or change model routes.
- If Telegram is already linked, leave its existing credentials and settings alone. Do not rerun bot setup or copy a full Jcode config into the generic home.

## Install this source into the hook runtime

For an already-authorized legacy Jcode hook, install the source checkout into the executable's existing environment; do not register a new hook as part of generic Telegram setup:

```sh
python3 -m venv "$HOME/.local/share/agent-telegram-alerts/venv"
"$HOME/.local/share/agent-telegram-alerts/venv/bin/python" -m pip install .
```

If installing a locally built wheel instead, use its absolute path with that same environment's `python -m pip install /absolute/path/to/package.whl`. Do not install only a shell wrapper. If Jcode's saved command points at another environment, install the source or wheel into that environment, or deliberately migrate the saved hook registration after inspecting it.

Inspect the saved commands and hook ownership locally before changing registration. The managed ownership manifest is `notifications/telegram-hook.json`. Its exact JSON shapes are either `{"version":1,"command":"..."}` or `{"version":2,"commands":{"session_start":"...","turn_start":"...","turn_end":"...","session_end":"..."}}`; a version-2 commands object contains the registered events. Hook status reports registration ownership, not whether that command's runtime contains the selector.

If an owner explicitly elects to retain the legacy adapter, the deprecated hook installer requires an explicitly selected home and executable:

```sh
"$HOME/.local/share/agent-telegram-alerts/venv/bin/telegram-alerts-hook" install \
  --command "$HOME/.local/share/agent-telegram-alerts/venv/bin/telegram-alerts-jcode" \
  --events lifecycle
```

Do not run this as a casual upgrade of an existing managed installation. Existing managed v1 hooks retain their old event set when no new selection is requested. The installer refuses a changed owned executable, threshold or event set. To migrate those deliberately, coordinate an uninstall of this helper's owned hooks followed by registration with the new options. `--from-command` is only for an unowned legacy hook, not an owned-installation upgrade. Preserve foreign hooks and native Telegram credentials. If no hook change is intended, update the runtime at the already-saved executable path instead.

Jcode may cache hook paths in active sessions. Upgrade the runtime those paths actually invoke, or coordinate a normal session restart separately. Never force a restart of shared active sessions to make the change take effect.

## Verify the installed runtime before enabling

Use the actual executable invoked by the saved hook command, not a similarly named command from your interactive `PATH`:

```sh
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode --help
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode selector
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode policy
```

The help must expose `selector` and its selector options. `selector` must be recognized and return read-only state. `status` is not a feature probe, and the version comes from `version.txt`; check the exact source/runtime rather than assuming a version implies selector support. If the executable rejects `selector`, stop and update the exact legacy runtime before proceeding. A `preview` command can inspect ordinary formatting, but it does **not** exercise Clef selection or prove selector connectivity.

## Prepare the key file

Put the existing API key in an absolute, owner-controlled regular file with mode `0600`. Keep the key out of shell arguments, command history, logs, chat, and this repository. For example, create the file through a trusted secret-management method, then check it locally:

```sh
stat -c '%a %F' /absolute/private/decision.key
```

The file must be a regular file owned by the invoking user, mode `0600`, non-empty, and contain a single whitespace-free key. Do not print or `cat` it as part of verification. The selector validates file safety when configured and reads the key only when making a request.

## Enable the selector

Run the following using the verified executable. Replace the example origin, key-file path, request alias, and exact response backend with the maintained deployment values. Do not put the key itself in this command.

```sh
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode selector on \
  --endpoint https://decision.example.ts.net:9105 \
  --key-file /absolute/private/decision.key \
  --model maintained-alias \
  --response-model exact-backend \
  --pir-turns 100
```

The endpoint is an HTTPS origin only, without a path, query, fragment, or embedded credentials. It calls the fixed `/v1/systemone` route. The request uses the configured maintained alias; the response must identify the configured exact backend and contain the strict typed Choice result. The option values shown are placeholders, not a service recommendation or deployment configuration.

The selector is disabled until configured. Enabling it configures the selector and enables the completion event. The response backend is checked exactly. The selector makes one finite request with no retry. A bad origin, unavailable/unsafe key, failed request, oversized input, invalid response, or busy model slot stays quiet. These failures are recorded separately from a semantic NO. There is no cloud fallback, Qwen call, generated rewrite, or automatic unfiltered completion send.

## Read-only checks and delivery behavior

After configuration, check the selector and delivery policy without changing them:

```sh
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode selector
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode policy
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode preview
```

Read selector status as local readiness and collection counts, not proof of a live API call or Telegram delivery. It does not expose conversation text or credentials. The preview renders illustrative notification formatting only; it does not invoke Clef. Do not send test notifications merely to test classification.

A YES sends a sanitized literal copy of the original final response and only independently validated original links. Clef chooses a label; it cannot author the notification or its links. Selected messages use a separate layout capped at 590 words and 4,000 UTF-16 units, including metadata and the link footer. Long bodies are visibly clipped, not summarized. There is no Qwen rewriting or cloud fallback. A selected completion bypasses the usual duration threshold and completion cooldown and sends a new message rather than editing a status card. Existing explicit attention and error handling remain independent of the selector. A NO sends no ordinary completion update.

Eligibility is conservative and source-bound: it requires a uniquely matched successful owner-root turn and excludes known child sessions, automated/coordination-only turns, and stale or ambiguous source. Forks are conservatively excluded because parent metadata alone cannot distinguish a user-created fork from a child; explicitly including an exact session ID permits that parented session. Existing include/exclude filters still apply, with exclusion winning. Do not infer complete coverage from hook status or the sample count.

Source recovery accepts a native snapshot up to 128 MiB and a journal up to 32 MiB. The current public final must fit 16,000 characters. Sanitized task context, the opening candidate excerpt, the current final and a previous public final together must fit the selector's 12,000-character input limit. Oversized input is rejected rather than silently classified from a clipped candidate. Reasoning and tool results are not supplied to Clef.

## Private post-implementation review evidence

The configured sample retains content for at most the first 100 unique eligible turns (or the smaller explicitly configured limit). The first 100 means unique eligible content records, not all hook invocations or all sessions. NO and YES decisions are distinct from failed, oversized, and busy requests and from unconfirmed Telegram delivery. A failure or busy result is not a NO judgment.

Marked acceptance turns are not natural-usefulness observations and must be excluded from usefulness rates. Once the content cap is reached, the selector continues filtering but does not retain more turn content. Status counts are not counts of every Jcode turn. No automatic PIR-report command is provided. Review the private local evidence through the separately coordinated PIR process, and do not publish private logs, records, receipts, or conversation content.

Local PIR scheduling is specific to the deployment and is not built into this package. Keep any review schedule and owner-only evidence access local. The selector does not create per-turn Telegram reports.

## Rollback

To stop ordinary completion updates while retaining errors, explicit attention, and the private selector evidence, run:

```sh
/absolute/path/to/hook-runtime/bin/telegram-alerts-jcode selector off
```

This quiets completions. It deliberately does not restore an unfiltered completion stream. It also does not erase collected evidence, disable errors, or disable explicit attention. Confirm with read-only `selector` and `policy` queries. Do not delete evidence or alter unrelated hooks as part of rollback.

## Troubleshooting

- **`selector` is unavailable or `invalid_policy` appears:** the saved hook may still invoke an older runtime. Check the exact saved command and install this source into that executable's environment. Hook ownership status and a version string do not prove feature support.
- **No selector records:** the event may not be an eligible successful root turn, source context may be unavailable/stale/ambiguous, the selector may be off, or the hook may not have reached the updated runtime. A zero count is not a semantic NO.
- **Semantic NO:** a valid strict Clef Choice returned NO. It means quiet completion by policy, not a request failure.
- **Failed or busy request:** inspect private local status/evidence through the established owner-only process. Failures and busy slots are not NO decisions. There are no automatic retries.
- **YES but Telegram is unconfirmed:** do not force YES or automatically resend. Delivery may be uncertain; the selector claims a turn before external work to prevent duplicate sends. Preserve the evidence for review.
- **Telegram alert missing after installation:** confirm the saved executable itself supports `selector`, then check selector and policy state. Do not rerun bot setup if Telegram is already linked, do not replace native credentials, and do not force a shared-session restart.

No system-prompt overlay change is required for this feature. This runbook changes neither Jcode model routes nor the maintained decision service.
