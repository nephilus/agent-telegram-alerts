# Generic Clef prompt resources

Generic routine updates require an explicitly configured, versioned prompt resource. The reader is shared with the existing selector transport but the generic route does **not** fall back to the legacy Jcode prompt. `legacy-inline-v1` remains reserved for the opt-in Jcode adapter and is rejected by `telegram-alerts clef configure` for generic updates.

The generic Clef configuration and legacy Jcode selector still use the same selector file when they target the same home. Configuration now refuses to switch that file between generic and legacy ownership. Use distinct `TELEGRAM_ALERTS_HOME` and `JCODE_HOME` values for intentionally separate routes; no migration or automatic copying is provided. Legacy processing proceeds only when its stored selection is exactly `legacy-inline-v1`, and generic processing proceeds only with a verified non-legacy resource. A wrong-route configuration is not reported as route-ready and is rejected before the Clef key is read or inference is requested.

## Resource format and immutable byte pins

Resources are listed in `prompts/clef/manifest.json`. Version 2 entries contain exactly a resource `id` and the lowercase SHA-256 of that resource's **raw question-file bytes**:

```json
{"version":2,"resources":[{"id":"example-v1","sha256":"<64 lowercase hex digits>"}]}
```

Each listed resource is named `<id>.json` and contains a bare question object (no wrapper, version, or embedded ID):

```json
{
  "type": "choice",
  "instructions": "Owner-vetted instructions",
  "criteria": {"yes": "Typed YES criterion", "no": "Typed NO criterion"}
}
```

The ID, filename, and manifest pin are one permanent binding. Do not change the bytes behind an ID or retarget that ID to a new digest; a revised prompt requires a new reviewed ID. Preserve the approved bytes exactly. At load, the reader bounds and reads those bytes once, checks their raw SHA-256 against the trusted manifest pin, and only then parses and validates that same byte buffer. It does not wrap, reformat, canonicalize, or compare a canonicalized hash. Whitespace, key order, or line-ending changes therefore fail the pin even when parsed JSON is equivalent.

The loader rejects duplicate JSON keys and manifest IDs, malformed/missing pins, unknown or missing schema fields, invalid IDs, unsupported versions, non-finite JSON values, invalid UTF-8, malformed questions, symlinks and over-sized files. Resource directories must be trusted directories; manifest and question files must be regular trusted files. All are owned by root or the executing user and must not be group- or other-writable. Normal `0755` directories and `0644` files are supported. The source-tree root or active installation data prefix is selected deliberately and its resource path is traversed from an open directory descriptor without following links. Only the configured installation-prefix alias itself is resolved intentionally; links inside the resource tree fail closed. A missing candidate tree may be skipped, but an existing unsafe, incomplete, or malformed selected tree is an error and is never a reason to fall back to another candidate. These checks protect installed resources against untrusted filesystem writers; they do not protect against compromised application code or arbitrary writes by the same user who runs the program.

## Installation and configuration

A supported deployed layout is a wheel installed into a virtual environment that remains at its install location. The loader reads `share/telegram-alerts/prompts/clef/` under that interpreter's `sysconfig` data prefix, independently of the current working directory. A source checkout uses the adjacent `prompts/clef/` development tree. This contract does not claim support for user-site, arbitrary `--prefix`, relocated environments, or every platform-specific installation layout; validate those deployments separately before relying on them.

The wheel explicitly packages the manifest in `share/telegram-alerts/prompts/clef/`; the source archive includes the prompt tree. No generic prompt file is packaged until its exact revision is reviewed and approved. This branch intentionally packages only the **empty v2 manifest** (`{"version":2,"resources":[]}`), so it contains **no enabled generic update prompt**. `clef configure` stores connection metadata and the explicitly supplied resource ID only; configuration without `--prompt-resource` remains unavailable. `clef status` separately reports generic and legacy route readiness. Configuration and status do not infer or send. An absent, stale, unsafe, malformed, or unavailable prompt is a structured fail-closed suppression before Clef inference or Telegram delivery.

## Owner-vetted activation boundary

The actual production prompt revision is still pending owner vet. Do not add a candidate or change the empty manifest's resource list until the exact prompt artifact and SHA-256 are explicitly approved by the owner. After approval, package the exact immutable bare question bytes and matching v2 manifest pin, add deterministic fixture tests, and configure only the approved ID in the generic home. Do not make the resource a generic default merely because its file is present. Installation, live inference, Telegram sends, merge, and release remain separate owner-authorized steps.

Offline tests use deterministic fixture questions and pins. They do not contact the decision endpoint, score or tune a final prompt, select a production resource, or send Telegram messages. The generic candidate envelope passed to Clef contains only `summary`, optional `context`, and optional `project`; links remain validated delivery data and are excluded from relevance evidence. Candidate text is untrusted input. Gate-only context is sanitized before the request and is not retained in update diagnostics or rendered/returned to Telegram.
