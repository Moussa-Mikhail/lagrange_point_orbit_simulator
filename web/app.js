// Main-thread UI. All simulation work happens in worker.js.
const worker = new Worker("worker.js");

const pending = new Map();
let nextId = 0;

worker.onmessage = ({ data }) => {
  if (data.type === "status") {
    setStatus(data.text);
    return;
  }
  const { resolve, reject } = pending.get(data.id);
  pending.delete(data.id);
  if (data.ok) resolve(data.result);
  else reject(new Error(data.error));
};

function request(type, payload) {
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, payload });
  });
}

const $ = (id) => document.getElementById(id);

const BUTTONS = {
  simulate: $("simulate"),
  toggleAnimation: $("toggle-animation"),
  plotConserved: $("plot-conserved"),
  toggleConserved: $("toggle-conserved"),
};

const COLORS = { star: "#ffff00", planet: "#0000ff", satellite: "#00ff00", lagrange: "#ffffff" };
const COMPONENT_COLORS = ["#ff0000", "#00ff00", "#0000ff"];
const ANIMATION_INTERVAL_MS = 33; // 30 fps

let spec;
const inputFields = {};
let presetSelect;
const presetButtons = {};

// The text of the user's presets file is kept here. The worker's file system doesn't outlast the page.
const PRESETS_STORAGE_KEY = "userPresets";

let plotted = false;
let calculating = false;
let orbitData;
let animationTimer = null;
let animationIndex = 0;

function setStatus(text) {
  $("status").textContent = text;
}

function showError(message) {
  $("error-message").textContent = message;
  $("error").showModal();
}

function withUnits(label, unit) {
  return unit ? `${label} (${unit})` : label;
}

function buildForm() {
  const form = $("inputs");

  const presetLabel = document.createElement("label");
  presetLabel.textContent = "Presets";
  presetSelect = document.createElement("select");
  presetSelect.addEventListener("change", () => {
    applyPreset(presetSelect.value);
    updateDeleteButton();
  });
  form.append(presetLabel, presetSelect, buildPresetButtons());
  refreshPresets();

  for (const [groupName, params] of Object.entries(spec.groups)) {
    const heading = document.createElement("h2");
    heading.textContent = groupName;
    form.append(heading);

    for (const { label, default: value, unit } of params) {
      const fieldLabel = document.createElement("label");
      fieldLabel.textContent = withUnits(label, unit);
      const field = document.createElement("input");
      field.type = "text";
      field.value = value;
      field.id = `field-${label.replaceAll(" ", "-")}`;
      fieldLabel.htmlFor = field.id;
      inputFields[label] = field;
      form.append(fieldLabel, field);
    }
  }

  const lagrangeLabel = document.createElement("label");
  lagrangeLabel.textContent = spec.lagrangeLabel;
  const lagrangeSelect = document.createElement("select");
  for (const name of spec.lagrangeLabels) lagrangeSelect.add(new Option(name));
  lagrangeSelect.value = spec.defaultLagrangeLabel;
  inputFields[spec.lagrangeLabel] = lagrangeSelect;
  form.append(lagrangeLabel, lagrangeSelect);

  // Enter in any field runs the simulation
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    simulate();
  });
  form.addEventListener("keydown", (event) => {
    // not on the buttons, where Enter has to press them
    if (event.key === "Enter" && event.target.tagName !== "BUTTON") {
      event.preventDefault();
      simulate();
    }
  });
}

function buildPresetButtons() {
  const row = document.createElement("div");
  row.id = "preset-buttons";

  const actions = {
    save: ["Save as…", savePreset],
    delete: ["Delete", deletePreset],
    edit: ["Edit…", editPresets],
    export: ["Export", exportPresets],
    import: ["Import…", () => importInput.click()],
  };
  for (const [key, [text, action]] of Object.entries(actions)) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", action);
    presetButtons[key] = button;
    row.append(button);
  }

  const importInput = document.createElement("input");
  importInput.type = "file";
  importInput.id = "import-presets";
  importInput.accept = ".toml,text/plain";
  importInput.hidden = true;
  importInput.addEventListener("change", async () => {
    const [file] = importInput.files;
    importInput.value = "";
    if (file) await importPresets(await file.text(), file.name);
  });
  row.append(importInput);

  return row;
}

// Reload the list of presets, keeping the current one selected unless selected is given.
function refreshPresets(selected = presetSelect.value) {
  presetSelect.replaceChildren(...Object.keys(spec.presets).map((name) => new Option(name)));
  if (selected in spec.presets) presetSelect.value = selected;
  updateDeleteButton();
}

// Only the user's own presets can be deleted.
function updateDeleteButton() {
  presetButtons.delete.disabled = !spec.userPresets.includes(presetSelect.value);
}

// result is what the worker returns after the presets changed: {error} or {text, presets, userPresets}
function adoptPresets(result) {
  spec.presets = result.presets;
  spec.userPresets = result.userPresets;
  try {
    localStorage.setItem(PRESETS_STORAGE_KEY, result.text);
  } catch {
    // storage can be blocked, the presets then last until the page closes
  }
}

async function changePresets(task, selected) {
  const result = await task().catch((error) => ({ error: error.message }));
  if (result.error) {
    showError(result.error);
    return false;
  }
  adoptPresets(result);
  if (presetSelect) refreshPresets(selected);
  return true;
}

async function savePreset() {
  const input = $("preset-name");
  input.value = spec.userPresets.includes(presetSelect.value) ? presetSelect.value : "";
  const dialog = $("save-preset");
  dialog.returnValue = "";
  dialog.showModal();
  input.select();

  await new Promise((resolve) => dialog.addEventListener("close", resolve, { once: true }));
  const name = input.value.trim();
  if (dialog.returnValue !== "save" || !name) return;

  if (name in spec.presets) {
    const kind = spec.userPresets.includes(name) ? "one of your presets" : "a built-in preset";
    if (!confirm(`'${name}' is ${kind}. Replace it?`)) return;
  }

  const values = Object.fromEntries(Object.entries(inputFields).map(([label, field]) => [label, field.value]));
  await changePresets(() => request("savePreset", { name, values }), name);
}

async function deletePreset() {
  const name = presetSelect.value;
  if (!confirm(`Delete the preset '${name}'?`)) return;
  await changePresets(() => request("deletePreset", name));
}

async function editPresets() {
  $("presets-text").value = await request("getPresetsText");
  $("presets-error").textContent = "";
  $("edit-presets").showModal();
}

async function savePresetsText() {
  const result = await request("setPresetsText", $("presets-text").value).catch((error) => ({ error: error.message }));
  if (result.error) {
    $("presets-error").textContent = result.error;
    return;
  }
  adoptPresets(result);
  refreshPresets();
  $("edit-presets").close();
}

async function exportPresets() {
  const text = await request("getPresetsText");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  link.download = "user_presets.toml";
  link.click();
  URL.revokeObjectURL(link.href);
}

async function importPresets(text, fileName) {
  if (!confirm(`Replace your presets with the contents of ${fileName}?`)) return;
  await changePresets(() => request("setPresetsText", text));
}

$("presets-save").addEventListener("click", savePresetsText);
$("presets-cancel").addEventListener("click", () => $("edit-presets").close());

function applyPreset(name) {
  const preset = spec.presets[name];
  for (const base of preset.bases ?? []) applyPreset(base);
  for (const [label, value] of Object.entries(preset)) {
    if (label !== "bases") inputFields[label].value = String(value);
  }
}

function setButtons(enabled, { except } = {}) {
  for (const [name, button] of Object.entries(BUTTONS)) button.disabled = !enabled && name !== except;
}

// Plots

const AXIS = { gridcolor: "#333", zerolinecolor: "#555", linecolor: "#777", tickcolor: "#777" };

function layout(title, xTitle, yTitle, { locked = false } = {}) {
  return {
    title: { text: title, font: { size: 13 } },
    paper_bgcolor: "#000",
    plot_bgcolor: "#000",
    font: { color: "#ccc" },
    margin: { l: 60, r: 15, t: 40, b: 45 },
    xaxis: { ...AXIS, title: { text: xTitle } },
    // automargin widens the left margin so wide tick labels like "-1.5e-14" don't run into the axis title
    yaxis: { ...AXIS, title: { text: yTitle, standoff: 8 }, automargin: true, ...(locked ? { scaleanchor: "x", scaleratio: 1 } : {}) },
    legend: { x: 1, xanchor: "right", y: 1, bgcolor: "rgba(0,0,0,0.4)" },
  };
}

const PLOT_CONFIG = { responsive: true, displaylogo: false };

function line(x, y, name, color) {
  return { type: "scattergl", mode: "lines", x, y, name, line: { color, width: 1 } };
}

function body({ x, y }) {
  return { x, y, n: x.length };
}

// The animated bodies are drawn on a canvas over the plot. Updating a Plotly trace every frame redraws the
// whole WebGL plot, which can't keep up with 30 fps for 10^5 points.
class MarkerOverlay {
  constructor(plotId, overlayId) {
    this.plot = $(plotId);
    this.canvas = $(overlayId);
    this.markers = [];
    this.attached = false;
  }

  // Call after the first Plotly.react, which is what adds .on to the plot element.
  attach() {
    if (this.attached) return;
    this.attached = true;
    // keep the markers in place when the user zooms, pans or resizes
    this.plot.on("plotly_afterplot", () => this.draw());
  }

  set(markers) {
    this.markers = markers;
    this.draw();
  }

  draw() {
    const layout = this.plot._fullLayout;
    if (!layout) return;

    const ratio = window.devicePixelRatio || 1;
    const { width, height } = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.round(width * ratio);
    this.canvas.height = Math.round(height * ratio);

    const context = this.canvas.getContext("2d");
    context.scale(ratio, ratio);

    const { xaxis, yaxis } = layout;
    for (const { x, y, color } of this.markers) {
      const px = xaxis._offset + xaxis.l2p(x);
      const py = yaxis._offset + yaxis.l2p(y);
      // skip bodies outside the visible plot area
      if (px < xaxis._offset || px > xaxis._offset + xaxis._length) continue;
      if (py < yaxis._offset || py > yaxis._offset + yaxis._length) continue;

      context.beginPath();
      context.arc(px, py, MARKER_RADIUS, 0, 2 * Math.PI);
      context.fillStyle = color;
      context.fill();
    }
  }
}

const MARKER_RADIUS = 5;
const BODY_NAMES = ["Star", "Planet", "Satellite"];
const BODY_COLORS = [COLORS.star, COLORS.planet, COLORS.satellite];

const overlays = {
  inertial: new MarkerOverlay("inertial-plot", "inertial-overlay"),
  corotating: new MarkerOverlay("corotating-plot", "corotating-overlay"),
};

function markersAt(bodies, i) {
  return bodies.map((b, k) => ({ x: b.x[i], y: b.y[i], color: BODY_COLORS[k] }));
}

function orbitTraces(bodies, extra = []) {
  const lines = bodies.map((b, i) => ({ ...line(b.x, b.y, BODY_NAMES[i], BODY_COLORS[i]), showlegend: false }));
  // Plots nothing. These only give the legend a marker for each body.
  const legend = BODY_NAMES.map((name, i) => ({
    type: "scatter",
    mode: "markers",
    x: [null],
    y: [null],
    name,
    marker: { color: BODY_COLORS[i], size: 10 },
  }));
  return [...lines, ...legend, ...extra];
}

function plotOrbits(data) {
  const inertial = data.inertial.map(body);
  const corotating = data.corotating.map(body);
  orbitData = { ...data, inertial, corotating };

  const [lx, ly] = data.lagrangePoint;
  const lagrangeTrace = {
    type: "scatter",
    mode: "markers",
    x: [lx],
    y: [ly],
    name: data.lagrangeLabel,
    marker: { color: COLORS.lagrange, size: 10 },
  };

  Plotly.react(
    "inertial-plot",
    orbitTraces(inertial),
    layout("Orbit in Inertial Coordinate System", "x (AU)", "y (AU)", { locked: true }),
    PLOT_CONFIG,
  );
  Plotly.react(
    "corotating-plot",
    orbitTraces(corotating, [lagrangeTrace]),
    layout("Orbit in Co-Rotating Coordinate System", "x (AU)", "y (AU)", { locked: true }),
    PLOT_CONFIG,
  );

  overlays.inertial.attach();
  overlays.corotating.attach();
  overlays.inertial.set(markersAt(inertial, 0));
  overlays.corotating.set(markersAt(corotating, 0));
}

function plotConserved(data) {
  const components = (arrays) =>
    ["x", "y", "z"].map((name, i) => line(data.times, arrays[i], name, COMPONENT_COLORS[i]));

  const quantities = [
    ["linear-momentum-plot", "Linear Momentum", components(data.linearMomentum)],
    ["angular-momentum-plot", "Angular Momentum", components(data.angularMomentum)],
    ["energy-plot", "Energy", [line(data.times, data.energy, "Energy", "#ffffff")]],
  ];

  $("conserved").hidden = false;
  for (const [id, name, traces] of quantities) {
    const yTitle = `Relative Change in ${name}`;
    const plotLayout = layout(`${yTitle} vs Time`, "Time (years)", yTitle);
    // tiny values would otherwise get SI prefixes like "10f"
    plotLayout.yaxis.exponentformat = "e";
    Plotly.react(id, traces, plotLayout, PLOT_CONFIG);
  }
}

// Animation

function stopAnimation() {
  clearInterval(animationTimer);
  animationTimer = null;
}

function toggleAnimation() {
  if (!plotted) {
    showError("No plots to animate.");
    return;
  }
  if (animationTimer !== null) {
    stopAnimation();
    return;
  }
  animationTimer = setInterval(animateFrame, ANIMATION_INTERVAL_MS);
}

function animateFrame() {
  // The orbits are decimated by `step` so the full-resolution index is scaled down.
  const { numSteps, animationRate, step, inertial, corotating } = orbitData;
  animationIndex += animationRate;
  if (animationIndex >= numSteps) animationIndex = 0;

  for (const [overlay, bodies] of [[overlays.inertial, inertial], [overlays.corotating, corotating]]) {
    const i = Math.min(Math.floor(animationIndex / step), bodies[0].n - 1);
    overlay.set(markersAt(bodies, i));
  }
}

// Actions

async function run(task, { except } = {}) {
  calculating = true;
  setButtons(false, { except });
  try {
    return await task();
  } finally {
    calculating = false;
    setButtons(true);
  }
}

async function simulate() {
  if (calculating) return;

  const inputs = Object.fromEntries(Object.entries(inputFields).map(([label, field]) => [label, field.value]));

  stopAnimation();
  setStatus("Simulating…");
  const start = performance.now();

  const result = await run(() => request("simulate", inputs)).catch((error) => ({ error: error.message }));
  if (result.error) {
    setStatus("");
    showError(result.error);
    return;
  }

  plotOrbits(result);
  plotted = true;
  animationIndex = 0;
  setStatus(`Simulated ${result.numSteps.toLocaleString()} steps in ${((performance.now() - start) / 1000).toFixed(2)} s`);

  if ($("auto-plot-conserved").checked) await plotConservedQuantities();
}

async function plotConservedQuantities() {
  if (!plotted) {
    showError("No data to plot.");
    return;
  }
  const result = await run(() => request("conserved"), { except: "toggleAnimation" }).catch((error) => ({
    error: error.message,
  }));
  if (result.error) {
    showError(result.error);
    return;
  }
  plotConserved(result);
}

function toggleConservedPlots() {
  const section = $("conserved");
  section.hidden = !section.hidden;
  if (!section.hidden) {
    for (const id of ["linear-momentum-plot", "angular-momentum-plot", "energy-plot"]) {
      if ($(id).data) Plotly.Plots.resize(id);
    }
  }
}

BUTTONS.simulate.addEventListener("click", simulate);
BUTTONS.toggleAnimation.addEventListener("click", toggleAnimation);
BUTTONS.plotConserved.addEventListener("click", plotConservedQuantities);
BUTTONS.toggleConserved.addEventListener("click", toggleConservedPlots);

try {
  spec = await request("init");

  let stored = null;
  try {
    stored = localStorage.getItem(PRESETS_STORAGE_KEY);
  } catch {
    // storage can be blocked
  }
  if (stored) {
    const loaded = await request("setPresetsText", stored);
    if (loaded.error) showError(`Your saved presets could not be loaded.\n${loaded.error}`);
    else adoptPresets(loaded);
  }

  buildForm();
  setButtons(true);
  setStatus("Ready");
} catch (error) {
  setStatus("");
  showError(`Failed to start: ${error.message}`);
}
