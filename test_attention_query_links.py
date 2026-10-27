"""End-to-end explicit attention query links with an offline confirming transport."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import alert_attention as attention
import alert_format as formatting
import alert_links
from test_action_links import OMNI_URL, OAUTH_URL, fixture_jwt


class AttentionQueryLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.environment = {'JCODE_SESSION_ID': 'session_action_fixture',
                            'JCODE_HOOK_CWD': 'fixture-project'}
        self.request = {'context': 'Owner access is required.',
                        'needs_you': 'Complete the synthetic access step 🐝.',
                        'links': [{'label': 'Open access', 'url': OMNI_URL}]}
        self.deliveries = []

    def deliver(self, method, body):
        self.deliveries.append((method, copy.deepcopy(body)))
        return {'message_id': 100 + len(self.deliveries), **copy.deepcopy(body)}

    def publish(self, **options):
        return attention.publish(self.home, self.environment, self.request,
                                 'fixture:access:revision1', self.deliver, 'a' * 64, **options)

    def assert_link(self, message, url):
        entities = [entity for entity in message['entities'] if entity['type'] == 'text_link']
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['url'], url)
        raw = message['text'].encode('utf-16-le')
        entity = entities[0]
        label = raw[entity['offset'] * 2:(entity['offset'] + entity['length']) * 2].decode('utf-16-le')
        self.assertEqual(label, 'Open access · ' + url.split('/')[2])
        self.assertEqual(message['link_preview_options'], {'is_disabled': True})
        self.assertNotIn(url, message['text'])
        self.assertTrue(formatting.formatting_confirmed(message, copy.deepcopy(message)))

    def test_render_preserves_exact_query_and_entity_ranges(self):
        for url in (OMNI_URL, OAUTH_URL):
            with self.subTest(url=url):
                self.request['links'][0]['url'] = url
                message = attention.render(self.request, self.environment, self.home)
                self.assert_link(message, url)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_publish_confirms_exact_oauth_entity_and_disables_previews(self):
        self.request['links'][0]['url'] = OAUTH_URL
        self.assertEqual(self.publish()['state'], 'sent')
        method, body = self.deliveries[0]
        self.assertEqual(method, 'sendMessage')
        self.assertIs(body['disable_notification'], False)
        self.assert_link(body, OAUTH_URL)

    def test_dedup_and_resend_store_only_non_sensitive_fingerprints(self):
        self.request['links'][0]['url'] = OAUTH_URL
        self.assertEqual(self.publish()['state'], 'sent')
        self.assertEqual(self.publish()['state'], 'already_sent')
        self.assertEqual(len(self.deliveries), 1)
        self.assertEqual(self.publish(resend=True)['state'], 'sent')
        self.assertEqual(len(self.deliveries), 2)
        path = self.home / 'notifications' / attention.STATE_FILE
        stored = path.read_text()
        state = json.loads(stored)
        self.assertEqual(set(state), {'version', 'requests'})
        self.assertEqual(len(state['requests']), 1)
        for key, entry in state['requests'].items():
            self.assertRegex(key, r'^[a-f0-9]{64}$')
            self.assertEqual(set(entry), {'at', 'message_id'})
        for value in (OAUTH_URL, 'final%2fValue', 'synthetic-nonce', 'fixture-cli',
                      self.request['context'], self.environment['JCODE_SESSION_ID'], 'revision1'):
            self.assertNotIn(value, stored)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejected_queries_never_reach_transport_or_dedup_state(self):
        bad = ('https://actions.example.org/review?access%5Ftoken=fixture',
               'https://actions.example.org/review?state=one&STATE=two',
               'https://actions.example.org/review?state=%0a',
               'https://actions.example.org/review?state=%GG',
               OMNI_URL + '#fragment',
               'https://actions.example.org/token?state=fixture')
        for url in bad:
            with self.subTest(url=url):
                self.request['links'][0]['url'] = url
                with self.assertRaises(attention.AttentionError):
                    self.publish()
                self.assertEqual(self.deliveries, [])
                self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_configured_secret_rejects_decoded_query_before_transport(self):
        self.request['links'][0]['url'] = 'https://actions.example.org/review?state=%53yntheticSecret'
        with self.assertRaises(attention.AttentionError) as caught:
            self.publish(secrets=('SyntheticSecret',))
        self.assertNotIn('SyntheticSecret', str(caught.exception))
        self.assertEqual(self.deliveries, [])
        self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_nested_sensitive_values_rejected_before_transport_or_state(self):
        cases = (('state=%2553yntheticSecret', ('SyntheticSecret',)),
                 ('state=%250a', ()), ('state=%2500', ()),
                 ('state=access_token%253Dfixture', ()),
                 ('state=Bearer%2520fixture-credential', ()),
                 ('state=' + fixture_jwt(), ()),
                 ('redirect_uri=https%3A%2F%2Ffixture-user%3Afixture-password%40service.example.org%2Freturn', ()),
                 ('redirect_uri=https%253A%252F%252Ffixture-user%2540service.example.org%252Freturn', ()))
        for query, secrets in cases:
            with self.subTest(query=query):
                self.request['links'][0]['url'] = 'https://actions.example.org/review?' + query
                with self.assertRaises(attention.AttentionError) as caught:
                    self.publish(secrets=secrets)
                self.assertNotIn('fixture-password', str(caught.exception))
                self.assertNotIn('SyntheticSecret', str(caught.exception))
                self.assertEqual(self.deliveries, [])
                self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_unconfirmed_changed_state_entity_cannot_mark_sent(self):
        self.request['links'][0]['url'] = OAUTH_URL

        def changed(method, body):
            response = self.deliver(method, body)
            for entity in response['entities']:
                if entity['type'] == 'text_link':
                    entity['url'] = entity['url'].replace('state=final', 'state=changed')
            return response

        with self.assertRaises(attention.AttentionError):
            attention.publish(self.home, self.environment, self.request, 'fixture:access:revision1',
                              changed, 'a' * 64)
        self.assertEqual(len(self.deliveries), 1)
        self.assertFalse((self.home / 'notifications' / attention.STATE_FILE).exists())

    def test_explicit_acceptance_does_not_enable_routine_extraction(self):
        self.assert_link(attention.render(self.request, self.environment, self.home), OMNI_URL)
        self.assertIsNone(alert_links.safe_url(OMNI_URL))
        self.assertEqual(alert_links.extract_links('Access: ' + OMNI_URL), [])


if __name__ == '__main__':
    unittest.main()
