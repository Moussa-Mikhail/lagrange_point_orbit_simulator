#!/usr/bin/env bash
set -euo pipefail

# base runtime deps only — nothing from any dependency-group
uv export --no-hashes --no-default-groups --output-file requirements.txt

# dev group (this already pulls in gui, since the dev group includes
# the self-referential "lagrange-point-orbit-simulator[gui]" entry)
uv export --no-hashes --no-default-groups --group dev --output-file requirements-dev.txt

# base deps + the gui extra, no dev-group tooling
uv export --no-hashes --no-default-groups --extra gui --output-file requirements-gui.txt
