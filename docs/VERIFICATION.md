# Verification guide

## Levels of evidence

| Check | What it demonstrates | What it does not demonstrate |
| --- | --- | --- |
| `python -m unittest discover -v` | Deterministic parser, redaction, Unicode, session-binding, configuration, CLI, and synthetic API behavior | Actual Telegram server acceptance or phone notification visibility |
| Build wheel and source archive | Distributable packaging from the public source | That an installed console command or hook runs correctly |
| Install wheel in a fresh environment and invoke public commands | Real packaged imports, entrypoints, version, no-send previews, and hook registration/removal | Delivery to a real bot |
| Hosted CI on Linux/macOS and supported Python versions | The same public source/packaging workflows work on runner environments | Compatibility with every native Jcode release |
| Real native Jcode turn through the installed hook and configured bot | Cross-process lifecycle and Telegram server delivery, with returned text/entities | Phone notification visibility, user reading, or correctness of the assistant's task claims |

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

Use a fresh temporary `JCODE_HOME`, then run the installed commands rather than importing source copies:

```sh
export JCODE_HOME=/path/to/temporary-jcode-home
/path/to/fresh-smoke-environment/bin/jcode-telegram --version
/path/to/fresh-smoke-environment/bin/jcode-telegram preview
/path/to/fresh-smoke-environment/bin/jcode-telegram verbosity brief
/path/to/fresh-smoke-environment/bin/jcode-telegram preview
/path/to/fresh-smoke-environment/bin/jcode-telegram preview --event turn_start
/path/to/fresh-smoke-environment/bin/jcode-telegram policy
/path/to/fresh-smoke-environment/bin/jcode-telegram policy activity --status-card on
/path/to/fresh-smoke-environment/bin/jcode-telegram policy balanced --status-card off
/path/to/fresh-smoke-environment/bin/jcode-telegram-hook dedupe-moshi
/path/to/fresh-smoke-environment/bin/jcode-telegram-hook install
/path/to/fresh-smoke-environment/bin/jcode-telegram-hook status
/path/to/fresh-smoke-environment/bin/jcode-telegram-hook uninstall
```

Confirm unrelated settings/foreign hooks are unchanged and no credentials or native reply flags were enabled. Test registration twice to verify idempotence. Restore or unset `JCODE_HOME` before returning to normal work.

On minimal Debian/Ubuntu installations, Python's `venv` support may require the distribution's `python3-venv` package. For an isolated maintainer check without `ensurepip`, an existing pip supporting `--python` can install into `python3 -m venv --without-pip ...`. This is a local environment prerequisite, not an application runtime dependency.

## Secret and publication checks

Before a public push, run an established scanner such as Gitleaks against the **whole Git history**, not just the current diff:

```sh
gitleaks git --redact --log-opts=--all .
```

Also inspect staged filenames, commit authors, package contents, and documentation for private configuration, real session data, local absolute paths, or personal contact details. Do not suppress genuine findings with a broad test-directory allowlist. Synthetic credential fixtures are constructed in tests rather than committing real credentials.

The public repository starts with sanitized source history. Private prototype history, native configuration, test transcripts, and live receipt identifiers are deliberately not imported. Runtime code is standard-library-only. A clean scan is risk reduction, not proof of universal secret detection or a full penetration test.

## Live acceptance

Only run a live send with the account owner's authorization. Do not put Telegram credentials into CI. Use the configured native private channel, one harmless test task, and the real installed native Jcode entrypoint/hook. In the originally tested Jcode v0.98.1, `--ndjson` invokes turn hooks while `--json` did not.

After the turn, correlate the hook receipt's session fingerprint with the actual native session. For ordinary completion delivery, check state `sent`, the selected profile's word/character limits, `response_confirmed`, `bold_entities`, `link_entities`, and `formatting_confirmed`. `notifications/telegram-last-alert.json` records the latest decision. Separate `telegram-last-completion.json`, `telegram-last-error.json` and corresponding lifecycle receipts retain the latest decision for each kind, so a disabled closure does not erase completion evidence. These metadata-only receipts can still be overwritten by another session of the same kind.

For clickable links, use harmless existing HTTPS targets in a real native turn. Verify the installed hook sends `text_link` entities with the intended destination-derived labels and exact URL targets, valid UTF-16 spans, and `link_preview_options.is_disabled` set to true. `formatting_confirmed` requires the returned text, bold ranges, link ranges and link destinations to match. Receipts record counts and fingerprints, not raw URLs. This demonstrates Telegram server acceptance of clickable-link entities, not that a phone rendered them, a user tapped them or a destination is public.

For event-aware delivery, exercise the real installed hook with two actual turns in the same session. Verify the first completion is acknowledged and the second is `suppressed_cooldown`, with no new delivery. Test activity/card mode in a private isolated helper profile: lifecycle starts create one silent message and completion/closure use `editMessageText` on that message. Check matching message IDs privately, never publish them. Repeated-error suppression, malformed-state refusal and error/card-edit failure isolation also have deterministic fixture tests. Those tests alone do not establish live Telegram acceptance.

Do not weaken global thresholds for a live check. Native process-only `JCODE_HOOK_*` command overrides can select the installed helper with `--min-seconds 0` or an isolated private helper `JCODE_HOME`. Keep credentials out of command arguments, logs and committed files, preserve the normal configuration, and do not start another polling loop. Observe detached hooks before interpreting receipts; event order and crash closure are not guaranteed.

During the event-aware upgrade on October 17, 2026 (UTC), a fresh built wheel completed real Jcode streaming turns using private isolated helper policies and the configured Telegram destination. Two turns in one native session produced one acknowledged expanded completion, then `suppressed_cooldown` with a grouped count of one. A separate short turn in activity/card mode produced acknowledged session-start, turn-start, completion and session-end updates sharing one Telegram message ID. Working/completion/closure used edits, and returned text and bold entities matched. Native configuration and the saved expanded preference were byte-for-byte unchanged. These were real native processes and Telegram server responses, not a mock transport.

The pre-publication implementation completed a real Jcode-to-installed-hook-to-Telegram check. Telegram returned the exact expanded text and all five intended bold ranges. Its private input, destination, session/message identifiers, and raw receipt are not published here. That server acknowledgment does not prove the phone displayed a notification or the account owner read it.

See the repository's actual [CI runs](https://github.com/nephilus/jcode-telegram-alerts/actions) and [release artifacts](https://github.com/nephilus/jcode-telegram-alerts/releases) for hosted outcomes. Report blocked or unobserved boundaries honestly instead of substituting synthetic tests for live acceptance.
