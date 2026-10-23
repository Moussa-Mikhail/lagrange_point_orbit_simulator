# Browser port

A static site that runs the simulator entirely in the browser, hosted on GitHub Pages: https://moussa-mikhail.github.io/lagrange_point_orbit_simulator/. There is no server-side compute, and the desktop app is unchanged. `web/README.md` covers building and the file layout.

## How it works
- Pyodide runs in a Web Worker, so the page stays responsive. `web/worker.js` loads it, unpacks the project wheels, and answers requests from `web/app.js`.
- Python still validates the inputs, sets the initial conditions and prepares the plot data (`web/py/bridge.py`). The integration itself runs in JavaScript (`web/integrator.js`).
- Plots are drawn with Plotly. The animated markers are drawn on a canvas overlay, because restyling Plotly traces every frame was too slow.
- The form, the presets and the expression evaluator come from the Qt-free `lagrangepointinputs` package, shared with the desktop GUI.
- `scripts/build_web.py` builds `build/site`: the contents of `web/` plus the project wheel and a `validateddescriptor` wheel built from the commit pinned in `requirements.txt`. `deploy-web.yml` runs the checks, builds the site and publishes it.

## Decisions
- **Pyodide, not Qt or Numba.** There is no WASM build of the Qt bindings, and Numba needs llvmlite, which Pyodide doesn't have. The core therefore runs without Numba: `njit` is a no-op and `transform_to_corotating` has a vectorized NumPy fallback.
- **The integrator is duplicated in JavaScript.** The Python integrator under Pyodide took about 1 s for 10 years and 11 s for 100 years. The JavaScript one takes about 0.4 to 0.6 s of page time for 10 years and 0.36 s for 100 years. The Numba version in `src/lagrangepointsimulator/numba_funcs.py` is the reference, and `tests/test_js_integrator.py` checks the JavaScript one against it. Keep the two in step when the algorithm changes.
- **No SharedArrayBuffer or multithreading.** GitHub Pages cannot set the COOP/COEP headers it needs.
- **Everything is pinned.** Pyodide is pinned to an exact version and only uses packages from that release. Every other asset comes from the repo or a pinned, versioned CDN URL (Plotly carries an integrity hash).

## Known limits
- The browser test (`tests/e2e`) loads the built site in Chromium and checks that simulations, presets, the conserved plots and error reporting work. It doesn't check how the plots look, and it needs network access because the page loads Pyodide and Plotly from their CDNs.
- Long runs aren't streamed to the UI and can't be cancelled.
