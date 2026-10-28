---
name: telegram
description: "Send relevance-selected generic updates or explicitly requested owner handoffs through Telegram Alerts."
---

# Telegram owner notifications

Use for one material update or explicit owner handoff, not routine command narration. “Needs you,” urgency, or a review URL alone does not request direct delivery. `attention` deliberately bypasses Clef; use it only for explicit direct-send intent or a required review/authentication link, never as a fallback when Clef is unavailable.

## Routine Clef-gated updates

Submit one UTF-8 JSON object with `telegram-alerts update --key STABLE_CANDIDATE_ID`:

- required `summary` (≤400 characters);
- optional gate-only `context` (≤3,000 characters);
- optional explicit `project` (≤120 characters; never infer from CWD);
- optional up to three `{ "label", "url" }` links.

The 8,192-byte input limit, duplicate/unknown-key refusal, and link validation are enforced by the CLI. **Put URLs only in `links`.** Generic Clef settings belong to the selected Alerts home; they never inherit a Jcode selector or key. `status` and `preview` never infer. The generic command does not require a Jcode session or read native sessions/lifecycle hooks.

Clef receives only summary/context/project; links are not relevance evidence. Context goes only to the configured decision endpoint, never to Telegram or update diagnostics. YES sends the original sanitized summary, explicit project, and validated links in the neutral `🔔 Update` template. NO, missing prompt/config/key, busy state, transport errors, or invalid decisions suppress delivery with a structured receipt. The versioned prompt manifest is intentionally empty pending owner vet, so updates currently return `prompt_unavailable` without inference or delivery. Do not switch to `attention` when Clef is unavailable.

Use a stable candidate key. Repeated identical candidates are idempotent; changed content is a new decision. Ambiguous delivery may have arrived: do not change the key to force another send or retry automatically.

## Explicit owner handoffs

`telegram-alerts attention` sends directly and bypasses Clef. The compatibility JSON requires `context` (≤400 characters) and `needs_you` (≤800); `recommendation` (≤600) and up to three links are optional. It uses the same neutral heading, without inferred project or invocation CWD. Keep a stable decision/revision key. **Do not automatically retry. Use `--resend` only after an explicit owner request.** Link syntax does not prove reachability or authorization.

## Inbox links and receipts

Pass the exact Plannotator Inbox URL in `links[].url`; do not rewrite it in the request. The CLI reads `~/.plannotator/inbox/inbox.json` read-only and uses its registered `port` and `tailscale.url`. Only `http://localhost:<registered-port>` and `http://127.0.0.1:<registered-port>` are rewritten. The outgoing path, query, and fragment are preserved byte-for-byte. If a trusted mapping is unavailable, the local link is omitted with a warning; never invent a mapping. `TELEGRAM_ALERTS_INBOX_REGISTRY` and `TELEGRAM_ALERTS_INBOX_BASE_URL` select registry/base overrides.

A receipt with `state: sent`, `response_confirmed`, and `formatting_confirmed` is delivery evidence, not proof of readership or approval. A suppression is not a delivery receipt. Generic commands do not require a Jcode session; a matching optional `JCODE_SESSION_ID` is used only by legacy compatibility filters. The profile defaults to `~/.config/telegram-alerts`; `TELEGRAM_ALERTS_HOME` selects another home. The old `~/.jcode/config.toml` is a read-only Telegram-credentials fallback only; it never supplies Clef configuration.
