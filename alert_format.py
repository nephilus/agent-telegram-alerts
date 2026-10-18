"""Bounded local excerpts for Telegram alerts. Never reads reasoning or tool blocks."""
import json
import os
from pathlib import Path
import re
import stat

from alert_links import extract_links

PROFILES = {
    "brief": {"words": 25, "chars": 320, "asked": 6, "result": 8, "checked": 0, "next": 0, "asked_chars": 80, "result_chars": 110, "extra_chars": 0},
    "contextual": {"words": 60, "chars": 800, "asked": 12, "result": 18, "checked": 8, "next": 8, "asked_chars": 180, "result_chars": 300, "extra_chars": 100},
    "expanded": {"words": 100, "chars": 1400, "asked": 20, "result": 34, "checked": 14, "next": 14, "asked_chars": 260, "result_chars": 520, "extra_chars": 220},
}
MAX_SESSION_BYTES = 8 * 1024 * 1024


def clip(text, words, chars=1400):
    """Keep line breaks while imposing both word and character limits."""
    matches = list(re.finditer(r"\S+", text))
    if len(matches) > words:
        text = text[:matches[words - 1].end()].rstrip() + "…"
    if len(text) > chars:
        text = text[:chars - 1].rstrip() + "…"
    return text


def sanitize(text, secrets=(), *, redact_paths=True):
    if not isinstance(text, str):
        return ""
    text = text[:16000].encode("utf-8", errors="replace").decode("utf-8")
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060\u2066-\u2069\ufeff]", "", text)
    text = re.sub(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)", "", text, flags=re.S)
    text = text.replace("**", "").replace("`", "").replace("__", "")
    for secret in secrets:
        if isinstance(secret, str) and secret:
            text = text.replace(secret, "[redacted]")
    text = re.sub(r"-----BEGIN [^-]+-----.*?(?:-----END [^-]+-----|\Z)", "[redacted]", text, flags=re.S)
    text = re.sub(r"\b[0-9]{5,}:[A-Za-z0-9_-]{20,}\b", "[redacted]", text)
    text = re.sub(r"\b(?:sk-|gh[pousr]_|github_pat_|xox[baprs]-|AKIA)[A-Za-z0-9_-]{8,}\b", "[redacted]", text)
    text = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted]", text)
    text = re.sub(
        r'''(?i)(["'](?:[\w-]+[_-])?(?:password|passwd|api[_ -]?key|(?:access[_ -]?|refresh[_ -]?|bot[_ -]?)?token|secret|authorization)["']\s*:\s*)(?:"(?:\\.|[^"\\])*(?:"|\Z)|'(?:\\.|[^'\\])*(?:'|\Z)|[^\s,}\]]+)''',
        r"\1[redacted]", text,
    )
    text = re.sub(
        r'''(?i)\b(password|passwd|api[_ -]?key|(?:access[_ -]?|refresh[_ -]?|bot[_ -]?)?token|secret|authorization)\b(\s*[:=]\s*)(?:"(?:\\.|[^"\\])*(?:"|\Z)|'(?:\\.|[^'\\])*(?:'|\Z)|[^\s,;]+)''',
        r"\1\2[redacted]", text,
    )
    text = re.sub(r"(?:https?|wss?)://[^\s<>]+", "[link]", text, flags=re.I)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", text)
    if redact_paths:
        text = re.sub(r"(?<!\w)(?:~?/|[A-Za-z]:\\)[^\s,;]+", "[path]", text)
    text = re.sub(r"\[([^\]\n]+)\]\(\[link\]\)?", r"\1 [link]", text)
    text = re.sub(r"\[([^\]\n]+)\]\([^\n)]*\)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def text_blocks(message):
    """Only public text blocks, never tool results, images, or hidden reasoning."""
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(block["text"] for block in content
                     if isinstance(block, dict) and block.get("type") == "text"
                     and isinstance(block.get("text"), str))


def read_session(home, session_id):
    if not isinstance(session_id, str) or not re.fullmatch(r"session_[A-Za-z0-9_-]{1,180}", session_id):
        return {}
    path = Path(home) / "sessions" / (session_id + ".json")
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SESSION_BYTES:
                return {}
            data = json.loads(stream.read(MAX_SESSION_BYTES + 1))
        if not isinstance(data, dict) or data.get("id") != session_id or not isinstance(data.get("messages"), list):
            return {}
        return data
    except (OSError, ValueError, RecursionError):
        return {}


def saved_session_name(home, session_id):
    """Follow native explicit-name precedence, never the generated title/name."""
    session = read_session(home, session_id)
    title = session.get("custom_title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    label = session.get("save_label")
    if session.get("saved") is True and isinstance(label, str):
        return label.strip()
    return ""


def user_request(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<(system-reminder|environment_context)[^>]*>.*?(?:</\1>|\Z)", "", text, flags=re.S | re.I)
    text = re.sub(r"^\[\d{4}-\d{2}-\d{2}[^\]]*\]\s*", "", text.strip())
    internal = ("[auto]", "[notification]", "[applet action]", "[swarm", "**background task**",
                "you have 1 incomplete todo", "<system-reminder>", "# session context")
    if text.lower().startswith(internal):
        return ""
    if text.strip().lower() in ("yes", "ok", "okay", "continue", "thanks", "exit"):
        return ""
    return text.strip()


def session_prompt(home, session_id, response):
    """Bind the prompt to an exact saved response, not a newer concurrent turn."""
    if not isinstance(response, str) or not response.strip():
        return ""
    data = read_session(home, session_id)
    messages = data.get("messages", [])
    expected = response.strip()
    matches = []
    for index, item in enumerate(messages):
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        saved = text_blocks(item).strip()
        if saved == expected or (len(response) >= 4000 and saved[:4000].strip() == expected):
            matches.append(index)
    if len(matches) != 1:
        return ""  # Repeated identical answers cannot safely identify a specific turn.
    for previous in reversed(messages[:matches[0]]):
        if not isinstance(previous, dict) or previous.get("role") != "user" or previous.get("display_role"):
            continue
        prompt = user_request(text_blocks(previous))
        if prompt:
            return prompt
    return ""


def response_parts(response, secrets=()):
    result, checked, next_step = [], [], []
    for line in sanitize(response, secrets).splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line).strip()
        if not line or (line.startswith("#") and len(line.split()) <= 6):
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        verify = re.match(r"(?i)^(?:checked|verified|verification|validation|tests?|checks?|build|lint)\s*:\s*(.+)", line)
        action = re.match(r"(?i)^(?:needs you|next(?: steps?)?|action(?: required)?|remaining(?: limitations?)?|blockers?|blocked|limitations?)\s*:\s*(.+)", line)
        if verify:
            checked.append(verify.group(1))
        elif action:
            next_step.append(action.group(1))
        elif re.search(r"(?i)\b(?:tests?|checks?|build|lint|typecheck)\b.*\b(?:passed|failed|not run|blocked)\b", line):
            checked.append(line)
        else:
            result.append(re.sub(r"(?i)^(?:result|outcome|summary)\s*:\s*", "", line))
    return " ".join(result[:3]), " ".join(checked[:2]), " ".join(next_step[:2])


def utf16_length(text):
    """Telegram entity offsets count UTF-16 units, not Python characters."""
    return len(text.encode("utf-16-le")) // 2


def duration_label(milliseconds):
    """Round native milliseconds to the nearest second, with correct carry."""
    if type(milliseconds) not in (str, int):
        return "time unavailable"
    try:
        if isinstance(milliseconds, str) and len(milliseconds) > 32:
            return "time unavailable"
        value = int(milliseconds)
        if value > 2**63 - 1:
            return "time unavailable"
        total = (max(0, value) + 500) // 1000
    except (ValueError, TypeError):
        return "time unavailable"
    minutes, seconds = divmod(total, 60)
    return f"{minutes}m {seconds}s"


def folder_label(environment, verbosity="expanded", secrets=()):
    """Display only native CWD metadata, never infer a project or read the disk.

    Preserve ancestry where it fits and the leaf when shortened. Only this
    explicit metadata field is exempt from generic path redaction.
    """
    raw = environment.get("JCODE_HOOK_CWD")
    if not isinstance(raw, str) or not raw.strip():
        return "Folder unavailable"
    text = " ".join(sanitize(raw, secrets, redact_paths=False).split())
    if not text:
        return "Folder unavailable"
    home = str(Path.home()).rstrip("/")
    if home and (text == home or text.startswith(home + "/")):
        text = "~" + text[len(home):]
    text = text.rstrip("/") or "/"
    limit = {"brief": 64, "contextual": 120, "expanded": 180}[verbosity]
    if len(text.split()) > 3:
        text = "…" + " ".join(text.split()[-3:])
    if len(text) > limit:
        tail = text[-(limit - 1):]
        boundary = tail.find("/")
        if 0 <= boundary < len(tail) - 1:
            tail = tail[boundary:]
        text = "…" + tail
    return text


def session_label(name, verbosity="expanded", secrets=()):
    """Keep explicit names single-line and body-redacted before shortening."""
    words, chars = {"brief": (2, 40), "contextual": (5, 80), "expanded": (8, 120)}[verbosity]
    return clip(" ".join(sanitize(name, secrets).split()), words, chars)


def response_links(response, secrets=()):
    """Keep validated original targets only when existing secret masking permits.

    Collision-free markers protect URL characters from ordinary body Markdown
    cleanup. A marker inside a secret value or code fence must not survive.
    Markers, source strings and URLs never enter local diagnostic receipts.
    """
    if not isinstance(response, str):
        return []
    # Keep one lookahead character so extraction can reject a target crossing
    # its 16000-character scan boundary instead of accepting a truncated prefix.
    source = response[:16001].encode("utf-8", errors="replace").decode("utf-8")
    # An invalid-URI sentinel, not deletion or whitespace, prevents adjoining
    # URL fragments from becoming a fabricated target or a shorter prefix.
    source = re.sub(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)",
                    lambda match: "\x00" * len(match[0]), source, flags=re.S)
    links = extract_links(source, secrets, limit=12)
    prefix = "JCODEALERTLINK"
    normalized = sanitize(source, secrets)
    while prefix in source or prefix in normalized:
        prefix += "X"
    chunks, candidates, cursor = [], [], 0
    for index, link in enumerate(links):
        start, end = link["start"], link["end"]
        if not cursor <= start < end <= len(source) or source[start:end] != link["source"]:
            continue
        marker = f"{prefix}{index}END"
        chunks.extend((source[cursor:start], marker))
        cursor = end
        candidates.append((marker, link))
    chunks.append(source[cursor:])
    masked = "".join(chunks)
    if candidates:
        markers = "|".join(re.escape(marker) for marker, _ in candidates)
        # Source labels are not trusted. Reduce the whole Markdown link to its
        # marker before secret scanning, including labels containing spaces.
        masked = re.sub(r"\[[^\]\n]*\]\(\s*(" + markers + r")\s*\)", r"\1", masked)
    allowed = "\n".join(line for line in sanitize(masked, secrets).splitlines()
                        if "[redacted]" not in line)
    return [{"url": link["url"], "label": link["label"]}
            for marker, link in candidates if marker in allowed][:3]


def link_footer(links, verbosity):
    if not links:
        return {"text": "", "entities": []}
    prefix = "\n\n🔗 "
    text = prefix + "Links:" + (" " if verbosity == "brief" else "\n")
    entities = [{"type": "bold", "offset": utf16_length(prefix), "length": len("Links:")}]
    for index, link in enumerate(links):
        if index:
            text += " · " if verbosity == "brief" else "\n"
        entities.append({"type": "text_link", "offset": utf16_length(text),
                         "length": utf16_length(link["label"]), "url": link["url"]})
        text += link["label"]
    return {"text": text, "entities": entities}


def render_message(environment, verbosity="expanded", prompt="", secrets=(), *, session_name=""):
    """Return literal text, trusted bold spans, and local context metadata.

    No parse_mode: user text can never introduce HTML or Markdown entities.
    Build spans before clipping, then retain complete unchanged spans only.
    """
    profile = PROFILES[verbosity]
    duration = duration_label(environment.get("JCODE_HOOK_DURATION_MS"))
    failed = environment.get("JCODE_HOOK_STATUS") == "error"
    label = "failed" if failed else ("preview" if environment.get("JCODE_HOOK_STATUS") == "preview" else "finished")
    icon = "❌" if failed else ("👀" if label == "preview" else "✅")
    folder = folder_label(environment, verbosity, secrets)
    chunks, spans, position = [], [], 0

    def append(text, bold=False):
        nonlocal position
        if bold:
            spans.append((position, position + len(text)))
        chunks.append(text)
        position += len(text)

    def field(emoji, title, text):
        append(f"\n\n{emoji} ")
        append(title + ":", bold=True)
        append(" " if verbosity == "brief" else "\n")
        append(text)

    append(icon + " ")
    append("Jcode turn " + label, bold=True)
    name = session_label(session_name, verbosity, secrets)
    if name:
        append("\n🏷 ")
        append("Session:", bold=True)
        append(" " + name)
    append(f"\n📁 {folder} · {duration}")
    response = environment.get("JCODE_HOOK_LAST_ASSISTANT_TEXT", "")
    if failed:
        response = environment.get("JCODE_HOOK_ERROR") or "Turn failed. No error details available."
    links = response_links(response, secrets)[:{"brief": 1, "contextual": 2, "expanded": 3}[verbosity]]
    footer = link_footer(links, verbosity)
    # Preserve complete clickable labels and at least some result text. Never
    # attach a destination to a label truncated by either clipping stage.
    while links:
        minimum = "".join(chunks) + "\n\n📝 Result: X" + footer["text"]
        if len(minimum) <= profile["chars"] and len(minimum.split()) <= profile["words"]:
            break
        links.pop()
        footer = link_footer(links, verbosity)
    body_words = profile["words"] - len(footer["text"].split())
    body_chars = profile["chars"] - len(footer["text"])
    result, checked, next_step = response_parts(response, secrets)
    result_words, result_chars = profile["result"], profile["result_chars"]
    if verbosity == "brief":
        reserved = "".join(chunks) + "\n\n📝 Result: "
        result_words = max(1, min(result_words, body_words - len(reserved.split())))
        result_chars = max(2, min(result_chars, body_chars - len(reserved)))
    result = clip(result or "No response excerpt available. Open Jcode to review.", result_words, result_chars)
    request = " ".join(sanitize(user_request(prompt), secrets).split())
    asked_words, asked_chars = profile["asked"], profile["asked_chars"]
    if verbosity == "brief":
        # A longer folder/duration must never push the result out of a brief alert.
        reserved = "".join(chunks) + "\n\n📝 Result: " + result + "\n\n💬 Asked: "
        asked_words = min(asked_words, body_words - len(reserved.split()))
        asked_chars = min(asked_chars, body_chars - len(reserved))
    if request and asked_words > 0 and asked_chars > 1:
        field("💬", "Asked", clip(request, asked_words, asked_chars))
    field("📝", "Result", result)
    if checked and profile["checked"]:
        field("🔎", "Checked", clip(checked, profile["checked"], profile["extra_chars"]))
    if next_step and profile["next"]:
        field("👉", "Needs you", clip(next_step, profile["next"], profile["extra_chars"]))
    original = "".join(chunks)
    text = clip(original, body_words, body_chars)
    entities = [
        {"type": "bold", "offset": utf16_length(text[:start]), "length": utf16_length(text[start:end])}
        for start, end in spans if end <= len(text) and text[start:end] == original[start:end]
    ]
    shifted = prepend_message(footer, text)
    return {"text": shifted["text"], "entities": entities + shifted["entities"], "prompt_available": bool(request)}


def render(environment, verbosity="expanded", prompt="", secrets=(), *, session_name=""):
    return render_message(environment, verbosity, prompt, secrets, session_name=session_name)["text"]


def render_lifecycle_message(environment, verbosity="expanded", secrets=(), *, session_name=""):
    """Render only lifecycle metadata, never an earlier turn's prompt or response."""
    states = {
        "session_start": ("▶️", "Jcode session active", "Session opened, attached, or resumed."),
        "turn_start": ("🔄", "Jcode working", "A turn is running. Its result is not available yet."),
        "session_end": ("⏹", "Jcode session closed", "Normal closure, not proof of task success."),
    }
    event = environment.get("JCODE_HOOK_EVENT")
    if event not in states:
        raise ValueError("Unsupported lifecycle event.")
    icon, heading, state = states[event]
    folder = folder_label(environment, verbosity, secrets)
    profile = PROFILES[verbosity]
    original = f"{icon} {heading}"
    spans = [(len(icon) + 1, len(original))]
    name = session_label(session_name, verbosity, secrets)
    if name:
        original += "\n🏷 "
        spans.append((len(original), len(original) + len("Session:")))
        original += "Session: " + name
    original += f"\n📁 {folder}\n\n📍 "
    spans.append((len(original), len(original) + len("State:")))
    original += f"State:\n{state}"
    text = clip(original, profile["words"], profile["chars"])
    entities = [{"type": "bold", "offset": utf16_length(text[:start]),
                 "length": utf16_length(text[start:end])}
                for start, end in spans if end <= len(text)]
    return {"text": text, "entities": entities, "prompt_available": False}


def prepend_message(message, prefix):
    """Shift trusted entities when adding an illustrative test notice."""
    shift = utf16_length(prefix)
    return {"text": prefix + message["text"], "entities": [
        {**entity, "offset": entity["offset"] + shift} for entity in message["entities"]
    ]}


def formatting_confirmed(message, delivered):
    """Bind trusted bold/link spans and exact targets, allowing auto entities."""
    def keys(entities):
        result = set()
        for entity in entities:
            if not isinstance(entity, dict) or entity.get("type") not in ("bold", "text_link"):
                continue
            if any(type(entity.get(key)) is not int for key in ("offset", "length")):
                return None
            url = entity.get("url") if entity["type"] == "text_link" else None
            if entity["type"] == "text_link" and (not isinstance(url, str) or not url):
                return None
            result.add((entity["type"], entity["offset"], entity["length"], url))
        return result

    expected = keys(message["entities"])
    actual = delivered.get("entities", [])
    if not isinstance(actual, list):
        return False
    return bool(expected) and expected == keys(actual) and delivered.get("text") == message["text"]


def sample_event():
    return {
        "JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "ok",
        "JCODE_HOOK_DURATION_MS": "95000", "JCODE_HOOK_CWD": "sample-project",
        "JCODE_HOOK_LAST_ASSISTANT_TEXT": (
            "Added selectable Telegram alert verbosity with expanded as the default.\n"
            "The request and response are condensed locally, without an extra model call.\n"
            "Checked: this is an illustrative preview, not a real task result.\n"
            "Needs you: choose brief or contextual if you prefer shorter alerts."
        ),
    }
