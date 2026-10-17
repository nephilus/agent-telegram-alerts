"""Bounded local excerpts for Telegram alerts. Never reads reasoning or tool blocks."""
import json
import os
from pathlib import Path
import re
import stat

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


def sanitize(text, secrets=()):
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
    text = re.sub(r"(?<!\w)(?:~?/|[A-Za-z]:\\)[^\s,;]+", "[path]", text)
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


def user_request(text):
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


def render_message(environment, verbosity="expanded", prompt="", secrets=()):
    """Return literal text, trusted bold spans, and local context metadata.

    No parse_mode: user text can never introduce HTML or Markdown entities.
    Build spans before clipping, then retain complete unchanged spans only.
    """
    profile = PROFILES[verbosity]
    try:
        seconds = max(0, int(environment.get("JCODE_HOOK_DURATION_MS", "0"))) / 1000
    except (TypeError, ValueError):
        seconds = 0
    failed = environment.get("JCODE_HOOK_STATUS") == "error"
    label = "failed" if failed else ("preview" if environment.get("JCODE_HOOK_STATUS") == "preview" else "finished")
    icon = "❌" if failed else ("👀" if label == "preview" else "✅")
    project = Path(str(environment.get("JCODE_HOOK_CWD", ""))).name or "Jcode"
    project = clip(" ".join(sanitize(project, secrets).split()), 3, 36) or "Jcode"
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
    append(f"\n{project} · {seconds:.0f}s")
    request = " ".join(sanitize(user_request(prompt), secrets).split())
    field("💬", "Asked", clip(request, profile["asked"], profile["asked_chars"]) if request else "Context unavailable for this turn.")
    response = environment.get("JCODE_HOOK_LAST_ASSISTANT_TEXT", "")
    if failed:
        response = environment.get("JCODE_HOOK_ERROR") or "Turn failed. No error details available."
    result, checked, next_step = response_parts(response, secrets)
    field("📝", "Result", clip(result or "No response excerpt available. Open Jcode to review.", profile["result"], profile["result_chars"]))
    if checked and profile["checked"]:
        field("🔎", "Checked", clip(checked, profile["checked"], profile["extra_chars"]))
    if next_step and profile["next"]:
        field("👉", "Needs you", clip(next_step, profile["next"], profile["extra_chars"]))
    original = "".join(chunks)
    text = clip(original, profile["words"], profile["chars"])
    entities = [
        {"type": "bold", "offset": utf16_length(text[:start]), "length": utf16_length(text[start:end])}
        for start, end in spans if end <= len(text) and text[start:end] == original[start:end]
    ]
    return {"text": text, "entities": entities, "prompt_available": bool(request)}


def render(environment, verbosity="expanded", prompt="", secrets=()):
    return render_message(environment, verbosity, prompt, secrets)["text"]


def prepend_message(message, prefix):
    """Shift trusted entities when adding an illustrative test notice."""
    shift = utf16_length(prefix)
    return {"text": prefix + message["text"], "entities": [
        {**entity, "offset": entity["offset"] + shift} for entity in message["entities"]
    ]}


def formatting_confirmed(message, delivered):
    """Confirm Telegram returned all expected bold spans, allowing auto entities."""
    expected = {(entity["offset"], entity["length"]) for entity in message["entities"]}
    actual = delivered.get("entities", [])
    if not isinstance(actual, list):
        return False
    bold = [entity for entity in actual if isinstance(entity, dict) and entity.get("type") == "bold"]
    if any(type(entity.get(key)) is not int for entity in bold for key in ("offset", "length")):
        return False
    actual = {(entity["offset"], entity["length"]) for entity in bold}
    return bool(expected) and expected == actual and delivered.get("text") == message["text"]


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
