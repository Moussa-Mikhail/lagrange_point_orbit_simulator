# Web UI

A static site that runs the simulator in the browser with Pyodide, in a Web Worker so the page stays responsive.

```bash
uv run python scripts/build_web.py      # writes build/site: web/ plus the wheels Pyodide installs
python -m http.server -d build/site     # then open http://localhost:8000
```

- `index.html`, `style.css`, `app.js`: the page. Plots use Plotly, pinned to 2.35.2 with an integrity hash.
- `worker.js`: loads Pyodide (pinned to 0.29.5 from jsdelivr) and the wheels, and answers requests from `app.js`.
- `integrator.js`: the integrator in JavaScript, about 100x faster than Pyodide running the Python one. The Python
  version in `src/lagrangepointsimulator/numba_funcs.py` is the reference, so keep the two in step.
- `py/bridge.py`: the Python the worker runs. It mirrors the parameters of `sim_gui.py` and the data preparation of
  `orbit_plotter.py`, which can't be imported there because they need Qt.
