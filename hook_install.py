"""Private, conservative registration of jcode-telegram lifecycle hooks."""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile
import tomllib
from contextlib import contextmanager


class HookError(Exception):
    """An intentionally value-free diagnostic safe to display publicly."""


def _snapshot(path: Path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError:
        raise HookError("Unsafe or inaccessible state file.") from None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise HookError("Unsafe state file ownership or type.")
        return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_mode,
                stream.read())


def _same(path, snapshot):
    if _snapshot(path) != snapshot:
        raise HookError("State changed concurrently. Retry after inspecting ownership.")


def _sync_directory(directory: Path):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic(path: Path, data: bytes, expected, guard=None):
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _same(path, expected)
        if guard is not None:
            guard()
        os.replace(name, path)
        _sync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def _lock(home):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = home / "notifications"
    if directory.is_symlink():
        raise HookError("Unsafe notifications directory.")
    directory.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(directory / ".telegram-hook.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise HookError("Unsafe lock file.")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _parse(raw):
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise HookError("Invalid TOML configuration. No changes made.") from None


EVENTS = ("session_start", "turn_start", "turn_end", "session_end")


def _hooks(document, event="turn_end"):
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        raise HookError("Unsupported hooks configuration.")
    value = hooks.get(event)
    if value is not None and not (isinstance(value, str) or
            isinstance(value, list) and all(isinstance(v, str) for v in value)):
        raise HookError("Unsupported hook event configuration.")
    return value


def _edit(raw, document, value, event="turn_end"):
    """Choose a surgical edit only if the entire parsed result is exactly expected."""
    text = raw.decode("utf-8")
    expected = copy.deepcopy(document)
    expected.setdefault("hooks", {})[event] = value
    encoded = json.dumps(value, ensure_ascii=False)
    candidates = []
    # Quoted keys and dotted keys are accepted when the semantic check agrees.
    key = r'(?:' + event + '|"' + event + '"|\'' + event + '\')'
    pattern = r'(?m)^[ \t]*(?:(?:hooks|"hooks"|\'hooks\')[ \t]*\.[ \t]*)?' + key + r'[ \t]*=[ \t]*'
    for match in re.finditer(pattern, text):
        start = match.end()
        for end in range(start + 1, len(text) + 1):
            if end < len(text) and text[end] not in "\r\n#":
                continue
            chunk = text[start:end].rstrip(" \t")
            try:
                parsed = tomllib.loads("v=" + chunk)
            except ValueError:
                continue
            if set(parsed) != {"v"}:
                continue
            stop = start + len(chunk)
            # Keep embedded comments, ignoring hash characters inside strings.
            tokens = re.finditer(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'[^\']*\'|#[^\r\n]*', chunk)
            comments = [token.group() for token in tokens if token.group().startswith("#")]
            replacement = encoded
            if comments:
                replacement = encoded[:-1] + "\n" + "\n".join(comments) + "\n]"
            candidates.append(text[:start] + replacement + text[stop:])
            break
    if event not in document.get("hooks", {}):
        candidates.append("hooks." + event + " = " + encoded + "\n" + text)
        for header in re.finditer(r'(?m)^[ \t]*\[[ \t]*(?:hooks|"hooks"|\'hooks\')[ \t]*\][^\n]*(?:\n|$)', text):
            pos = header.end()
            candidates.append(text[:pos] + ("\n" if pos and text[pos-1] != "\n" else "") +
                              event + " = " + encoded + "\n" + text[pos:])
    valid = []
    for candidate in candidates:
        try:
            if tomllib.loads(candidate) == expected:
                valid.append(candidate)
        except ValueError:
            pass
    if len(valid) != 1:
        raise HookError("Cannot unambiguously edit hooks while preserving configuration.")
    return valid[0].encode("utf-8")


def _command(explicit, seconds, verb="alert"):
    if explicit is None:
        sibling = Path(sys.argv[0]).absolute().parent / "jcode-telegram"
        explicit = str(sibling) if sibling.is_file() and os.access(sibling, os.X_OK) else shutil.which("jcode-telegram")
    if not explicit:
        raise HookError("Cannot find an executable jcode-telegram.")
    path = Path(explicit).absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise HookError("Command must be an existing executable file.")
    # Always quote, including paths that shlex.quote would leave bare.
    quoted = "'" + str(path).replace("'", "'\"'\"'") + "'"
    return f"{quoted} {verb} --min-seconds {seconds}"


def _is_alert_hook(command):
    """Recognize direct and shell-wrapped legacy commands without executing them."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        words = list(lexer)
    except ValueError:
        # Ambiguous malformed legacy commands must not silently get a duplicate.
        return bool(re.search(r"jcode[-_]telegram(?:\.py)?", command) and
                    re.search(r"\b(?:alert|event)\b", command))
    direct = any(Path(executable).name in
                 {"jcode-telegram", "jcode-telegram.py", "jcode_telegram.py"}
                 and argument in {"alert", "event"}
                 for executable, argument in zip(words, words[1:]))
    return direct or any(word != command and re.search(r"jcode[-_]telegram", word)
                         and _is_alert_hook(word) for word in words)


def _entries(document, event):
    value = _hooks(document, event)
    return [value] if isinstance(value, str) else list(value or [])


def _ownership(snapshot):
    if snapshot is None:
        return None
    try:
        data = json.loads(snapshot[-1])
        if type(data.get("version")) is not int:
            raise ValueError
        if data["version"] == 1 and set(data) == {"version", "command"}:
            commands = {"turn_end": data["command"]}
        elif data["version"] == 2 and set(data) == {"version", "commands"}:
            commands = data["commands"]
        else:
            raise ValueError
        if not isinstance(commands, dict) or not commands or not set(commands) <= set(EVENTS):
            raise ValueError
        if not all(isinstance(v, str) and v for v in commands.values()):
            raise ValueError
        return data, commands
    except (ValueError, TypeError, KeyError, UnicodeError, AttributeError):
        raise HookError("Invalid ownership manifest. No changes made.") from None


def _backup(home, raw):
    fd, name = tempfile.mkstemp(prefix="config.toml.backup-", dir=home)
    with os.fdopen(fd, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(home)


def _legacy_match(command, executable):
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        words = list(lexer)
    except ValueError:
        return False
    return (len(words) in (2, 4) and words[:2] == [executable, "alert"] and
            (len(words) == 2 or words[2] == "--min-seconds" and
             re.fullmatch(r"[0-9]+", words[3]) is not None))


def manage(action, command=None, min_seconds=30, events=None, from_command=None,
           *, _cli_default=False):
    """Old API defaults to v1. CLI defaults apply only to new installations."""
    if type(min_seconds) is not int or min_seconds < 0:
        raise HookError("Minimum seconds must be a nonnegative integer.")
    if events not in (None, "lifecycle", "turn_end"):
        raise HookError("Unsupported event selection.")
    if action not in ("install", "uninstall", "status") or from_command is not None and action != "install":
        raise HookError("Unknown operation or migration option.")
    home = Path(os.environ.get("JCODE_HOME", str(Path.home() / ".jcode")))
    config = home / "config.toml"
    manifest = home / "notifications" / "telegram-hook.json"
    with _lock(home):
        before, owned_before = _snapshot(config), _snapshot(manifest)
        ownership = _ownership(owned_before)
        owned = ownership[1] if ownership else {}
        if action == "uninstall" and not owned:
            return "missing"
        raw = before[-1] if before else b""
        document = _parse(raw)
        entries = {event: _entries(document, event) for event in EVENTS}
        if owned and any(entries[event].count(value) != 1 for event, value in owned.items()):
            raise HookError("Ownership does not match configuration.")
        if action == "status":
            return "installed" if owned else "missing"
        if events is None and owned:
            selected = tuple(owned)
            version = ownership[0]["version"]
        else:
            selection = events or ("lifecycle" if _cli_default or from_command is not None else "turn_end")
            selected = EVENTS if selection == "lifecycle" else ("turn_end",)
            version = 2 if selection == "lifecycle" else 1
        desired = {}
        if action == "install":
            value = _command(command, min_seconds, "event" if version == 2 else "alert")
            desired = dict.fromkeys(selected, value)
            if owned and owned != desired:
                raise HookError("Ownership does not match requested hook. No changes made.")
            legacy = None
            if from_command is not None:
                if owned or events == "turn_end":
                    raise HookError("Migration requires unowned legacy lifecycle registration.")
                path = Path(from_command)
                if not path.is_absolute():
                    raise HookError("Migration requires an absolute executable path.")
                executable = shlex.split(_command(str(path), min_seconds))[0]
                matches = [(event, entry) for event in EVENTS for entry in entries[event]
                           if _legacy_match(entry, executable)]
                if len(matches) != 1 or matches[0][0] != "turn_end":
                    raise HookError("Legacy hook is missing, ambiguous, or mismatched.")
                legacy = matches[0][1]
            for event in EVENTS:
                for entry in entries[event]:
                    if entry != owned.get(event) and not (event == "turn_end" and entry == legacy) and (
                            entry in desired.values() or _is_alert_hook(entry)):
                        raise HookError("Unowned Telegram alert hook exists. Remove or migrate the old manual hook first.")
            if owned:
                return "installed"
            if legacy is not None:
                entries["turn_end"].remove(legacy)
            for event, value in desired.items():
                entries[event].append(value)
        else:
            for event, value in owned.items():
                entries[event].remove(value)
        updated = raw
        for event in EVENTS:
            if entries[event] != _entries(document, event):
                # Keep the historical three-argument editor call for turn_end.
                if event == "turn_end":
                    updated = _edit(updated, _parse(updated), entries[event])
                else:
                    updated = _edit(updated, _parse(updated), entries[event], event)
        _same(config, before)
        _same(manifest, owned_before)
        if before is not None:
            _backup(home, raw)
        _same(config, before)
        _same(manifest, owned_before)
        if action == "install":
            data = {"version": 1, "command": desired["turn_end"]} if version == 1 else {"version": 2, "commands": desired}
            payload = (json.dumps(data) + "\n").encode()
            _atomic(manifest, payload, owned_before, guard=lambda: _same(config, before))
            prepared = _snapshot(manifest)
            if prepared is None or prepared[-1] != payload:
                raise HookError("Ownership changed during preparation. No hook activated.")
            try:
                _atomic(config, updated, before, guard=lambda: _same(manifest, prepared))
            except Exception:
                try:
                    _same(config, before)
                    _same(manifest, prepared)
                    manifest.unlink()
                    _sync_directory(manifest.parent)
                except Exception:
                    pass
                raise HookError("Hook activation failed. Inspect local ownership state before retrying.") from None
            return "installed"
        _atomic(config, updated, before, guard=lambda: _same(manifest, owned_before))
        _same(manifest, owned_before)
        manifest.unlink()
        _sync_directory(manifest.parent)
        return "missing"


def _is_moshi(command):
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        words = list(lexer)
        return len(words) == 2 and Path(words[0]).name == "moshi-hook" and words[1] == "jcode-hook"
    except ValueError:
        return False


def dedupe_moshi():
    """Remove only repeated exact direct Moshi strings, never claim ownership."""
    home = Path(os.environ.get("JCODE_HOME", str(Path.home() / ".jcode")))
    config = home / "config.toml"
    manifest = home / "notifications" / "telegram-hook.json"
    with _lock(home):
        before, owned_before = _snapshot(config), _snapshot(manifest)
        raw = before[-1] if before else b""
        document = _parse(raw)
        updated, removed = raw, 0
        for event in EVENTS:
            values = _entries(document, event)
            seen, kept = set(), []
            for value in values:
                if _is_moshi(value) and value in seen:
                    removed += 1
                else:
                    kept.append(value)
                seen.add(value)
            if kept != values:
                updated = _edit(updated, _parse(updated), kept, event)
        if not removed:
            return 0
        _same(config, before)
        _same(manifest, owned_before)
        _backup(home, raw)
        _atomic(config, updated, before, guard=lambda: _same(manifest, owned_before))
        return removed


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Register or deregister the Telegram hook. Package removal is separate (pip/venv).")
    parser.add_argument("action", choices=("install", "uninstall", "status", "dedupe-moshi"))
    parser.add_argument("--command", metavar="PATH")
    parser.add_argument("--min-seconds", type=int, default=30)
    parser.add_argument("--events", choices=("lifecycle", "turn_end"), help="New installs default to lifecycle, existing installs retain their events.")
    parser.add_argument("--from-command", metavar="PATH")
    args = parser.parse_args(argv)
    try:
        if args.action == "dedupe-moshi":
            if args.command is not None or args.events is not None or args.from_command is not None:
                raise HookError("Unsupported dedupe option.")
            print(dedupe_moshi())
        else:
            print(manage(args.action, args.command, args.min_seconds, args.events,
                         args.from_command, _cli_default=True))
        return 0
    except HookError as exc:
        print(str(exc), file=sys.stderr)
    except Exception:
        print("Hook operation failed. Inspect local state before retrying.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(cli())
