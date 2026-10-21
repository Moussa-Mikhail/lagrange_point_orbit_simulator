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
  for (const name of Object.keys(spec.presets)) presetSelect.add(new Option(name));
  presetSelect.addEventListener("change", () => applyPreset(presetSelect.value));
  form.append(presetLabel, presetSelect);

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
    if (event.key === "Enter") {
      event.preventDefault();
      simulate();
    }
  });
}

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
  buildForm();
  setButtons(true);
  setStatus("Ready");
} catch (error) {
  setStatus("");
  showError(`Failed to start: ${error.message}`);
}
