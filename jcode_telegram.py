#!/usr/bin/env python3
"""Unofficial event-aware Telegram alerts for Jcode. Python 3.11+, standard library only."""
import argparse
import getpass
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request

import alert_format as formatting


class SetupError(Exception):
    pass


def version():
    try:
        return package_version("jcode-telegram-alerts")
    except PackageNotFoundError:
        path = Path(__file__).with_name("version.txt")
        try:
            value = path.read_text().strip()
            return value if re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)", value) else "unknown"
        except OSError:
            return "unknown"


def config_path():
    return Path(os.environ.get("JCODE_HOME", str(Path.home() / ".jcode"))) / "config.toml"


def load_config():
    path = config_path()
    document = tomllib.loads(path.read_text()) if path.exists() else {}
    if any(not isinstance(document.get(key, {}), dict) for key in ("safety", "hooks")):
        raise ValueError("Invalid local configuration table.")
    return document


def api(token, method, values=None, timeout=15):
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(values or {}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        # Never stringify HTTP exceptions: their URL contains the bot token.
        raise SetupError(f"Telegram {method} failed (HTTP {error.code}). Check the token, chat permissions, or rate limits.") from None
    except (OSError, ValueError):
        raise SetupError(f"Telegram {method} failed. Check network access to api.telegram.org.") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise SetupError(f"Telegram rejected {method}.")
    return result.get("result")


def update_safety(text, changes):
    """Change only single-line native safety keys, preserving unrelated config."""
    original = tomllib.loads(text)
    if not isinstance(original.get("safety", {}), dict):
        raise ValueError("Invalid local safety table.")
    match = re.search(r"(?ms)^\[safety\][ \t]*\n(.*?)(?=^\[|\Z)", text)
    if match:
        body = match.group(1)
        for key, value in changes.items():
            literal = str(value).lower() if isinstance(value, bool) else json.dumps(value)
            pattern = rf"(?m)^{re.escape(key)}[ \t]*=[^\n]*$"
            replacement = f"{key} = {literal}"
            if re.search(pattern, body):
                body = re.sub(pattern, lambda _: replacement, body, count=1)
            else:
                body = body.rstrip() + "\n" + replacement + "\n"
        text = text[:match.start(1)] + body + text[match.end(1):]
    else:
        text = text.rstrip() + "\n\n[safety]\n"
        return update_safety(text, changes)
    expected = dict(original)
    expected["safety"] = {**original.get("safety", {}), **changes}
    if tomllib.loads(text) != expected:
        raise SetupError("Config safety check failed. No settings were saved.")
    return text


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".telegram-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_safety(changes):
    path = config_path()
    if path.is_symlink():
        raise SetupError("Config is a symlink. Refusing to replace it automatically.")
    original = path.read_text() if path.exists() else ""
    updated = update_safety(original, changes)
    if original:
        backup = path.with_name(f"config.toml.telegram-backup-{time.time_ns()}")
        private_write(backup, original)
    # Recheck after creating the backup to avoid overwriting intervening edits.
    if (path.read_text() if path.exists() else "") != original:
        raise SetupError("Config changed during setup. Retry without concurrent config edits.")
    private_write(path, updated)


def credentials():
    safety = load_config().get("safety", {})
    token = safety.get("telegram_bot_token")
    chat = safety.get("telegram_chat_id")
    if not safety.get("telegram_enabled") or not token or not chat:
        raise SetupError("Telegram is not linked yet. Run: jcode-telegram setup")
    return token, str(chat)


def setup():
    if not sys.stdin.isatty():
        raise SetupError("Run setup in your own terminal. The bot token is entered privately, not in this chat.")
    print("Use a dedicated bot created with @BotFather /newbot. Do not paste its token into Jcode chat.")
    token = getpass.getpass("BotFather bot token (hidden): ").strip()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,200}", token):
        raise SetupError("That does not look like a Telegram bot token.")
    me = api(token, "getMe")
    webhook = api(token, "getWebhookInfo")
    if webhook.get("url"):
        raise SetupError("This bot has an existing webhook. Use a dedicated bot. Nothing was changed.")
    challenge = f"/start jcode_{secrets.token_hex(8)}"
    print(f"\nIn Telegram, open @{me['username']} and send this exact message:\n\n{challenge}\n")
    print("Waiting up to 3 minutes to verify your private chat...")
    deadline, offset, chat = time.monotonic() + 180, None, None
    while time.monotonic() < deadline and chat is None:
        values = {"timeout": 10, "allowed_updates": ["message"]}
        if offset is not None:
            values["offset"] = offset
        for update in api(token, "getUpdates", values, timeout=20):
            offset = update["update_id"] + 1
            message = update.get("message", {})
            destination = message.get("chat", {})
            if (message.get("text", "").strip() == challenge
                    and destination.get("type") == "private"
                    and destination.get("id") == message.get("from", {}).get("id")):
                chat = str(destination["id"])
                break
    if chat is None:
        raise SetupError("No matching private message arrived. Run setup again when Telegram is ready.")
    # A successful test is required before enabling the local channel.
    api(token, "sendMessage", {"chat_id": chat, "text": "Jcode Telegram test: your private chat is linked. Outbound alerts only. Remote commands are disabled."})
    save_safety({"telegram_enabled": True, "telegram_bot_token": token,
                 "telegram_chat_id": chat, "telegram_reply_enabled": False})
    print("Linked and test delivered. Config and backup are owner-readable only (0600).")
    print("Alerts: qualifying completions, distinct turn errors, and separately configured native ambient/approval alerts.")
    print("Completion alerts hot-reload. Restart Jcode normally when convenient to refresh any cached ambient channels.")


def settings_path():
    return config_path().parent / "notifications" / "telegram-settings.json"


def selected_verbosity(override=None):
    if override is not None:
        return override
    path = settings_path()
    if path.is_symlink():
        return "brief"
    if not path.exists():
        return "expanded"
    try:
        if path.is_symlink() or path.stat().st_size > 4096:
            return "brief"
        settings = json.loads(path.read_text())
        value = settings.get("verbosity") if isinstance(settings, dict) else None
        return value if isinstance(value, str) and value in formatting.PROFILES else "brief"
    except (OSError, ValueError, RecursionError):
        return "brief"  # A damaged preference must not unexpectedly increase disclosure.


def save_verbosity(value):
    if value not in formatting.PROFILES:
        raise SetupError("Choose brief, contextual, or expanded.")
    path = settings_path()
    if path.is_symlink():
        raise SetupError("Alert settings are a symlink. Refusing to replace them.")
    private_write(path, json.dumps({"verbosity": value}, indent=2) + "\n")


def alert_secrets():
    try:
        value = load_config().get("safety", {}).get("telegram_bot_token")
        return (value,) if isinstance(value, str) and value else ()
    except (OSError, ValueError):
        return ()


def alert_message(environment, min_seconds=30, verbosity=None):
    if environment.get("JCODE_HOOK_EVENT") != "turn_end":
        return None
    status = environment.get("JCODE_HOOK_STATUS")
    if status not in ("ok", "error"):
        return None
    try:
        duration = max(0, int(environment.get("JCODE_HOOK_DURATION_MS", "0"))) / 1000
    except (TypeError, ValueError):
        duration = 0
    if status == "ok" and duration < min_seconds:
        return None
    prompt = ""
    if status == "ok":
        prompt = formatting.session_prompt(
            config_path().parent, environment.get("JCODE_HOOK_SESSION_ID", ""),
            environment.get("JCODE_HOOK_LAST_ASSISTANT_TEXT", ""),
        )
    name = formatting.saved_session_name(config_path().parent, environment.get("JCODE_HOOK_SESSION_ID", ""))
    return formatting.render_message(environment, selected_verbosity(verbosity), prompt, alert_secrets(), session_name=name)


def alert_text(environment, min_seconds=30, verbosity=None):
    message = alert_message(environment, min_seconds, verbosity)
    return message["text"] if message else None


def event_message(environment, verbosity="expanded"):
    if environment.get("JCODE_HOOK_EVENT") == "turn_end":
        return alert_message(environment, 0, verbosity)
    name = formatting.saved_session_name(config_path().parent, environment.get("JCODE_HOOK_SESSION_ID", ""))
    return formatting.render_lifecycle_message(environment, verbosity, alert_secrets(), session_name=name)


def observe_event(environment, min_seconds=30, verbosity="expanded"):
    """Best-effort observer: never reveal exceptions or mutate native settings."""
    if environment.get("JCODE_HOOK_EVENT") not in ("session_start", "turn_start", "turn_end", "session_end"):
        return
    try:
        token, chat = credentials()
    except SetupError:
        record_receipt("pending_setup")
        return
    except (OSError, ValueError):
        record_receipt("config_error")
        return
    try:
        import alert_policy
        destination = hashlib.sha256((token + "\0" + chat).encode()).hexdigest()

        def deliver(method, body):
            if method not in ("sendMessage", "editMessageText"):
                raise SetupError("Unsupported notification operation.")
            return api(token, method, {**body, "chat_id": chat})

        receipt = alert_policy.notify(config_path().parent, environment,
                                      lambda: event_message(environment, verbosity), deliver,
                                      destination, verbosity=verbosity, min_seconds=min_seconds)
        receipt = dict(receipt)
        state = receipt.pop("state")
        record_receipt(state, **receipt)
    except Exception:
        # Hooks are detached observers. Diagnostics deliberately omit exception values.
        record_receipt("observer_error")


def preview_message(verbosity, session_id=None, event=None):
    name = ""
    if event in ("session_start", "turn_start", "session_end"):
        return formatting.render_lifecycle_message({"JCODE_HOOK_EVENT": event,
                                                    "JCODE_HOOK_CWD": "sample-project"},
                                                   verbosity, alert_secrets())
    if event == "error":
        return formatting.render_message({"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "error",
                                          "JCODE_HOOK_ERROR": "Illustrative turn error, not a real task failure.",
                                          "JCODE_HOOK_CWD": "sample-project"}, verbosity, "", alert_secrets())
    if session_id:
        session = formatting.read_session(config_path().parent, session_id)
        messages = session.get("messages", [])
        response = next((formatting.text_blocks(item) for item in reversed(messages)
                         if isinstance(item, dict) and item.get("role") == "assistant"
                         and formatting.text_blocks(item)), "")
        if not response:
            raise SetupError("No readable public assistant response exists in that session.")
        event = {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "preview",
                 "JCODE_HOOK_DURATION_MS": "0", "JCODE_HOOK_SESSION_ID": session_id,
                 "JCODE_HOOK_CWD": session.get("working_dir"),
                 "JCODE_HOOK_LAST_ASSISTANT_TEXT": response[:4000]}
        prompt = formatting.session_prompt(config_path().parent, session_id, response[:4000])
        name = formatting.saved_session_name(config_path().parent, session_id)
    else:
        event = formatting.sample_event()
        prompt = "Add selectable Telegram alert verbosity, default to expanded, and keep messages concise."
    return formatting.render_message(event, verbosity, prompt, alert_secrets(), session_name=name)


def preview_text(verbosity, session_id=None, event=None):
    return preview_message(verbosity, session_id, event)["text"]


def receipt_path():
    return config_path().parent / "notifications" / "telegram-last-alert.json"


def record_receipt(state, **metadata):
    # Diagnostics contain no session IDs, paths, user content, destinations, or tokens.
    try:
        payload = json.dumps({
            "state": state,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "recorded_at_ns": time.time_ns(),
            "session_fingerprint": hashlib.sha256(os.environ.get("JCODE_HOOK_SESSION_ID", "").encode()).hexdigest()[:16],
            **{key: metadata[key] for key in ("kind", "grouped", "method", "verbosity", "words", "characters", "telegram_message_id", "text_fingerprint", "response_confirmed", "prompt_available", "bold_entities", "link_entities", "formatting_confirmed") if key in metadata},
        }) + "\n"
        kind = metadata.get("kind")
        if kind in ("session_start", "turn_start", "completion", "error", "session_end"):
            private_write(receipt_path().with_name("telegram-last-" + kind + ".json"), payload)
        private_write(receipt_path(), payload)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s " + version())
    parser.add_argument("command", choices=("setup", "status", "test", "alert", "event", "disable", "verbosity", "preview", "policy"))
    parser.add_argument("value", nargs="?", help="verbosity level or delivery-policy preset")
    parser.add_argument("--min-seconds", type=int, default=30)
    parser.add_argument("--verbosity", choices=tuple(formatting.PROFILES), help="override the saved level for one invocation")
    parser.add_argument("--session", help="use one saved session for a no-send preview")
    parser.add_argument("--event", choices=("session_start", "turn_start", "completion", "error", "session_end"),
                        help="lifecycle kind for a no-send illustrative preview")
    kinds = ("session_start", "turn_start", "completion", "error", "session_end")
    parser.add_argument("--cooldown-seconds", type=int, help="policy: completion interval per session")
    parser.add_argument("--error-repeat-seconds", type=int, help="policy: suppress repeats of the same error")
    parser.add_argument("--status-card", choices=("on", "off"), help="policy: optional editable session card")
    parser.add_argument("--enable", action="append", choices=kinds, help="policy: enable an event kind")
    parser.add_argument("--disable", action="append", choices=kinds, help="policy: disable an event kind")
    parser.add_argument("--silent", action="append", choices=kinds, help="policy: send an event without sound")
    parser.add_argument("--audible", action="append", choices=kinds, help="policy: allow sound for an event")
    parser.add_argument("--include-session", action="append", help="policy: replace explicit included session IDs")
    parser.add_argument("--exclude-session", action="append", help="policy: replace explicit excluded session IDs")
    parser.add_argument("--clear-session-filters", action="store_true", help="policy: clear explicit session filters")
    args = parser.parse_args()
    if args.value and args.command not in ("verbosity", "policy"):
        parser.error("a positional value is only valid after verbosity or policy")
    if args.command == "verbosity" and args.value and args.value not in formatting.PROFILES:
        parser.error("choose brief, contextual, or expanded")
    if args.command == "policy" and args.value and args.value not in ("attention", "balanced", "activity"):
        parser.error("choose attention, balanced, or activity")
    policy_options = (args.cooldown_seconds, args.error_repeat_seconds, args.status_card,
                      args.enable, args.disable, args.silent, args.audible,
                      args.include_session, args.exclude_session)
    if args.command != "policy" and (any(value is not None for value in policy_options) or args.clear_session_filters):
        parser.error("delivery-policy options are only valid after policy")
    if args.min_seconds < 0 or any(value is not None and not 0 <= value <= 86400
                                   for value in (args.cooldown_seconds, args.error_repeat_seconds)):
        parser.error("durations must be nonnegative; policy intervals cannot exceed 86400 seconds")
    if args.session and args.command != "preview":
        parser.error("--session is only valid for the no-send preview command")
    if args.event and args.command != "preview":
        parser.error("--event is only valid for the no-send preview command")
    if args.session and args.event not in (None, "completion"):
        parser.error("saved sessions can preview completion text only")
    if args.command == "policy":
        import alert_policy
        if set(args.enable or []) & set(args.disable or []):
            parser.error("the same event cannot be enabled and disabled together")
        if set(args.silent or []) & set(args.audible or []):
            parser.error("the same event cannot be silent and audible together")
        if args.clear_session_filters and (args.include_session or args.exclude_session):
            parser.error("clear filters separately from setting new filters")
        changes = {}
        if args.value:
            changes["preset"] = args.value
        for argument, key in ((args.cooldown_seconds, "cooldown_seconds"),
                              (args.error_repeat_seconds, "error_repeat_seconds")):
            if argument is not None:
                changes[key] = argument
        if args.status_card is not None:
            changes["status_card"] = args.status_card == "on"
        if args.enable or args.disable:
            changes["events"] = {**{kind: True for kind in args.enable or []},
                                 **{kind: False for kind in args.disable or []}}
        for argument, key in ((args.include_session, "include_sessions"),
                              (args.exclude_session, "exclude_sessions")):
            if argument is not None:
                changes[key] = argument
        if args.clear_session_filters:
            changes.update(include_sessions=[], exclude_sessions=[])
        if changes or args.silent or args.audible:
            policy = alert_policy.save_policy(config_path().parent, changes,
                                              silent=args.silent or (), audible=args.audible or ())
        else:
            policy = alert_policy.load_policy(config_path().parent)
        print(json.dumps(policy, indent=2, sort_keys=True))
        return
    level = selected_verbosity(args.verbosity)
    if args.command == "verbosity":
        if args.value:
            save_verbosity(args.value)
        print("Telegram alert verbosity: " + selected_verbosity())
        return
    if args.command == "preview":
        print("Preview only, not sent (" + level + "):\n" + preview_text(level, args.session, args.event))
        return
    if args.command in ("alert", "event"):
        observe_event(os.environ, args.min_seconds, level)
        return  # An optional detached observer must never disrupt agent work.
    if args.command == "setup":
        setup()
    elif args.command == "status":
        safety = load_config().get("safety", {})
        linked = bool(safety.get("telegram_enabled") and safety.get("telegram_bot_token") and safety.get("telegram_chat_id"))
        print("Telegram: " + ("configured locally (use 'test' to verify delivery)" if linked else "pending bot creation and private token entry"))
        print("Remote commands: " + ("ENABLED" if safety.get("telegram_reply_enabled") else "disabled"))
        print("Alert verbosity: " + level + f" (up to {formatting.PROFILES[level]['words']} words)")
        import alert_policy
        policy = alert_policy.load_policy(config_path().parent)
        print(f"Delivery policy: {policy['preset']}, completion interval {policy['cooldown_seconds']}s per session")
        print("Status card: " + ("on" if policy["status_card"] else "off"))
        print("Completion hook: " + ("installed" if "jcode-telegram" in str(load_config().get("hooks", {}).get("turn_end", "")) else "not installed"))
        try:
            receipt = json.loads(receipt_path().read_text())
            if not isinstance(receipt, dict):
                raise ValueError("Invalid local diagnostic receipt.")
            print("Last hook observation: " + str(receipt.get("state")) + " at " + str(receipt.get("at")))
        except (OSError, ValueError):
            print("Last hook observation: none recorded yet")
    elif args.command == "test":
        token, chat = credentials()
        message = formatting.prepend_message(preview_message(level), "Telegram verbosity preview (illustrative, not a real task result):\n\n")
        api(token, "sendMessage", {"chat_id": chat, "text": message["text"], "entities": message["entities"],
                                   "link_preview_options": {"is_disabled": True}})
        print("Test preview delivered to Telegram (" + level + ").")
    elif args.command == "disable":
        save_safety({"telegram_enabled": False, "telegram_reply_enabled": False})
        print("Telegram alerts and remote replies disabled. Stored credentials retained locally.")


def cli():
    try:
        main()
        return 0
    except (SetupError, OSError, ValueError, TypeError, RecursionError) as error:
        # File/parser exceptions could contain config values, so only show our controlled messages.
        print(str(error) if isinstance(error, SetupError) else "Local config could not be read or updated safely.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
