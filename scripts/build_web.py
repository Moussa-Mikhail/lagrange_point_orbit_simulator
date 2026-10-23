"""Builds the static site into build/site: the files in web/ plus the wheels that Pyodide installs.

Usage: python scripts/build_web.py [output_dir]
Needs uv and git. validateddescriptor isn't in Pyodide's package list, so its wheel is built from the commit pinned
in requirements.txt.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def version_label() -> str:
    """The version of pyproject.toml and the commit the site is built from, like "0.2.0 (3a1f9c2)"."""
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    return f"{version} ({commit})" if commit else version


def put_version_in_title(index: Path) -> None:
    title = "<title>Orbits near Lagrange Points</title>"
    html = index.read_text()
    if title not in html:
        msg = f"{index} doesn't have the title {title}"
        raise RuntimeError(msg)

    index.write_text(html.replace(title, f"<title>Orbits near Lagrange Points {version_label()}</title>", 1))


def pinned_validateddescriptor() -> tuple[str, str]:
    requirements = (ROOT / "requirements.txt").read_text()
    match = re.search(r"^validateddescriptor @ git\+(\S+?)@([0-9a-f]{40})$", requirements, re.MULTILINE)
    if not match:
        msg = "validateddescriptor pin not found in requirements.txt"  # sourcery skip: inline-variable
        raise RuntimeError(msg)

    return match[1], match[2]


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "site"

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(WEB, output, ignore=shutil.ignore_patterns("__pycache__"))
    put_version_in_title(output / "index.html")

    wheels = output / "wheels"
    run("uv", "build", "--wheel", "--out-dir", str(wheels), str(ROOT))

    url, commit = pinned_validateddescriptor()
    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / "validated-descriptor"
        run("git", "clone", "--quiet", url, str(checkout))
        run("git", "-C", str(checkout), "checkout", "--quiet", commit)
        run("uv", "build", "--wheel", "--out-dir", str(wheels), str(checkout))

    names = sorted(path.name for path in wheels.glob("*.whl"))
    (wheels / "manifest.json").write_text(json.dumps({"wheels": names}, indent=2) + "\n")
    print(f"Built {output} with wheels: {', '.join(names)}")


if __name__ == "__main__":
    main()
