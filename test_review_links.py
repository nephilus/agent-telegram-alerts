"""Offline adversarial tests for the attention-only review exception."""
import contextlib
import copy
from concurrent.futures import ThreadPoolExecutor
import fcntl
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import alert_attention as attention
import alert_links
import alert_policy as policy
import telegram_alerts as app


class ReviewLinksTests(unittest.TestCase):
    host = 'device.tailnet.ts.net'
    port = 19433

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.env = {}
        self.url = f'https://{self.host}:{self.port}/'
        self.request = {'context': 'Review context', 'needs_you': 'Review this document',
                        'links': [{'label': 'Review', 'url': self.url}]}

    def configure(self):
        attention.review_host(self.home, self.host, write=True)

    def render(self, **kwargs):
        return attention.render(self.request, self.env, self.home, review_port=self.port, **kwargs)

    def reject(self):
        with patch.object(policy, 'load_policy', side_effect=AssertionError('state boundary')), \
                patch.object(policy, '_locked', side_effect=AssertionError('state boundary')):
            with self.assertRaises(attention.AttentionError) as error:
                attention.publish(self.home, self.env, self.request, 'review',
                                  lambda *_: self.fail('transport called'), 'a' * 64,
                                  review_port=self.port)
        self.assertNotIn(self.host, str(error.exception))
        self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_default_query_is_disabled_and_read_only(self):
        self.assertEqual(attention.review_host(self.home), {'version': 1, 'host': None})
        self.assertEqual(list(self.home.iterdir()), [])
        self.reject()
        self.assertEqual(list(self.home.iterdir()), [])

    def test_exact_review_links_render_host_port_and_github(self):
        self.configure()
        for path in ('', '/'):
            self.request['links'][0]['url'] = self.url.rstrip('/') + path
            self.request['links'] = self.request['links'][:1] + [
                {'label': 'PR', 'url': 'https://github.com/org/repo/pull/1'}]
            body = self.render()
            self.assertIn(self.host + ':' + str(self.port), body['text'])
            self.assertEqual([e['url'] for e in body['entities'] if e['type'] == 'text_link'],
                             [self.url, 'https://github.com/org/repo/pull/1'])
        for port in (1024, 65535):
            self.port = port
            self.request['links'][0]['url'] = f'https://{self.host}:{port}'
            self.render()

    def test_slashless_and_root_review_urls_render_identically(self):
        self.configure()
        root = self.render()
        self.request['links'][0]['url'] = self.url.rstrip('/')
        self.assertEqual(self.render(), root)

    def test_simulated_telegram_root_normalization_confirms_both_inputs(self):
        self.configure()
        sent_urls = []

        def deliver(method, body):
            response = {'message_id': 1, **copy.deepcopy(body)}
            for entity in response['entities']:
                if entity['type'] == 'text_link':
                    sent_urls.append(entity['url'])
                    entity['url'] = entity['url'].rstrip('/') + '/'
            return response

        for suffix in ('', '/'):
            self.request['links'][0]['url'] = self.url.rstrip('/') + suffix
            result = attention.publish(self.home, self.env, self.request,
                                       'review' + suffix, deliver, 'a' * 64,
                                       review_port=self.port)
            self.assertEqual(result['state'], 'sent')
            self.assertTrue(result['formatting_confirmed'])
        self.assertEqual(sent_urls, [self.url, self.url])

    def test_changed_telegram_host_port_or_path_is_not_confirmed(self):
        self.configure()
        for changed in (self.url.replace(self.host, 'other.tailnet.ts.net'),
                        self.url.replace(':19433', ':19434'), self.url + 'changed',
                        self.url.rstrip('/')):
            def deliver(method, body):
                response = {'message_id': 1, **copy.deepcopy(body)}
                for entity in response['entities']:
                    if entity['type'] == 'text_link':
                        entity['url'] = changed
                return response

            with self.subTest(changed=changed), self.assertRaisesRegex(
                    attention.AttentionError, 'not confirmed'):
                attention.publish(self.home, self.env, self.request, 'review',
                                  deliver, 'a' * 64, review_port=self.port)
            self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_canonical_only_port_slash_secret_rejects_before_transport_or_state(self):
        self.configure()
        self.port = 43929
        raw = f'https://{self.host}:{self.port}'
        secret = ':43929/'
        self.assertNotIn(secret, raw)
        self.request['links'][0]['url'] = raw
        for value in (raw, raw + '/'):
            self.request['links'][0]['url'] = value
            with self.subTest(value=value), \
                    patch.object(policy, '_locked', side_effect=AssertionError('lock called')), \
                    self.assertRaises(attention.AttentionError):
                attention.publish(self.home, self.env, self.request, 'review',
                                  lambda *_: self.fail('transport called'), 'a' * 64,
                                  review_port=self.port, secrets=(secret,))
        self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_routine_policy_and_undeclared_attention_stay_strict(self):
        self.configure()
        self.assertIsNone(alert_links.safe_url(self.url))
        self.assertEqual(alert_links.extract_links(self.url), [])
        with self.assertRaises(attention.AttentionError):
            attention.render(self.request, self.env, self.home)
        self.request.pop('links')
        attention.render(self.request, self.env, self.home)
        self.reject()

    def test_raw_hostile_urls_and_spoofed_authorities(self):
        self.configure()
        bad = [None, True, 123, [], '', self.url + 'x' * 513,
               self.url.replace('https:', 'http:'), self.url.replace('https:', 'HTTPS:'),
               self.url.replace(self.host, 'sub.' + self.host),
               self.url.replace(self.host, self.host + '.evil.org'),
               self.url.replace(self.host, self.host.upper()),
               self.url.replace(self.host, 'other.tailnet.ts.net'),
               self.url.replace(self.host, self.host + '.'),
               self.url.replace(self.host, 'user@' + self.host),
               self.url.replace(self.host, 'user:password@' + self.host),
               self.url.replace(':19433', ':19434'), self.url.replace(':19433', ':019433'),
               self.url.replace(':19433', ':443'), self.url.replace(':19433', ''),
               self.url.replace(':19433', ':19433:19433')]
        bad += [self.url + suffix for suffix in ('?', '#', '?x=y', '#x', '%2f', '.', '..',
                                                  '/path', '\\', '\n', '\r', '\t', '\x00',
                                                  '\x7f', '\u200b', 'é', ' ', '"', "'", '<', '>')]
        bad += ['\n' + self.url, ' ' + self.url, self.url.replace('/', '/%2f', 1)]
        for url in bad:
            with self.subTest(url=repr(url)):
                self.request['links'][0]['url'] = url
                self.reject()

    def test_original_port_and_host_secret_checks(self):
        self.configure()
        for secret in ('19433', ':19433/', 'TAILNET', self.url):
            with self.subTest(secret=secret), self.assertRaises(attention.AttentionError):
                self.render(secrets=(secret,))
        self.host = 'ghp_abcdefghijk.tailnet.ts.net'
        self.assertFalse(attention._review_host(self.host))

    def test_validator_never_resolves_hosts_or_starts_processes(self):
        self.configure()
        with patch('socket.getaddrinfo', side_effect=AssertionError('DNS called')), \
                patch('socket.socket', side_effect=AssertionError('network called')), \
                patch('subprocess.Popen', side_effect=AssertionError('process called')):
            self.render()

    def test_review_publish_rereads_trust_after_waiting_for_lock(self):
        self.configure()
        validated, release = threading.Event(), threading.Event()
        original = attention.render

        def render(*args, **kwargs):
            result = original(*args, **kwargs)
            if not validated.is_set():
                validated.set()
                if not release.wait(5):
                    raise AssertionError('test release timed out')
            return result

        with patch.object(attention, 'render', side_effect=render), \
                patch.object(policy, 'load_policy', side_effect=AssertionError('state touched')), \
                ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(attention.publish, self.home, self.env, self.request,
                                 'review', lambda *_: self.fail('transport called'),
                                 'a' * 64, review_port=self.port)
            try:
                self.assertTrue(validated.wait(5))
                attention.review_host(self.home, None, write=True)
            finally:
                release.set()
            with self.assertRaises(attention.AttentionError):
                future.result(timeout=5)
        self.assertIsNone(attention.review_host(self.home)['host'])
        self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_review_publish_holds_trust_lock_through_transport(self):
        self.configure()
        delivering, release, revoking = threading.Event(), threading.Event(), threading.Event()
        order = []

        def deliver(method, body):
            delivering.set()
            if not release.wait(5):
                raise AssertionError('test release timed out')
            self.assertEqual(attention.review_host(self.home)['host'], self.host)
            order.append('sent')
            return {'message_id': 1, **body}

        def revoke():
            revoking.set()
            attention.review_host(self.home, None, write=True)
            order.append('revoked')

        with ThreadPoolExecutor(max_workers=2) as pool:
            sent = pool.submit(attention.publish, self.home, self.env, self.request,
                               'review', deliver, 'a' * 64, review_port=self.port)
            try:
                self.assertTrue(delivering.wait(5))
                # A kernel-level probe, not timing/sleep, proves the same lock
                # used by review-host writes is held during the transport call.
                with (self.home / 'notifications' / '.telegram-review.lock').open('r+') as lock:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                revoked = pool.submit(revoke)
                self.assertTrue(revoking.wait(5))
            finally:
                release.set()
            self.assertEqual(sent.result(timeout=5)['state'], 'sent')
            revoked.result(timeout=5)
        self.assertEqual(order, ['sent', 'revoked'])
        self.assertIsNone(attention.review_host(self.home)['host'])

    def test_double_render_preserves_generator_secret_redaction(self):
        self.configure()
        self.request['context'] = 'A PRIVATE_CANARY needs review'
        messages = []

        def deliver(method, body):
            messages.append(body)
            return {'message_id': 1, **body}

        attention.publish(self.home, self.env, self.request, 'review', deliver, 'a' * 64,
                          review_port=self.port, secrets=(s for s in ('PRIVATE_CANARY',)))
        self.assertNotIn('PRIVATE_CANARY', messages[0]['text'])
        self.assertIn('[redacted]', messages[0]['text'])

    def test_invalid_publish_options_reject_before_review_lock_or_render(self):
        self.configure()
        lock = self.home / 'notifications' / '.telegram-review.lock'
        lock.unlink()
        for changes in ({'key': ''}, {'key': 'invalid key'},
                        {'destination_fingerprint': 'bad'}, {'resend': 1}):
            options = {'home': self.home, 'environment': self.env, 'request': self.request,
                       'key': 'review', 'deliver': lambda *_: self.fail('transport called'),
                       'destination_fingerprint': 'a' * 64, 'review_port': self.port, **changes}
            with self.subTest(changes=changes), \
                    patch.object(attention, 'render', side_effect=AssertionError('render called')), \
                    patch.object(policy, '_locked', side_effect=AssertionError('lock called')):
                with self.assertRaises(attention.AttentionError):
                    attention.publish(**options)
            self.assertFalse(lock.exists())

    def test_directory_symlinks_and_foreign_owner_fail_closed(self):
        self.configure()
        folder = self.home / 'notifications'
        moved = self.home / 'moved'
        folder.rename(moved)
        folder.symlink_to(moved, target_is_directory=True)
        self.reject()
        folder.unlink()
        moved.rename(folder)
        uid = os.getuid()
        with patch.object(policy.os, 'getuid', return_value=uid + 1):
            self.reject()

    def test_attention_cli_passes_declared_port_without_mutating_other_config(self):
        self.configure()
        native = self.home / 'config.toml'
        original = ('[safety]\ntelegram_enabled=true\ntelegram_bot_token="fixture-token"\n'
                    'telegram_chat_id="fixture-chat"\ntelegram_reply_enabled=true\n')
        native.write_text(original)
        policy.save_policy(self.home, {'preset': 'activity'})
        routine = self.home / 'notifications' / policy.POLICY_FILE
        saved = routine.read_bytes()
        calls = []

        def deliver(token, method, body):
            calls.append((method, body))
            return {'message_id': 1, **body}

        with patch.dict(os.environ, {'TELEGRAM_ALERTS_HOME': str(self.home), **self.env}), \
                patch.object(sys, 'argv', ['telegram-alerts', 'attention', '--key', 'review',
                                          '--review-port', str(self.port)]), \
                patch.object(sys, 'stdin', io.StringIO(json.dumps(self.request))), \
                patch.object(app, 'api', side_effect=deliver), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(app.cli(), 0)
        self.assertEqual(json.loads(output.getvalue())['state'], 'sent')
        self.assertEqual(len(calls), 1)
        self.assertIn(self.host + ':' + str(self.port), calls[0][1]['text'])
        self.assertEqual(native.read_text(), original)
        self.assertEqual(routine.read_bytes(), saved)

    def test_matching_link_is_required_even_with_valid_other_links(self):
        self.configure()
        for links in ([], [{'label': 'PR', 'url': 'https://github.com/org/repo/pull/1'}]):
            self.request['links'] = links
            self.reject()

    def test_api_rejects_bool_and_non_integer_ports(self):
        self.configure()
        for port in (False, True, 0, 443, 1023, 65536, '19433', 19433.0, [], {}):
            with self.subTest(port=port), self.assertRaises(attention.AttentionError):
                attention.render(self.request, self.env, self.home, review_port=port)

    def test_invalid_hosts_never_create_configuration(self):
        for host in (True, 123, '', 'ts.net', 'tailnet.ts.net', 'Device.tailnet.ts.net',
                     'https://device.tailnet.ts.net', 'device.tailnet.ts.net:443',
                     '*.tailnet.ts.net', 'device..tailnet.ts.net', '-d.tailnet.ts.net',
                     'a' * 64 + '.tailnet.ts.net', 'd.t.ts.net.', 'd.t.ts.net/',
                     'evil.org/a.tailnet.ts.net', 'd.é.ts.net', 'd.t.ts.net\n'):
            with self.subTest(host=host), self.assertRaises(attention.AttentionError):
                attention.review_host(self.home, host, write=True)
            self.assertEqual(list(self.home.iterdir()), [])

    def test_malformed_configuration_fails_closed(self):
        self.configure()
        target = self.home / 'notifications' / attention.REVIEW_FILE
        for raw in ('{}', '[]', '{"version":true,"host":null}',
                    '{"version":1,"host":true}', '{"version":1,"host":null,"extra":1}',
                    '{"version":1,"host":null,"host":null}',
                    '{"version":1,"host":"PRIVATE_VALUE"}', '{"version":NaN,"host":null}',
                    '[' * 1100, 'x' * 1025):
            target.write_text(raw)
            with self.subTest(raw=raw[:50]):
                self.reject()
                with self.assertRaises(attention.AttentionError):
                    attention.review_host(self.home)

    def test_unsafe_files_and_directory_are_rejected_without_overwrite(self):
        self.configure()
        folder = self.home / 'notifications'
        target = folder / attention.REVIEW_FILE
        original = target.read_bytes()
        target.chmod(0o644)
        for operation in (lambda: attention.review_host(self.home),
                          lambda: attention.review_host(self.home, None, write=True)):
            with self.assertRaises(attention.AttentionError):
                operation()
        self.reject()
        target.chmod(0o600)
        target.unlink()
        other = self.home / 'other'
        other.write_bytes(original)
        other.chmod(0o600)
        for hazard in ('symlink', 'hardlink', 'fifo', 'directory'):
            if hazard == 'symlink':
                target.symlink_to(other)
            elif hazard == 'hardlink':
                os.link(other, target)
            elif hazard == 'fifo':
                os.mkfifo(target, 0o600)
            else:
                target.mkdir()
            with self.subTest(hazard=hazard):
                self.reject()
                with self.assertRaises(attention.AttentionError):
                    attention.review_host(self.home, None, write=True)
                self.assertEqual(other.read_bytes(), original)
            if hazard == 'directory':
                target.rmdir()
            else:
                target.unlink()
        target.write_bytes(original)
        target.chmod(0o600)
        folder.chmod(0o777)
        self.reject()
        with self.assertRaises(attention.AttentionError):
            attention.review_host(self.home)

    def cli(self, *args):
        with patch.dict(os.environ, {'TELEGRAM_ALERTS_HOME': str(self.home)}), \
                patch.object(sys, 'argv', ['telegram-alerts', *args]), \
                patch.object(app, 'api', side_effect=AssertionError('network called')), \
                patch.object(app, 'credentials', side_effect=AssertionError('credentials read')), \
                contextlib.redirect_stdout(io.StringIO()) as output, \
                contextlib.redirect_stderr(io.StringIO()):
            code = app.cli()
        return code, output.getvalue()

    def test_cli_query_set_disable_are_private_no_send_and_preserve_config(self):
        self.assertEqual(json.loads(self.cli('review-host')[1])['host'], None)
        self.assertEqual(list(self.home.iterdir()), [])
        config = self.home / 'config.toml'
        config.write_text('private native config sentinel')
        policy.save_policy(self.home, {'preset': 'activity'})
        routine = self.home / 'notifications' / policy.POLICY_FILE
        original = routine.read_bytes()
        self.assertEqual(self.cli('review-host', self.host)[0], 0)
        target = routine.with_name(attention.REVIEW_FILE)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.parent.iterdir()}
        self.assertEqual(json.loads(self.cli('review-host')[1])['host'], self.host)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.parent.iterdir()})
        self.assertEqual(json.loads(self.cli('review-host', 'off')[1])['host'], None)
        self.assertEqual(config.read_text(), 'private native config sentinel')
        self.assertEqual(routine.read_bytes(), original)
        self.reject()

    def test_cli_malformed_existing_schema_is_not_overwritten(self):
        self.configure()
        target = self.home / 'notifications' / attention.REVIEW_FILE
        for raw in ('{}', '[]', '{"version":true,"host":null}',
                    '{"version":1,"host":true}', '{"version":2,"host":null}',
                    '{"version":1}', '{"version":1,"host":"PRIVATE_CANARY"}',
                    '{"version":1,"host":null,"extra":1}'):
            target.write_text(raw)
            original = (target.read_bytes(), target.stat().st_mtime_ns, target.stat().st_ino)
            for value in (None, self.host, 'off'):
                with self.subTest(raw=raw, value=value):
                    args = ('review-host',) if value is None else ('review-host', value)
                    code, output = self.cli(*args)
                    self.assertEqual((code, output), (1, ''))
                    self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns,
                                      target.stat().st_ino), original)
        self.assertFalse(target.with_name(attention.STATE_FILE).exists())

    def test_wrong_cli_flags_are_rejected_before_side_effects(self):
        for args in (('policy', '--review-port', '19433'), ('preview', '--review-port', '19433'),
                     ('review-host', '--review-port', '19433'), ('review-host', '--key', 'key'),
                     ('review-host', '--resend'), ('review-host', '--enable', 'error'),
                     ('review-host', '--event', 'error'), ('review-host', '--session', 'session_x'),
                     ('review-host', '--session', ''),
                     ('attention', '--key', 'key', '--session', ''),
                     ('review-host', '--verbosity', 'brief'), ('review-host', '--min-seconds=30'),
                     ('review-host', '--min', '30'),
                     ('attention', '--key', 'key', '--review-port', 'true'),
                     ('attention', '--key', 'key', '--review-port', '65536')):
            with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                self.cli(*args)
            self.assertEqual(error.exception.code, 2)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_invalid_cli_port_diagnostic_does_not_echo_input(self):
        with patch.object(sys, 'argv', ['telegram-alerts', 'attention', '--key', 'review',
                                      '--review-port', 'PRIVATE_CANARY']), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                app.cli()
        self.assertNotIn('PRIVATE_CANARY', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
