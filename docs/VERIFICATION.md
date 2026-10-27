# Verification guide

## Levels of evidence

| Check | What it demonstrates | What it does not demonstrate |
| --- | --- | --- |
| `python -m unittest discover -v` | Deterministic parser, redaction, Unicode, session-binding, configuration, CLI, and synthetic API behavior | Actual Telegram server acceptance or phone notification visibility |
| Build wheel and source archive | Distributable packaging from the public source | That an installed console command or hook runs correctly |
| Install wheel in a fresh environment and invoke public commands | Real packaged imports, entrypoints, version, no-send previews, and hook registration/removal | Delivery to a real bot |
| Hosted CI on Linux/macOS and supported Python versions | The same generic CLI/source/packaging workflows work on runner environments | Compatibility of the optional legacy event adapter with every Jcode release |
| Real generic `telegram-alerts attention` call with `JCODE_SESSION_ID` unset | Installed CLI accepts the request and Telegram returns the exact text/link formatting receipt | Phone notification visibility, user reading, or correctness of the assistant's task claims |

## Repeat the local package workflow

From a clean checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python -m build
python -m venv /path/to/fresh-smoke-environment
/path/to/fresh-smoke-environment/bin/python -m pip install dist/*.whl
```

Use a fresh temporary `TELEGRAM_ALERTS_HOME`, then run the installed commands rather than importing source copies:

```sh
export TELEGRAM_ALERTS_HOME=/path/to/temporary-telegram-alerts-home
/path/to/fresh-smoke-environment/bin/telegram-alerts --version
/path/to/fresh-smoke-environment/bin/telegram-alerts preview
/path/to/fresh-smoke-environment/bin/telegram-alerts verbosity brief
/path/to/fresh-smoke-environment/bin/telegram-alerts preview
/path/to/fresh-smoke-environment/bin/telegram-alerts preview --event turn_start
/path/to/fresh-smoke-environment/bin/telegram-alerts policy
/path/to/fresh-smoke-environment/bin/telegram-alerts policy activity --status-card on
/path/to/fresh-smoke-environment/bin/telegram-alerts policy balanced --status-card off
/path/to/fresh-smoke-environment/bin/telegram-alerts-hook dedupe-moshi
/path/to/fresh-smoke-environment/bin/telegram-alerts-hook install
/path/to/fresh-smoke-environment/bin/telegram-alerts-hook status
/path/to/fresh-smoke-environment/bin/telegram-alerts-hook uninstall
```

Confirm unrelated settings/foreign hooks are unchanged and no credentials or native reply flags were enabled. Test registration twice to verify idempotence. Restore or unset `TELEGRAM_ALERTS_HOME` before returning to normal work. If unset, the writable default is `~/.config/telegram-alerts`; the old `~/.jcode/config.toml` is a read-only Telegram-credentials fallback for unconfigured default homes.

On minimal Debian/Ubuntu installations, Python's `venv` support may require the distribution's `python3-venv` package. For an isolated maintainer check without `ensurepip`, an existing pip supporting `--python` can install into `python3 -m venv --without-pip ...`. This is a local environment prerequisite, not an application runtime dependency.

## Secret and publication checks

Before a public push, run an established scanner such as Gitleaks against the **whole Git history**, not just the current diff:

```sh
gitleaks git --redact --log-opts=--all .
```

Also inspect staged filenames, commit authors, package contents, and documentation for private configuration, real session data, local absolute paths, or personal contact details. Do not suppress genuine findings with a broad test-directory allowlist. Synthetic credential fixtures are constructed in tests rather than committing real credentials.

The public repository starts with sanitized source history. Private prototype history, native configuration, test transcripts, and live receipt identifiers are deliberately not imported. Runtime code is standard-library-only. A clean scan is risk reduction, not proof of universal secret detection or a full penetration test.

## Live acceptance

Only run a live send with the account owner's authorization. Do not put Telegram credentials into CI. For generic acceptance, invoke the installed `telegram-alerts attention` command directly with `JCODE_SESSION_ID` unset; a Jcode tool invocation or hook is not required. Use an explicitly selected `TELEGRAM_ALERTS_HOME` when the Telegram profile is not in the generic default home.

For `attention`, check the printed receipt has `state: sent`, `response_confirmed: true`, and `formatting_confirmed: true`. For an Inbox link, verify the receipt's origin mapping and that the sent `text_link` entity points at the registered `tailscale.url` while retaining path/query/fragment bytes. The CLI has no automatic retry; a timeout or unconfirmed response may mean delivery happened.

For generic Inbox rewriting, pass one harmless `http://localhost:<registered-port>/` URL only in `links[].url`. Verify Telegram's response confirms the rewritten tailnet entity and the receipt reports only the source/destination origins, not a thread fragment. Synthetic tests cover suffix preservation and refusal to rewrite other loopback targets.

For the deprecated legacy Jcode event adapter only, exercise the real installed hook with two actual turns in the same session. Verify the first completion is acknowledged and the second is `suppressed_cooldown`, with no new delivery. Test activity/card mode in a private isolated helper profile: lifecycle starts create one silent message and completion/closure use `editMessageText` on that message. Check matching message IDs privately, never publish them. Repeated-error suppression, malformed-state refusal and error/card-edit failure isolation also have deterministic fixture tests. Those tests alone do not establish live Telegram acceptance.

Do not weaken global thresholds for a legacy adapter check. Native process-only `JCODE_HOOK_*` command overrides can select the installed helper with `--min-seconds 0` or an isolated private helper `TELEGRAM_ALERTS_HOME`. Keep credentials out of command arguments, logs and committed files, preserve the normal configuration, and do not start another polling loop. Observe detached hooks before interpreting receipts; event order and crash closure are not guaranteed.

During the event-aware upgrade on October 17, 2026 (UTC), a fresh built wheel completed real Jcode streaming turns using private isolated helper policies and the configured Telegram destination. Two turns in one native session produced one acknowledged expanded completion, then `suppressed_cooldown` with a grouped count of one. A separate short turn in activity/card mode produced acknowledged session-start, turn-start, completion and session-end updates sharing one Telegram message ID. Working/completion/closure used edits, and returned text and bold entities matched. Native configuration and the saved expanded preference were byte-for-byte unchanged. These were real native processes and Telegram server responses, not a mock transport.

The pre-publication implementation completed a real Jcode-to-installed-hook-to-Telegram check. Telegram returned the exact expanded text and all five intended bold ranges. Its private input, destination, session/message identifiers, and raw receipt are not published here. That server acknowledgment does not prove the phone displayed a notification or the account owner read it.

See the repository's actual [CI runs](https://github.com/nephilus/agent-telegram-alerts/actions) and [release artifacts](https://github.com/nephilus/agent-telegram-alerts/releases) for hosted outcomes. Report blocked or unobserved boundaries honestly instead of substituting synthetic tests for live acceptance.

## Explicit attention acceptance

Use the actual installed `telegram-alerts attention --help` first. With a temporary `TELEGRAM_ALERTS_HOME`, verify malformed JSON, inline URLs, invalid explicit links, and an explicitly disabled profile all fail without delivery. Confirm the wheel includes `alert_attention`, the generic `telegram-alerts` entry point, and the `jcode-telegram` compatibility alias. The compatibility alias must forward to the same implementation and home resolver; no hook is needed for attention.

With owner authorization, run exactly one real installed `telegram-alerts attention` command with `JCODE_SESSION_ID` unset. Clearly label its message as an acceptance test, not an actual outstanding approval. Include only a short context, `needs_you`, and an optional verified link in `links`. Do not put credentials or command payloads into public logs. Check the returned `state: sent`, `response_confirmed`, `formatting_confirmed`, and (when applicable) `url_rewrites`. The message is a fresh normal-notification send, and no automatic resend occurs. Global disable and configured session filters still apply.

Repeat the same decision/revision key without `--resend`: expect `already_sent` and the same private message ID. Only with an explicit owner-authorized resend test, repeat with `--resend`: expect `sent` and a different message ID. A different reviewed revision is a different key. Inspect the private state for fingerprints, timestamps and message IDs only, with file mode 0600. Ensure normal policy/preferences, native reply settings and foreign hooks were unchanged. Also exercise an ordinary reversible task that completes without publishing attention, to check the instruction block does not require unnecessary questions.

Do not retry automatically after ambiguous transport, interrupted delivery or a post-acknowledgment local-state failure. An API acknowledgment is not a human read receipt or approval. These checks cannot prove an agent will always remember to invoke the command, that an operating system displayed a push notification, or that every URL is reachable by the owner. No deterministic fixture or local preview substitutes for the real native-to-installed-command-to-Telegram path.
