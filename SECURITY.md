# Security policy

## Supported versions

During the initial 0.x series, security fixes target the latest released version only. The generic Telegram CLI/skill is best effort, with no availability or support SLA. The package also retains an optional, deprecated Jcode event adapter; that adapter is not required by the generic attention flow.

## Report a vulnerability privately

Use this repository's **Security > Report a vulnerability** page to open a private report. Do not post secrets or exploitable private details in a public issue. Include affected version, a minimal synthetic reproducer, expected behavior, and impact. Remove bot tokens, chat IDs, session transcripts, configuration/backups, and private file paths.

If private reporting is unavailable, open a public issue requesting a private contact channel without including the vulnerability or sensitive data. If a real bot credential was exposed, stop using that credential and handle revocation directly in Telegram before sharing a report.

## Threat model and data flow

The generic attention command intentionally transmits the caller's bounded `context`, `needs_you`, optional recommendation, and validated `links` to the selected Telegram destination. It is invoked from any agent or shell and does not depend on a Jcode session or hook. The optional legacy Jcode event adapter can additionally forward bounded public request/result excerpts when explicitly enabled. Anyone with access to the destination can read forwarded content; device notifications may reveal it on a lock screen.

No incoming command server, webhook endpoint, remote shell, reply poller, or network listener is implemented here. New bot setup disables remote replies by default. The generic CLI does not modify Plannotator or start/stop its Inbox service. Telegram delivery is not an approval channel; use the reviewed Plannotator/GitHub route for decisions.

The helper:

- Uses HTTPS JSON requests to Telegram with a timeout.
- Accepts bot tokens only through hidden interactive terminal input during setup.
- Requires an exact challenge from a matching private user/chat before saving a new destination.
- Tests delivery before enabling the native channel, and refuses to replace an existing webhook.
- In legacy Jcode event mode, includes request context only after uniquely matching the current successful public response in the same saved session.
- Legacy event formatting omits unbound prompt context on failure and prefers the current error over stale successful output.
- Does not use reasoning, images, or tool-result blocks as request context.
- Uses explicit UTF-16 bold and validated `text_link` entities rather than interpreting task text as HTML or Markdown.
- Disables Telegram link previews and does not fetch or resolve output-link destinations.
- Writes configuration/backups, preferences, policy state and receipts under the selected `TELEGRAM_ALERTS_HOME` with mode 0600. The default is `~/.config/telegram-alerts`.
- Legacy lifecycle events do not reuse earlier request/response text for session-start, working or closure events.
- Legacy editable status-card IDs are scoped to a hashed session and destination, so relinking does not edit an old destination.

These controls do not defend against a compromised local user account, malicious replacements of installed code, a compromised Telegram account/bot, or hostile native Jcode components. Protect the installation directory and the parent directories of Jcode state. File-level symlink checks are not a substitute for an owner-controlled filesystem.

## Redaction is not data-loss prevention

Redaction removes common known credential forms, the configured bot token, labeled secret values, code fences, paths inside request/result text, ordinary body URLs, and email addresses. Generic attention displays the invoking command's current working directory, never a session name or ID. Legacy event alerts may display bounded native working-folder/session metadata; folder names can be sensitive, and home abbreviation is not anonymization. This is **best effort** and may miss arbitrary private prose, unfamiliar credential formats, encoded secrets, or misleadingly structured text. Do not use it as the sole control protecting confidential projects. Preview before forwarding sensitive work.

Attention forwards up to three validated `links[].url` targets with derived labels and disabled previews; URLs in text fields are rejected. Ordinary links reject query/fragment data, credentials, IP/local hosts, nonstandard ports, and recognized credential forms. The sole Inbox exception rewrites an exact registered localhost port to the read-only Plannotator `tailscale.url`, preserving path/query/fragment in the outbound link. Missing mapping omits the local link with a warning rather than inventing a destination. The registry is not modified, and the receipt reports only mapping origins. The helper performs no DNS, redirect, repository-visibility or content checks. URL paths can still contain sensitive names or private identifiers; do not assume a syntactically accepted target is safe or public.

Checks in the notification are excerpts from the assistant response. They are not independently verified. A successful model turn is not proof that the entire user's goal succeeded.

## Local state and removal

`TELEGRAM_ALERTS_HOME` selects the writable profile and defaults to `~/.config/telegram-alerts`; deprecated `JCODE_HOME` is honored only if the generic variable is unset. When the default generic home has no Telegram credentials/config, the CLI reads only Telegram safety fields from `~/.jcode/config.toml` in read-only compatibility mode and prints a notice. Legacy policy and attention-dedup files are also read-only fallbacks; all new writes stay in the selected generic home. No credentials or Jcode session data are copied. Do not upload configuration/backups or private receipts. Backups can contain live credentials.

The Jcode hook installer is deprecated and requires an explicit home. When deliberately used, `telegram-alerts-hook uninstall` removes only manifest-owned hooks and preserves unrelated settings. It is not needed for generic attention. `telegram-alerts disable` disables only the selected Alerts profile; it does not change Jcode's native Telegram flags unless the operator explicitly selects a native home.

Policy/card state stores only one-way fingerprints, timestamps, counters and Telegram message IDs. Explicit session filters remain in the private policy file. Existing state is validated before it can select a card to edit. Protect the notifications directory against other local users. Neither cooldowns nor message editing provide guaranteed exactly-once delivery if Telegram accepts a request but the connection fails before acknowledgment, or the process crashes before local state is durable.

## Supply chain and releases

Runtime dependencies are empty. Build tooling and GitHub Actions are updated through Dependabot. Actions are pinned to full commit SHAs with version comments. CI runs with read-only repository access except narrowly scoped release jobs. Release automation uses the repository token rather than requiring a personal access token. No bot credential is required by CI or release automation, and no PyPI publishing credential is configured.

Release Please prepares version/changelog pull requests from Conventional Commits. Required CI checks and a merge gate protect the default branch. Release assets include checksums. Checksums detect inconsistent downloads but are not a substitute for reviewing the trusted repository and release workflow.

A clean secret scan reduces publication risk but does not prove the absence of every possible secret or vulnerability.
