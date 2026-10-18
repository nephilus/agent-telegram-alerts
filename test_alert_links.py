"""Offline adversarial checks for the alert link policy."""

import unittest

from alert_links import extract_links, safe_url


class AlertLinksTests(unittest.TestCase):
    def test_canonical(self):
        self.assertEqual(safe_url('HTTPS://GitHub.COM:443/o/r/pull/1'),
                         'https://github.com/o/r/pull/1')
        self.assertEqual(safe_url('https://docs.python.org'), 'https://docs.python.org')

    def test_reject_policy(self):
        bad = [
            'http://github.com/a', 'https://u:p@github.com/a',
            'https://github.com:80/a', 'https://github.com:0443/a',
            'https://127.0.0.1/a', 'https://2130706433/a',
            'https://[::1]/a', 'https://localhost/a', 'https://x.localhost/a',
            'https://123.com/a', 'https://a.123/a', 'https://a.c/a',
            'https://-bad.com/a', 'https://bad-.com/a', 'https://a..com/a',
            'https://a_b.com/a', 'https://github.com./a',
            'https://github.com/a?', 'https://github.com/a#',
            'https://github.com/a?token=bad', 'https://github.com/a%2fb',
            'https://github.com/safe\\bad', 'https://github.com/"bad',
            'https://github.com/<bad>', 'https://github.com/[bad]',
            'https://github.com/a(b', 'https://github.com/a)b(',
        ]
        bad += ['https://x.' + suffix + '/a' for suffix in
                ('local', 'internal', 'lan', 'home', 'onion', 'test',
                 'invalid', 'example', 'arpa')]
        for url in bad:
            with self.subTest(url=url):
                self.assertIsNone(safe_url(url))
                self.assertEqual(extract_links(url), [])

    def test_all_controls_and_unicode_suffixes(self):
        for suffix in [chr(n) + 'bad' for n in range(33)] + [
                '\x7f', '\u200b', '\u202e', '\ufeff', 'é', '。evil.com']:
            url = 'https://github.com/o/r/pull/1' + suffix
            with self.subTest(suffix=repr(suffix)):
                self.assertIsNone(safe_url(url))
                # ASCII space is a real prose delimiter, not part of a URL.
                if not suffix.startswith(' '):
                    self.assertEqual(extract_links(url), [])

    def test_secrets(self):
        for secret in ('token', 'password', 'secret', 'credential', 'reset',
                       'webhook', 'auth', 'oauth', 'invite', 'login',
                       'apikey', 'api_key', 'sk-abcdefgh', 'ghp_abcdefgh',
                       'github_pat_abcdefgh', 'bot123456:ABCDEFGH',
                       '123456:ABCDEFGH', 'xoxb-abcdefgh', 'AKIAABCDEFGH'):
            self.assertIsNone(safe_url('https://github.com/' + secret))
        for value in ('AbCdEf', 'abcdef', 'ABCDEF', '%41bCdEf'):
            url = 'https://github.com/' + value
            self.assertIsNone(safe_url(url, ['AbCdEf']))
            self.assertEqual(extract_links(url, ['AbCdEf']), [])
        self.assertEqual(extract_links('https://github.com/a.', ['a.']), [])

    def test_markdown_and_labels(self):
        links = extract_links('[IGNORE ME](https://GitHub.com/o/r/pull/12) '
                              '<https://github.com/o/r/issues/7/> '
                              '[fake](https://github.com/o/r/releases/tag/v1)')
        self.assertEqual([x['label'] for x in links], [
            'GitHub PR #12', 'GitHub issue #7', 'github.com/o/r/releases/tag/v1'])
        self.assertEqual(links[0]['url'], 'https://github.com/o/r/pull/12')
        for path in ('/o/r/pull/0', '/o/r/pull/01', '/o/r/pull/1/extra'):
            self.assertTrue(extract_links('https://github.com' + path)[0]['label']
                            .startswith('github.com'))

    def test_parentheses_and_prose(self):
        url = 'https://docs.python.org/a(b(c))'
        self.assertEqual(extract_links('See (' + url + ').')[0]['url'], url)
        self.assertEqual(extract_links('<https://github.com/a>')[0]['url'],
                         'https://github.com/a')
        for suffix in ('?token=bad', '\\bad', '\x01bad', 'é', ')evil',
                       '%3Ftoken=bad', '#fragment', '>evil', '")evil'):
            self.assertEqual(extract_links('https://github.com/o/r/pull/1' + suffix), [])
        self.assertEqual(extract_links('[ok](https://github.com/a?token=bad)'), [])

    def test_order_dedup_and_cap(self):
        links = extract_links('HTTPS://GITHUB.COM:443/a https://github.com/a '
                              'https://python.org/b https://pypi.org/c https://docs.python.org/d')
        self.assertEqual([x['url'] for x in links], [
            'https://github.com/a', 'https://python.org/b', 'https://pypi.org/c'])

    def test_bounds_and_revalidation(self):
        prefix = 'https://github.com/'
        self.assertIsNotNone(safe_url(prefix + 'a' * (512 - len(prefix))))
        self.assertIsNone(safe_url(prefix + 'a' * (513 - len(prefix))))
        self.assertEqual(extract_links(' ' * 16000 + prefix), [])
        self.assertEqual(extract_links(' ' * 15980 + prefix + 'a' * 50), [])
        self.assertEqual(extract_links(prefix + 'a' * 20000), [])
        for link in extract_links(prefix + 'a' * 200):
            self.assertLessEqual(len(link['label']), 64)
            self.assertTrue(link['label'].startswith('github.com'))
            self.assertEqual(safe_url(link['url']), link['url'])
        host = 'a' * 59 + '.com'
        link = extract_links('https://' + host + '/longpath')[0]
        self.assertTrue(link['label'].startswith(host))
        self.assertLessEqual(len(link['label']), 64)

    def test_source_and_limit(self):
        source = 'HTTPS://GitHub.COM:443/owner/repo__name/pull/12'
        link = extract_links('[untrusted](' + source + ').')[0]
        self.assertEqual(link['source'], source)
        self.assertEqual(link['url'], source.replace('HTTPS://GitHub.COM:443',
                                                   'https://github.com'))
        text = ' '.join('https://github.com/a/' + str(n) for n in range(15))
        self.assertEqual(len(extract_links(text, limit=12)), 12)
        self.assertEqual(len(extract_links(text)), 3)
        for limit in (0, -1, 13, True, 1.0, '3', None):
            with self.assertRaises(ValueError):
                extract_links(text, limit=limit)
        self.assertIsNone(safe_url('https://GiThUb.com', iter(['github'])))
        self.assertEqual(extract_links('https://github.com/o/r/pull/1',
                                       ['GitHub PR']), [])

    def test_exact_source_offsets(self):
        raw = 'HTTPS://GitHub.COM:443/o/repo__name/pull/12'
        text = ('Unicode prefix é [spoof](' + raw + '). '
                '<https://docs.python.org/a(b(c))> '
                'https://github.com/o/repo__name/pull/12 '
                'https://github.com/o/repo__name/pull/12?token=bad')
        links = extract_links(text)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]['start'], text.index(raw))
        self.assertEqual(links[0]['end'], text.index(raw) + len(raw))
        for link in links:
            self.assertEqual(text[link['start']:link['end']], link['source'])
            self.assertEqual(link['end'], link['start'] + len(link['source']))
            self.assertEqual(safe_url(link['source']), link['url'])
        rebuilt = text
        for link in reversed(links):
            rebuilt = rebuilt[:link['start']] + 'MARKER' + rebuilt[link['end']:]
        self.assertIn('pull/12?token=bad', rebuilt)
        self.assertIn('https://github.com/o/repo__name/pull/12 ', rebuilt)

    def test_lf_line_boundary_contract(self):
        pr = 'https://github.com/example/project/pull/42'
        docs = 'https://docs.python.org/3/library/urllib.parse.html'
        for text in ('Review: ' + pr + '\nDocs: ' + docs,
                     pr + '\n' + docs, pr + '\n\n  Docs: ' + docs):
            links = extract_links(text)
            self.assertEqual([item['url'] for item in links], [pr, docs])
            for item in links:
                self.assertEqual(text[item['start']:item['end']], item['source'])
        self.assertEqual(extract_links(pr + '\n')[0]['url'], pr)
        for continuation in ('.evil.com', '/path', '?token=bad', '#bad',
                             'evil.com', 'pull/43', 'bad', '\tDocs: fine',
                             '  /path', '\n.evil.com'):
            with self.subTest(continuation=continuation):
                self.assertEqual(extract_links(pr + '\n' + continuation), [])
        self.assertEqual(extract_links('https://git\nhub.com/o/r'), [])
        self.assertEqual(extract_links('https://github.com/o/\nr/pull/1'), [])

    def test_repository_names_not_credentials(self):
        for repo in ('task-runner', 'tokenizer', 'authenticator',
                     'credential-manager', 'secretary', 'enough_work'):
            url = 'https://github.com/owner/' + repo + '/pull/42'
            with self.subTest(repo=repo):
                self.assertEqual(safe_url(url), url)
                self.assertEqual(extract_links(url)[0]['label'], 'GitHub PR #42')
        for endpoint in ('token', 'token=abcdef', 'password:abc',
                         'safe;api_key=abc', 'auth/callback', 'oauth', 'reset'):
            self.assertIsNone(safe_url('https://github.com/' + endpoint))
        for short in ('sk-abc', 'ghp_abc', 'github_pat_abc'):
            self.assertIsNotNone(safe_url('https://github.com/' + short))
            self.assertIsNone(safe_url('https://github.com/' + short, [short]))

    def test_explicit_extended_sensitive_keys(self):
        for key in ('access_token', 'refresh_token', 'passwd', 'authorization',
                    'ACCESS_TOKEN', 'Refresh-Token', 'accessToken'):
            for suffix in ('/abcdefghijk', '=abcdefghijk', ':abcdefghijk'):
                url = 'https://github.com/' + key + suffix
                with self.subTest(url=url):
                    self.assertIsNone(safe_url(url))
                    self.assertEqual(extract_links(url), [])
        for repo in ('tokenizer', 'task-runner', 'authenticator'):
            url = 'https://github.com/owner/' + repo + '/pull/42'
            self.assertEqual(safe_url(url), url)
            self.assertEqual(extract_links(url)[0]['label'], 'GitHub PR #42')

    def test_invalid_types(self):
        for value in (None, 1, b'https://github.com'):
            self.assertIsNone(safe_url(value))
            self.assertEqual(extract_links(value), [])


if __name__ == '__main__':
    unittest.main()
