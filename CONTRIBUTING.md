# Contributing

This is a generic Telegram Alerts CLI and skill, with an optional deprecated Jcode event adapter for compatibility. Keep runtime code compatible with Python 3.11+ and standard-library-only unless a dependency has a clear, reviewed justification.

## Work locally

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python -m build
```

Use temporary `TELEGRAM_ALERTS_HOME` directories for development. Never use a maintainer's bot credentials or real transcripts in tests. Add synthetic regressions for parser, redaction, session-association, encoding, and configuration changes. A unit test or mocked Telegram response does not replace a real integration check when delivery behavior changes.

Do not run `setup`, `test`, or an unsuppressed send against a real profile without the account owner's authorization. Those operations may send messages or modify the selected Telegram Alerts profile; they do not modify native Jcode settings unless an operator explicitly selects a Jcode home. `preview` is the safe no-send entrypoint.

## Commits and pull requests

Use Conventional Commit titles, for example:

- `feat: add a new alert profile`
- `fix: preserve Unicode entity offsets`
- `docs: explain private bot setup`
- `chore(deps): update build tooling`
- `feat!: change a public CLI contract`

Keep the type lowercase and the subject on one line. Mark breaking changes with `!` and explain migration steps in the pull-request body. Squash merges use the pull-request title, so that title is the release-relevant commit. CI validates it. Release automation manages version files and changelogs; do not edit them casually.

Before requesting review:

1. Run the tests and build a wheel/source archive.
2. Install the wheel in a fresh virtual environment and exercise `telegram-alerts --help`, `preview`, and `attention --help` with a temporary `TELEGRAM_ALERTS_HOME`; verify that the `jcode-telegram` compatibility alias uses the same home.
3. If touching the deprecated hook adapter, exercise it only with an explicitly selected temporary home and confirm unrelated hooks/credentials remain intact.
4. Scan the diff for secrets and personal paths. Use Gitleaks locally when available.
5. Describe observed behavior, known limitations, and any integration check that could not be performed.

Never commit configuration/backups, bot tokens, chat IDs, real session data, latest-alert receipts, personal email addresses, or local absolute paths. Use generic synthetic examples.

## Release process

See [docs/RELEASING.md](docs/RELEASING.md). Maintainers merge a passing release pull request to publish a release. Do not push ad-hoc version tags or bypass required checks.

Report security-sensitive issues through the private channel in [SECURITY.md](SECURITY.md), not a public issue.
