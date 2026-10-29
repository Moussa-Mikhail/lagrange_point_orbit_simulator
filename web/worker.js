// Runs Pyodide and the simulator off the UI thread.
// Requests are {id, type, payload}. Replies are {id, ok, result} or {id, ok: false, error}.
// {type: "status", text} messages report loading progress.

const PYODIDE_VERSION = "0.29.5";

importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`, "integrator.js");

const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let bridge;

// Pyodide asks for numpy only once it has started. Fetching it now, beside Pyodide, leaves it in the HTTP cache by then.
const numpyDownload = (async () => {
  try {
    const lock = await (await fetch(`${PYODIDE_URL}pyodide-lock.json`)).json();
    await (await fetch(`${PYODIDE_URL}${lock.packages.numpy.file_name}`)).arrayBuffer();
  } catch {
    // loadPackage fetches it again and reports the failure
  }
})();

function status(text) {
  self.postMessage({ type: "status", text });
}

async function fetchBuffer(path) {
  const response = await fetch(new URL(path, self.location));
  if (!response.ok) throw new Error(`Failed to fetch ${path}: ${response.status}`);
  return response.arrayBuffer();
}

async function init() {
  status("Loading Python…");
  const pyodide = await loadPyodide();

  status("Loading numpy…");
  await numpyDownload;
  await pyodide.loadPackage("numpy");

  status("Loading simulator…");
  const manifest = JSON.parse(new TextDecoder().decode(await fetchBuffer("wheels/manifest.json")));
  for (const wheel of manifest.wheels) {
    await pyodide.unpackArchive(await fetchBuffer(`wheels/${wheel}`), "wheel");
  }

  pyodide.runPython(new TextDecoder().decode(await fetchBuffer("py/bridge.py")));
  bridge = {
    get_spec: pyodide.globals.get("get_spec"),
    prepare: pyodide.globals.get("prepare"),
    finish: pyodide.globals.get("finish"),
    conserved: pyodide.globals.get("conserved"),
    report: pyodide.globals.get("report"),
    get_user_text: pyodide.globals.get("get_user_text"),
    set_user_text: pyodide.globals.get("set_user_text"),
    save_preset: pyodide.globals.get("save_preset"),
    delete_preset: pyodide.globals.get("delete_preset"),
  };

  return bridge.get_spec();
}

function collectBuffers(value, buffers = []) {
  if (ArrayBuffer.isView(value)) {
    buffers.push(value.buffer);
  } else if (value && typeof value === "object") {
    for (const child of Object.values(value)) collectBuffers(child, buffers);
  }
  return buffers;
}

const handlers = {
  init,
  // Python validates the inputs and sets up the first row, JS integrates, and Python prepares the plot data.
  simulate: (inputs) => {
    const setup = bridge.prepare(inputs);
    if (setup.error) return setup;
    const rows = integrate(setup.timeStep, setup.numSteps, setup.gStar, setup.gPlanet, setup.state, setup.step);
    return bridge.finish(rows);
  },
  conserved: () => bridge.conserved(),
  report: () => bridge.report(),
  // the user's presets, see bridge.py
  getPresetsText: () => bridge.get_user_text(),
  setPresetsText: (text) => bridge.set_user_text(text),
  savePreset: ({ name, values }) => bridge.save_preset(name, values),
  deletePreset: (name) => bridge.delete_preset(name),
};

self.onmessage = async ({ data: { id, type, payload } }) => {
  try {
    const result = await handlers[type](payload);
    self.postMessage({ id, ok: true, result }, collectBuffers(result));
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error.message ?? error) });
  }
};
