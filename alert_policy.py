"""Bounded, local Telegram delivery policy. No transport or transcript access.

Invalid configuration/state raises ValueError in configuration APIs and fails closed
in notify. A shared flock also serializes different sessions, deliberately trading
throughput for a bounded state file and an unambiguous delivery transaction.
Inactive entries expire after at least one day and both suppression windows.
At active capacity new sessions fail closed rather than evicting live history.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import stat
import time

from alert_format import PROFILES, clip, formatting_confirmed, utf16_length
from alert_links import safe_url

EVENTS = ('session_start', 'turn_start', 'completion', 'error', 'session_end')
PRESETS = {
    'attention': {key: key == 'error' for key in EVENTS},
    'balanced': {key: key in ('completion', 'error') for key in EVENTS},
    'activity': dict.fromkeys(EVENTS, True),
}
DEFAULT_POLICY = {
    'version': 1, 'preset': 'balanced', 'events': PRESETS['balanced'],
    'cooldown_seconds': 300, 'error_repeat_seconds': 300, 'status_card': False,
    'silent_events': ['session_start', 'turn_start', 'session_end'],
    'include_sessions': [], 'exclude_sessions': [], 'completion_selector': 'off',
}
MAX_SETTINGS_BYTES = 8192
MAX_STATE_BYTES = 524288
MAX_SESSIONS = 128
MAX_SECONDS = 31 * 86400
MAX_COUNTER = 999999
MAX_TIMESTAMP = 2**53 - 1
STATE_TTL_SECONDS = 86400
POLICY_FILE = 'telegram-policy.json'
STATE_FILE = 'telegram-policy-state.json'
_HEX = re.compile(r'[0-9a-f]{64}\Z')


def _hash(value):
    return hashlib.sha256(value.encode('utf-8', errors='replace')).hexdigest()


def _integer(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def _validate(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_POLICY):
        raise ValueError('Invalid policy keys')
    result = copy.deepcopy(DEFAULT_POLICY)
    preset = value.get('preset', result['preset'])
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ValueError('Invalid preset')
    result['events'] = PRESETS[preset].copy()
    result.update({k: v for k, v in value.items() if k != 'events'})
    events = value.get('events', {})
    if not isinstance(events, dict) or set(events) - set(EVENTS) or any(type(v) is not bool for v in events.values()):
        raise ValueError('Invalid events')
    result['events'].update(events)
    if type(result['version']) is not int or result['version'] != 1:
        raise ValueError('Invalid version')
    for key in ('cooldown_seconds', 'error_repeat_seconds'):
        if not _integer(result[key], MAX_SECONDS):
            raise ValueError('Invalid seconds')
    if type(result['status_card']) is not bool:
        raise ValueError('Invalid status card')
    if result['completion_selector'] not in ('off', 'clef'):
        raise ValueError('Invalid completion selector')
    for key in ('silent_events', 'include_sessions', 'exclude_sessions'):
        items = result[key]
        if not isinstance(items, list) or len(items) > 128:
            raise ValueError('Invalid list')
        if any(not isinstance(item, str) or not item or len(item) > 256 or any(ord(c) < 32 for c in item) for item in items):
            raise ValueError('Invalid identifier')
        if len(set(items)) != len(items):
            raise ValueError('Duplicate identifier')
        if key == 'silent_events' and set(items) - set(EVENTS):
            raise ValueError('Invalid silent event')
    _encode(result, MAX_SETTINGS_BYTES)
    return copy.deepcopy(result)


def _encode(value, limit):
    try:
        data = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError('Invalid JSON') from exc
    if len(data) > limit:
        raise ValueError('JSON limit exceeded')
    return data


@contextmanager
def _directory(home, create=False):
    try:
        if create:
            os.makedirs(home, mode=0o700, exist_ok=True)
        try:
            parent = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except FileNotFoundError:
            yield None
            return
        try:
            if os.fstat(parent).st_uid != os.getuid():
                raise ValueError('Unsafe home directory')
            if create:
                try:
                    os.mkdir('notifications', mode=0o700, dir_fd=parent)
                except FileExistsError:
                    pass
            try:
                fd = os.open('notifications', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                yield None
                return
        finally:
            os.close(parent)
    except OSError as exc:
        raise ValueError('Unsafe notifications directory') from exc
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid():
            raise ValueError('Unsafe notifications directory')
        if info.st_mode & 0o022:
            if not create:
                try:
                    os.stat(POLICY_FILE, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    # Legacy helper directories may be 0775. A missing-policy
                    # query reads no untrusted file and must remain read-only.
                    yield None
                    return
            raise ValueError('Unsafe notifications directory')
        yield fd
    finally:
        os.close(fd)


def _check(fd, private=False):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise ValueError('Unsafe file')
    if private and info.st_mode & 0o077:
        raise ValueError('Non-private state')
    return info


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _read(folder, name, limit, default, private=False):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
    except FileNotFoundError:
        return copy.deepcopy(default)
    except OSError as exc:
        raise ValueError('Unsafe file') from exc
    with os.fdopen(fd, 'rb') as stream:
        if _check(stream.fileno(), private).st_size > limit:
            raise ValueError('File limit exceeded')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('File limit exceeded')
    try:
        return json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON') from exc


def _write(folder, name, value, limit):
    data = _encode(value, limit)
    # Refuse replacing an unsafe target, even though rename itself does not follow it.
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
    except FileNotFoundError:
        pass
    else:
        try:
            _check(fd)
        finally:
            os.close(fd)
    temp = '.policy-' + secrets.token_hex(12)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, name, src_dir_fd=folder, dst_dir_fd=folder)
        os.fsync(folder)
    finally:
        try:
            os.unlink(temp, dir_fd=folder)
        except FileNotFoundError:
            pass


@contextmanager
def _locked(folder, name):
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=folder)
    try:
        _check(fd, True)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def load_policy(home):
    """Return a fresh validated policy, defaulting only for a missing file."""
    with _directory(home) as folder:
        return _validate({} if folder is None else _read(folder, POLICY_FILE, MAX_SETTINGS_BYTES, {}))


def save_policy(home, changes, *, silent=(), audible=()):
    """Atomically merge fields and silence deltas under the configuration lock.

    Selecting a preset resets event overrides. Deltas apply after any explicit
    silent_events replacement, preserve existing order and add in EVENTS order.
    The original two-argument API remains supported.
    """
    if not isinstance(changes, dict):
        raise ValueError('Invalid changes')
    _validate(changes)
    for delta in (silent, audible):
        if not isinstance(delta, (list, tuple)) or len(delta) > len(EVENTS):
            raise ValueError('Invalid silence delta')
        if any(not isinstance(event, str) or event not in EVENTS for event in delta):
            raise ValueError('Invalid silence event')
        if len(set(delta)) != len(delta):
            raise ValueError('Duplicate silence event')
    silent, audible = set(silent), set(audible)
    if silent & audible:
        raise ValueError('Conflicting silence deltas')
    try:
        with _directory(home, create=True) as folder, _locked(folder, '.telegram-policy-config.lock'):
            current = _validate(_read(folder, POLICY_FILE, MAX_SETTINGS_BYTES, {}))
            if 'preset' in changes:
                current['events'] = PRESETS[changes['preset']].copy()
            events = {**current['events'], **changes.get('events', {})}
            current.update(changes)
            current['events'] = events
            current['silent_events'] = [event for event in current['silent_events'] if event not in audible]
            current['silent_events'].extend(event for event in EVENTS
                                           if event in silent and event not in current['silent_events'])
            current = _validate(current)
            _write(folder, POLICY_FILE, current, MAX_SETTINGS_BYTES)
            return current
    except OSError as exc:
        raise ValueError('Cannot save policy') from exc


def _state(value):
    if not isinstance(value, dict) or set(value) != {'version', 'sessions'} or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Invalid state')
    sessions = value['sessions']
    if not isinstance(sessions, dict) or len(sessions) > MAX_SESSIONS:
        raise ValueError('Invalid sessions')
    for key, entry in sessions.items():
        if not _HEX.fullmatch(key) or not isinstance(entry, dict) or set(entry) - {'completion', 'grouped', 'errors', 'card', 'last_seen'}:
            raise ValueError('Invalid session state')
        if 'completion' in entry and not _integer(entry['completion'], MAX_TIMESTAMP):
            raise ValueError('Invalid timestamp')
        if 'last_seen' in entry and not _integer(entry['last_seen'], MAX_TIMESTAMP):
            raise ValueError('Invalid timestamp')
        if not _integer(entry.get('grouped', 0), MAX_COUNTER):
            raise ValueError('Invalid count')
        errors = entry.get('errors', {})
        if not isinstance(errors, dict) or len(errors) > 32 or any(not _HEX.fullmatch(k) or not _integer(v, MAX_TIMESTAMP) for k, v in errors.items()):
            raise ValueError('Invalid error history')
        if 'card' in entry:
            card = entry['card']
            if not isinstance(card, dict) or set(card) != {'destination', 'message_id'} or not isinstance(card['destination'], str) or not _HEX.fullmatch(card['destination']) or not _message_id(card['message_id']):
                raise ValueError('Invalid card')
    return value


def _message_id(value):
    return type(value) is int and 0 < value <= 2**52 - 1


def _message(rendered, verbosity, grouped, selected=False):
    if not isinstance(rendered, dict) or not isinstance(rendered.get('text'), str) or not 0 < len(rendered['text']) <= 65536:
        raise ValueError('Invalid rendering')
    profile = {'words': 600, 'chars': 4096} if selected else PROFILES[verbosity]
    suffix = f'\n\nGrouped: {grouped} earlier completions.' if grouped else ''
    original = rendered['text']
    supplied = rendered.get('entities', [])
    has_links = isinstance(supplied, list) and any(
        isinstance(e, dict) and e.get('type') == 'text_link' and isinstance(e.get('url'), str)
        and safe_url(e['url']) == e['url'] for e in supplied[:100])
    if has_links and (len(original + suffix) > profile['chars']
                      or len((original + suffix).split()) > profile['words']):
        # Useful links take precedence over the optional grouping footer. Do
        # not cut their labels just to repeat an already-recorded counter.
        suffix = ''
    text = clip(original, profile['words'] - len(suffix.split()), profile['chars'] - len(suffix))
    # clip appends an ellipsis. Only original, unchanged code points may retain
    # trusted spans, and neither endpoint may bisect a UTF-16 surrogate pair.
    prefix = 0
    for left, right in zip(original, text):
        if left != right:
            break
        prefix += 1
    boundaries = {0}
    units = 0
    for char in text[:prefix]:
        units += utf16_length(char)
        boundaries.add(units)
    entities = rendered.get('entities', [])
    if not isinstance(entities, list):
        entities = []
    valid = []
    for entity in entities[:100]:
        if not isinstance(entity, dict) or entity.get('type') not in ('bold', 'text_link'):
            continue
        expected = {'type', 'offset', 'length', 'url'} if entity['type'] == 'text_link' else {'type', 'offset', 'length'}
        if (set(entity) != expected or type(entity['offset']) is not int or type(entity['length']) is not int
                or entity['length'] <= 0 or entity['offset'] not in boundaries
                or entity['offset'] + entity['length'] not in boundaries):
            continue
        if entity['type'] == 'text_link' and (not isinstance(entity['url'], str)
                                             or safe_url(entity['url']) != entity['url']):
            continue
        valid.append(dict(entity))
    if utf16_length(text + suffix) > 4096:
        raise ValueError('Telegram text limit exceeded')
    return {'text': text + suffix, 'entities': valid, 'link_preview_options': {'is_disabled': True}}


def notify(home, environment, render, deliver, destination_fingerprint,
           verbosity='expanded', min_seconds=30, policy=None, now=None,
           selector_authorized=False):
    """Make one serialized delivery decision. Callbacks execute inside the lock.

    deliver returns the TelegramMessage itself, not an API envelope. Unconfirmed
    responses and exceptions are not retried. No exception text is persisted.
    Enabled card completions always update quietly, regardless of duration or
    push cooldown, and do not advance the ordinary completion-push timestamp.
    """
    event = environment.get('JCODE_HOOK_EVENT')
    status = environment.get('JCODE_HOOK_STATUS')
    kind = ({'ok': 'completion', 'error': 'error'}.get(status) if event == 'turn_end' and isinstance(status, str)
            else event if event in ('session_start', 'turn_start', 'session_end') else None)
    receipt = {'state': 'ignored', 'kind': kind, 'grouped': 0, 'verbosity': verbosity,
               'response_confirmed': False, 'formatting_confirmed': False}
    if kind is None:
        return receipt

    def finish(state):
        receipt['state'] = state
        return receipt

    try:
        stored = load_policy(home)
        config = stored if policy is None else _validate(policy)
        if verbosity not in PROFILES or not _integer(min_seconds, MAX_SECONDS):
            return finish('invalid_policy')
        if now is None:
            now = time.time()
        if type(now) not in (int, float) or not math.isfinite(now) or not 0 <= now <= MAX_TIMESTAMP:
            return finish('invalid_policy')
        now = int(now)
        session = environment.get('JCODE_HOOK_SESSION_ID')
        if not isinstance(session, str) or not session or len(session) > 256:
            return finish('ignored')
        if not isinstance(destination_fingerprint, str) or not destination_fingerprint or len(destination_fingerprint) > 256:
            return finish('invalid_policy')
        if not config['events'][kind] or session in config['exclude_sessions'] or (config['include_sessions'] and session not in config['include_sessions']):
            return finish('disabled')
        selected = kind == 'completion' and config['completion_selector'] == 'clef'
        if selected and selector_authorized is not True:
            return finish('selector_required')
        if kind == 'completion' and not config['status_card']:
            duration = environment.get('JCODE_HOOK_DURATION_MS', '0')
            if type(duration) not in (str, int):
                return finish('ignored')
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                return finish('ignored')
            if duration < min_seconds * 1000:
                return finish('ignored')
        key, destination = _hash(session), _hash(destination_fingerprint)
        with _directory(home, create=True) as folder, _locked(folder, '.telegram-policy-state.lock'):
            state = _state(_read(folder, STATE_FILE, MAX_STATE_BYTES, {'version': 1, 'sessions': {}}, True))
            ttl = max(STATE_TTL_SECONDS, config['cooldown_seconds'], config['error_repeat_seconds'])
            state['sessions'] = {k: v for k, v in state['sessions'].items()
                                 if now - v.get('last_seen', max([v.get('completion', now), *v.get('errors', {}).values()])) <= ttl}
            if key not in state['sessions'] and len(state['sessions']) >= MAX_SESSIONS:
                return finish('invalid_policy')
            entry = state['sessions'].setdefault(key, {})
            entry['last_seen'] = now
            if kind == 'completion' and not config['status_card'] and 'completion' in entry and now - entry['completion'] < config['cooldown_seconds']:
                entry['grouped'] = min(MAX_COUNTER, entry.get('grouped', 0) + 1)
                _write(folder, STATE_FILE, state, MAX_STATE_BYTES)
                return finish('suppressed_cooldown')
            error = _hash(str(environment.get('JCODE_HOOK_ERROR') or 'Turn failed')) if kind == 'error' else None
            errors = entry.get('errors', {})
            if error in errors and now - errors[error] < config['error_repeat_seconds']:
                _write(folder, STATE_FILE, state, MAX_STATE_BYTES)
                return finish('suppressed_repeat_error')
            grouped = entry.get('grouped', 0) if kind == 'completion' and not selected else 0
            receipt['grouped'] = grouped
            card = entry.get('card')
            matching_card = card if card and card['destination'] == destination else None
            method = 'editMessageText' if config['status_card'] and matching_card and kind != 'error' else 'sendMessage'
            try:
                rendered = render()
                message = _message(rendered, verbosity, grouped, selected=selected)
                receipt['prompt_available'] = rendered.get('prompt_available') is True
                receipt['method'] = method
                receipt.update(words=len(message['text'].split()), characters=len(message['text']),
                               bold_entities=sum(e['type'] == 'bold' for e in message['entities']),
                               link_entities=sum(e['type'] == 'text_link' for e in message['entities']),
                               text_fingerprint=_hash(message['text']))
                body = copy.deepcopy(message)
                if method == 'editMessageText':
                    body['message_id'] = matching_card['message_id']
                elif (config['status_card'] and kind != 'error') or kind in config['silent_events']:
                    body['disable_notification'] = True
                response = deliver(method, body)
                confirmed = (isinstance(response, dict) and _message_id(response.get('message_id'))
                             and response.get('text') == message['text']
                             and (method != 'editMessageText' or response['message_id'] == matching_card['message_id']))
                if not confirmed:
                    return finish('delivery_failed')
                receipt['response_confirmed'] = True
                receipt['telegram_message_id'] = response['message_id']
                receipt['formatting_confirmed'] = formatting_confirmed(message, response)
            except Exception:
                return finish('delivery_failed')
            if kind == 'completion':
                entry['grouped'] = 0
                if not config['status_card']:
                    entry['completion'] = now
            if error:
                # Keep a bounded recent fingerprint set, with no raw error details.
                errors = {k: v for k, v in errors.items() if now - v < config['error_repeat_seconds']}
                errors[error] = now
                entry['errors'] = dict(sorted(errors.items(), key=lambda item: item[1])[-32:])
            if config['status_card'] and kind != 'error':
                entry['card'] = {'destination': destination, 'message_id': response['message_id']}
            # Persist confirmed attention delivery before attempting a best-effort edit.
            _write(folder, STATE_FILE, state, MAX_STATE_BYTES)
            if kind == 'error' and config['status_card'] and matching_card:
                try:
                    deliver('editMessageText', {**message, 'message_id': matching_card['message_id']})
                except Exception:
                    pass
            return finish('edited' if method == 'editMessageText' else 'sent')
    except (OSError, ValueError, TypeError, RecursionError):
        return finish('invalid_policy')
