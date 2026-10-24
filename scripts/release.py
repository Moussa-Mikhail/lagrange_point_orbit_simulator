"""Makes a release: bumps the version, commits, tags and pushes, which starts the release workflow.

Usage: uv run --no-project scripts/release.py X.Y.Z [--yes] [--dry-run]
       a pre-release is X.Y.ZrcN, which the workflow publishes as one

Needs git, uv and the GitHub CLI. It refuses unless the work tree is clean, HEAD is main and the same as origin/main,
the checks passed on it, and the tag is new. See docs/RELEASING.md.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$")
VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def run(*args: str, check: bool = True) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=check).stdout.strip()


def fail(message: str) -> None:
    sys.exit(f"error: {message}")


def sort_key(version: str) -> tuple[int, int, int, float]:
    """Orders versions, a release candidate coming before the release it is a candidate for."""
    match = VERSION.match(version)
    if not match:
        fail(f"'{version}' isn't a version like 1.2.3 or 1.2.3rc1")

    major, minor, patch, candidate = match.groups()
    return int(major), int(minor), int(patch), float("inf") if candidate is None else int(candidate)


def current_version() -> str:
    match = VERSION_LINE.search(PYPROJECT.read_text())
    if not match:
        fail("pyproject.toml has no version")

    return match[1]


def check_repository(version: str) -> str:
    """The commit that would be released, or the exit with the reason it can't be."""
    if sort_key(version) <= sort_key(current_version()):
        fail(f"{version} isn't newer than the current version {current_version()}")
    if run("git", "status", "--porcelain"):
        fail("the work tree has changes")
    if run("git", "branch", "--show-current") != "main":
        fail("releases are made from main")

    run("git", "fetch", "--quiet", "origin", "main", "--tags")
    commit = run("git", "rev-parse", "HEAD")
    if commit != run("git", "rev-parse", "origin/main"):
        fail("main isn't the same as origin/main")
    if run("git", "tag", "--list", f"v{version}"):
        fail(f"the tag v{version} exists")

    return commit


def check_ci(commit: str) -> None:
    runs = run(
        "gh",
        "run",
        "list",
        "--commit",
        commit,
        "--json",
        "workflowName,status,conclusion",
        "--jq",
        ".[]|[.workflowName,.status,.conclusion]|@tsv",
    )
    results = [line.split("\t") for line in runs.splitlines()]
    if not results:
        fail(f"no checks have run for {commit[:7]}")

    unfinished = [name for name, status, _ in results if status != "completed"]
    failed = [name for name, status, conclusion in results if status == "completed" and conclusion != "success"]
    if unfinished or failed:
        fail(f"the checks for {commit[:7]} aren't all green: unfinished {unfinished}, failed {failed}")


def bump(version: str) -> None:
    PYPROJECT.write_text(VERSION_LINE.sub(f'version = "{version}"', PYPROJECT.read_text(), count=1))
    run("uv", "lock")
    run("git", "add", "pyproject.toml", "uv.lock")
    run("git", "commit", "--message", f"build: bump version to {version}")
    run("git", "tag", "--annotate", f"v{version}", "--message", f"v{version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="the new version, like 0.3.0 or 0.3.0rc1")
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    parser.add_argument("--dry-run", action="store_true", help="check, and show what would be released")
    arguments = parser.parse_args()
    version = arguments.version

    commit = check_repository(version)
    check_ci(commit)

    notes = run(sys.executable, "scripts/release_notes.py", "HEAD")
    print(f"Releasing {version} from {commit[:7]}, up from {current_version()}.\n\n{notes}\n")
    if arguments.dry_run:
        return
    if not arguments.yes and input("Bump, tag and push? [y/N] ").lower() != "y":
        sys.exit("cancelled")

    bump(version)
    run("git", "push", "--atomic", "origin", "main", f"v{version}")
    print(f"Pushed v{version}. The release workflow creates the release: gh run watch")


if __name__ == "__main__":
    main()
