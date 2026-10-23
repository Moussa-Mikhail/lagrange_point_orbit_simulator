"""Writes the release notes for a tag as Markdown: the commits since the previous tag, grouped by their type.

Usage: python scripts/release_notes.py [revision]   (the revision defaults to HEAD, and is usually a tag)
"""

import re
import subprocess
import sys

SECTIONS = {
    "feat": "Features",
    "fix": "Fixes",
    "perf": "Performance",
}
OTHER = "Other changes"
SUBJECT = re.compile(r"^(?P<type>\w+)(\([^)]*\))?!?: (?P<text>.*)$")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def previous_tag(revision: str) -> str | None:
    try:
        return git("describe", "--tags", "--abbrev=0", f"{revision}^")
    except subprocess.CalledProcessError:
        return None


def commits(revision: str) -> list[tuple[str, str]]:
    """(hash, subject) of the commits in the release, newest first, without the version bumps."""
    previous = previous_tag(revision)
    span = f"{previous}..{revision}" if previous else revision
    lines = git("log", "--format=%h %s", span).splitlines()
    pairs = [tuple(line.split(" ", 1)) for line in lines]
    return [(sha, subject) for sha, subject in pairs if not subject.startswith("build: bump version")]


def notes(revision: str) -> str:
    grouped: dict[str, list[str]] = {}
    for sha, subject in commits(revision):
        match = SUBJECT.match(subject)
        section = SECTIONS.get(match["type"], OTHER) if match else OTHER
        text = match["text"] if match else subject
        grouped.setdefault(section, []).append(f"- {text} ({sha})")

    order = [*SECTIONS.values(), OTHER]
    return "\n\n".join(f"## {section}\n" + "\n".join(grouped[section]) for section in order if section in grouped)


if __name__ == "__main__":
    print(notes(sys.argv[1] if len(sys.argv) > 1 else "HEAD"))
