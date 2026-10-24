"""Offline selector contract tests. All keys, inputs and transports are synthetic."""
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import alert_selector as selector


def envelope(choice='yes'):
    return {'model': selector.EXPECTED_MODEL, 'usage': {'input_tokens': 20, 'output_tokens': 0},
            'answers': {'publish': {'type': 'choice', 'choice': choice, 'confidence': .9,
                                   'probabilities': {choice: .9, 'no' if choice == 'yes' else 'yes': .1}}}}


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.key = self.home / 'fake-key'
        self.key.write_text('synthetic-inference-key-only')
        self.key.chmod(0o600)
        self.configure()
        self.folder = self.home / 'notifications'
        self.deliver = Mock(return_value={'state': 'sent', 'response_confirmed': True,
                                         'formatting_confirmed': True, 'telegram_message_id': 12})

    def configure(self, **changes):
        args = dict(endpoint='https://synthetic.invalid:9105', key_file=self.key,
                    model='alias', expected_model=selector.EXPECTED_MODEL)
        args.update(changes)
        return selector.configure(self.home, **args)

    def turn(self, number=1, **changes):
        value = dict(session_id='session_native_123', turn_id='message_' + str(number),
                     task_context='Ship the requested capability', candidate_text='ELIF: usable',
                     current_public_final='ELIF: usable result ' + str(number), previous_public_final='',
                     links=[{'label': 'Review', 'url': 'https://github.com/owner/repo/pull/1'}])
        value.update(changes)
        return value

    def process(self, number=1, answer=None, **changes):
        return selector.process(self.home, self.turn(number, **changes), self.deliver,
                                request=lambda *args: envelope() if answer is None else answer)

    def state(self):
        return json.loads((self.folder / selector.STATE).read_text())

    def test_prompt_frozen_digest(self):
        # Digest of exact prompts.json['e'], independent of installed scratch files.
        self.assertEqual(hashlib.sha256(json.dumps(selector.QUESTION, sort_keys=True).encode()).hexdigest(),
                         'ee3b84dba0033765c9128074766585c83a5d1b23ab6f7403d7c4676d5ab300aa')

    def test_yes_no_and_original_delivery_links(self):
        original = self.turn()
        def request(config, payload, key):
            self.assertEqual(set(payload['state']), set(selector.TEXT_FIELDS) | {'last_published_update', 'attention_state'})
            self.assertIsNone(payload['state']['last_published_update'])
            self.assertEqual(payload['state']['attention_state'], 'unknown')
            self.assertEqual(payload['questions']['publish'], selector.QUESTION)
            self.assertEqual(self.state()['records'][0]['outcome'], 'pending')
            self.assertEqual(len(self.state()['claims']), 1)
            result = envelope()
            result['links'] = [{'url': 'https://evil.com/forged'}]
            return result
        receipt = selector.process(self.home, original, self.deliver, request=request)
        self.assertEqual(receipt['selector_choice'], 'yes')
        self.assertEqual(receipt['state'], 'sent')
        self.deliver.assert_called_once_with(secrets=('synthetic-inference-key-only',))
        self.assertEqual(self.state()['records'][0]['links'], original['links'])
        self.assertNotIn('evil.com', json.dumps(self.state()))
        self.process(2, envelope('no'))
        self.assertEqual(self.deliver.call_count, 1)
        self.assertEqual(selector.status(self.home)['totals'], dict(observed=2, yes=1, no=1, fail=0, busy=0))

    def test_duplicates_claimed_before_request_and_never_retry(self):
        self.deliver.return_value = {'state': 'delivery_failed', 'response_confirmed': False}
        nested = []
        def request(*args):
            nested.append(selector.process(self.home, self.turn(), self.deliver, request=Mock()))
            return envelope()
        first = selector.process(self.home, self.turn(), self.deliver, request=request)
        self.assertEqual(first['selector_reason'], 'delivery_unconfirmed')
        self.assertEqual(nested[0]['selector_reason'], 'duplicate')
        self.assertEqual(self.process()['selector_reason'], 'duplicate')
        self.assertEqual(self.process(2, current_public_final=self.turn()['current_public_final'])['selector_reason'], 'duplicate')
        self.deliver.assert_called_once()

    def test_malformed_responses_never_deliver(self):
        cases = [None, [], {}, envelope()]
        cases[-1]['model'] = 'wrong'
        for change in (lambda x: x['usage'].update(input_tokens=0),
                       lambda x: x['usage'].update(output_tokens=1),
                       lambda x: x['answers'].update(other={}),
                       lambda x: x['answers']['publish'].update(choice='maybe'),
                       lambda x: x['answers']['publish'].update(confidence=float('nan')),
                       lambda x: x['answers']['publish'].update(probabilities={'yes': .1, 'no': .9}),
                       lambda x: x['answers']['publish'].update(probabilities={'yes': True, 'no': 0})):
            value = envelope()
            change(value)
            cases.append(value)
        for index, value in enumerate(cases):
            receipt = selector.process(self.home, self.turn(index), self.deliver, request=lambda *args, value=value: value)
            self.assertEqual(receipt['selector_state'], 'fail')
        self.deliver.assert_not_called()

    def test_timeout_and_key_failure_are_counted_and_private(self):
        transport = Mock(side_effect=TimeoutError('synthetic-inference-key-only'))
        receipt = selector.process(self.home, self.turn(), self.deliver, request=transport)
        self.assertEqual(receipt['selector_reason'], 'request_failed')
        self.key.unlink()
        receipt = selector.process(self.home, self.turn(2), self.deliver, request=transport)
        self.assertEqual(receipt['selector_reason'], 'key_unavailable')
        self.assertEqual(selector.status(self.home)['totals']['fail'], 2)
        self.assertNotIn('synthetic-inference-key-only', json.dumps(self.state()))
        self.deliver.assert_not_called()

    def test_secrets_scrubbed_twice_and_receipt_allowlist(self):
        text = 'ELIF: synthetic-inference-key-only telegram-token chat-98765 usable'
        def request(config, payload, key):
            self.assertEqual(key, 'synthetic-inference-key-only')
            for secret in (key, 'telegram-token', 'chat-98765'):
                self.assertNotIn(secret, json.dumps(payload))
            return envelope()
        self.deliver.return_value['unsafe'] = text
        receipt = selector.process(self.home, self.turn(current_public_final=text), self.deliver,
                                   secrets=('telegram-token', 'chat-98765'), request=request)
        for secret in ('synthetic-inference-key-only', 'telegram-token', 'chat-98765'):
            self.assertNotIn(secret, json.dumps(self.state()) + json.dumps(receipt))

    def test_config_preserves_records_and_rejects_damaged_existing(self):
        self.process()
        before = (self.folder / selector.STATE).read_bytes()
        first = selector.status(self.home)['generation']
        self.configure(model='new-alias')
        self.assertNotEqual(selector.status(self.home)['generation'], first)
        self.assertEqual((self.folder / selector.STATE).read_bytes(), before)
        with self.assertRaises(ValueError):
            self.configure(pir_turns=99)
        for raw in ('null', '{}', '{', '{"version":1,"version":1}'):
            (self.folder / selector.CONFIG).write_text(raw)
            with self.assertRaises(ValueError):
                self.configure()
            self.assertEqual((self.folder / selector.CONFIG).read_text(), raw)

    def test_strict_endpoint_and_key_metadata(self):
        for endpoint in ('http://host', 'https://u:p@host', 'https://host/', 'https://host/path',
                         'https://host?', 'https://host#', 'https://host:bad'):
            with self.assertRaises(ValueError):
                self.configure(endpoint=endpoint)
        with patch.object(selector, '_key_file', wraps=selector._key_file) as key_check:
            self.configure()
            key_check.assert_called_once_with(str(self.key))
        self.key.chmod(0o644)
        with self.assertRaises(ValueError):
            self.configure()

    def test_unsafe_config_state_and_locks_refused(self):
        self.process()
        for name in (selector.CONFIG, selector.STATE, '.telegram-selector-state.lock', '.telegram-selector-lease.lock'):
            target = self.folder / name
            original = target.read_bytes()
            for kind in ('symlink', 'hardlink', 'fifo', 'directory', 'mode'):
                target.unlink()
                other = self.home / ('other-' + name)
                other.write_bytes(original)
                other.chmod(0o600)
                if kind == 'symlink':
                    target.symlink_to(other)
                elif kind == 'hardlink':
                    os.link(other, target)
                elif kind == 'fifo':
                    os.mkfifo(target, 0o600)
                elif kind == 'directory':
                    target.mkdir()
                else:
                    target.write_bytes(original)
                    target.chmod(0o644)
                receipt = self.process(100 + len(kind) + len(name))
                self.assertNotEqual(receipt['state'], 'sent', (name, kind))
                if target.is_dir():
                    target.rmdir()
                else:
                    target.unlink()
                other.unlink()
                target.write_bytes(original)
                target.chmod(0o600)

    def test_status_is_read_only(self):
        with tempfile.TemporaryDirectory() as missing:
            root = Path(missing) / 'absent'
            self.assertFalse(selector.status(root)['enabled'])
            self.assertFalse(root.exists())
        self.process()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.folder.iterdir()}
        result = selector.status(self.home)
        self.assertNotIn('key_file', json.dumps(result))
        self.assertNotIn('usable result', json.dumps(result))
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.folder.iterdir()})

    def test_cap100_survives_reconfigure_and_inference_continues(self):
        for index in range(102):
            receipt = self.process(index, envelope('no'))
            self.assertEqual(receipt['selector_choice'], 'no')
        self.assertEqual(len(self.state()['records']), 100)
        self.assertLess((self.folder / selector.STATE).stat().st_size, selector.LIMIT)
        self.assertNotIn('usable result 101', (self.folder / selector.STATE).read_text())
        self.configure()
        result = selector.status(self.home)
        self.assertEqual(result['count'], 100)
        self.assertTrue(result['ready'])
        self.assertEqual(result['totals']['no'], 102)

    def test_busy_turn_recorded_once_concurrent_finish_preserves_both(self):
        entered, release = threading.Event(), threading.Event()
        result = []
        def blocked(*args):
            entered.set()
            self.assertTrue(release.wait(3))
            return envelope('no')
        thread = threading.Thread(target=lambda: result.append(selector.process(self.home, self.turn(), self.deliver, request=blocked)))
        thread.start()
        self.assertTrue(entered.wait(2))
        try:
            receipt = self.process(2)
            self.assertEqual(receipt['selector_reason'], 'busy')
            self.assertEqual(self.process(2)['selector_reason'], 'duplicate')
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(selector.status(self.home)['totals'], dict(observed=2, yes=0, no=1, fail=0, busy=1))
        self.assertEqual([r['outcome'] for r in self.state()['records']], ['no', 'busy'])
        self.deliver.assert_not_called()

    def test_oversized_input_is_counted_not_silently_truncated(self):
        receipt = self.process(current_public_final='a' * 12001)
        self.assertEqual(receipt['selector_reason'], 'oversized')
        self.assertEqual(selector.status(self.home)['totals']['fail'], 1)
        self.assertEqual(self.state()['records'][0]['input'], {})
        self.deliver.assert_not_called()

    def test_production_parser_rejects_duplicate_nan_and_truncated(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1'):
            with self.assertRaises(ValueError):
                selector._parse(raw)

    def test_native_http_shape_response_limits_and_no_redirect(self):
        for number, (status, raw) in enumerate(((200, json.dumps(envelope()).encode()),
                (302, b'{}'), (200, b'x' * 262145), (200, b'{"model":1,"model":2}'),
                (200, b'{"x":NaN}'), (200, b'{'))):
            response = Mock(status=status)
            response.read.return_value = raw
            connection = Mock()
            connection.getresponse.return_value = response
            with patch.object(selector.http.client, 'HTTPSConnection', return_value=connection):
                receipt = selector.process(self.home, self.turn(number), self.deliver)
            connection.request.assert_called_once()
            args = connection.request.call_args.args
            self.assertEqual(args[:2], ('POST', '/v1/systemone'))
            self.assertLessEqual(len(args[2]), 32768)
            self.assertEqual(args[3]['Authorization'], 'Bearer synthetic-inference-key-only')
            if status == 200:
                self.assertEqual(response.read.call_args.args, (262145,))
            else:
                response.read.assert_not_called()
            connection.close.assert_called_once()
            self.assertEqual(receipt['selector_choice'], 'yes' if number == 0 else None)
        self.deliver.assert_called_once_with(secrets=('synthetic-inference-key-only',))

    def test_key_special_files_and_private_directory_refused(self):
        for kind in ('symlink', 'hardlink', 'fifo', 'directory'):
            self.key.unlink()
            other = self.home / 'other-key'
            other.write_text('synthetic-other-key')
            other.chmod(0o600)
            if kind == 'symlink':
                self.key.symlink_to(other)
            elif kind == 'hardlink':
                os.link(other, self.key)
            elif kind == 'fifo':
                os.mkfifo(self.key, 0o600)
            else:
                self.key.mkdir()
            with self.assertRaises((ValueError, OSError)):
                self.configure()
            if self.key.is_dir():
                self.key.rmdir()
            else:
                self.key.unlink()
            other.unlink()
            self.key.write_text('synthetic-inference-key-only')
            self.key.chmod(0o600)
        self.folder.chmod(0o755)
        with self.assertRaises(ValueError):
            selector.status(self.home)
        self.assertEqual(self.process()['selector_reason'], 'invalid')
        self.deliver.assert_not_called()

    def test_corrupted_state_is_not_reset(self):
        self.process()
        for raw in ('null', '{}', '{', '{"version":1,"version":1}'):
            target = self.folder / selector.STATE
            target.write_text(raw)
            with self.assertRaises(ValueError):
                self.configure()
            with self.assertRaises(ValueError):
                selector.status(self.home)
            self.assertEqual(self.process(2)['selector_reason'], 'invalid')
            self.assertEqual(target.read_text(), raw)

    def test_unicode_evidence_complete_and_model_input_not_clipped(self):
        text = '\U0001f600' * 400 + 'a' * 600
        observed = []
        def request(config, payload, key):
            observed.append(payload['state']['current_public_final'])
            return envelope('no')
        for number in range(100):
            receipt = selector.process(self.home, self.turn(number, task_context=text,
                candidate_text=text, current_public_final=text + str(number), previous_public_final=text),
                self.deliver, request=request)
            self.assertEqual(receipt['selector_choice'], 'no')
        self.assertEqual(observed[-1], text + '99')
        self.assertLess((self.folder / selector.STATE).stat().st_size, selector.LIMIT)
        self.assertFalse(self.state()['records'][0]['input_clipped'])
        self.assertEqual(self.state()['records'][99]['input']['current_public_final'], text + '99')
        self.assertEqual(self.state()['records'][99]['input']['previous_public_final'], text)

    def test_distinct_link_content_is_not_duplicate(self):
        self.process(current_public_final='Review https://github.com/owner/repo/pull/1')
        receipt = self.process(2, current_public_final='Review https://github.com/owner/repo/pull/2')
        self.assertEqual(receipt['selector_choice'], 'yes')
        self.assertEqual(self.deliver.call_count, 2)

    def test_late_owner_action_retained_and_secret_reaches_delivery(self):
        text = 'ordinary ' * 1100 + ' PLEASE APPROVE synthetic-inference-key-only'
        sent = []
        def deliver(*, secrets=()):
            sent.append(selector.formatting.sanitize(text, secrets))
            self.assertIn('synthetic-inference-key-only', secrets)
            return {'state': 'sent', 'response_confirmed': True, 'formatting_confirmed': True}
        receipt = selector.process(self.home, self.turn(current_public_final=text), deliver,
                                   secrets=('synthetic-chat',), request=lambda *args: envelope())
        self.assertEqual(receipt['state'], 'sent')
        record = self.state()['records'][0]
        self.assertIn('PLEASE APPROVE', record['input']['current_public_final'])
        self.assertNotIn('synthetic-inference-key-only', sent[0])
        self.assertIn('PLEASE APPROVE', sent[0])
        self.assertFalse(record['input_clipped'])

    def test_latency_metadata_and_prompt_identity(self):
        with patch.object(selector.time, 'monotonic', side_effect=(10.0, 10.125, 20.0, 20.25)):
            self.process()
        record = self.state()['records'][0]
        self.assertEqual(record['request_seconds'], .125)
        self.assertEqual(record['delivery_seconds'], .25)
        self.assertEqual(selector.status(self.home)['prompt_hash'], record['prompt_hash'])
        target = self.folder / selector.STATE
        original = self.state()
        for value in (-1, True, '0.1', float('inf')):
            state = json.loads(json.dumps(original))
            state['records'][0]['request_seconds'] = value
            target.write_text(json.dumps(state))
            with self.assertRaises(ValueError):
                selector.status(self.home)
        target.write_text(json.dumps(original))
        self.process(2, envelope('no'))
        self.assertEqual(self.state()['records'][1]['delivery_seconds'], 0)

    def test_increased_claim_capacity_and_expiry_without_live_eviction(self):
        self.assertEqual(selector.MAX_CLAIMS, 8192)
        self.assertEqual(selector.CLAIM_TTL, 86400)
        state = selector._empty()
        now = time.time()
        state['claims'] = {selector._hash(str(i)): {'content': selector._hash('content' + str(i)), 'at': now}
                           for i in range(selector.MAX_CLAIMS)}
        target = self.folder / selector.STATE
        target.write_text(json.dumps(state))
        target.chmod(0o600)
        receipt = self.process()
        self.assertEqual(receipt['selector_reason'], 'capacity')
        self.assertEqual(len(self.state()['claims']), selector.MAX_CLAIMS)
        with patch.object(selector.time, 'time', return_value=now + selector.CLAIM_TTL + 1):
            receipt = self.process()
        self.assertEqual(receipt['selector_choice'], 'yes')
        self.assertEqual(len(self.state()['claims']), 1)

    def test_native_client_deadline_and_worker_thread_guard(self):
        class SlowConnection:
            def __init__(self, *args, **kwargs):
                pass
            def request(self, *args):
                time.sleep(.3)
            def close(self):
                pass
        with patch.object(selector.http.client, 'HTTPSConnection', SlowConnection):
            self.configure(timeout_seconds=.05)
            start = time.monotonic()
            receipt = selector.process(self.home, self.turn(), self.deliver)
            self.assertLess(time.monotonic() - start, .25)
            self.assertEqual(receipt['selector_reason'], 'request_failed')
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0, 0))
        with patch.object(selector.http.client, 'HTTPSConnection') as connection:
            thread = threading.Thread(target=lambda: selector.process(self.home, self.turn(2), self.deliver))
            thread.start()
            thread.join(2)
            connection.assert_not_called()
        self.deliver.assert_not_called()


if __name__ == '__main__':
    unittest.main()
