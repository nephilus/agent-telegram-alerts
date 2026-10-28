#!/usr/bin/env python3
"""Generic Telegram delivery for agent alerts. Python 3.11+, standard library only."""
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
import alert_home


class SetupError(Exception):
    pass


def version():
    try:
        return package_version("agent-telegram-alerts")
    except PackageNotFoundError:
        path = Path(__file__).with_name("version.txt")
        try:
            value = path.read_text().strip()
            return value if re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)", value) else "unknown"
        except OSError:
            return "unknown"


def config_path():
    return alert_home.home_path() / "config.toml"


def legacy_cli():
    """Deprecated generic alias; it never invokes the legacy Jcode adapter."""
    print("Notice: jcode-telegram is deprecated; use telegram-alerts.", file=sys.stderr)
    return cli()


_legacy_config_notice_emitted = False


def _telegram_credentials(safety):
    return (isinstance(safety, dict) and safety.get("telegram_enabled") is True
            and bool(safety.get("telegram_bot_token")) and bool(safety.get("telegram_chat_id")))


def _legacy_notice():
    global _legacy_config_notice_emitted
    if not _legacy_config_notice_emitted:
        print("Notice: reading legacy Telegram credentials from ~/.jcode/config.toml and compatible policy/dedup state from ~/.jcode/notifications/ (read-only); "
              f"new writes remain under {config_path().parent}.", file=sys.stderr)
        _legacy_config_notice_emitted = True


def load_config():
    path = config_path()
    document = tomllib.loads(path.read_text()) if path.exists() else {}
    if not isinstance(document.get("safety", {}), dict):
        raise ValueError("Invalid local safety configuration table.")
    safety = document.get("safety", {})
    if safety.get("telegram_enabled") is not False and not _telegram_credentials(safety):
        legacy_home = alert_home.legacy_read_home()
        if legacy_home is not None:
            legacy_path = legacy_home / "config.toml"
            if legacy_path.is_file() and not legacy_path.is_symlink():
                legacy = tomllib.loads(legacy_path.read_text())
                legacy_safety = legacy.get("safety", {})
                if not isinstance(legacy_safety, dict):
                    raise ValueError("Invalid legacy Telegram configuration table.")
                if _telegram_credentials(legacy_safety):
                    _legacy_notice()
                    return {"safety": legacy_safety}
    return document


def delivery_policy(home=None):
    """Read current policy, using a read-only legacy fallback when still needed."""
    import alert_attention
    home = config_path().parent if home is None else Path(home)
    legacy_home = alert_home.legacy_read_home()
    if legacy_home is not None:
        primary = home / "notifications" / alert_attention.policy.POLICY_FILE
        legacy = legacy_home / "notifications" / alert_attention.policy.POLICY_FILE
        if not os.path.lexists(primary) and os.path.lexists(legacy):
            _legacy_notice()
    return alert_attention._load_policy(home, legacy_home)


def _note_legacy_attention_fallback(home, legacy_home):
    if legacy_home is None:
        return
    import alert_attention
    for name in (alert_attention.policy.POLICY_FILE, alert_attention.STATE_FILE):
        if (not os.path.lexists(Path(home) / "notifications" / name)
                and os.path.lexists(Path(legacy_home) / "notifications" / name)):
            _legacy_notice()
            return


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
        raise SetupError("Telegram is not configured in this home. Run: telegram-alerts setup")
    return token, str(chat)


def setup():
    if not sys.stdin.isatty():
        raise SetupError("Run setup in your own terminal. The bot token is entered privately, not in this chat.")
    print("Use a dedicated bot created with @BotFather /newbot. Do not paste its token into an agent conversation.")
    token = getpass.getpass("BotFather bot token (hidden): ").strip()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,200}", token):
        raise SetupError("That does not look like a Telegram bot token.")
    me = api(token, "getMe")
    webhook = api(token, "getWebhookInfo")
    if webhook.get("url"):
        raise SetupError("This bot has an existing webhook. Use a dedicated bot. Nothing was changed.")
    challenge = f"/start telegram_alerts_{secrets.token_hex(8)}"
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
    api(token, "sendMessage", {"chat_id": chat, "text": "Telegram alerts test: your private chat is linked. Outbound alerts only. Remote commands are disabled."})
    save_safety({"telegram_enabled": True, "telegram_bot_token": token,
                 "telegram_chat_id": chat, "telegram_reply_enabled": False})
    print("Linked and test delivered. Config and backup are owner-readable only (0600).")
    print("Use telegram-alerts attention for generic owner handoffs. Legacy Jcode events are isolated in the optional telegram-alerts-jcode adapter.")
    print("Telegram credentials and alert state are private to this alerts home.")


def alert_secrets():
    try:
        value = load_config().get("safety", {}).get("telegram_bot_token")
        return (value,) if isinstance(value, str) and value else ()
    except (OSError, ValueError):
        return ()


def preview_message():
    """Render a generic owner-handoff example without consulting session state."""
    import alert_attention
    return alert_attention.render(
        {"context": "Illustrative owner handoff; no task transcript is read.",
         "needs_you": "No action is required; this is only a preview."},
        {"TELEGRAM_ALERTS_CWD": "sample-project"}, config_path().parent,
    )


def preview_text():
    return preview_message()["text"]


def main():
    def review_port(value):
        try:
            port = int(value)
            if 1024 <= port <= 65535:
                return port
        except ValueError:
            pass
        raise argparse.ArgumentTypeError('review port must be an integer from 1024 through 65535')

    parser = argparse.ArgumentParser(prog="telegram-alerts", description=__doc__, epilog=(
        "attention --key OWNER/REPO:DECISION:REVISION reads JSON from stdin: required context "
        "(400 chars), needs_you (800); optional recommendation (600), links "
        "(up to 3 label/url objects, labels 80 chars). No native session or hook is required. "
        "A legacy JCODE_SESSION_ID is consulted only by configured compatibility policy filters. "
        "Sends a fresh message outside routine cooldowns; reuse the key for duplicates. "
        "Use --resend only for an explicit owner resend request. No automatic retries. "
        "Inbox links are rewritten only for the registry's exact loopback port, using tailscale.url; "
        "path, query and fragment are preserved. Configure TELEGRAM_ALERTS_INBOX_REGISTRY or "
        "TELEGRAM_ALERTS_INBOX_BASE_URL to override. Unmapped local links are omitted with a warning; "
        "other loopback URLs are not rewritten. "
        "The home defaults to ~/.config/telegram-alerts; TELEGRAM_ALERTS_HOME overrides it, "
        "and legacy JCODE_HOME is still honored. "
        "review-host [HOST|off] queries read-only, trusts one exact lower-case ASCII "
        "device.tailnet.ts.net host, or disables review trust (default disabled). "
        "It changes neither alert policy nor the read-only Plannotator registry and never sends. "
        "attention --review-port N declares a port (1024..65535) for this invocation only; "
        "requires at least one HTTPS root link to that exact configured host and port, "
        "without credentials, query, fragment or escapes. GitHub links may accompany it. "
        "Routine URL extraction is unchanged. Syntax validation does not prove reachability. "
        "Jcode lifecycle alerts and native session previews are available only through the separate, explicit telegram-alerts-jcode adapter."
    ))
    parser.add_argument("--version", action="version", version="%(prog)s " + version())
    parser.add_argument("command", choices=("setup", "status", "test", "disable", "preview", "attention", "review-host"))
    parser.add_argument("value", nargs="?", help="review-host HOST|off")
    parser.add_argument("--key", help="attention: stable repository/decision/reviewed-revision identifier")
    parser.add_argument("--resend", action="store_true", help="attention: send again only when the owner explicitly requests it")
    parser.add_argument("--review-port", type=review_port, help="attention only: declare exact trusted review port, 1024..65535")
    args = parser.parse_args()
    if args.value is not None and args.command != "review-host":
        parser.error("a positional value is only valid after review-host")
    if args.review_port is not None and args.command != "attention":
        parser.error("--review-port requires attention")
    if args.command != "attention" and (args.key is not None or args.resend):
        parser.error("--key and --resend are only valid after attention")
    if args.command == "attention" and not args.key:
        parser.error("attention requires --key")
    if args.command == "review-host":
        import alert_attention
        try:
            result = alert_attention.review_host(config_path().parent,
                None if args.value == "off" else args.value, write=args.value is not None)
        except alert_attention.AttentionError as error:
            raise SetupError(str(error)) from None
        print(json.dumps(result, sort_keys=True))
        return
    if args.command == "attention":
        import alert_attention
        try:
            request = alert_attention.read_request(sys.stdin)
            token, chat = credentials()
            environment = {"TELEGRAM_ALERTS_CWD": os.getcwd()}
            if "JCODE_SESSION_ID" in os.environ:
                environment["JCODE_SESSION_ID"] = os.environ["JCODE_SESSION_ID"]
            for name in (alert_attention.INBOX_REGISTRY_ENV, alert_attention.INBOX_BASE_ENV):
                if name in os.environ:
                    environment[name] = os.environ[name]
            destination = hashlib.sha256((token + "\0" + chat).encode()).hexdigest()
            legacy_home = alert_home.legacy_read_home()
            _note_legacy_attention_fallback(config_path().parent, legacy_home)

            def deliver(method, body):
                try:
                    return api(token, method, {**body, "chat_id": chat})
                except SetupError:
                    raise alert_attention.AttentionError(
                        "Attention delivery was not confirmed. It may have arrived; do not retry automatically."
                    ) from None

            receipt = alert_attention.publish(config_path().parent, environment, request, args.key,
                                              deliver, destination, secrets=(token, chat), resend=args.resend,
                                              review_port=args.review_port,
                                              legacy_home=legacy_home)
        except alert_attention.AttentionError as error:
            raise SetupError(str(error)) from None
        for warning in receipt.get("url_rewrite_warnings", []):
            print("Warning: " + warning, file=sys.stderr)
        print(json.dumps(receipt, sort_keys=True))
        return
    if args.command == "preview":
        print("Preview only, not sent:\n" + preview_text())
        return
    if args.command == "setup":
        setup()
    elif args.command == "status":
        safety = load_config().get("safety", {})
        linked = bool(safety.get("telegram_enabled") and safety.get("telegram_bot_token") and safety.get("telegram_chat_id"))
        print("Telegram: " + ("configured locally (use 'test' to verify delivery)" if linked else "pending bot creation and private token entry"))
        print("Remote commands: disabled (not supported by this CLI)")
        print("Owner handoffs: explicit attention command only; no native session or lifecycle hook is read")
    elif args.command == "test":
        token, chat = credentials()
        import alert_attention
        message = formatting.prepend_message(
            preview_message(), "Telegram Alerts test (illustrative, not a live request):\n\n")
        api(token, "sendMessage", {"chat_id": chat, "text": message["text"], "entities": message["entities"],
                                   "link_preview_options": {"is_disabled": True}})
        print("Generic Telegram Alerts test preview delivered.")
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
