"""Explicit action URLs preserve signed-in flow bytes without widening routine links."""
import base64
import json
import unittest

import alert_links


OMNI_URL = ('https://access.example.org/authenticate?flow=cli&public-key-id='
            + '0123456789abcdef' * 4)
OAUTH_URL = ('https://identity.example.org/oidc/authorize?client_id=fixture-cli'
             '&response_type=code&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob'
             '&scope=openid+profile&nonce=synthetic-nonce'
             '&code_challenge=synthetic_challenge_0123456789abcdef'
             '&code_challenge_method=S256&state=final%2fValue%2Fwith+space%20end')


def fixture_jwt():
    def encode(value):
        data = json.dumps(value, separators=(',', ':')).encode()
        return base64.urlsafe_b64encode(data).decode().rstrip('=')

    return '.'.join((encode({'alg': 'none'}), encode({'sub': 'fixture'}),
                     'fixture_signature'))


class ActionLinkTests(unittest.TestCase):
    def check_url(self, value, secrets=()):
        return alert_links.safe_action_url(value, secrets=secrets)

    def test_supported_flows_preserve_every_query_byte(self):
        for url in (OMNI_URL, OAUTH_URL,
                    'https://actions.example.org/review?z=last&a=%2f%2F&title=a+b%20c&state=tail'):
            with self.subTest(url=url):
                self.assertEqual(self.check_url(url), url)

    def test_no_query_retains_existing_origin_canonicalization(self):
        for url in ('https://actions.example.org/review',
                    'HTTPS://Actions.Example.ORG:443/review'):
            self.assertEqual(self.check_url(url), alert_links.safe_url(url))

    def test_query_does_not_widen_routine_policy(self):
        for url in (OMNI_URL, OAUTH_URL, 'https://actions.example.org/review?state=ok'):
            self.assertIsNone(alert_links.safe_url(url))
            self.assertEqual(alert_links.extract_links(url), [])
        plain = 'https://actions.example.org/review'
        self.assertEqual(alert_links.safe_url(plain), plain)
        self.assertEqual(alert_links.extract_links(plain)[0]['url'], plain)

    def test_credential_names_are_rejected_even_when_obfuscated(self):
        names = ('token', 'access_token', 'refresh_token', 'id_token', 'client_secret',
                 'password', 'passwd', 'api_key', 'authorization', 'code',
                 'code_verifier', 'signature', 'ACCESS_TOKEN', 'Access-Token',
                 'accessToken', 'client.secret', 'api-key', '%74oken',
                 'access%5ftoken', '%63ode', 'CODE-VERIFIER')
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(self.check_url('https://actions.example.org/review?' + name + '=fixture'))

    def test_duplicate_normalized_names_rejected(self):
        for query in ('state=a&state=b', 'state=a&STATE=b',
                      'state=a&%73tate=b', 'client_id=a&client-id=b',
                      'client_id=a&clientId=b'):
            with self.subTest(query=query):
                self.assertIsNone(self.check_url('https://actions.example.org/review?' + query))

    def test_raw_and_decoded_configured_secrets_rejected(self):
        for value in ('SyntheticSecret', 'syntheticsecret', '%53yntheticSecret',
                      'Synthetic%53ecret'):
            with self.subTest(value=value):
                self.assertIsNone(self.check_url('https://actions.example.org/review?state=' + value,
                                                ('SyntheticSecret',)))
        self.assertIsNone(self.check_url(OMNI_URL, ('0123456789abcdef',)))

    def test_malformed_escapes_controls_and_unicode_hazards_rejected(self):
        for value in ('%', '%0', '%GG', '%2g', '%00', '%09', '%0a', '%0D', '%7f',
                      '%E2%80%AE', '%E2%80%8B', '%EF%BB%BF', '\u202e', '\u200b',
                      '\ufeff', '\n', '\r', '\t', ' ', '\\bad'):
            with self.subTest(value=repr(value)):
                self.assertIsNone(self.check_url('https://actions.example.org/review?state=' + value))

    def test_origin_path_and_fragment_restrictions_are_not_bypassed(self):
        bases = ('http://actions.example.org/review', 'https://user:pass@actions.example.org/review',
                 'https://actions.example.org:8443/review', 'https://127.0.0.1/review',
                 'https://[::1]/review', 'https://2130706433/review',
                 'https://localhost/review', 'https://actions.local/review',
                 'https://actions.example.org/token', 'https://actions.example.org/auth/callback',
                 'https://actions.example.org/a%2fb', 'https://actions.example.org/a\\b')
        for base in bases:
            with self.subTest(base=base):
                self.assertIsNone(self.check_url(base + '?state=fixture'))
        for suffix in ('#', '#fragment'):
            self.assertIsNone(self.check_url(OMNI_URL + suffix))

    def test_action_length_and_field_bounds(self):
        prefix = 'https://actions.example.org/review?state='
        at_limit = prefix + 'a' * (2048 - len(prefix))
        self.assertEqual(self.check_url(at_limit), at_limit)
        self.assertIsNone(self.check_url(at_limit + 'a'))
        prefix = 'https://actions.example.org/review?'
        fields = ['field' + str(n) + '=x' for n in range(65)]
        accepted = prefix + '&'.join(fields[:64])
        self.assertEqual(self.check_url(accepted), accepted)
        self.assertIsNone(self.check_url(prefix + '&'.join(fields)))

    def test_double_encoded_known_secrets_and_controls_rejected(self):
        for value, secrets in (('%2553yntheticSecret', ('SyntheticSecret',)),
                               ('%2573yntheticsecret', ('SyntheticSecret',)),
                               ('%2500', ()), ('%250a', ()), ('%250D', ()),
                               ('%2509', ()), ('%257f', ()),
                               ('%25E2%2580%25AE', ())):
            with self.subTest(value=value):
                self.assertIsNone(self.check_url('https://actions.example.org/review?state=' + value,
                                                secrets))

    def test_nested_credential_assignments_rejected(self):
        values = ('token%3Dfixture', 'access_token%3Dfixture',
                  'client-secret%253Dfixture',
                  'https%3A%2F%2Fservice.example.org%2Freturn%3Fpassword%3Dfixture',
                  'mode%3Dok%26api_key%3Dfixture',
                  'mode%253Dok%253Bcode_verifier%253Dfixture')
        for value in values:
            with self.subTest(value=value):
                self.assertIsNone(self.check_url('https://actions.example.org/review?state=' + value))

    def test_jwt_and_bearer_values_rejected_without_sensitive_parameter_name(self):
        jwt = fixture_jwt()
        for value in (jwt, 'Bearer+fixture-credential', 'bEaReR%20fixture-credential',
                      'Bearer%2520fixture-credential'):
            with self.subTest(value=value):
                self.assertIsNone(self.check_url('https://actions.example.org/review?state=' + value))

    def test_nested_redirect_url_userinfo_rejected(self):
        from urllib.parse import quote

        for scheme in ('https', 'http', 'wss', 'ws'):
            for userinfo in ('fixture-user@', 'fixture-user:fixture-password@'):
                nested = scheme + '://' + userinfo + 'service.example.org/return'
                for value in (nested, quote(nested, safe=''), quote(quote(nested, safe=''), safe='')):
                    with self.subTest(value=value):
                        self.assertIsNone(self.check_url('https://actions.example.org/review?redirect_uri=' + value))
        ordinary = ('https://actions.example.org/review?redirect_uri='
                    'https%3A%2F%2Fservice.example.org%2Freturn&state=fixture')
        self.assertEqual(self.check_url(ordinary), ordinary)

    def test_non_string_inputs_rejected(self):
        for value in (None, False, 42, [], {}, b'https://actions.example.org/review'):
            with self.subTest(value=value):
                self.assertIsNone(self.check_url(value))


if __name__ == '__main__':
    unittest.main()
