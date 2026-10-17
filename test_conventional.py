import contextlib
import io
import os
import unittest
from unittest.mock import patch

from scripts.check_conventional import is_conventional, main


class ConventionalTests(unittest.TestCase):
    def test_valid(self):
        for title in ("feat: add alerts", "fix(hook): repair install", "feat!: break API",
                      "fix(api)!: change signature", "chore(main): release 0.1.0",
                      "chore(deps): update actions", "docs: explain releases"):
            with self.subTest(title=title):
                self.assertTrue(is_conventional(title))

    def test_invalid(self):
        for title in ("", "Fix: typo", "feat:", "feat: ", "feat:  space", "feat(): x",
                      "feat: x\nfix: y", "feat: x\r", "feat: x\x00", " feat: x", "feat: x "):
            with self.subTest(title=title):
                self.assertFalse(is_conventional(title))

    def test_env_input_is_data(self):
        with patch.dict(os.environ, {"TITLE": "fix: $(touch /not-executed)"}):
            self.assertEqual(main([]), 0)
        with patch.dict(os.environ, {"TITLE": "fix: safe\n::error::injected"}):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([]), 1)
            self.assertNotIn("\n::error::", output.getvalue())

    def test_commit_range_is_argv_not_shell(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("scripts.check_conventional.subprocess.run") as run:
                run.return_value.stdout = "feat: first\nfix: second\n"
                self.assertEqual(main(["--commits", "base..head"]), 0)
                self.assertEqual(run.call_args.args[0],
                                 ["git", "log", "--format=%s", "base..head", "--"])
                self.assertNotIn("shell", run.call_args.kwargs)

    def test_no_subject_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    main([])
            self.assertEqual(result.exception.code, 2)

    def test_invalid_range_is_not_executed(self):
        with patch("scripts.check_conventional.subprocess.run") as run:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(["--commits=--all..HEAD"])
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
