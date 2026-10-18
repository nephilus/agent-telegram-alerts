"""Explicit owner handoffs, separate from best-effort routine completion alerts."""
import json
import re
import time
from urllib.parse import urlsplit

import alert_format as formatting
from alert_links import safe_url
import alert_policy as policy

MAX_INPUT_BYTES = 8192
MAX_REQUESTS = 256
RETENTION_SECONDS = 30 * 86400
STATE_FILE = "telegram-attention-state.json"
MAX_STATE_BYTES = 65536


class AttentionError(ValueError):
    """Only fixed, user-safe diagnostics may cross the CLI boundary."""


def read_request(stream):
    if stream.isatty():
        raise AttentionError("Attention expects a JSON object on standard input; see --help.")
    raw = getattr(stream, "buffer", stream).read(MAX_INPUT_BYTES + 1)
    try:
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError
        return json.loads(raw.decode("utf-8"), object_pairs_hook=policy._pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise AttentionError("Attention input must be one UTF-8 JSON object of at most 8192 bytes, without duplicate keys.") from None


def _text(value, title, limit, secrets, *, optional=False):
    if not isinstance(value, str) or len(value) > limit:
        raise AttentionError(f"Attention {title} must be text of at most {limit} characters.")
    if any(re.search(r"(?:https?|wss?)://", text, flags=re.I)
           for text in (value, formatting.normalize_text(value))):
        raise AttentionError("Put attention URLs in links, not text fields.")
    cleaned = formatting.sanitize(value, secrets)
    if "[link]" in cleaned:
        raise AttentionError("Put attention URLs in links, not text fields.")
    if not cleaned and not optional:
        raise AttentionError(f"Attention {title} cannot be empty after redaction.")
    return cleaned


def render(request, environment, home, secrets=()):
    allowed = {"context", "needs_you", "recommendation", "links"}
    if not isinstance(request, dict) or not {"context", "needs_you"} <= request.keys() or request.keys() - allowed:
        raise AttentionError("Attention requires context and needs_you; only recommendation and links are optional.")
    context = _text(request["context"], "context", 400, secrets)
    needed = _text(request["needs_you"], "needs_you", 800, secrets)
    recommendation = _text(request.get("recommendation", ""), "recommendation", 600, secrets, optional=True)
    supplied = request.get("links", [])
    if not isinstance(supplied, list) or len(supplied) > 3:
        raise AttentionError("Attention links must be a list of at most three label/url objects.")
    links = []
    for link in supplied:
        if not isinstance(link, dict) or set(link) != {"label", "url"}:
            raise AttentionError("Each attention link requires only label and url.")
        label = _text(link["label"], "link label", 80, secrets)
        if len(label.splitlines()) != 1 or "[redacted]" in label:
            raise AttentionError("Attention link labels must be single-line, non-sensitive text.")
        target = safe_url(link["url"], secrets)
        if target is None:
            raise AttentionError("Attention link rejected: use a verified public-DNS HTTPS URL without credentials, query, fragment, escapes or a non-443 port. No message sent.")
        # Show the destination host even when the agent supplies a friendly label.
        links.append({"label": label + " · " + urlsplit(target).netloc, "url": target})
    text, entities = "🔔 ", []

    def append(value, *, bold=False):
        nonlocal text
        if bold:
            entities.append({"type": "bold", "offset": formatting.utf16_length(text),
                             "length": formatting.utf16_length(value)})
        text += value

    append("Jcode needs you", bold=True)
    session = environment.get("JCODE_SESSION_ID", "")
    name = formatting.session_label(formatting.saved_session_name(home, session), secrets=secrets)
    if name:
        append("\n🏷 " + name)
    append("\n📁 " + formatting.folder_label({"JCODE_HOOK_CWD": environment.get("JCODE_HOOK_CWD")}, secrets=secrets))
    for icon, title, value in (("👉", "Needs you", needed), ("🧭", "Context", context),
                                ("✅", "Recommended", recommendation)):
        if value:
            append("\n\n" + icon + " ")
            append(title + ":", bold=True)
            append("\n" + value)
    footer = formatting.prepend_message(formatting.link_footer(links, "expanded"), text)
    message = {"text": footer["text"], "entities": entities + footer["entities"],
               "link_preview_options": {"is_disabled": True}, "disable_notification": False}
    # Attention never silently clips a required action, choice or link.
    if formatting.utf16_length(message["text"]) > 3500:
        raise AttentionError("Attention message is too long; shorten its fields. No message sent.")
    return message


def _state(value):
    if (not isinstance(value, dict) or set(value) != {"version", "requests"}
            or type(value["version"]) is not int or value["version"] != 1
            or not isinstance(value["requests"], dict) or len(value["requests"]) > MAX_REQUESTS):
        raise ValueError("Invalid attention state")
    for key, entry in value["requests"].items():
        if (not isinstance(key, str) or not policy._HEX.fullmatch(key) or not isinstance(entry, dict)
                or set(entry) != {"at", "message_id"}
                or not policy._integer(entry["at"], policy.MAX_TIMESTAMP)
                or not policy._message_id(entry["message_id"])):
            raise ValueError("Invalid attention entry")
    return value


def publish(home, environment, request, key, deliver, destination_fingerprint, *, secrets=(), resend=False):
    session = environment.get("JCODE_SESSION_ID")
    if not isinstance(session, str) or not re.fullmatch(r"session_[A-Za-z0-9_-]{1,180}", session):
        raise AttentionError("Attention requires JCODE_SESSION_ID from a Jcode tool invocation.")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,199}", key):
        raise AttentionError("Attention --key must be a stable decision/revision identifier of 1-200 ASCII characters.")
    if (not isinstance(destination_fingerprint, str) or not policy._HEX.fullmatch(destination_fingerprint)
            or type(resend) is not bool):
        raise AttentionError("Invalid attention destination or resend option.")
    message = render(request, environment, home, secrets)
    try:
        config = policy.load_policy(home)
        if session in config["exclude_sessions"] or (config["include_sessions"] and session not in config["include_sessions"]):
            raise AttentionError("Attention disabled by the configured session filters. No message sent.")
        fingerprint = policy._hash(destination_fingerprint + "\0" + key)
        now = int(time.time())
        with policy._directory(home, create=True) as folder, policy._locked(folder, ".telegram-attention.lock"):
            state = _state(policy._read(folder, STATE_FILE, MAX_STATE_BYTES, {"version": 1, "requests": {}}, True))
            state["requests"] = {k: v for k, v in state["requests"].items() if now - v["at"] <= RETENTION_SECONDS}
            if fingerprint in state["requests"] and not resend:
                return {"state": "already_sent", "telegram_message_id": state["requests"][fingerprint]["message_id"]}
            if fingerprint not in state["requests"] and len(state["requests"]) >= MAX_REQUESTS:
                raise AttentionError("Attention state is at capacity. No message sent.")
            response = deliver("sendMessage", message)
            if (not isinstance(response, dict) or not policy._message_id(response.get("message_id"))
                    or not formatting.formatting_confirmed(message, response)):
                raise AttentionError("Attention delivery was not confirmed. It may have arrived; do not retry automatically.")
            state["requests"][fingerprint] = {"at": now, "message_id": response["message_id"]}
            try:
                policy._write(folder, STATE_FILE, state, MAX_STATE_BYTES)
            except (OSError, ValueError):
                raise AttentionError("Telegram accepted the attention message, but local confirmation could not be saved. Do not retry automatically.") from None
            return {"state": "sent", "telegram_message_id": response["message_id"],
                    "response_confirmed": True, "formatting_confirmed": True}
    except AttentionError:
        raise
    except KeyboardInterrupt:
        raise AttentionError("Attention interrupted. Delivery may have arrived; do not retry automatically.") from None
    except (OSError, ValueError, TypeError, RecursionError):
        raise AttentionError("Attention policy/state could not be used safely. No automatic retry was made.") from None
