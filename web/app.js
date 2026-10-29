// Main-thread UI. All simulation work happens in worker.js.
const worker = window.simulatorWorker; // started by index.html

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
const ANIMATION_STEPS_PER_SECOND = 30; // the animation advances this many times a second, each by animationRate steps

let spec;
const inputFields = {};
let presetSelect;
const presetButtons = {};

// The text of the user's presets file is kept here. The worker's file system doesn't outlast the page.
const PRESETS_STORAGE_KEY = "userPresets";

let plotted = false;
let calculating = false;
let orbitData;
let animationFrameId = null;
let animationLastTime = 0;
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
    save: ["Save…", savePreset],
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

// the axes are drawn the way the desktop app draws them: a line and inward ticks, no grid
const AXIS = { title: { font: { size: 17 } }, ticklabeloverflow: "allow", showgrid: false, zeroline: false, linecolor: "#999", tickcolor: "#999", ticks: "inside", ticklen: 7 };

// The space around the data in the desktop's plots, in pixels, measured from pyqtgraph: the left margin is the width of
// the y axis, which is wider when its labels are, see setTicks
const MARGIN = { l: 57.6, r: 0.5, t: 31, b: 42.1 };
const MIN_LEFT_MARGIN = MARGIN.l;
const LABEL_MARGIN = 27.4; // what the y axis needs beside its widest label: ticks, the axis title and spacing

// The y title, which is also placed by hand, 10 px from the left. The desktop centres it on the data, a pixel above the
// middle, except that its long titles, the ones about momentum, sit 32 px higher.
function yTitleAnnotation(text, left, width, height) {
  const dataHeight = height - MARGIN.t - MARGIN.b;
  const centre = MARGIN.t + dataHeight / 2 - 0.5 - (measureText(text) > 300 ? 32 : 0);
  return {
    text,
    textangle: -90,
    xref: "paper",
    x: (9 - left) / (width - left - MARGIN.r),
    xanchor: "center",
    yref: "paper",
    y: 1 - (centre - MARGIN.t) / dataHeight,
    yanchor: "middle",
    showarrow: false,
    font: { size: 17, color: "#b3b3b3" },
  };
}

function layout(title, xTitle, yTitle, plotId, { locked = false, yRange = null, xRange = null } = {}) {
  const { clientWidth: width, clientHeight: height } = $(plotId);
  const dataHeight = height - MARGIN.t - MARGIN.b;
  return {
    // centred over the data, 16 px from the top, as in the desktop
    title: { text: title, font: { size: 15, color: "#b3b3b3" }, xref: "container", yref: "container", x: (MARGIN.l + (width - MARGIN.l - MARGIN.r) / 2) / width, xanchor: "center", y: 1 - 16 / height, yanchor: "middle" },
    paper_bgcolor: "#000",
    plot_bgcolor: "#000",
    font: { family: "Arial, Liberation Sans, sans-serif", color: "#b3b3b3", size: 17 },
    margin: { l: MARGIN.l, r: MARGIN.r, t: MARGIN.t, b: MARGIN.b },
    xaxis: { ...AXIS, ticklabelstandoff: -6, title: { ...AXIS.title, text: "" }, ...(xRange ? { range: xRange, autorange: false } : {}) },
    yaxis: { ...AXIS, title: { ...AXIS.title, text: "" }, ...(locked ? { scaleanchor: "x", scaleratio: 1 } : {}), ...(yRange ? { range: yRange, autorange: false } : {}) },
    // The x title is placed by hand: the space under the data is as small as the desktop's, and too small for Plotly to
    // put the title under the tick labels
    annotations: [
      { text: xTitle, xref: "x domain", x: 0.5, yref: "paper", y: -32 / dataHeight, yanchor: "middle", showarrow: false, font: { size: 17, color: "#b3b3b3" } },
      yTitleAnnotation(yTitle, MARGIN.l, width, height),
    ],
    showlegend: false, // see setLegend
    hovermode: false, // looking up the point under the mouse in 10^5 points blocks the page, and the animation with it
  };
}

const PLOT_CONFIG = { responsive: true, displaylogo: false };

// Ticks the way the desktop app's pyqtgraph writes them: "1.0", "0.5", "0", "-0.5", spaced about 85 px apart on x and 45 px on y, with the
// SI prefix of the largest value in the axis title, like "y (mAU)", or "(x1e-15)" when the axis has no unit.
const SI_PREFIXES = { "-15": "f", "-12": "p", "-9": "n", "-6": "µ", "-3": "m", 0: "", 3: "k", 6: "M" };
const MIN_TICK_PIXELS = { xaxis: 85, yaxis: 45 };

function niceStep(minimum) {
  const power = Math.floor(Math.log10(minimum));
  return [1, 2, 5, 10].map((m) => m * 10 ** power).find((step) => step >= minimum);
}

// {tickvals, ticktext, title} for an axis spanning range over pixels, or null when it isn't drawn yet
function pyqtgraphAxis(key, { name, unit, siPrefix = true }, [low, high], pixels) {
  if (!pixels || !(high > low)) return null;

  const largest = Math.max(Math.abs(low), Math.abs(high));
  const exponent = siPrefix ? Math.min(6, Math.max(-15, 3 * Math.floor(Math.log10(largest) / 3))) : 0;
  const scale = 10 ** exponent;
  const step = niceStep((MIN_TICK_PIXELS[key] * (high - low)) / pixels / scale);
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));

  const tickvals = [];
  const ticktext = [];
  for (let i = Math.ceil(low / scale / step - 1e-9); i * step * scale <= high * (1 + 1e-12); i++) {
    tickvals.push(i * step * scale);
    ticktext.push(i === 0 ? "0" : (i * step).toFixed(decimals));
  }

  const prefix = unit ? SI_PREFIXES[exponent] + unit : exponent ? `x1e${exponent}` : "";
  return { tickvals, ticktext, minorStep: (step * scale) / 10, title: prefix ? `${name} (${prefix})` : name };
}

// Plotly chooses its own ticks, so they are set after every draw, and again when the range changes by zooming.
function matchTicks(plot, specs) {
  plot._tickSpecs = specs;
  if (!plot._ticksHooked) {
    plot._ticksHooked = true;
    plot.on("plotly_afterplot", () => setTicks(plot));
  }
  setTicks(plot); // the plot is already drawn
}

function setTicks(plot) {
  const update = {};
  let yLabels = [];
  let xTitle = null;
  let yTitle = null;
  for (const key of ["xaxis", "yaxis"]) {
    const axis = plot._fullLayout[key];
    const ticks = pyqtgraphAxis(key, plot._tickSpecs[key], axis.range, axis._length);
    if (!ticks) continue;
    if (key === "yaxis") yLabels = ticks.ticktext;
    const current = plot.layout[key] ?? {};
    if (key === "xaxis") xTitle = ticks.title;
    if (key === "yaxis") yTitle = ticks.title;
    if (current.tickmode === "array" && current.ticktext?.join() === ticks.ticktext.join()) continue;
    Object.assign(update, {
      [`${key}.tickmode`]: "array",
      [`${key}.tickvals`]: ticks.tickvals,
      [`${key}.ticktext`]: ticks.ticktext,
      [`${key}.minor.ticks`]: "inside",
      [`${key}.minor.ticklen`]: 4.5,
      [`${key}.minor.dtick`]: ticks.minorStep,
    });
  }
  // the y axis is as wide as its widest label needs, but not narrower than the desktop's
  const widest = Math.max(0, ...yLabels.map((text) => measureText(text)));
  const left = Math.max(MIN_LEFT_MARGIN, widest + LABEL_MARGIN);
  if (Math.abs(left - plot.layout.margin.l) > 0.05) update["margin.l"] = left;

  // the title follows the prefix of the ticks, as in "Time (kyears)" for a thousand years
  if (xTitle !== null && plot.layout.annotations[0].text !== xTitle) update["annotations[0].text"] = xTitle;

  if (yTitle !== null) {
    const { clientWidth: width, clientHeight: height } = plot;
    const annotation = yTitleAnnotation(yTitle, left, width, height);
    const current = plot.layout.annotations[1];
    for (const [name, value] of Object.entries(annotation)) {
      if (name !== "font" && current[name] !== value) update[`annotations[1].${name}`] = value;
    }
  }

  if (Object.keys(update).length) Plotly.relayout(plot, update);
}

const textContext = document.createElement("canvas").getContext("2d");
function measureText(text) {
  textContext.font = "17px Arial, Liberation Sans, sans-serif";
  return textContext.measureText(text).width;
}

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
    this.top = []; // markers that stay put, drawn over the moving ones, like the desktop's Lagrange point
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
    for (const { x, y, color } of [...this.markers, ...this.top]) {
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

// The bodies at position i in their points, between two points when i isn't a whole number
function markersAt(bodies, position) {
  return bodies.map((b, k) => {
    const from = Math.min(Math.floor(position), b.n - 1);
    const to = Math.min(from + 1, b.n - 1);
    const along = position - from;
    return { x: b.x[from] + (b.x[to] - b.x[from]) * along, y: b.y[from] + (b.y[to] - b.y[from]) * along, color: BODY_COLORS[k] };
  });
}

function orbitTraces(bodies, extra = []) {
  const lines = bodies.map((b, i) => ({ ...line(b.x, b.y, BODY_NAMES[i], BODY_COLORS[i]), showlegend: false }));
  return [...lines, ...extra];
}

// The range of an axis with the space around it that the desktop's plots leave, as a fraction of the range on each side.
// Plotly's own autorange leaves more.
// measured from pyqtgraph's view ranges in the desktop's plots, as fractions of the data range on each side
const ORBIT_PADDING = { x: 0.0652, y: 0.034 };
const CONSERVED_PADDING = { x: 0.0441, y: 0.0515 };

function paddedRange(bodies, axis, extra = [], padding = ORBIT_PADDING[axis]) {
  let low = Infinity;
  let high = -Infinity;
  for (const body of bodies) {
    const values = body[axis];
    for (let i = 0; i < values.length; i++) {
      if (values[i] < low) low = values[i];
      if (values[i] > high) high = values[i];
    }
  }
  for (const value of extra) {
    low = Math.min(low, value);
    high = Math.max(high, value);
  }
  const pad = padding * (high - low);
  return [low - pad, high + pad];
}

// Ranges for x and y that show the padded ranges at the same scale, which Plotly would otherwise work out from the
// size of the plot before its axes have taken their space. The data area is what the margins in layout() leave.
function equalScaleRanges(plotId, xRange, yRange, xShift = 0) {
  const width = $(plotId).clientWidth - MARGIN.l - MARGIN.r;
  const height = $(plotId).clientHeight - MARGIN.t - MARGIN.b;
  const scale = Math.min(width / (xRange[1] - xRange[0]), height / (yRange[1] - yRange[0]));
  const around = ([low, high], pixels, shift = 0) => [(low + high) / 2 + shift - pixels / (2 * scale), (low + high) / 2 + shift + pixels / (2 * scale)];
  return { xRange: around(xRange, width, xShift), yRange: around(yRange, height) };
}

// pyqtgraph centres the inertial plot a little to the right of its data: by this fraction of the data's width
const INERTIAL_X_SHIFT = 0.00775;

// Plotly's legend can't be put where, and spaced as, the desktop's is, so the legend is HTML over the plot.
// entries: [{name, color, dot}], a dot for a body and a line for a component
function setLegend(plotId, entries) {
  const container = $(plotId).closest(".plot");
  let legend = container.querySelector(".legend");
  if (!legend) {
    legend = document.createElement("div");
    legend.className = "legend";
    container.append(legend);
  }
  legend.replaceChildren(
    ...entries.map(({ name, color, dot }) => {
      const row = document.createElement("div");
      const swatch = document.createElement("span");
      swatch.className = dot ? "dot" : "swatch";
      swatch.style.background = color;
      const label = document.createElement("span");
      label.className = "name";
      label.textContent = name;
      row.append(swatch, label);
      return row;
    }),
  );
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

  const inertialX = paddedRange(inertial, "x");
  const inertialWidth = (inertialX[1] - inertialX[0]) / (1 + 2 * ORBIT_PADDING.x); // of the data, without the padding
  // no prefix such as "mAU", so that a difference of 1 on x and on y is the same length and reads the same
  const orbitAxes = { xaxis: { name: "x", unit: "AU", siPrefix: false }, yaxis: { name: "y", unit: "AU", siPrefix: false } };
  Plotly.react(
    "inertial-plot",
    orbitTraces(inertial),
    layout("Orbit in Inertial Coordinate System", "x (AU)", "y (AU)", "inertial-plot", { locked: true, ...equalScaleRanges("inertial-plot", inertialX, paddedRange(inertial, "y"), INERTIAL_X_SHIFT * inertialWidth) }),
    PLOT_CONFIG,
  ).then((plot) => matchTicks(plot, orbitAxes));
  Plotly.react(
    "corotating-plot",
    orbitTraces(corotating, [lagrangeTrace]),
    layout("Orbit in Co-Rotating Coordinate System", "x (AU)", "y (AU)", "corotating-plot", { locked: true, ...equalScaleRanges("corotating-plot", paddedRange(corotating, "x", [lx]), paddedRange(corotating, "y", [ly])) }),
    PLOT_CONFIG,
  ).then((plot) => matchTicks(plot, orbitAxes));

  const bodyEntries = BODY_NAMES.map((name, i) => ({ name, color: BODY_COLORS[i], dot: true }));
  setLegend("inertial-plot", bodyEntries);
  setLegend("corotating-plot", [...bodyEntries, { name: data.lagrangeLabel, color: COLORS.lagrange, dot: true }]);
  overlays.corotating.top = [{ x: lx, y: ly, color: COLORS.lagrange }];
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
    const span = data.times.at(-1) - data.times[0];
    const plotLayout = layout(`${yTitle} vs Time`, "Time (years)", yTitle, id, {
      xRange: [data.times[0] - CONSERVED_PADDING.x * span, data.times.at(-1) + CONSERVED_PADDING.x * span],
      yRange: paddedRange(traces, "y", [], CONSERVED_PADDING.y),
    });
    // only the momenta have more than one line
    if (traces.length > 1) setLegend(id, traces.map((trace) => ({ name: trace.name, color: trace.line.color })));
    Plotly.react(id, traces, plotLayout, PLOT_CONFIG).then((plot) =>
      matchTicks(plot, { xaxis: { name: "Time", unit: "years" }, yaxis: { name: yTitle, unit: "" } }),
    );
  }
}

// Animation

function stopAnimation() {
  cancelAnimationFrame(animationFrameId);
  animationFrameId = null;
}

function toggleAnimation() {
  if (!plotted) {
    showError("No plots to animate.");
    return;
  }
  if (animationFrameId !== null) {
    stopAnimation();
    return;
  }
  animationLastTime = performance.now();
  animationFrameId = requestAnimationFrame(animateFrame);
}

// Runs for every frame the browser draws, and moves the markers by the time since the last one, so the motion is smooth
// at any refresh rate. The orbits are decimated by `step`, so a frame can move a marker by a fraction of a point, which
// markersAt interpolates; without that the markers would stand still for several frames and then jump.
function animateFrame(now) {
  const { numSteps, animationRate, step, inertial, corotating } = orbitData;
  const elapsed = Math.min((now - animationLastTime) / 1000, 0.1);
  animationLastTime = now;

  animationIndex += animationRate * ANIMATION_STEPS_PER_SECOND * elapsed;
  if (animationIndex >= numSteps) animationIndex = 0;

  for (const [overlay, bodies] of [[overlays.inertial, inertial], [overlays.corotating, corotating]]) {
    overlay.set(markersAt(bodies, animationIndex / step));
  }
  animationFrameId = requestAnimationFrame(animateFrame);
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

  const analytics = await run(() => request("report")).catch((error) => ({ error: error.message }));
  if (analytics.error) showError(analytics.error);
  else showAnalytics(analytics.rows);
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

function showAnalytics(rows) {
  $("analytics-hint").hidden = true;
  $("analytics-rows").replaceChildren(
    ...rows.flatMap(([name, value]) => {
      const term = document.createElement("dt");
      const definition = document.createElement("dd");
      term.textContent = name;
      definition.textContent = value;
      return [term, definition];
    }),
  );
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
