"""Explicit opt-in adapter for legacy Jcode lifecycle hooks.

The generic ``telegram-alerts`` CLI and ``jcode-telegram`` compatibility alias
never call this module. Install hooks deliberately with
``telegram-alerts-hook`` if the legacy lifecycle integration is still needed.
"""
import argparse
import hashlib
import json
import os
import sys
import time

import alert_format as formatting
import alert_policy
import alert_selector
import telegram_alerts as core

# Explicit adapter bindings stay local so tests and external installers can
# replace transport/config dependencies without coupling the generic CLI.
api = core.api
credentials = core.credentials
config_path = core.config_path
alert_secrets = core.alert_secrets
delivery_policy = core.delivery_policy
SetupError = core.SetupError


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
        return "brief"


def save_verbosity(value):
    if value not in formatting.PROFILES:
        raise core.SetupError("Choose brief, contextual, or expanded.")
    path = settings_path()
    if path.is_symlink():
        raise core.SetupError("Alert settings are a symlink. Refusing to replace it automatically.")
    core.private_write(path, json.dumps({"verbosity": value}, indent=2) + "\n")


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
    name = formatting.chat_identity(config_path().parent, environment.get("JCODE_HOOK_SESSION_ID", ""))
    return formatting.render_message(environment, selected_verbosity(verbosity), prompt,
                                     alert_secrets(), session_name=name)


def alert_text(environment, min_seconds=30, verbosity=None):
    message = alert_message(environment, min_seconds, verbosity)
    return message["text"] if message else None


def event_message(environment, verbosity="expanded"):
    if environment.get("JCODE_HOOK_EVENT") == "turn_end":
        return alert_message(environment, 0, verbosity)
    name = formatting.chat_identity(config_path().parent, environment.get("JCODE_HOOK_SESSION_ID", ""))
    return formatting.render_lifecycle_message(environment, verbosity, alert_secrets(), session_name=name)


def selected_completion(home, environment, token, chat, destination, verbosity, stored):
    """Only the Clef yes branch may reach ordinary completion delivery."""
    sid = environment.get("JCODE_HOOK_SESSION_ID", "")
    if (not stored["events"]["completion"] or sid in stored["exclude_sessions"]
            or (stored["include_sessions"] and sid not in stored["include_sessions"])):
        return {"state": "disabled", "kind": "completion"}
    try:
        context = formatting.selector_context(home, environment, (token, chat),
                                             allow_fork=sid in stored["include_sessions"])
    except (OSError, ValueError, TypeError, RecursionError) as error:
        allowed = {"source_unavailable", "source_oversize", "internal_session", "internal_turn", "stale_source", "empty_source"}
        reason = error.args[0] if isinstance(error, ValueError) and error.args and error.args[0] in allowed else "source_unavailable"
        return {"state": "selector_skipped", "kind": "completion", "selector_reason": reason}

    def selected_deliver(*, secrets=()):
        # An off command completes only after an already-admitted send ends.
        # Never send using stale policy captured before a model request.
        with alert_policy._directory(home, create=True) as folder, alert_policy._locked(folder, ".telegram-policy-config.lock"):
            current = delivery_policy(home)
            if current["completion_selector"] != "clef":
                return {"state": "disabled", "kind": "completion"}
            selected = {**current, "cooldown_seconds": 0, "status_card": False}

            def deliver(method, body):
                return api(token, method, {**body, "chat_id": chat})

            return alert_policy.notify(home, context["environment"],
                lambda: formatting.render_selected_message(context["environment"], secrets,
                                                            session_name=context["session_name"]),
                deliver, destination, verbosity=verbosity, min_seconds=0,
                policy=selected, selector_authorized=True)

    return {**alert_selector.process(home, context["turn"], selected_deliver, secrets=(token, chat)),
            "kind": "completion"}


def receipt_path():
    return config_path().parent / "notifications" / "telegram-last-alert.json"


def record_receipt(state, **metadata):
    """Store only bounded receipt metadata; never persist session content."""
    try:
        payload = json.dumps({
            "state": state,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "recorded_at_ns": time.time_ns(),
            "session_fingerprint": hashlib.sha256(os.environ.get("JCODE_HOOK_SESSION_ID", "").encode()).hexdigest()[:16],
            **{key: metadata[key] for key in ("kind", "grouped", "method", "verbosity", "words", "characters", "telegram_message_id", "text_fingerprint", "response_confirmed", "prompt_available", "bold_entities", "link_entities", "formatting_confirmed", "selector_choice", "selector_reason", "pir_count", "pir_ready") if key in metadata},
        }) + "\n"
        kind = metadata.get("kind")
        if kind in ("session_start", "turn_start", "completion", "error", "session_end"):
            core.private_write(receipt_path().with_name("telegram-last-" + kind + ".json"), payload)
        core.private_write(receipt_path(), payload)
    except OSError:
        pass


def observe_event(environment, min_seconds=30, verbosity="expanded"):
    """Best-effort observer; call only from the explicit Jcode adapter."""
    if environment.get("JCODE_HOOK_EVENT") not in ("session_start", "turn_start", "turn_end", "session_end"):
        return
    try:
        token, chat = credentials()
    except core.SetupError:
        record_receipt("pending_setup")
        return
    except (OSError, ValueError):
        record_receipt("config_error")
        return
    try:
        destination = hashlib.sha256((token + "\0" + chat).encode()).hexdigest()

        def deliver(method, body):
            if method not in ("sendMessage", "editMessageText"):
                raise core.SetupError("Unsupported notification operation.")
            return api(token, method, {**body, "chat_id": chat})

        home = config_path().parent
        policy = delivery_policy(home)
        if (environment.get("JCODE_HOOK_EVENT") == "turn_end"
                and environment.get("JCODE_HOOK_STATUS") == "ok"
                and policy["completion_selector"] == "clef"):
            receipt = selected_completion(home, environment, token, chat, destination, verbosity, policy)
        else:
            receipt = alert_policy.notify(home, environment,
                                          lambda: event_message(environment, verbosity), deliver,
                                          destination, verbosity=verbosity, min_seconds=min_seconds)
        receipt = dict(receipt)
        state = receipt.pop("state")
        record_receipt(state, **receipt)
    except Exception:
        # Detached hook diagnostics intentionally omit exception text.
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
            raise core.SetupError("No readable public assistant response exists in that session.")
        event_data = {"JCODE_HOOK_EVENT": "turn_end", "JCODE_HOOK_STATUS": "preview",
                      "JCODE_HOOK_DURATION_MS": "0", "JCODE_HOOK_SESSION_ID": session_id,
                      "JCODE_HOOK_CWD": session.get("working_dir"),
                      "JCODE_HOOK_LAST_ASSISTANT_TEXT": response[:4000]}
        prompt = formatting.session_prompt(config_path().parent, session_id, response[:4000])
        name = formatting.chat_identity(config_path().parent, session_id)
    else:
        event_data = formatting.sample_event()
        prompt = "Add selectable Telegram alert verbosity, default to expanded, and keep messages concise."
    return formatting.render_message(event_data, verbosity, prompt, alert_secrets(), session_name=name)


def preview_text(verbosity, session_id=None, event=None):
    return preview_message(verbosity, session_id, event)["text"]


def _policy(args, parser):
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
        return alert_policy.save_policy(config_path().parent, changes,
                                        silent=args.silent or (), audible=args.audible or ())
    return delivery_policy(config_path().parent)


def main(argv=None):
    kinds = ("session_start", "turn_start", "completion", "error", "session_end")
    parser = argparse.ArgumentParser(
        prog="telegram-alerts-jcode",
        description="Explicit opt-in legacy Jcode lifecycle event adapter; not used by the generic Telegram CLI.",
        epilog="Use telegram-alerts attention for generic owner handoffs. This adapter may read native Jcode sessions.")
    parser.add_argument("command", choices=("status", "alert", "event", "preview", "policy", "selector", "verbosity"))
    parser.add_argument("value", nargs="?", help="legacy policy preset, selector on|off, or verbosity level")
    parser.add_argument("--min-seconds", type=int, default=30)
    parser.add_argument("--verbosity", choices=tuple(formatting.PROFILES), help="override this legacy event or preview only")
    parser.add_argument("--session", help="read one saved Jcode session for an illustrative no-send preview")
    parser.add_argument("--event", choices=("session_start", "turn_start", "completion", "error", "session_end"),
                        help="legacy lifecycle kind for a no-send preview")
    parser.add_argument("--cooldown-seconds", type=int)
    parser.add_argument("--error-repeat-seconds", type=int)
    parser.add_argument("--status-card", choices=("on", "off"))
    parser.add_argument("--enable", action="append", choices=kinds)
    parser.add_argument("--disable", action="append", choices=kinds)
    parser.add_argument("--silent", action="append", choices=kinds)
    parser.add_argument("--audible", action="append", choices=kinds)
    parser.add_argument("--include-session", action="append")
    parser.add_argument("--exclude-session", action="append")
    parser.add_argument("--clear-session-filters", action="store_true")
    parser.add_argument("--endpoint")
    parser.add_argument("--key-file")
    parser.add_argument("--model")
    parser.add_argument("--response-model")
    parser.add_argument("--pir-turns", type=int)
    args = parser.parse_args(argv)
    if args.min_seconds < 0 or any(value is not None and not 0 <= value <= 86400
                                   for value in (args.cooldown_seconds, args.error_repeat_seconds)):
        parser.error("durations must be nonnegative; policy intervals cannot exceed 86400 seconds")
    policy_options = (args.cooldown_seconds, args.error_repeat_seconds, args.status_card,
                      args.enable, args.disable, args.silent, args.audible,
                      args.include_session, args.exclude_session)
    selector_options = (args.endpoint, args.key_file, args.model, args.response_model, args.pir_turns)
    if args.command != "policy" and (any(value is not None for value in policy_options) or args.clear_session_filters):
        parser.error("delivery-policy options are only valid after policy")
    if args.command != "selector" and any(value is not None for value in selector_options):
        parser.error("selector connection options require selector on")
    if args.command != "preview" and (args.session is not None or args.event is not None):
        parser.error("--session and --event are only valid for no-send previews")
    if args.session and args.event not in (None, "completion"):
        parser.error("saved sessions can preview completion text only")
    if args.command not in ("alert", "event", "preview", "verbosity") and args.verbosity is not None:
        parser.error("--verbosity is only valid for event, preview, or verbosity commands")
    if args.command not in ("alert", "event") and args.min_seconds != 30:
        parser.error("--min-seconds is only valid for event commands")
    if args.value is not None and args.command not in ("policy", "selector", "verbosity"):
        parser.error("a positional value is only valid after policy, selector, or verbosity")
    if args.command == "policy" and args.value and args.value not in ("attention", "balanced", "activity"):
        parser.error("choose attention, balanced, or activity")
    if args.command == "selector":
        options = (args.endpoint, args.key_file, args.model, args.response_model, args.pir_turns)
        if any(value is not None for value in options) and (args.value != "on"):
            parser.error("selector connection options require selector on")
        if args.value not in (None, "on", "off"):
            parser.error("selector accepts on, off, or a read-only query")
        if args.value == "on" and not all((args.endpoint, args.key_file, args.model, args.response_model)):
            parser.error("selector on requires --endpoint, --key-file, --model and --response-model")
        if args.pir_turns is not None and not 1 <= args.pir_turns <= 100:
            parser.error("--pir-turns must be from 1 through 100")
        home = config_path().parent
        if args.value == "on":
            alert_selector.configure(home, endpoint=args.endpoint, key_file=args.key_file,
                                     model=args.model, expected_model=args.response_model,
                                     pir_turns=100 if args.pir_turns is None else args.pir_turns)
            alert_policy.save_policy(home, {"completion_selector": "clef", "events": {"completion": True}})
        elif args.value == "off":
            alert_policy.save_policy(home, {"completion_selector": "off", "events": {"completion": False}})
        result = alert_selector.status(home)
        policy = delivery_policy(home)
        route_ready = result.get("legacy_route_ready") is True
        print(json.dumps({**result, "enabled": result.get("configured") is True and route_ready
                          and policy["completion_selector"] == "clef" and policy["events"]["completion"],
                          "mode": policy["completion_selector"], "route_ready": route_ready,
                          "completion_enabled": policy["events"]["completion"]}, sort_keys=True))
        return
    if args.command == "verbosity":
        if args.value is not None and args.value not in formatting.PROFILES:
            parser.error("choose brief, contextual, or expanded")
        if args.value:
            save_verbosity(args.value)
        print("Legacy Jcode event verbosity: " + selected_verbosity(args.verbosity))
        return
    if args.command == "policy":
        policy = _policy(args, parser)
        print(json.dumps(policy, indent=2, sort_keys=True))
        return
    if args.command == "preview":
        level = selected_verbosity(args.verbosity)
        print("Preview only, not sent (" + level + "):\n" +
              preview_text(level, args.session, args.event))
        return
    if args.command in ("alert", "event"):
        observe_event(os.environ, args.min_seconds, selected_verbosity(args.verbosity))
        return
    if args.command == "status":
        safety = core.load_config().get("safety", {})
        linked = bool(safety.get("telegram_enabled") and safety.get("telegram_bot_token") and safety.get("telegram_chat_id"))
        print("Legacy Jcode event adapter: " + ("configured locally" if linked else "pending Telegram profile"))
        level = selected_verbosity()
        print(f"Legacy event verbosity: {level} (up to {formatting.PROFILES[level]['words']} words)")
        policy = delivery_policy(config_path().parent)
        selector_status = alert_selector.status(config_path().parent)
        print(f"Legacy delivery policy: {policy['preset']}, completion interval {policy['cooldown_seconds']}s per session")
        print("Completion selector: " + policy["completion_selector"])
        print("Completion selector route: " + ("ready" if selector_status.get("legacy_route_ready") else "not ready"))
        print("Status card: " + ("on" if policy["status_card"] else "off"))
        try:
            receipt = json.loads(receipt_path().read_text())
            if not isinstance(receipt, dict):
                raise ValueError("Invalid local diagnostic receipt.")
            print("Last legacy event receipt: " + str(receipt.get("state")) + " at " + str(receipt.get("at")))
        except (OSError, ValueError):
            print("Last legacy event receipt: none recorded yet")


def cli():
    try:
        main()
        return 0
    except alert_selector.RouteOwnershipError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (core.SetupError, OSError, ValueError, TypeError, RecursionError) as error:
        print(str(error) if isinstance(error, core.SetupError) else "Legacy Jcode adapter state could not be used safely.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
