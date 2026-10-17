"""Filesystem and callback seam tests, no Telegram connectivity."""
import concurrent.futures
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import unittest

import alert_policy as p
from alert_format import PROFILES


def process_notify(home, queue):
    def deliver(method, body):
        with open(Path(home) / 'deliveries', 'a') as stream:
            stream.write('sent\n')
        return {**body, 'message_id': 7}
    env = {'JCODE_HOOK_EVENT': 'turn_end', 'JCODE_HOOK_STATUS': 'ok',
           'JCODE_HOOK_SESSION_ID': 'process', 'JCODE_HOOK_DURATION_MS': '31000'}
    result = p.notify(home, env, lambda: {'text': 'done', 'entities': []}, deliver, 'dest', now=1000)
    queue.put(result['state'])


def process_save_silent(home, barrier, queue, event):
    barrier.wait(timeout=15)
    try:
        p.save_policy(home, {}, silent=[event])
        queue.put('saved')
    except Exception as exc:
        queue.put(type(exc).__name__)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.calls = []
        self.renders = 0

    def render(self):
        self.renders += 1
        return {'text': 'Done result', 'entities': [{'type': 'bold', 'offset': 0, 'length': 4}], 'prompt_available': True}

    def deliver(self, method, body):
        self.calls.append((method, body))
        return dict(body, message_id=body.get('message_id', len(self.calls)))

    def notify(self, now=1000, event='turn_end', status='ok', session='secret-session', **kwargs):
        env = {'JCODE_HOOK_EVENT': event, 'JCODE_HOOK_STATUS': status,
               'JCODE_HOOK_SESSION_ID': session, 'JCODE_HOOK_DURATION_MS': '95000', 'JCODE_HOOK_ERROR': kwargs.pop('error', 'secret-error')}
        return p.notify(self.home, env, self.render, kwargs.pop('deliver', self.deliver),
                        kwargs.pop('destination_fingerprint', 'dest-a'), now=now, **kwargs)

    def test_defaults_merge_presets(self):
        default = p.load_policy(self.home)
        self.assertEqual(default['preset'], 'balanced')
        self.assertEqual(default['cooldown_seconds'], 300)
        self.assertFalse(default['events']['session_start'])
        p.save_policy(self.home, {'preset': 'activity'})
        changed = p.save_policy(self.home, {'events': {'turn_start': False}})
        self.assertTrue(changed['events']['session_end'])
        self.assertFalse(changed['events']['turn_start'])
        self.assertEqual(changed, p.save_policy(self.home, {}))
        self.assertFalse((self.home / 'notifications/telegram-verbosity.json').exists())

    def test_silent_deltas_merge_inside_threaded_config_lock(self):
        p.save_policy(self.home, {'silent_events': []})
        barrier = threading.Barrier(2)
        def save(event):
            barrier.wait(timeout=15)
            return p.save_policy(self.home, {}, silent=[event])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(save, ['completion', 'error']))
        self.assertEqual(set(p.load_policy(self.home)['silent_events']), {'completion', 'error'})

    def test_silent_deltas_merge_across_processes(self):
        p.save_policy(self.home, {'silent_events': []})
        context = multiprocessing.get_context('spawn')
        barrier, queue = context.Barrier(2), context.Queue()
        workers = [context.Process(target=process_save_silent, args=(str(self.home), barrier, queue, event))
                   for event in ('completion', 'error')]
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=15) for _ in workers]
        for worker in workers:
            worker.join(timeout=15)
            self.assertEqual(worker.exitcode, 0)
        queue.close()
        queue.join_thread()
        self.assertEqual(results, ['saved', 'saved'])
        self.assertEqual(set(p.load_policy(self.home)['silent_events']), {'completion', 'error'})

    def test_silent_audible_deltas_validate_and_preserve_two_argument_api(self):
        p.save_policy(self.home, {'silent_events': ['session_start', 'error']})
        result = p.save_policy(self.home, {}, silent=['completion'], audible=['error'])
        self.assertEqual(result['silent_events'], ['session_start', 'completion'])
        self.assertEqual(result, p.save_policy(self.home, {}))
        self.assertEqual(result, p.save_policy(self.home, {}, silent=['completion'], audible=['error']))
        for kwargs in ({'silent': ['unknown']}, {'audible': ['unknown']}, {'silent': 'error'},
                       {'silent': [True]}, {'silent': ['error'], 'audible': ['error']},
                       {'silent': ['error', 'error']}, {'audible': None}):
            with self.assertRaises(ValueError):
                p.save_policy(self.home, {}, **kwargs)
        self.assertEqual(result, p.load_policy(self.home))

    def test_load_is_read_only_even_for_missing_home(self):
        self.assertEqual(p.load_policy(self.home)['preset'], 'balanced')
        self.assertEqual(list(self.home.iterdir()), [])
        missing = self.home / 'missing'
        self.assertEqual(p.load_policy(missing)['preset'], 'balanced')
        self.assertFalse(missing.exists())
        p.save_policy(missing, {})
        self.assertTrue((missing / 'notifications' / p.POLICY_FILE).is_file())

    def test_missing_policy_in_legacy_group_writable_directory(self):
        folder = self.home / 'notifications'
        folder.mkdir()
        folder.chmod(0o775)
        self.assertEqual(p.load_policy(self.home)['preset'], 'balanced')
        self.assertEqual(list(folder.iterdir()), [])
        self.assertEqual(folder.stat().st_mode & 0o777, 0o775)
        self.assertEqual(self.notify()['state'], 'invalid_policy')
        with self.assertRaises(ValueError):
            p.save_policy(self.home, {})
        (folder / p.POLICY_FILE).write_text('{}')
        with self.assertRaises(ValueError):
            p.load_policy(self.home)

    def test_invalid_settings(self):
        for change in ({'cooldown_seconds': True}, {'cooldown_seconds': -1}, {'version': 2},
                       {'events': {'unknown': True}}, {'include_sessions': 'all'}, {'wat': 1},
                       {'error_repeat_seconds': 10**20}):
            with self.assertRaises(ValueError):
                p.save_policy(self.home, change)
        folder = self.home / 'notifications'
        folder.mkdir(exist_ok=True)
        (folder / 'telegram-policy.json').write_text('{broken')
        self.assertEqual(self.notify()['state'], 'invalid_policy')
        self.assertEqual(self.renders, 0)

    def test_cooldown_grouped_session_scope(self):
        self.assertEqual(self.notify()['state'], 'sent')
        self.assertEqual(self.notify(now=1001)['state'], 'suppressed_cooldown')
        self.assertEqual(self.notify(now=1002, session='other')['state'], 'sent')
        result = self.notify(now=1301)
        self.assertEqual(result['grouped'], 1)
        self.assertIn('Grouped: 1 earlier completions.', self.calls[-1][1]['text'])
        self.assertEqual(self.renders, 3)

    def test_errors_and_repeat(self):
        self.notify()
        self.assertEqual(self.notify(now=1001, status='error')['state'], 'sent')
        self.assertEqual(self.notify(now=1002, status='error')['state'], 'suppressed_repeat_error')
        self.assertEqual(self.notify(now=1003, status='error', error='different')['state'], 'sent')
        self.assertEqual(self.notify(now=1302, status='error')['state'], 'sent')

    def test_unknown_and_filters(self):
        self.assertEqual(self.notify(event='crash')['state'], 'ignored')
        self.assertEqual(self.notify(status='cancelled')['state'], 'ignored')
        p.save_policy(self.home, {'include_sessions': ['other']})
        self.assertEqual(self.notify()['state'], 'disabled')
        self.assertEqual(self.renders, 0)

    def test_cards_destination_and_error(self):
        p.save_policy(self.home, {'status_card': True, 'cooldown_seconds': 0})
        self.assertEqual(self.notify()['state'], 'sent')
        self.assertTrue(self.calls[-1][1]['disable_notification'])
        self.assertEqual(self.notify(now=1001)['state'], 'edited')
        self.assertNotIn('disable_notification', self.calls[-1][1])
        self.assertEqual(self.notify(now=1002, destination_fingerprint='dest-b')['state'], 'sent')
        self.assertEqual(self.notify(now=1003, status='error', destination_fingerprint='dest-b')['state'], 'sent')
        self.assertEqual(self.calls[-2][0], 'sendMessage')
        self.assertNotIn('disable_notification', self.calls[-2][1])

    def test_card_completions_close_short_turns_without_push_cooldown(self):
        p.save_policy(self.home, {'preset': 'activity', 'status_card': True})
        self.assertEqual(self.notify(event='turn_start')['state'], 'sent')
        self.assertEqual(self.notify(now=1001)['state'], 'edited')
        self.assertEqual(self.notify(now=1002, event='turn_start')['state'], 'edited')
        env = {'JCODE_HOOK_EVENT': 'turn_end', 'JCODE_HOOK_STATUS': 'ok',
               'JCODE_HOOK_SESSION_ID': 'secret-session', 'JCODE_HOOK_DURATION_MS': '1000'}
        result = p.notify(self.home, env, self.render, self.deliver, 'dest-a', now=1003)
        self.assertEqual(result['state'], 'edited')
        self.assertEqual([method for method, body in self.calls],
                         ['sendMessage', 'editMessageText', 'editMessageText', 'editMessageText'])
        state = json.loads((self.home / 'notifications' / p.STATE_FILE).read_text())
        self.assertNotIn('completion', next(iter(state['sessions'].values())))
        p.save_policy(self.home, {'status_card': False})
        self.assertEqual(self.notify(now=1004)['state'], 'sent')
        self.assertEqual(self.notify(now=1005)['state'], 'suppressed_cooldown')

    def test_failure_does_not_advance(self):
        def fail(method, body):
            raise RuntimeError('PRIVATE TOKEN ERROR')
        self.assertEqual(self.notify(deliver=fail)['state'], 'delivery_failed')
        self.assertEqual(self.notify(now=1001)['state'], 'sent')
        self.assertEqual(self.notify(now=1400, deliver=lambda *a: {})['state'], 'delivery_failed')
        self.assertEqual(self.notify(now=1401)['state'], 'sent')

    def test_private_state_and_malformed(self):
        self.notify()
        paths = list((self.home / 'notifications').rglob('*'))
        for path in paths:
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                data = path.read_text()
                for secret in ('secret-session', 'secret-error', 'Done result', 'TOKEN'):
                    self.assertNotIn(secret, data)
        state = next(path for path in paths if path.suffix == '.json')
        state.write_text('{bad')
        self.assertEqual(self.notify(now=1400)['state'], 'invalid_policy')

    def test_symlink_rejected(self):
        folder = self.home / 'notifications'
        folder.mkdir()
        target = self.home / 'target'
        target.write_text('{}')
        (folder / 'telegram-policy.json').symlink_to(target)
        self.assertEqual(self.notify()['state'], 'invalid_policy')
        with self.assertRaises(ValueError):
            p.save_policy(self.home, {})

    def test_concurrent_real_locks(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _: self.notify(), range(24)))
        self.assertEqual(sum(r['state'] == 'sent' for r in results), 1)
        self.assertEqual(len(self.calls), 1)

    def test_profiles_grouping(self):
        for profile, limits in PROFILES.items():
            p.save_policy(self.home, {'cooldown_seconds': 300})
            render = lambda: {'text': 'word ' * 2000, 'entities': [], 'prompt_available': False}
            env = {'JCODE_HOOK_EVENT': 'turn_end', 'JCODE_HOOK_STATUS': 'ok', 'JCODE_HOOK_DURATION_MS': '95000', 'JCODE_HOOK_SESSION_ID': profile}
            for when in (1000, 1001, 1400):
                result = p.notify(self.home, env, render, self.deliver, 'dest', verbosity=profile, now=when)
            text = self.calls[-1][1]['text']
            self.assertLessEqual(len(text), limits['chars'])
            self.assertLessEqual(len(text.split()), limits['words'])
            self.assertIn('Grouped: 1 earlier completions.', text)

    def test_process_concurrency(self):
        context = multiprocessing.get_context('spawn')
        queue = context.Queue()
        workers = [context.Process(target=process_notify, args=(str(self.home), queue)) for _ in range(6)]
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=15) for _ in workers]
        for worker in workers:
            worker.join(timeout=15)
            self.assertEqual(worker.exitcode, 0)
        queue.close()
        queue.join_thread()
        self.assertEqual(results.count('sent'), 1)
        self.assertEqual((self.home / 'deliveries').read_text(), 'sent\n')

    def test_card_error_edit_failure_keeps_fresh_alert(self):
        p.save_policy(self.home, {'status_card': True})
        self.notify()
        def deliver(method, body):
            if method == 'editMessageText':
                raise RuntimeError('private error')
            return self.deliver(method, body)
        result = self.notify(now=1001, status='error', deliver=deliver)
        self.assertEqual(result['state'], 'sent')
        self.assertTrue(result['response_confirmed'])
        self.assertEqual(self.notify(now=1002, status='error')['state'], 'suppressed_repeat_error')

    def test_failed_card_edit_never_sends_fallback(self):
        p.save_policy(self.home, {'status_card': True, 'cooldown_seconds': 0})
        self.notify()
        calls = []
        def deliver(method, body):
            calls.append(method)
            raise RuntimeError('failure')
        self.assertEqual(self.notify(now=1001, deliver=deliver)['state'], 'delivery_failed')
        self.assertEqual(calls, ['editMessageText'])

    def test_lifecycle_and_attention_presets(self):
        p.save_policy(self.home, {'preset': 'activity'})
        for event in ('session_start', 'turn_start', 'session_end'):
            result = self.notify(event=event)
            self.assertEqual(result['kind'], event)
            self.assertEqual(result['state'], 'sent')
            self.assertTrue(self.calls[-1][1]['disable_notification'])
        p.save_policy(self.home, {'preset': 'attention'})
        self.assertEqual(self.notify()['state'], 'disabled')
        self.assertEqual(self.notify(status='error')['state'], 'sent')

    def test_duration_gate_and_error_bypass(self):
        env = {'JCODE_HOOK_EVENT': 'turn_end', 'JCODE_HOOK_STATUS': 'ok', 'JCODE_HOOK_SESSION_ID': 'short'}
        for value in ('0', '29999', 'bad', True):
            env['JCODE_HOOK_DURATION_MS'] = value
            self.assertEqual(p.notify(self.home, env, self.render, self.deliver, 'dest')['state'], 'ignored')
        env['JCODE_HOOK_STATUS'] = 'error'
        self.assertEqual(p.notify(self.home, env, self.render, self.deliver, 'dest')['state'], 'sent')

    def test_profile_entities_survive_clipping(self):
        env = {'JCODE_HOOK_EVENT': 'turn_end', 'JCODE_HOOK_STATUS': 'ok', 'JCODE_HOOK_SESSION_ID': 'entities'}
        message = {'text': '😀 Done ' + 'word ' * 100, 'entities': [
            {'type': 'bold', 'offset': 3, 'length': 4},
            {'type': 'bold', 'offset': 1, 'length': 1},
            {'type': 'bold', 'offset': True, 'length': 1},
            {'type': 'bold', 'offset': 500, 'length': 200},
        ]}
        result = p.notify(self.home, env, lambda: message, self.deliver, 'dest', verbosity='brief', min_seconds=0)
        self.assertEqual(result['state'], 'sent')
        self.assertEqual(self.calls[-1][1]['entities'], [{'type': 'bold', 'offset': 3, 'length': 4}])
        self.assertTrue(result['formatting_confirmed'])

    def test_config_json_limits_duplicate_keys_nonregular(self):
        folder = self.home / 'notifications'
        folder.mkdir()
        path = folder / p.POLICY_FILE
        for data in (' ' * 8193, '{"version":1,"version":1}', '{"cooldown_seconds":NaN}', '[]'):
            path.write_text(data)
            self.assertEqual(self.notify(policy=p.DEFAULT_POLICY)['state'], 'invalid_policy')
        path.unlink()
        os.mkfifo(path, 0o600)
        self.assertEqual(self.notify()['state'], 'invalid_policy')

    def test_malformed_state_fields_and_capacity(self):
        self.notify()
        path = self.home / 'notifications' / p.STATE_FILE
        original = json.loads(path.read_text())
        key = next(iter(original['sessions']))
        for entry in ({'completion': True}, {'grouped': -1}, {'card': {'destination': 'a'*64, 'message_id': True}},
                      {'card': {'destination': 'a'*64, 'message_id': -1}}, {'errors': {'raw secret': 1000}}, {'raw': 'private'}):
            path.write_text(json.dumps({'version': 1, 'sessions': {key: entry}}))
            self.assertEqual(self.notify(now=1500)['state'], 'invalid_policy')
        path.write_text(json.dumps({'version': 1, 'sessions': {f'{i:064x}': {} for i in range(p.MAX_SESSIONS)}}))
        self.assertEqual(self.notify(session='new-session')['state'], 'invalid_policy')
        self.assertEqual(len(self.calls), 1)

    def test_unsafe_state_and_directories(self):
        self.notify()
        path = self.home / 'notifications' / p.STATE_FILE
        path.chmod(0o644)
        self.assertEqual(self.notify(now=1400)['state'], 'invalid_policy')
        path.unlink()
        path.symlink_to(self.home / 'missing')
        self.assertEqual(self.notify(now=1400)['state'], 'invalid_policy')
        path.unlink()
        (self.home / 'notifications').chmod(0o777)
        self.assertEqual(self.notify()['state'], 'invalid_policy')

    def test_foreign_owned_settings_when_privileged(self):
        if os.getuid() != 0:
            self.skipTest('Changing file ownership requires root')
        p.save_policy(self.home, {})
        path = self.home / 'notifications' / p.POLICY_FILE
        os.chown(path, 65534, -1)
        self.assertEqual(self.notify()['state'], 'invalid_policy')

    def test_unchanged_answer_distinct_turn_is_sent_after_window(self):
        self.notify()
        self.assertEqual(self.notify(now=1300)['state'], 'sent')
        self.assertEqual(self.renders, 2)

    def test_inactive_state_expires_but_live_windows_survive(self):
        self.notify()
        path = self.home / 'notifications' / p.STATE_FILE
        path.write_text(json.dumps({'version': 1, 'sessions': {
            f'{i:064x}': {'last_seen': 1000, 'completion': 1000} for i in range(p.MAX_SESSIONS)}}))
        self.assertEqual(self.notify(now=1100, session='new')['state'], 'invalid_policy')
        p.save_policy(self.home, {'cooldown_seconds': 2 * p.STATE_TTL_SECONDS})
        self.assertEqual(self.notify(now=1001 + p.STATE_TTL_SECONDS, session='new')['state'], 'invalid_policy')
        self.assertEqual(self.notify(now=1001 + 2 * p.STATE_TTL_SECONDS, session='new')['state'], 'sent')
        self.assertEqual(len(json.loads(path.read_text())['sessions']), 1)

    def test_receipt_metadata_and_explicit_error_silence(self):
        p.save_policy(self.home, {'silent_events': ['error']})
        result = self.notify(status='error')
        self.assertTrue(self.calls[-1][1]['disable_notification'])
        self.assertEqual(result['telegram_message_id'], 1)
        self.assertEqual(result['method'], 'sendMessage')
        self.assertTrue(result['prompt_available'])
        self.assertTrue(result['formatting_confirmed'])

    def test_home_and_notifications_symlinks_rejected(self):
        alias = self.home / 'alias'
        alias.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError):
            p.load_policy(alias)
        target = self.home / 'elsewhere'
        target.mkdir()
        (self.home / 'notifications').symlink_to(target, target_is_directory=True)
        self.assertEqual(self.notify()['state'], 'invalid_policy')

    def test_grouped_count_survives_failed_send(self):
        self.notify()
        self.notify(now=1001)
        self.assertEqual(self.notify(now=1400, deliver=lambda *args: {})['state'], 'delivery_failed')
        result = self.notify(now=1401)
        self.assertEqual(result['state'], 'sent')
        self.assertEqual(result['grouped'], 1)


if __name__ == '__main__':
    unittest.main()
