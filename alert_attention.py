"""Explicit owner handoffs, separate from best-effort routine completion alerts."""
import os
import json
import re
import stat
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import alert_format as formatting
from alert_links import safe_url, _known, _TOKEN, _MAX_URL, _SECRET_PATH
import alert_policy as policy

MAX_INPUT_BYTES = 8192
MAX_REQUESTS = 256
RETENTION_SECONDS = 30 * 86400
STATE_FILE = "telegram-attention-state.json"
MAX_STATE_BYTES = 65536
MAX_INBOX_REGISTRY_BYTES = 65536
INBOX_REGISTRY_ENV = "TELEGRAM_ALERTS_INBOX_REGISTRY"
INBOX_BASE_ENV = "TELEGRAM_ALERTS_INBOX_BASE_URL"
_INBOX_PATH = re.compile(r"/(?:[A-Za-z0-9._~!$&()*+,;=:@/-]|%[0-9A-Fa-f]{2})*\Z")
_INBOX_QUERY = re.compile(r"[A-Za-z0-9._~!$&()*+,;=:@/?%-]*\Z")
_INBOX_FORBIDDEN = tuple(chr(code) for code in (92, 34, 39, 60, 62, 91, 93))
_INBOX_BASE_FORBIDDEN = _INBOX_FORBIDDEN + tuple(chr(code) for code in (37, 63, 35))
_INBOX_DECODED_PATH_FORBIDDEN = _INBOX_FORBIDDEN + ("?", "#")


class AttentionError(ValueError):
    """Only fixed, user-safe diagnostics may cross the CLI boundary."""


REVIEW_FILE = "telegram-review-policy.json"
REVIEW_ERROR = "Review host configuration could not be used safely. No message sent."


def _review_host(host):
    return (isinstance(host, str) and host == host.lower()
            and re.fullmatch(r'[a-z0-9.-]+', host) is not None
            and len(host.split('.')) >= 4 and host.endswith('.ts.net')
            and safe_url('https://' + host) == 'https://' + host)


def _review_policy(value):
    if (not isinstance(value, dict) or set(value) != {'version', 'host'}
            or type(value['version']) is not int or value['version'] != 1
            or (value['host'] is not None and not _review_host(value['host']))):
        raise ValueError
    return value


def review_host(home, host=None, *, write=False):
    """Query without creating files, or atomically set one private trusted host."""
    try:
        value = _review_policy({'version': 1, 'host': host})
        # _directory permits legacy writable directories for missing routine
        # policy queries. That compatibility exception is not for review trust.
        try:
            if os.stat(os.path.join(home, 'notifications'), follow_symlinks=False).st_mode & 0o022:
                raise ValueError
        except FileNotFoundError:
            pass
        with policy._directory(home, create=write) as folder:
            if folder is None:
                return value
            if write:
                with policy._locked(folder, '.telegram-review.lock'):
                    _review_policy(policy._read(folder, REVIEW_FILE, 1024, value, True))
                    policy._write(folder, REVIEW_FILE, value, 1024)
                return value
            return _review_policy(policy._read(folder, REVIEW_FILE, 1024,
                                               {'version': 1, 'host': None}, True))
    except (OSError, ValueError, TypeError, RecursionError):
        raise AttentionError(REVIEW_ERROR) from None


def _review_url(value, host, port, secrets):
    # Check the original, not just the port-neutral candidate, for all raw
    # hazards and known secrets (including secrets occurring in the port).
    if (not isinstance(value, str) or not value or len(value) > _MAX_URL
            or any(ord(c) < 33 or ord(c) > 126 for c in value)
            or any(c in value for c in '\\%?#[]"\'<>')
            or _known(value, secrets) or _TOKEN.search(value)):
        return None
    authority = host + ':' + str(port)
    if value not in ('https://' + authority, 'https://' + authority + '/'):
        return None
    path = '/' if value.endswith('/') else ''
    if safe_url('https://' + host + path, secrets) is None:
        return None
    # Telegram normalizes an empty HTTPS path to '/'. Send that exact root
    # spelling so strict entity confirmation need not accept changed targets.
    canonical = 'https://' + authority + '/'
    if _known(canonical, secrets) or _TOKEN.search(canonical):
        return None
    return canonical


def _read_inbox_registry(path):
    """Read only the registry's port and tailnet URL; never expose other fields."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except (OSError, TypeError, ValueError):
        return None, None
    try:
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or info.st_mode & 0o077
                    or info.st_size > MAX_INBOX_REGISTRY_BYTES):
                return None, None
            raw = stream.read(MAX_INBOX_REGISTRY_BYTES + 1)
    except OSError:
        return None, None
    if len(raw) > MAX_INBOX_REGISTRY_BYTES:
        return None, None
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=policy._pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        return None, None
    if not isinstance(value, dict):
        return None, None
    port = value.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        return None, None
    tailscale = value.get("tailscale")
    return port, tailscale.get("url") if isinstance(tailscale, dict) else None


def _trusted_inbox_base(value, port):
    if (not isinstance(value, str) or not value or len(value) > _MAX_URL
            or any(ord(c) < 33 or ord(c) > 126 for c in value)
            or any(c in value for c in _INBOX_BASE_FORBIDDEN)):
        return None
    try:
        parts = urlsplit(value)
        actual_port = parts.port
    except ValueError:
        return None
    host = parts.hostname
    if (parts.scheme != "https" or parts.username is not None or parts.password is not None
            or host is None or host != host.lower()
            or safe_url("https://" + host) != "https://" + host
            or parts.path not in ("", "/")
            or parts.query or parts.fragment):
        return None
    if actual_port != port and not (port == 443 and actual_port is None):
        return None
    authority = host if actual_port is None else f"{host}:{actual_port}"
    if parts.netloc != authority:
        return None
    return "https://" + authority


def _has_inbox_link(request):
    if not isinstance(request, dict) or not isinstance(request.get("links", []), list):
        return False
    return any(isinstance(link, dict) and isinstance(link.get("url"), str)
               and (link["url"].startswith(("http://localhost:", "http://127.0.0.1:"))
                    or link["url"].lower().startswith("https://"))
               for link in request.get("links", []))


def _inbox_mapping(environment, request):
    if not _has_inbox_link(request):
        return {"port": None, "base": None}
    registry = environment.get(INBOX_REGISTRY_ENV) if isinstance(environment, dict) else None
    if not isinstance(registry, str) or not registry:
        registry = str(Path.home() / ".plannotator" / "inbox" / "inbox.json")
    port, registered_url = _read_inbox_registry(os.path.expanduser(registry))
    override = environment.get(INBOX_BASE_ENV) if isinstance(environment, dict) else None
    source = override if isinstance(override, str) and override else registered_url
    base = _trusted_inbox_base(source, port) if port is not None else None
    return {"port": port, "base": base}


def _loopback_prefix(value, port):
    if not isinstance(value, str):
        return None
    if port is None:
        match = re.match(r"http://(?:localhost|127\.0\.0\.1):[0-9]+(?=[/?#]|$)", value)
        return match.group(0) if match else None
    for host in ("localhost", "127.0.0.1"):
        prefix = f"http://{host}:{port}"
        if value.startswith(prefix) and (len(value) == len(prefix) or value[len(prefix)] in "/?#"):
            return prefix
    return None


def _valid_inbox_target(value, mapping, secrets):
    if (not isinstance(value, str) or not value or len(value) > _MAX_URL
            or any(ord(c) < 33 or ord(c) > 126 for c in value)
            or any(c in value for c in _INBOX_FORBIDDEN)
            or re.search(r"%(?![0-9A-Fa-f]{2})", value)
            or _known(value, secrets) or _TOKEN.search(value)):
        return False
    try:
        parts = urlsplit(value)
        base_parts = urlsplit(mapping["base"])
    except ValueError:
        return False
    decoded_path = unquote(parts.path)
    if (parts.scheme != "https" or parts.netloc != base_parts.netloc
            or parts.username is not None or parts.password is not None
            or parts.hostname != base_parts.hostname or parts.port != base_parts.port
            or not _INBOX_PATH.fullmatch(parts.path)
            or chr(0xFFFD) in decoded_path
            or any(ord(c) < 32 or ord(c) == 127 or c in _INBOX_DECODED_PATH_FORBIDDEN for c in decoded_path)
            or _SECRET_PATH.search(decoded_path) or _TOKEN.search(decoded_path)
            or _known(decoded_path, secrets)):
        return False
    depth = 0
    for char in decoded_path:
        depth += (char == "(") - (char == ")")
        if depth < 0:
            return False
    if depth:
        return False
    for part in (parts.query, parts.fragment):
        decoded = unquote(part)
        if (not _INBOX_QUERY.fullmatch(part) or chr(0xFFFD) in decoded
                or _TOKEN.search(decoded) or _known(decoded, secrets)
                or _SECRET_PATH.search(decoded.replace("&", "/"))):
            return False
    return True


def _rewrite_inbox_url(value, mapping, secrets=()):
    prefix = _loopback_prefix(value, mapping.get("port"))
    if prefix is None:
        return None, None, False
    if not mapping.get("base"):
        return None, prefix, True
    suffix = value[len(prefix):]
    target = mapping["base"] + (suffix if suffix.startswith("/") else "/" + suffix)
    if not _valid_inbox_target(target, mapping, secrets):
        return None, prefix, False
    return target, prefix, False


def _record_inbox_rewrite(report, prefix, base):
    if report is None:
        return
    target = base + "/"
    for entry in report.setdefault("url_rewrites", []):
        if entry["from"] == prefix and entry["to"] == target:
            entry["count"] += 1
            return
    report["url_rewrites"].append({"from": prefix, "to": target, "count": 1})


def _record_inbox_warning(report, mapping):
    if report is None:
        return
    port = mapping.get("port")
    if port is None:
        warning = "Local Inbox link omitted because the read-only Plannotator registry did not provide a valid port and tailnet URL."
    else:
        warning = f"Local Inbox link for registered port {port} omitted because no trusted tailnet URL is available."
    warnings = report.setdefault("url_rewrite_warnings", [])
    if warning not in warnings:
        warnings.append(warning)


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


def render(request, environment, home, secrets=(), *, review_port=None,
           inbox_mapping=None, rewrite_report=None):
    secrets = tuple(secrets)
    host = None
    if review_port is not None:
        if type(review_port) is not int or not 1024 <= review_port <= 65535:
            raise AttentionError("Review port must be an integer from 1024 through 65535. No message sent.")
        host = review_host(home)['host']
        if host is None:
            raise AttentionError(REVIEW_ERROR)
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
    matched_review = False
    for link in supplied:
        if not isinstance(link, dict) or set(link) != {"label", "url"}:
            raise AttentionError("Each attention link requires only label and url.")
        label = _text(link["label"], "link label", 80, secrets)
        if len(label.splitlines()) != 1 or "[redacted]" in label:
            raise AttentionError("Attention link labels must be single-line, non-sensitive text.")
        mapped = None
        source_prefix = None
        unmapped = False
        if inbox_mapping is not None:
            mapped, source_prefix, unmapped = _rewrite_inbox_url(link["url"], inbox_mapping, secrets)
        if unmapped:
            _record_inbox_warning(rewrite_report, inbox_mapping)
            continue
        review = _review_url(link['url'], host, review_port, secrets) if host else None
        matched_review = matched_review or review is not None
        direct_inbox = (link["url"] if inbox_mapping and inbox_mapping.get("base")
                        and _valid_inbox_target(link["url"], inbox_mapping, secrets) else None)
        target = review or mapped or direct_inbox or safe_url(link["url"], secrets)
        if target is None:
            raise AttentionError("Attention link rejected: use a safe public-DNS HTTPS URL or a safe URL on the trusted Inbox origin. No message sent.")
        if mapped is not None:
            _record_inbox_rewrite(rewrite_report, source_prefix, inbox_mapping["base"])
        # Show the destination host even when the agent supplies a friendly label.
        links.append({"label": label + " · " + urlsplit(target).netloc, "url": target})
    if review_port is not None and not matched_review:
        raise AttentionError("Attention requires a matching root HTTPS review link for the declared port. No message sent.")
    text, entities = "🔔 ", []

    def append(value, *, bold=False):
        nonlocal text
        if bold:
            entities.append({"type": "bold", "offset": formatting.utf16_length(text),
                             "length": formatting.utf16_length(value)})
        text += value

    append("Agent needs you", bold=True)
    # Explicit attention is agent-agnostic; never fetch or display a Jcode session name.
    append("\n📁 " + formatting.folder_label({"TELEGRAM_ALERTS_CWD": environment.get("TELEGRAM_ALERTS_CWD")}, secrets=secrets))
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


def _load_policy(home, legacy_home):
    primary = os.path.join(home, "notifications", policy.POLICY_FILE)
    legacy = (os.path.join(legacy_home, "notifications", policy.POLICY_FILE)
              if legacy_home is not None else None)
    if legacy is not None and not os.path.lexists(primary) and os.path.lexists(legacy):
        return policy.load_policy(legacy_home)
    return policy.load_policy(home)


def _legacy_requests(home, legacy_home):
    if legacy_home is None or os.path.abspath(home) == os.path.abspath(legacy_home):
        return {}
    path = os.path.join(legacy_home, "notifications", STATE_FILE)
    if not os.path.lexists(path):
        return {}
    with policy._directory(legacy_home) as folder:
        if folder is None:
            raise ValueError("Unsafe legacy attention state directory")
        value = _state(policy._read(folder, STATE_FILE, MAX_STATE_BYTES,
                                   {"version": 1, "requests": {}}, True))
    return value["requests"]


def _publish_options(key, destination_fingerprint, resend):
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,199}", key):
        raise AttentionError("Attention --key must be a stable decision/revision identifier of 1-200 ASCII characters.")
    if (not isinstance(destination_fingerprint, str) or not policy._HEX.fullmatch(destination_fingerprint)
            or type(resend) is not bool):
        raise AttentionError("Invalid attention destination or resend option.")


def publish(home, environment, request, key, deliver, destination_fingerprint, *, secrets=(), resend=False,
            review_port=None, legacy_home=None):
    _publish_options(key, destination_fingerprint, resend)
    options = {'secrets': secrets, 'resend': resend, 'review_port': review_port,
               'legacy_home': legacy_home}
    if review_port is None:
        return _publish(home, environment, request, key, deliver, destination_fingerprint, **options)
    # Reject malformed input or absent/unsafe trust before any lock-file
    # creation, then validate again under the trust lock before sending.
    options['secrets'] = tuple(secrets)
    render(request, environment, home, options['secrets'], review_port=review_port,
           inbox_mapping=_inbox_mapping(environment, request))
    try:
        with policy._directory(home) as folder:
            if folder is None:
                raise AttentionError(REVIEW_ERROR)
            # Always take review before attention state. _publish/render re-reads
            # trust inside this lock, held until delivery and recording finish.
            # Thus a completed revoke cannot be followed by an old-trust send.
            with policy._locked(folder, '.telegram-review.lock'):
                return _publish(home, environment, request, key, deliver, destination_fingerprint, **options)
    except AttentionError:
        raise
    except (OSError, ValueError, TypeError, RecursionError):
        raise AttentionError(REVIEW_ERROR) from None


def _publish(home, environment, request, key, deliver, destination_fingerprint, *, secrets=(), resend=False,
             review_port=None, legacy_home=None):
    session = environment.get("JCODE_SESSION_ID")
    mapping = _inbox_mapping(environment, request)
    message = render(request, environment, home, secrets, review_port=review_port,
                     inbox_mapping=mapping)
    try:
        config = _load_policy(home, legacy_home)
        if session in config["exclude_sessions"] or (config["include_sessions"] and session not in config["include_sessions"]):
            raise AttentionError("Attention disabled by the configured session filters. No message sent.")
        fingerprint = policy._hash(destination_fingerprint + "\0" + key)
        now = int(time.time())
        with policy._directory(home, create=True) as folder, policy._locked(folder, ".telegram-attention.lock"):
            state = _state(policy._read(folder, STATE_FILE, MAX_STATE_BYTES, {"version": 1, "requests": {}}, True))
            state["requests"] = {k: v for k, v in state["requests"].items() if now - v["at"] <= RETENTION_SECONDS}
            legacy_requests = _legacy_requests(home, legacy_home)
            legacy_requests = {k: v for k, v in legacy_requests.items() if now - v["at"] <= RETENTION_SECONDS}
            existing = state["requests"].get(fingerprint) or legacy_requests.get(fingerprint)
            if existing and not resend:
                return {"state": "already_sent", "telegram_message_id": existing["message_id"]}
            active = {**legacy_requests, **state["requests"]}
            if fingerprint not in active and len(active) >= MAX_REQUESTS:
                raise AttentionError("Attention state is at capacity. No message sent.")
            # Re-read the read-only registry immediately before rendering the
            # message sent under this lock. Only the outgoing copy is rewritten.
            report = {"url_rewrites": [], "url_rewrite_warnings": []}
            message = render(request, environment, home, secrets, review_port=review_port,
                             inbox_mapping=_inbox_mapping(environment, request), rewrite_report=report)
            response = deliver("sendMessage", message)
            if (not isinstance(response, dict) or not policy._message_id(response.get("message_id"))
                    or not formatting.formatting_confirmed(message, response)):
                raise AttentionError("Attention delivery was not confirmed. It may have arrived; do not retry automatically.")
            state["requests"][fingerprint] = {"at": now, "message_id": response["message_id"]}
            try:
                policy._write(folder, STATE_FILE, state, MAX_STATE_BYTES)
            except (OSError, ValueError):
                raise AttentionError("Telegram accepted the attention message, but local confirmation could not be saved. Do not retry automatically.") from None
            receipt = {"state": "sent", "telegram_message_id": response["message_id"],
                       "response_confirmed": True, "formatting_confirmed": True}
            if report["url_rewrites"]:
                receipt["url_rewrites"] = report["url_rewrites"]
            if report["url_rewrite_warnings"]:
                receipt["url_rewrite_warnings"] = report["url_rewrite_warnings"]
            return receipt
    except AttentionError:
        raise
    except KeyboardInterrupt:
        raise AttentionError("Attention interrupted. Delivery may have arrived; do not retry automatically.") from None
    except (OSError, ValueError, TypeError, RecursionError):
        raise AttentionError("Attention policy/state could not be used safely. No automatic retry was made.") from None
