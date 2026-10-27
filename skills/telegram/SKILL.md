---
name: telegram
description: "Send concise owner notifications and actionable handoffs with the generic Telegram Alerts CLI."
---

# Telegram owner notifications

**Use for:** An owner notification, an explicitly requested Telegram update, or an owner-dependent handoff before waiting. Do not narrate every command or duplicate routine notifications.

**Produce:** A concise message through the configured Telegram Alerts CLI and retain the actual receipt. A Telegram acknowledgment proves delivery formatting, not readership or approval.

## Actionable owner handoff

- Use `telegram-alerts attention` from any shell or agent tool. It does not require a Jcode session, native Jcode CLI, or hook. A legacy session include-list may still require a matching optional `JCODE_SESSION_ID`; otherwise no session ID is needed.
- Obtain the reviewed revision and stable decision key from `owner-review`. Use `<owner>/<repo>:<decision>:<revision>` and reuse that key for the same decision/revision.
- Send one UTF-8 JSON object on stdin. `context` and `needs_you` are required; `recommendation` and up to three `{ "label", "url" }` links are optional. Put URLs only in `links`, never in text fields.

```sh
telegram-alerts attention --key owner/repo:decision:revision <<'JSON'
{
  "context": "The reviewed change is ready for an owner decision.",
  "needs_you": "Choose the approved rollout option.",
  "recommendation": "Use the staged option because it preserves rollback.",
  "links": [{"label": "Review", "url": "https://github.com/owner/repo/pull/123"}]
}
JSON
```

Use the actual published revision and verified destination, not the illustrative values above. The CLI rejects unsafe or malformed requests before sending. Its input is bounded to 8192 bytes and rejects duplicate/unknown keys.

## Plannotator Inbox links

Pass the Inbox URL exactly as returned by Plannotator in `links[].url`; do not rewrite or store a replacement in the request. At send time, the CLI reads `~/.plannotator/inbox/inbox.json` read-only and uses its registered `port` and `tailscale.url`.

Only the exact `http://localhost:<registered-port>` and `http://127.0.0.1:<registered-port>` prefixes are rewritten. The path, query, and fragment (including `#thread=...`) are preserved byte-for-byte in the Telegram link. Other loopback URLs are not rewritten and remain subject to normal URL validation. Set `TELEGRAM_ALERTS_INBOX_REGISTRY` to select another registry path or `TELEGRAM_ALERTS_INBOX_BASE_URL` to explicitly override the published base. If no trusted tailnet URL is available, the local Inbox link is omitted with a warning; the alert still sends. Never invent or guess a tailnet mapping.

The receipt reports the rewritten source and destination origins without echoing the private path, query, or thread fragment. The request is not mutated or saved by rewriting.

## Delivery and retries

- Check and retain the CLI's printed receipt. `state: sent`, `response_confirmed`, and `formatting_confirmed` are required evidence of an acknowledged delivery. `already_sent` means this invocation did not contact Telegram.
- Do not automatically retry a failed or ambiguous send; it may already have arrived. Use `--resend` only after an explicit owner request.
- A delivery receipt is not proof that the owner saw or approved the message. Follow `owner-review` for authorization and revision correlation.
- Do not add a bot, poller, hook, or notification service, and do not change credentials, trust, or delivery policy to force a send. If the CLI or Telegram profile is unavailable, report the prerequisite instead.

The Telegram profile is independent of Jcode session state. `TELEGRAM_ALERTS_HOME` selects the profile; the CLI defaults to `~/.config/telegram-alerts`. Existing installations may read the old Telegram-only credentials from `~/.jcode` in read-only compatibility mode, with a notice; all new writes go to the selected Alerts home.
