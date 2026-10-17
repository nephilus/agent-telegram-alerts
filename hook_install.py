"""Private, conservative registration of the jcode-telegram turn-end hook."""
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


def _hooks(document):
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        raise HookError("Unsupported hooks configuration.")
    value = hooks.get("turn_end")
    if value is not None and not (isinstance(value, str) or
            isinstance(value, list) and all(isinstance(v, str) for v in value)):
        raise HookError("Unsupported turn-end configuration.")
    return value


def _edit(raw, document, value):
    """Choose a surgical edit only if the entire parsed result is exactly expected."""
    text = raw.decode("utf-8")
    expected = copy.deepcopy(document)
    expected.setdefault("hooks", {})["turn_end"] = value
    encoded = json.dumps(value, ensure_ascii=False)
    candidates = []
    # Quoted keys and dotted keys are accepted when the semantic check agrees.
    key = r'(?:turn_end|"turn_end"|\'turn_end\')'
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
    if "turn_end" not in document.get("hooks", {}):
        candidates.append("hooks.turn_end = " + encoded + "\n" + text)
        for header in re.finditer(r'(?m)^[ \t]*\[[ \t]*(?:hooks|"hooks"|\'hooks\')[ \t]*\][^\n]*(?:\n|$)', text):
            pos = header.end()
            candidates.append(text[:pos] + ("\n" if pos and text[pos-1] != "\n" else "") +
                              "turn_end = " + encoded + "\n" + text[pos:])
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


def _command(explicit, seconds):
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
    return f"{quoted} alert --min-seconds {seconds}"


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
                    re.search(r"\balert\b", command))
    return any(Path(executable).name in
               {"jcode-telegram", "jcode-telegram.py", "jcode_telegram.py"}
               and argument == "alert"
               for executable, argument in zip(words, words[1:]))


def manage(action, command=None, min_seconds=30):
    if type(min_seconds) is not int or min_seconds < 0:
        raise HookError("Minimum seconds must be a nonnegative integer.")
    home = Path(os.environ.get("JCODE_HOME", str(Path.home() / ".jcode")))
    config = home / "config.toml"
    manifest = home / "notifications" / "telegram-hook.json"
    with _lock(home):
        before = _snapshot(config)
        owned_before = _snapshot(manifest)
        owned = None
        if owned_before is not None:
            try:
                data = json.loads(owned_before[-1])
                if set(data) != {"version", "command"} or type(data["version"]) is not int or data["version"] != 1 or not isinstance(data["command"], str) or not data["command"]:
                    raise ValueError
                owned = data["command"]
            except (ValueError, TypeError, KeyError, UnicodeError):
                raise HookError("Invalid ownership manifest. No changes made.") from None
        if action == "uninstall" and owned is None:
            return "missing"
        raw = before[-1] if before else b""
        document = _parse(raw)
        old = _hooks(document)
        entries = [old] if isinstance(old, str) else list(old or [])
        if action == "status":
            if owned is None:
                return "missing"
            if entries.count(owned) != 1:
                raise HookError("Ownership does not match configuration.")
            return "installed"
        desired = _command(command, min_seconds) if action == "install" else None
        if owned is not None and (entries.count(owned) != 1 or desired is not None and owned != desired):
            raise HookError("Ownership does not match requested hook. No changes made.")
        if action == "install":
            if any(entry != owned and (entry == desired or _is_alert_hook(entry))
                   for entry in entries):
                raise HookError("Unowned Telegram alert hook exists. Remove or migrate the old manual hook first.")
            if owned is not None:
                return "installed"
            entries.append(desired)
        elif action == "uninstall":
            entries.remove(owned)
        else:
            raise HookError("Unknown operation.")
        updated = _edit(raw, document, entries)
        _same(config, before)
        _same(manifest, owned_before)
        if before is not None:
            fd, backup = tempfile.mkstemp(prefix="config.toml.backup-", dir=home)
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        _same(config, before)
        _same(manifest, owned_before)
        if action == "install":
            # Ownership is durable before a new hook can become active. An
            # interrupted preparation may leave an inactive manifest, never an
            # active hook without its ownership record.
            payload = (json.dumps({"version": 1, "command": desired}) + "\n").encode()
            _atomic(manifest, payload, owned_before)
            prepared = _snapshot(manifest)
            if prepared is None or prepared[-1] != payload:
                raise HookError("Ownership changed during preparation. No hook activated.")
            try:
                _atomic(config, updated, before,
                        guard=lambda: _same(manifest, prepared))
            except Exception:
                # Remove only our unchanged preparation, and only when the
                # config is still the original. If activation or an external
                # edit occurred, retain ownership rather than orphan a hook.
                try:
                    _same(config, before)
                    _same(manifest, prepared)
                    manifest.unlink()
                    _sync_directory(manifest.parent)
                except Exception:
                    pass
                raise HookError("Hook activation failed. Inspect local ownership state before retrying.") from None
            return "installed"
        _atomic(config, updated, before,
                guard=lambda: _same(manifest, owned_before))
        _same(manifest, owned_before)
        manifest.unlink()
        _sync_directory(manifest.parent)
        return "missing"


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Register or deregister the Telegram hook. Package removal is separate (pip/venv).")
    parser.add_argument("action", choices=("install", "uninstall", "status"))
    parser.add_argument("--command", metavar="PATH")
    parser.add_argument("--min-seconds", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        print(manage(args.action, args.command, args.min_seconds))
        return 0
    except HookError as exc:
        print(str(exc), file=sys.stderr)
    except Exception:
        print("Hook operation failed. Inspect local state before retrying.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(cli())
