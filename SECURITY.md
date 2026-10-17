# Security policy

## Supported versions

During the initial 0.x series, security fixes target the latest released version only. The integration is unofficial and best effort, with no availability or support SLA. It was developed against Jcode v0.98.1, not every Jcode release.

## Report a vulnerability privately

Use this repository's **Security > Report a vulnerability** page to open a private report. Do not post secrets or exploitable private details in a public issue. Include affected version, a minimal synthetic reproducer, expected behavior, and impact. Remove bot tokens, chat IDs, session transcripts, configuration/backups, and private file paths.

If private reporting is unavailable, open a public issue requesting a private contact channel without including the vulnerability or sensitive data. If a real bot credential was exposed, stop using that credential and handle revocation directly in Telegram before sharing a report.

## Threat model and data flow

The extension intentionally transmits short public user-request and assistant-response excerpts to the Telegram destination already configured in the local Jcode profile. Installing it grants that capability to hooked turns in every project using that profile, including worker/swarm turns. Anyone with access to the destination can read those excerpts. Device notifications may reveal them on a lock screen.

No incoming command server, webhook endpoint, remote shell, or network listener is implemented here. Optional remote commands and approval replies belong to Jcode's native channel. New bot setup disables native replies by default. Hook registration and verbosity changes do not alter an existing native reply choice. Do not enable native remote control without evaluating Jcode's authorization and approval model separately.

The helper:

- Uses HTTPS JSON requests to Telegram with a timeout.
- Accepts bot tokens only through hidden interactive terminal input during setup.
- Requires an exact challenge from a matching private user/chat before saving a new destination.
- Tests delivery before enabling the native channel, and refuses to replace an existing webhook.
- Includes request context only after uniquely matching the current successful public response in the same saved session.
- Omits unbound prompt context on failure and prefers the current error over stale successful output.
- Does not use reasoning, images, or tool-result blocks as request context.
- Uses explicit UTF-16 bold entities rather than interpreting task text as HTML or Markdown.
- Writes configuration/backups, preferences, hook ownership, and receipts with mode 0600.

These controls do not defend against a compromised local user account, malicious replacements of installed code, a compromised Telegram account/bot, or hostile native Jcode components. Protect the installation directory and the parent directories of Jcode state. File-level symlink checks are not a substitute for an owner-controlled filesystem.

## Redaction is not data-loss prevention

Redaction removes common known credential forms, the configured bot token, labeled secret values, code fences, paths, URLs, and email addresses. It is **best effort** and may miss arbitrary private prose, unfamiliar credential formats, encoded secrets, or misleadingly structured text. Do not use it as the sole control protecting confidential projects. Review no-send previews and unregister the hook for work that must not leave the machine.

Checks in the notification are excerpts from the assistant response. They are not independently verified. A successful model turn is not proof that the entire user's goal succeeded.

## Local state and removal

`JCODE_HOME` defaults to `~/.jcode`. It contains credentials, session data, configuration backups, preferences, hook ownership metadata, and latest-receipt diagnostics. None belongs in this repository, release artifacts, CI secrets, public screenshots, or issue attachments. Backups can contain live credentials.

`jcode-telegram-hook uninstall` removes only the manifest-owned completion hook and preserves native settings. `jcode-telegram disable` also disables the native Telegram flags, so those commands are not interchangeable.

## Supply chain and releases

Runtime dependencies are empty. Build tooling and GitHub Actions are updated through Dependabot. Actions are pinned to full commit SHAs with version comments. CI runs with read-only repository access except narrowly scoped release jobs. Release automation uses the repository token rather than requiring a personal access token. No bot credential is required by CI or release automation, and no PyPI publishing credential is configured.

Release Please prepares version/changelog pull requests from Conventional Commits. Required CI checks and a merge gate protect the default branch. Release assets include checksums. Checksums detect inconsistent downloads but are not a substitute for reviewing the trusted repository and release workflow.

A clean secret scan reduces publication risk but does not prove the absence of every possible secret or vulnerability.
