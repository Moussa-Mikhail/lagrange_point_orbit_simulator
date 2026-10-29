[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# About

Python code used to simulate satellite orbits near Lagrange points. It is meant for the L4/L5 points but any of the 5
points can be used. The initial position and velocity of the satellite can be specified by the user. Additionally, the
masses of the star, planet, and the distance between them can also be specified.

There are three ways to use it, for different purposes:

- **In the browser** is for demonstrations, showing the orbits to others and trying parameters quickly:
  https://moussa-mikhail.github.io/lagrange_point_orbit_simulator/ runs the whole simulation on your machine, with
  nothing to install. It plots at most 100,000 points of a run. See [web/README.md](web/README.md).
- **The `Simulator` class** is for analysis and research. It keeps every step of a run as NumPy arrays, which can be
  used in a script or a notebook, see [Using the simulator from Python](#using-the-simulator-from-python).
- **The desktop app** is a Qt front-end for the same simulator, run from the source, see below. Builds to download
  aren't published any more, the last ones are on
  [v0.2.0](https://github.com/Moussa-Mikhail/lagrange_point_orbit_simulator/releases/tag/v0.2.0).

## Installation

The project needs Python 3.13 or newer. To use the simulator as a library, install it with pip:

```
pip install "lagrange-point-orbit-simulator[numba] @ git+https://github.com/Moussa-Mikhail/lagrange_point_orbit_simulator.git"
```

`[numba]` compiles the integrator, which is much faster. Leave it out to install the core only (NumPy and
`validateddescriptor`), or use `[gui]` for the Qt desktop app too. With uv, use
`uv add git+https://github.com/Moussa-Mikhail/lagrange_point_orbit_simulator.git`.

### Installation of source code

To work on the project or run the desktop app from the source, use [uv](https://docs.astral.sh/uv/).

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

#### Running the GUI from source

```
./start-gui-source.sh        # Linux and macOS
start-gui-source.bat         # Windows
```

## Using the simulator from Python

```python
from lagrangepointsimulator import Simulator

sim = Simulator(num_years=10, lagrange_label="L4")
sim.simulate()

sim.sat_pos  # (num_steps + 1, 3) array of satellite positions in metres
sim.calc_conserved_quantities()
```

`help(Simulator)` lists every parameter. The attributes of an instance can be changed after creation. The first call to
`simulate` is slower with Numba because it compiles the integrator.

Every step is kept, which takes 144 bytes of memory per step: a run of 10,000 years with a time step of 1 hour has about
88 million steps and needs about 12.6 GB. Choose `time_step` and `num_years` to fit, or use the web page if only the
overall shape of the orbit is wanted.

## Presets

The GUI and the web page offer presets of the system and satellite parameters. The defaults are in
`src/lagrangepointinputs/default_presets.toml`, which also explains the format.

You can make your own in the app. **Save…** stores the current values of the fields under a name, **Delete** removes
one of your presets, and **Edit…** opens the text of your presets file, where you can also define constants and build on
other presets with `bases`. Built-in presets can't be deleted, but saving one under the same name replaces it until you
delete your version.

On the desktop the presets are in `user_presets.toml` in your user config directory, which you can also edit by hand:

| System  | Directory                                              |
| ------- | ------------------------------------------------------ |
| Linux   | `~/.config/lagrange-point-orbit-simulator/`            |
| macOS   | `~/Library/Application Support/lagrange-point-orbit-simulator/` |
| Windows | `%APPDATA%\lagrange-point-orbit-simulator\`            |

On the web page they are kept in the browser, so they are per browser and are lost if its site data is cleared.
**Export** and **Import…** copy them to and from a file in the same format, which moves them between browsers or to the
desktop app.

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
`dist/sim_gui/sim_gui --self-test` checks the build. CI builds it on every push to check it still works, but the build isn't published. Releases are made with `scripts/release.py`, see [docs/RELEASING.md](docs/RELEASING.md).

Layout:

- `src/lagrangepointsimulator`: the simulation. It has no Qt dependency.
- `src/lagrangepointinputs`: the presets and the expression evaluator for user input, shared by the GUI and the web
  page. It depends on the simulator and has no Qt dependency.
- `src/lagrangepointapi`: the form, simulation, plot data and presets as plain data, which the web page's Python side uses.
- `src/lagrangepointgui`: the Qt Widgets desktop GUI.
- `web`: the browser version, built by `scripts/build_web.py`. See [web/README.md](web/README.md).

The code is licensed under the GPL-3.0, see `LICENSE`.
