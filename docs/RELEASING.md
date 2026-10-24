# Versions and releases

## What is released

- **The web page** is deployed from `main` by every push that passes the checks. It has no releases of its own, and
  shows the version and commit it was built from in the title of its tab.
- **The desktop app** is run from the source (`uv run`). Builds aren't published since they are over 100 MB and do what
  the web page does, so a release has no files. The last ones are on v0.2.0. CI still builds the app on Linux and runs
  `--self-test` on every push, so that publishing can start again when the app can do more than the page.
- Nothing is published to PyPI.

## Version numbers

One version for the repository: `version` in `pyproject.toml`, which a release tag must equal (`v0.3.0` for `0.3.0`).
The desktop app reads it from the installed package for its window title and `--version`, and `build_web.py` puts it
in the title of the page.

The project is a work in progress and is `0.y.z`. The numbers are labels and promise no compatibility, because
Semantic Versioning's compatibility rules don't fit an application. They are still used consistently:

- **Minor (0.3.0):** a new feature, or a change users will see.
- **Patch (0.2.1):** fixes and performance work only.
- **1.0.0:** when the app has the features it is meant to have. From then on the `user_presets.toml` format, the
  names in `default_presets.toml`, the command-line flags and the public API of `lagrangepointsimulator` don't change
  incompatibly within a major version. Until then a release may change them, and its notes say so.

A release candidate is `X.Y.ZrcN` (`0.3.0rc1`) in `pyproject.toml` and in the tag. It is published as a pre-release.

## When to release

A release is a milestone: a tag, and notes saying what changed since the last one. The web page is live already, so a
release adds nothing to what users can run. Release when there is something worth pointing at, not on a schedule.

## How

```bash
uv run --no-project scripts/release.py 0.3.0 --dry-run   # the checks and the notes, changing nothing
uv run --no-project scripts/release.py 0.3.0
```

The script refuses unless the work tree is clean, `HEAD` is `main` and the same as `origin/main`, the checks passed on
it, and the tag is new. It then commits "build: bump version to 0.3.0", tags `v0.3.0` and pushes both. The release
workflow checks that the tag is on `main` and matches `pyproject.toml`, and creates the release. The release notes list the commits since the previous tag by type
(`feat`, `fix`, `perf`, and the rest). Edit the release afterwards to add a summary, and a warning for anything that
breaks users' presets or scripts.

## Rules

- **A published tag or release is never moved or deleted.** If a release is bad, release a new patch version and say so
  in the notes of the old one.
- `main` isn't rewritten once a tag points into the history being rewritten.
- Releases come from `main`, from a commit whose checks passed.
