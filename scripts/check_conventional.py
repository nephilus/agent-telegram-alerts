"""Validate a single Conventional Commit subject without executing input."""

import argparse
import os
import re
import subprocess

SUBJECT = re.compile(
    r"(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([A-Za-z0-9][A-Za-z0-9._/-]*\))?!?: [^\s].*"
)


def is_conventional(subject: str) -> bool:
    """Require one printable line, a known type, and a nonempty description."""
    return (
        bool(subject)
        and all(char.isprintable() for char in subject)
        and subject == subject.strip()
        and SUBJECT.fullmatch(subject) is not None
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", help="subject to check (prefer TITLE environment in CI)")
    parser.add_argument("--commits", metavar="BASE..HEAD", help="also check a local git revision range")
    args = parser.parse_args(argv)
    subjects = []
    title = args.title if args.title is not None else os.environ.get("TITLE")
    if title is not None:
        subjects.append(title)
    if args.commits:
        if args.commits.startswith("-") or ".." not in args.commits:
            parser.error("--commits requires BASE..HEAD, not an option")
        result = subprocess.run(
            ["git", "log", "--format=%s", args.commits, "--"],
            check=True, capture_output=True, text=True,
        )
        subjects.extend(result.stdout.splitlines())
    if not subjects:
        parser.error("provide --title, TITLE, or a nonempty --commits range")
    invalid = [subject for subject in subjects if not is_conventional(subject)]
    for subject in invalid:
        print(f"Invalid conventional subject: {subject!r}")
    return int(bool(invalid))


if __name__ == "__main__":
    raise SystemExit(main())
