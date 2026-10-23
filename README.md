[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# About

Python code used to simulate satellite orbits near Lagrange points. It is meant for the L4/L5 points but any of the 5
points can be used. The initial position and velocity of the satellite can be specified by the user. Additionally, the
masses of the star, planet, and the distance between them can also be specified.

There are three ways to use it:

- **In the browser:** https://moussa-mikhail.github.io/lagrange_point_orbit_simulator/ runs the whole simulation on
  your machine, with nothing to install. See [web/README.md](web/README.md).
- **Desktop app:** download the build for your system from the
  [releases page](https://github.com/Moussa-Mikhail/lagrange_point_orbit_simulator/releases) and extract it. Run
  `sim_gui` (`sim_gui.exe` on Windows). Each release lists a SHA256 checksum for every download. The builds are not code
  signed, so Windows may block a downloaded zip until you unblock it (right-click, Properties, Unblock) before
  extracting. On Linux the system needs `libEGL` (the `libegl1` package on Debian and Ubuntu), which desktop installs
  normally have.
- **Python library and source GUI:** see below.

## Installation of source code

The project needs Python 3.13 or newer and uses [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/Moussa-Mikhail/lagrange_point_orbit_simulator.git
cd lagrange_point_orbit_simulator
uv sync
```

`uv sync` installs everything for development, including the GUI and Numba. The extras can be chosen separately:

| Install                                   | What you get                                                  |
| ----------------------------------------- | ------------------------------------------------------------- |
| `uv sync --no-default-groups`             | the core simulator only (NumPy and `validateddescriptor`)     |
| `uv sync --no-default-groups --extra numba` | the core, compiled with Numba (much faster)                 |
| `uv sync --no-default-groups --extra gui` | the core and the Qt desktop GUI (includes Numba)              |

Numba is optional. Without it the integrator runs as plain Python, which works but is much slower.

If you use pip instead, `requirements.txt` (core), `requirements-gui.txt` and `requirements-dev.txt` are generated from
`uv.lock`.

### Running the GUI from source

```
./start-gui-source.sh        # Linux and macOS
start-gui-source.bat         # Windows
```

### Using the simulator from Python

```python
from lagrangepointsimulator import Simulator

sim = Simulator(num_years=10, lagrange_label="L4")
sim.simulate()

sim.sat_pos  # (num_steps + 1, 3) array of satellite positions in metres
sim.calc_conserved_quantities()
```

`help(Simulator)` lists every parameter. The attributes of an instance can be changed after creation. The first call to
`simulate` is slower with Numba because it compiles the integrator.

## Presets

The GUI and the web page offer presets of the system and satellite parameters. The defaults are in
`src/lagrangepointinputs/default_presets.toml`, which also explains the format. To add your own presets and
constants, create `user_presets.toml` in your user config directory:

| System  | Directory                                              |
| ------- | ------------------------------------------------------ |
| Linux   | `~/.config/lagrange-point-orbit-simulator/`            |
| macOS   | `~/Library/Application Support/lagrange-point-orbit-simulator/` |
| Windows | `%APPDATA%\lagrange-point-orbit-simulator\`            |

Edits are picked up without restarting the app.

## Development

```
uv run ruff check .
uv run ruff format --check .
uv run ty check src
uv run refurb src tests scripts
uv run sourcery review --check src scripts tests web
uv run pytest
```

The web page has a browser test, which needs Node. Build the site, then run it with Playwright (Apache-2.0):

```
uv run --no-project scripts/build_web.py
cd tests/e2e && npm ci && npx playwright install chromium && npm test
```

Install the git hooks once per clone with `uv run pre-commit install`. They run ruff, ty, refurb and Sourcery on each commit,
regenerate the `requirements*.txt` files when `pyproject.toml` or `uv.lock` are staged, and run pytest before a push.
A hook that fixes a file fails the commit so you can review and stage the change.

The linters, type check and tests also run in CI on every push and pull request, which is what enforces them.

`./update-requirements.sh` regenerates the `requirements*.txt` files. CI fails if they are out of date, so run it (or
let the hook) after changing `pyproject.toml` or `uv.lock`.

To build the desktop app locally run `./build.sh` (`build.bat` on Windows). The result is in `dist/sim_gui`, and
`dist/sim_gui/sim_gui --self-test` checks the build. A release is made by pushing a tag like `v0.1.1`.

Layout:

- `src/lagrangepointsimulator`: the simulation. It has no Qt dependency.
- `src/lagrangepointinputs`: the presets and the expression evaluator for user input, shared by the GUI and the web
  page. It depends on the simulator and has no Qt dependency.
- `src/lagrangepointgui`: the Qt desktop GUI.
- `web`: the browser version, built by `scripts/build_web.py`. See [web/README.md](web/README.md).

The code is licensed under the GPL-3.0, see `LICENSE`.
