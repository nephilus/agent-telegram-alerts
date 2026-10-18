"""Conservative, offline alert-link policy. No network or visibility checks.

Callers apply full secret-context masking after extraction and before delivery.
These helpers independently validate destinations as an additional boundary:
only ASCII HTTPS public-DNS-shaped destinations are accepted, never fetched.
"""

import re
from urllib.parse import urlsplit

_MAX_INPUT = 16000
_MAX_URL = 512
_LOCAL = ("local", "internal", "localhost", "lan", "home", "onion",
          "test", "invalid", "example", "arpa")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_PATH = re.compile(r"/[A-Za-z0-9._~!$&()*+,;=:@/-]*\Z")
_SECRET_PATH = re.compile(
    r"(?:^|[/;=:@,])(?:token|access[_-]?token|refresh[_-]?token|password|passwd|secret|credential|reset|webhook|auth|authorization|oauth|invite|login|api[_-]?key)(?=$|[/;=:@,])",
    re.IGNORECASE,
)
_TOKEN = re.compile(
    r"\b(?:sk-|gh[pousr]_|github_pat_|xox[baprs]-|AKIA)[A-Za-z0-9_-]{8,}\b"
    r"|\b(?:bot)?\d{5,}:[A-Za-z0-9_-]{8,}\b",
    re.IGNORECASE,
)
_START = re.compile(r"https://", re.IGNORECASE)


def _known(value, secrets):
    folded = value.casefold()
    return any(isinstance(s, str) and s and s.casefold() in folded for s in secrets)


def safe_url(value, secrets=()):
    """Return canonical HTTPS URL or None. Secrets are case-insensitive substrings.

    No decoding, DNS resolution, redirects, or repository visibility inference.
    Query strings, fragments and percent escapes are rejected, including empty ones.
    Credential heuristics require token boundaries and at least eight payload
    characters, or an explicit sensitive path segment/assignment. Configured
    secrets remain case-insensitive substring matches regardless of length.
    """
    if not isinstance(value, str) or not value or len(value) > _MAX_URL:
        return None
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        return None
    if any(c in value for c in '\\%?#[]\"\'<>'):
        return None
    secrets = tuple(secrets)
    if _known(value, secrets) or _TOKEN.search(value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme.lower() != "https" or not parts.netloc:
        return None
    authority = parts.netloc.lower()
    if "@" in authority:
        return None
    if ":" in authority:
        if authority.count(":") != 1 or not authority.endswith(":443"):
            return None
        authority = authority[:-4]
    if len(authority) > 253:
        return None
    labels = authority.split(".")
    if len(labels) < 2 or any(not _LABEL.fullmatch(p) for p in labels):
        return None
    if not re.fullmatch(r"[a-z]{2,63}", labels[-1]):
        return None
    if labels[-1] in _LOCAL or authority == "localhost":
        return None
    if any(p == "localhost" for p in labels) or all(p.isdigit() for p in labels[:-1]):
        return None
    path = parts.path
    if path and not _PATH.fullmatch(path):
        return None
    if _SECRET_PATH.search(path):
        return None
    depth = 0
    for char in path:
        depth += (char == "(") - (char == ")")
        if depth < 0:
            return None
    if depth:
        return None
    canonical = "https://" + authority + path
    return None if _known(canonical, secrets) else canonical


def _label(url):
    parts = urlsplit(url)
    match = re.fullmatch(r"/[^/]+/[^/]+/(pull|issues)/([1-9][0-9]*)/?", parts.path)
    if parts.netloc == "github.com" and match:
        title = "GitHub PR #" if match[1] == "pull" else "GitHub issue #"
        label = title + match[2]
        if len(label) <= 64:
            return label
    # A long hostname cannot be represented clearly within the label budget.
    if len(parts.netloc) > 64:
        return None
    budget = 64 - len(parts.netloc)
    if len(parts.path) <= budget:
        return parts.netloc + parts.path
    return parts.netloc + (parts.path[:budget - 3] + "..." if budget >= 3 else "")


def extract_links(text, secrets=(), *, limit=3):
    """Return first-seen {'url', 'label', 'source', 'start', 'end'} dictionaries.

    limit must be a non-bool integer from 1 through 12 or ValueError is raised.
    source is the original URL substring without wrappers/prose punctuation.
    start/end are original-text slice offsets: text[start:end] == source.
    Candidate runs terminate at ASCII spaces or clear LF line boundaries.
    LF is clear before EOF, another HTTPS URL, or recognizable ASCII prose
    (including list items), ignoring blank lines/space indentation. Ambiguous
    single tokens and path continuations reject the candidate. URL-only single
    backtick wrappers are supported. All non-LF controls are rejected.

    Only the first 16000 characters are inspected. A candidate crossing that
    boundary is discarded, not truncated into an apparently safe destination.
    Source Markdown labels are never used. Long hostnames that cannot fit an
    unambiguous 64-character destination label are omitted.
    """
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError("limit must be an integer from 1 through 12")
    if not isinstance(text, str):
        return []
    secrets = tuple(secrets)
    bounded = text[:_MAX_INPUT]
    results, seen = [], set()
    end = 0
    for match in _START.finditer(bounded):
        if match.start() < end:
            continue
        start = match.start()
        end = start
        # Consume hostile suffixes whole, including controls and Unicode.
        while end < len(bounded) and bounded[end] not in " \n":
            end += 1
        if end < len(bounded) and bounded[end] == "\n":
            following = bounded[end + 1:].lstrip(" \n")
            clear_lf = (
                (not following and len(text) <= _MAX_INPUT)
                or _START.match(following)
                or re.match(r"[A-Za-z][A-Za-z0-9 _-]{0,63}: +", following)
                or re.match(r"(?:[-*•] +|[0-9]+[.)] +)?"
                            r"[A-Za-z][A-Za-z0-9,'-]*(?: +[A-Za-z]|[.!](?: |$))",
                            following)
            )
            if not clear_lf:
                continue
        if end == _MAX_INPUT and len(text) > _MAX_INPUT and text[end] != " ":
            continue
        candidate = bounded[start:end]
        if len(candidate) > _MAX_URL + 16 or _known(candidate, secrets):
            continue
        angle = start > 0 and bounded[start - 1] == "<"
        code = start > 0 and bounded[start - 1] == "`"
        candidate = candidate.rstrip(".,!;:")
        if code:
            # Only a complete, URL-only single-backtick span is unambiguous.
            if (start > 1 and bounded[start - 2] == "`") or not candidate.endswith("`"):
                continue
            candidate = candidate[:-1]
        if angle and candidate.endswith(">"):
            candidate = candidate[:-1]
        # Remove only unmatched terminal prose/Markdown parentheses.
        while not code and candidate.endswith(")") and candidate.count(")") > candidate.count("("):
            candidate = candidate[:-1]
        url = safe_url(candidate, secrets)
        if url is None or url in seen:
            continue
        label = _label(url)
        if label is None or _known(label, secrets):
            continue
        seen.add(url)
        results.append({"url": url, "label": label, "source": candidate,
                        "start": start, "end": start + len(candidate)})
        if len(results) == limit:
            break
    return results
