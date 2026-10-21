// Runs Pyodide and the simulator off the UI thread.
// Requests are {id, type, payload}. Replies are {id, ok, result} or {id, ok: false, error}.
// {type: "status", text} messages report loading progress.

const PYODIDE_VERSION = "0.29.5";

importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`);

let bridge;

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
  await pyodide.loadPackage("numpy");

  status("Loading simulator…");
  const manifest = JSON.parse(new TextDecoder().decode(await fetchBuffer("wheels/manifest.json")));
  for (const wheel of manifest.wheels) {
    await pyodide.unpackArchive(await fetchBuffer(`wheels/${wheel}`), "wheel");
  }

  pyodide.runPython(new TextDecoder().decode(await fetchBuffer("py/bridge.py")));
  bridge = {
    get_spec: pyodide.globals.get("get_spec"),
    simulate: pyodide.globals.get("simulate"),
    conserved: pyodide.globals.get("conserved"),
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
  simulate: (inputs) => bridge.simulate(inputs),
  conserved: () => bridge.conserved(),
};

self.onmessage = async ({ data: { id, type, payload } }) => {
  try {
    const result = await handlers[type](payload);
    self.postMessage({ id, ok: true, result }, collectBuffers(result));
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error.message ?? error) });
  }
};
