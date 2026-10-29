# Web UI

A static site that runs the simulator in the browser with Pyodide, in a Web Worker so the page stays responsive.

```bash
uv run python scripts/build_web.py      # writes build/site: web/ plus the wheels Pyodide installs
python -m http.server -d build/site     # then open http://localhost:8000
```

To try a change on another device without pushing it, `uv run --no-project scripts/serve_web.py --build --tunnel`
builds the site and serves it at a public https address from [localhost.run](https://localhost.run) through `ssh`.
Anyone with the address can open the page until you press Ctrl-C, and your machine has to stay on. The free tunnels
stop answering now and then, so the script fetches the page every 20 s and, if that fails twice, opens a new tunnel and
prints its new address. Without `--tunnel` it
only serves `http://localhost:8000`.

- `index.html`, `style.css`, `app.js`: the page. Plots use Plotly, pinned to 2.35.2 with an integrity hash.
- `worker.js`: loads Pyodide (pinned to 0.29.5 from jsdelivr) and the wheels, and answers requests from `app.js`.
- `integrator.js`: the integrator in JavaScript, about 100x faster than Pyodide running the Python one. The Python
  version in `src/lagrangepointsimulator/numba_funcs.py` is the reference, so keep the two in step.
- User presets: the text of the user's presets file is kept in `localStorage`. The file itself lives in Pyodide's
  in-memory file system, where the shared `lagrangepointinputs.user_presets` validates and writes it, and `app.js` sends
  the stored text back at startup.
- `py/bridge.py`: the Python the worker runs. It mirrors the parameters of `sim_gui.py` and the data preparation of
  `orbit_plotter.py`, which can't be imported there because they need Qt.
