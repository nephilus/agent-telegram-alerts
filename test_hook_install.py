from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import hook_install as hook


class HookInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"JCODE_HOME": str(self.home)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = self.home / "config.toml"
        self.manifest = self.home / "notifications" / "telegram-hook.json"
        self.exe = self.home / "bin space's" / "jcode-telegram"
        self.exe.parent.mkdir()
        self.exe.write_text("#!/bin/sh\nexit 0\n")
        self.exe.chmod(0o700)

    def install(self, seconds=30):
        return hook.manage("install", str(self.exe), seconds)

    def doc(self):
        return tomllib.loads(self.config.read_text())

    def test_preservation_and_idempotence(self):
        original = '# keep\n[telegram]\nbot_token="secret"\nenabled=false\n[hooks]\nturn_end = "foreign" # tail\nturn_start=["other"]\n'
        self.config.write_text(original)
        expected = self.doc()
        self.assertEqual(self.install(), "installed")
        command = json.loads(self.manifest.read_text())["command"]
        expected["hooks"]["turn_end"] = ["foreign", command]
        self.assertEqual(self.doc(), expected)
        self.assertIn('# keep', self.config.read_text())
        self.assertIn('# tail', self.config.read_text())
        snapshot = self.config.read_bytes(), self.manifest.read_bytes()
        self.install()
        self.assertEqual(snapshot, (self.config.read_bytes(), self.manifest.read_bytes()))
        self.assertEqual(hook.manage("status"), "installed")
        self.assertEqual(hook.manage("uninstall"), "missing")
        expected["hooks"]["turn_end"] = ["foreign"]
        self.assertEqual(self.doc(), expected)
        self.assertFalse(self.manifest.exists())
        for path in [self.config, *self.home.glob("config.toml.backup-*")]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        backups = list(self.home.glob("config.toml.backup-*"))
        self.assertTrue(any(p.read_text() == original for p in backups))

    def test_hook_forms(self):
        forms = ['# blank\n', '[hooks]\n# existing table\n',
                 'hooks.turn_end = ["one", "two"]\n',
                 '["hooks"]\n"turn_end" = [\n "a#b", # inside\n "😀",\n] # outside\n',
                 "[hooks]\nturn_end = '''multi\nline'''\n"]
        for text in forms:
            with self.subTest(text=text):
                self.config.write_text(text)
                before = self.doc()
                self.install()
                after = self.doc()
                owned = json.loads(self.manifest.read_text())["command"]
                value = before.get("hooks", {}).get("turn_end", [])
                expected = [value] if isinstance(value, str) else value
                self.assertEqual(after['hooks']['turn_end'], expected + [owned])
                for comment in ('# inside', '# outside', '# existing table', '# blank'):
                    if comment in text:
                        self.assertIn(comment, self.config.read_text())
                hook.manage('uninstall')

    def test_shell_quoting_and_threshold(self):
        self.install(42)
        command = json.loads(self.manifest.read_text())["command"]
        self.assertEqual(shlex.split(command), [str(self.exe), 'alert', '--min-seconds', '42'])
        self.assertEqual(stat.S_IMODE(self.manifest.stat().st_mode), 0o600)

    def test_bad_config_and_types(self):
        for text in ['token="private-secret\n', 'hooks=3', '[hooks]\nturn_end=[1]']:
            self.config.write_text(text)
            with self.assertRaises(hook.HookError) as error:
                self.install()
            self.assertNotIn('private-secret', str(error.exception))
            self.assertEqual(self.config.read_text(), text)
            self.assertFalse(self.manifest.exists())

    def test_symlinks(self):
        target = self.home / 'target'
        target.write_text('')
        self.config.symlink_to(target)
        with self.assertRaises(hook.HookError):
            self.install()
        self.config.unlink()
        self.manifest.parent.mkdir(exist_ok=True)
        self.manifest.symlink_to(target)
        with self.assertRaises(hook.HookError):
            self.install()
        self.assertEqual(target.read_text(), '')

    def test_ownership_mismatch_and_duplicate(self):
        self.install()
        original = self.config.read_bytes()
        with self.assertRaises(hook.HookError):
            self.install(99)
        self.assertEqual(self.config.read_bytes(), original)
        owned = json.loads(self.manifest.read_text())['command']
        self.config.write_text('hooks.turn_end=' + json.dumps([owned, owned]))
        with self.assertRaises(hook.HookError):
            hook.manage('uninstall')
        self.config.write_text('hooks.turn_end=["foreign"]')
        with self.assertRaises(hook.HookError):
            hook.manage('status')
        with self.assertRaises(hook.HookError):
            hook.manage('uninstall')

    def test_unowned_exact_command_is_not_adopted(self):
        command = hook._command(str(self.exe), 30)
        self.config.write_text('hooks.turn_end=' + json.dumps(command))
        with self.assertRaises(hook.HookError):
            self.install()
        before = self.config.read_bytes()
        self.assertEqual(hook.manage('uninstall'), 'missing')
        self.assertEqual(self.config.read_bytes(), before)

    def test_no_manifest_noop_even_malformed(self):
        self.config.write_text('not valid TOML secret')
        self.assertEqual(hook.manage('uninstall'), 'missing')
        self.assertEqual(self.config.read_text(), 'not valid TOML secret')
        self.config.unlink()
        self.assertEqual(hook.manage('uninstall'), 'missing')
        self.assertFalse(self.config.exists())

    def test_manifest_validation(self):
        self.manifest.parent.mkdir()
        for data in ['secret invalid', '{}', '[]', '{"version":true,"command":"x"}']:
            self.manifest.write_text(data)
            with self.assertRaises(hook.HookError):
                self.install()
            self.assertFalse(self.config.exists())

    def test_concurrent_config_edit(self):
        self.config.write_text('# initial\n')
        real = hook._edit
        def concurrent(*args):
            result = real(*args)
            self.config.write_text('# external edit\n')
            return result
        with patch.object(hook, '_edit', side_effect=concurrent):
            with self.assertRaises(hook.HookError):
                self.install()
        self.assertEqual(self.config.read_text(), '# external edit\n')
        self.assertFalse(self.manifest.exists())

    def test_concurrent_uninstall_edit(self):
        self.install()
        real = hook._edit
        def concurrent(*args):
            result = real(*args)
            self.config.write_text('# external edit\n')
            return result
        with patch.object(hook, '_edit', side_effect=concurrent):
            with self.assertRaises(hook.HookError):
                hook.manage('uninstall')
        self.assertTrue(self.manifest.exists())
        self.assertEqual(self.config.read_text(), '# external edit\n')

    def test_default_sibling_and_fallback(self):
        sibling = self.exe.parent / 'jcode-telegram-hook'
        with patch.object(sys, 'argv', [str(sibling)]), patch.object(hook.shutil, 'which') as which:
            self.assertEqual(shlex.split(hook._command(None, 30))[0], str(self.exe))
            which.assert_not_called()
        with patch.object(sys, 'argv', [str(self.home / 'missing' / 'hook')]), patch.object(hook.shutil, 'which', return_value=str(self.exe)):
            self.assertEqual(shlex.split(hook._command(None, 30))[0], str(self.exe))

    def test_invalid_executable_and_threshold(self):
        for command, seconds in [(str(self.home / 'missing'), 30), (str(self.exe.parent), 30), (str(self.exe), -1)]:
            with self.assertRaises(hook.HookError):
                hook.manage('install', command, seconds)
        self.exe.chmod(0o600)
        with self.assertRaises(hook.HookError):
            self.install()
        self.assertFalse(self.config.exists())

    def test_concurrent_manifest_edit(self):
        real = hook._edit
        def concurrent(*args):
            result = real(*args)
            self.manifest.write_text('{"version":1,"command":"foreign"}')
            return result
        with patch.object(hook, '_edit', side_effect=concurrent):
            with self.assertRaises(hook.HookError):
                self.install()
        self.assertFalse(self.config.exists())
        self.assertEqual(json.loads(self.manifest.read_text())['command'], 'foreign')

    def test_parallel_installers(self):
        args = [sys.executable, '-B', '-m', 'hook_install', 'install', '--command', str(self.exe)]
        processes = [subprocess.Popen(args, cwd=Path(__file__).parent,
                                     env=os.environ.copy(), stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True) for _ in range(3)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(stdout.strip(), 'installed')
        self.assertEqual(len(self.doc()['hooks']['turn_end']), 1)

    def test_legacy_unowned_hooks_require_manual_migration(self):
        legacy = ["'/old location/jcode-telegram' alert --min-seconds 10",
                  '/old/bin/jcode-telegram alert',
                  'env TAG=old /old/bin/jcode-telegram alert --min-seconds 5',
                  'true && /old/bin/jcode-telegram alert',
                  'python3 /old/jcode_telegram.py alert']
        for command in legacy:
            with self.subTest(command=command):
                self.config.write_text('hooks.turn_end=' + json.dumps([command]))
                original = self.config.read_bytes()
                stderr = io.StringIO()
                with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
                    result = hook.cli(['install', '--command', str(self.exe)])
                self.assertEqual(result, 1)
                self.assertIn('Remove or migrate the old manual hook first', stderr.getvalue())
                self.assertNotIn('/old', stderr.getvalue())
                self.assertEqual(self.config.read_bytes(), original)
                self.assertFalse(self.manifest.exists())
        self.config.write_text('hooks.turn_end=["echo jcode-telegram", "jcode-telegram status"]')
        self.install()

    def test_legacy_hook_added_next_to_owned_is_refused(self):
        self.install()
        entries = self.doc()['hooks']['turn_end']
        entries.append('/old/bin/jcode-telegram alert')
        self.config.write_text('hooks.turn_end=' + json.dumps(entries))
        before = self.config.read_bytes(), self.manifest.read_bytes()
        with self.assertRaisesRegex(hook.HookError, 'Remove or migrate'):
            self.install()
        self.assertEqual(before, (self.config.read_bytes(), self.manifest.read_bytes()))
        hook.manage('uninstall')
        self.assertEqual(self.doc()['hooks']['turn_end'], ['/old/bin/jcode-telegram alert'])

    def test_manifest_replace_failure_never_activates_hook(self):
        self.config.write_text('# original\n')
        real_replace = hook.os.replace
        def fail_manifest(source, destination):
            if Path(destination) == self.manifest:
                raise OSError('PRIVATE_EXCEPTION_CONTENT')
            return real_replace(source, destination)
        stderr = io.StringIO()
        with patch.object(hook.os, 'replace', side_effect=fail_manifest):
            with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
                result = hook.cli(['install', '--command', str(self.exe)])
        self.assertEqual(result, 1)
        self.assertNotIn('PRIVATE_EXCEPTION_CONTENT', stderr.getvalue())
        self.assertEqual(self.config.read_text(), '# original\n')
        self.assertFalse(self.manifest.exists())

    def test_config_replace_failure_rolls_back_prepared_manifest(self):
        real_replace = hook.os.replace
        for existing in [False, True]:
            with self.subTest(existing=existing):
                if existing:
                    self.config.write_text('# original\n')
                def fail_config(source, destination):
                    if Path(destination) == self.config:
                        self.assertTrue(self.manifest.exists())
                        self.assertEqual(stat.S_IMODE(self.manifest.stat().st_mode), 0o600)
                        raise OSError('PRIVATE_EXCEPTION_CONTENT')
                    return real_replace(source, destination)
                with patch.object(hook.os, 'replace', side_effect=fail_config):
                    with self.assertRaises(hook.HookError) as error:
                        self.install()
                self.assertNotIn('PRIVATE_EXCEPTION_CONTENT', str(error.exception))
                self.assertFalse(self.manifest.exists())
                self.assertEqual(self.config.exists(), existing)
                if existing:
                    self.assertEqual(self.config.read_text(), '# original\n')
        self.install()
        self.assertEqual(hook.manage('status'), 'installed')

    def test_manifest_durability_failure_never_activates(self):
        real_sync = hook._sync_directory
        def fail_sync(directory):
            if directory == self.manifest.parent:
                raise OSError('sync failure')
            return real_sync(directory)
        with patch.object(hook, '_sync_directory', side_effect=fail_sync):
            with self.assertRaises(OSError):
                self.install()
        self.assertFalse(self.config.exists())
        # A manifest may survive a post-replace failure, but no hook is active.
        self.assertTrue(self.manifest.exists())

    def test_post_activation_sync_failure_keeps_ownership(self):
        real_sync = hook._sync_directory
        def fail_sync(directory):
            if directory == self.home:
                raise OSError('sync failure')
            return real_sync(directory)
        with patch.object(hook, '_sync_directory', side_effect=fail_sync):
            with self.assertRaises(hook.HookError):
                self.install()
        self.assertEqual(hook.manage('status'), 'installed')
        self.assertTrue(self.manifest.exists())
        hook.manage('uninstall')

    def test_failed_activation_does_not_rollback_external_manifest(self):
        real_atomic = hook._atomic
        def external_manifest(path, *args, **kwargs):
            if path == self.config:
                self.manifest.write_text('{"version":1,"command":"external"}')
                raise OSError('activation failed')
            return real_atomic(path, *args, **kwargs)
        with patch.object(hook, '_atomic', side_effect=external_manifest):
            with self.assertRaises(hook.HookError):
                self.install()
        self.assertFalse(self.config.exists())
        self.assertEqual(json.loads(self.manifest.read_text())['command'], 'external')

    def test_failed_activation_keeps_manifest_after_external_config_edit(self):
        real_atomic = hook._atomic
        def external_config(path, *args, **kwargs):
            if path == self.config:
                self.config.write_text('# external edit\n')
                raise OSError('activation failed')
            return real_atomic(path, *args, **kwargs)
        with patch.object(hook, '_atomic', side_effect=external_config):
            with self.assertRaises(hook.HookError):
                self.install()
        self.assertEqual(self.config.read_text(), '# external edit\n')
        self.assertTrue(self.manifest.exists())

    def test_cli_subprocess(self):
        def run(*args):
            return subprocess.run([sys.executable, '-B', '-m', 'hook_install', *args],
                                  cwd=Path(__file__).parent, env=os.environ.copy(),
                                  capture_output=True, text=True, timeout=10)
        for args, output in [(('status',), 'missing'),
                             (('install', '--command', str(self.exe)), 'installed'),
                             (('status',), 'installed'), (('uninstall',), 'missing')]:
            result = run(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), output)
        self.assertEqual(run('--help').returncode, 0)
        self.config.write_text('token="SUPER_SECRET\n')
        result = run('install', '--command', str(self.exe))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('SUPER_SECRET', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
