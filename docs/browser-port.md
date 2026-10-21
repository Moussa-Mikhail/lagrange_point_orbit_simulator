# Browser-only (Pyodide) port

Goal: a static site that runs the simulator entirely in the browser, hosted on GitHub Pages. No server-side compute. The desktop app stays unchanged.

## Decisions already made
- Runtime is Pyodide. Do not try to get Qt/PySide or Numba running in the browser: there is no WASM build of the Qt bindings, and Numba needs llvmlite, which Pyodide doesn't have.
- Slower integration than Numba is acceptable for now. Do not rewrite kernels in Cython or Rust unless asked.
- No SharedArrayBuffer or multithreading. GitHub Pages cannot set COOP/COEP headers.
- Pin the Pyodide version exactly and use only packages in that release's package list. Report anything needed that isn't there.
- Every asset the page loads must come from the repo or a pinned, versioned CDN URL.

## Phase 0: Investigate (no code changes)
Read the repo and report:
1. Whether the core imports Qt/GUI code anywhere, and every non-pure-Python dependency it needs.
2. Every use of Numba (decorators and options such as `inline`, `cache`, `parallel`, `fastmath`) and whether any code depends on Numba-specific behavior.
3. Which plotting library the GUI uses, and every plot, control, and dialog, so I know what a web UI must reproduce.
4. How `Plotter` and `Simulator` are coupled, and whether that must change for a web front end.

Stop and summarize before Phase 1.

## Phase 1: Core runs without Numba
- Make `njit` a no-op when Numba isn't installed. It must accept both `@njit` and `@njit(...)` with keyword options, including `inline`. Numba must not be a hard dependency of the browser build.

## Phase 2: Core in Pyodide
- Build the core as a pure-Python wheel and load it in Pyodide (Node-based Pyodide is fine for CI).
- Run a representative simulation and report wall-clock time in Pyodide versus native Numba.

Stop and report the numbers. I will decide whether to continue to the UI based on them.

## Phase 3: Web UI
- Static page (plain HTML/JS or a small framework; justify the choice) that loads Pyodide in a Web Worker so the UI thread never blocks.
- Controls match the desktop GUI's inputs, and layout and control names follow it as closely as reasonable.
- Plots use a JS-rendered library (e.g. Plotly), not matplotlib, unless the plots are static.

## Phase 4: Deploy
- GitHub Actions workflow that builds the wheel and site and publishes to GitHub Pages.

## Reporting
At the end of each phase, report what was done, how it was verified, and what is still open. Make one commit per phase.

## Out of scope
Cython/Rust ports, Qt for WebAssembly, and desktop refactors. If a phase cannot be completed without one of these, ask first.
