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

After the turn, correlate the hook receipt's session fingerprint with the actual native session. Check state `sent`, the selected profile's word/character limits, `response_confirmed`, `bold_entities`, and `formatting_confirmed`. The latest receipt can be overwritten by another turn, so do not mistake a later session's metadata for this test.

The pre-publication implementation completed a real Jcode-to-installed-hook-to-Telegram check. Telegram returned the exact expanded text and all five intended bold ranges. Its private input, destination, session/message identifiers, and raw receipt are not published here. That server acknowledgment does not prove the phone displayed a notification or the account owner read it.

See the repository's actual [CI runs](https://github.com/nephilus/jcode-telegram-alerts/actions) and [release artifacts](https://github.com/nephilus/jcode-telegram-alerts/releases) for hosted outcomes. Report blocked or unobserved boundaries honestly instead of substituting synthetic tests for live acceptance.
