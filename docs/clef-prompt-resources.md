# Generic Clef prompt resources

Generic routine updates require an explicitly configured, versioned prompt resource. The reader is shared with the existing selector transport but the generic route does **not** fall back to the legacy Jcode prompt. `legacy-inline-v1` remains reserved for the opt-in Jcode adapter and is rejected by `telegram-alerts clef configure` for generic updates.

## Resource format

Resources are data files under `prompts/clef/`, listed by `manifest.json`:

```json
{"version":1,"resources":["owner-vetted-update-v1"]}
```

Each listed resource is named `<id>.json` and has this shape:

```json
{
  "version": 1,
  "id": "owner-vetted-update-v1",
  "question": {
    "type": "choice",
    "instructions": "Owner-vetted instructions",
    "criteria": {"yes": "Typed YES criterion", "no": "Typed NO criterion"}
  }
}
```

The loader rejects duplicate JSON keys, unknown/missing fields, invalid IDs, unsafe resource paths, unsupported versions, malformed questions, symlinks and over-sized files. The prompt hash is a SHA-256 of the question object serialized as UTF-8 JSON with sorted keys, ASCII escapes, no insignificant whitespace, and non-finite values forbidden. Status and private selector diagnostics report resource ID and hash separately from candidate content. `telegram-selector.json` stores only the explicitly selected resource ID, not the prompt body, endpoint/key values in status, or candidate text.

The package copies the manifest to `share/telegram-alerts/prompts/clef/manifest.json`; the loader checks the source tree for development and that share directory for installed wheels. This branch intentionally packages an empty manifest, so it contains **no enabled generic update prompt**. `clef configure` without a prompt ID configures only explicit endpoint/model/key-file metadata and reports `update_route_ready: false`. An absent/unavailable prompt is a structured fail-closed suppression before inference or Telegram delivery.

## Owner-vetted activation boundary

Do not add a candidate or change the manifest's resource list until the prompt revision has been independently reviewed and its exact hash explicitly approved by the owner. After approval, integrate the exact immutable artifact without editing its question text, add deterministic loader and input-contract tests, and package that resource as a versioned asset. Do not make the resource a generic default merely because its file is present: generic configuration must select its exact ID explicitly in the generic home. Installation, live inference, Telegram sends, merge and release remain separate owner-authorized steps.

Offline tests use an injected deterministic fixture resource. They do not contact the decision endpoint, score/tune a final prompt, select a production resource, or send Telegram messages. The generic candidate envelope passed to Clef contains only `summary`, optional `context`, and optional `project`; links remain validated delivery data and are excluded from relevance evidence. Candidate text is untrusted input. Gate-only context is sanitized before the request and is not retained in update diagnostics or rendered/returned to Telegram.
