// Loads build/site in Chromium and drives the page. Run `uv run --no-project scripts/build_web.py` first.
// The page loads Pyodide and Plotly from their CDNs, so this needs network access.
// Set CHROMIUM_PATH to use an installed browser instead of the one from `npx playwright install chromium`.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const SITE = fileURLToPath(new URL("../../build/site/", import.meta.url));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };
const LOAD_TIMEOUT = 180_000;

let server, browser, page, url;

before(async () => {
  server = createServer(async (request, response) => {
    let path = normalize(decodeURIComponent(new URL(request.url, "http://x").pathname)).replace(/^(\.\.[/\\])+/, "");
    if (path.endsWith("/")) path += "index.html";
    try {
      const body = await readFile(join(SITE, path));
      response.writeHead(200, { "Content-Type": TYPES[extname(path)] ?? "application/octet-stream" });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  url = `http://127.0.0.1:${server.address().port}/`;

  browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  page = await browser.newPage();
  page.setDefaultTimeout(LOAD_TIMEOUT);
  page.on("pageerror", (error) => assert.fail(`uncaught error in the page: ${error.message}`));
  await page.goto(url);
  await page.waitForFunction(() => !document.getElementById("simulate").disabled);
});

after(async () => {
  await browser?.close();
  server?.close();
});

const plotTraces = (id) => page.evaluate((id) => document.getElementById(id).data?.length ?? 0, id);
const errorMessage = () => page.evaluate(() => (document.getElementById("error").open ? document.getElementById("error-message").textContent : null));

async function simulate() {
  await page.click("#simulate");
  await page.waitForFunction(() => !document.getElementById("simulate").disabled && document.getElementById("inertial-plot").data);
}

test("the preset list and the parameter form are filled in", async () => {
  const presets = await page.$$eval("#inputs select:first-of-type option", (options) => options.map((o) => o.value));
  assert.ok(presets.includes("Default"));
  assert.ok(presets.includes("Earth Moon"));
  assert.equal(await page.inputValue("#field-star-mass"), "sun_mass");
});

test("the default simulation plots both orbit views", async () => {
  await simulate();

  assert.equal(await errorMessage(), null);
  assert.ok((await plotTraces("inertial-plot")) >= 3, "star, planet and satellite are plotted");
  assert.ok((await plotTraces("corotating-plot")) >= 3);
});

test("a satellite at L4 stays at L4 in the co-rotating view", async () => {
  await simulate();

  // the co-rotating satellite trace is a point near (0.5, 0.87) AU that barely moves
  const spread = await page.evaluate(() => {
    const satellite = document.getElementById("corotating-plot").data.find((trace) => trace.name === "Satellite");
    const range = (values) => Math.max(...values) - Math.min(...values);
    return { x: range(satellite.x), y: range(satellite.y), meanX: satellite.x[0], meanY: satellite.y[0] };
  });
  assert.ok(spread.x < 1e-3 && spread.y < 1e-3, `satellite drifted by ${spread.x}, ${spread.y} AU`);
  assert.ok(Math.abs(spread.meanX - 0.5) < 1e-3 && Math.abs(spread.meanY - 0.866) < 1e-3);
});

test("applying a preset changes the inputs and still simulates", async () => {
  await page.selectOption("#inputs select:first-of-type", "Earth Moon");
  assert.equal(await page.inputValue("#field-star-mass"), "earth_mass");

  await simulate();

  assert.equal(await errorMessage(), null);
  assert.ok((await plotTraces("inertial-plot")) >= 3);
});

test("the conserved quantity plots show", async () => {
  await page.selectOption("#inputs select:first-of-type", "Default");
  await simulate();
  await page.click("#plot-conserved");
  await page.waitForFunction(() => document.getElementById("energy-plot").data);

  assert.equal(await page.isVisible("#conserved"), true);
  assert.ok((await plotTraces("energy-plot")) >= 1);
});

test("hovering the plots does no work, since looking up a point among 10^5 blocks the page and the animation", async () => {
  const hovermodes = await page.evaluate(() =>
    ["inertial-plot", "corotating-plot", "energy-plot"].map((id) => document.getElementById(id)._fullLayout.hovermode),
  );

  assert.deepEqual(hovermodes, [false, false, false]);
});

test("an invalid expression is reported without breaking the page", async () => {
  await page.fill("#field-star-mass", "not_a_constant");
  await page.click("#simulate");
  await page.waitForFunction(() => document.getElementById("error").open);

  assert.match(await errorMessage(), /Invalid expression in field 'star mass'/);

  await page.click("#error button");
  await page.fill("#field-star-mass", "sun_mass");
  await simulate();
  assert.equal(await errorMessage(), null);
});

// User presets

const presetNames = () => page.$$eval("#inputs select:first-of-type option", (options) => options.map((o) => o.value));

async function reload() {
  await page.reload();
  await page.waitForFunction(() => !document.getElementById("simulate").disabled);
}

async function savePresetAs(name) {
  await page.click("text=Save…");
  await page.fill("#preset-name", name);
  await page.keyboard.press("Enter");
  await page.waitForFunction((name) => [...document.querySelectorAll("#inputs select:first-of-type option")].some((o) => o.value === name), name);
}

async function deletePreset(name) {
  await page.selectOption("#inputs select:first-of-type", name);
  page.once("dialog", (dialog) => dialog.accept());
  await page.click("text=Delete");
  await page.waitForFunction((name) => ![...document.querySelectorAll("#inputs select:first-of-type option")].some((o) => o.value === name), name);
}

test("a saved preset applies, survives a reload and can be deleted", async () => {
  await page.selectOption("#inputs select:first-of-type", "Default");
  assert.equal(await page.isDisabled("text=Delete"), true, "built-in presets can't be deleted");

  await page.fill("#field-star-mass", "sun_mass/3");
  await page.fill("#field-initial-speed", "0.95");
  await savePresetAs("Mine");
  assert.equal(await page.inputValue("#inputs select:first-of-type"), "Mine");
  assert.equal(await page.isDisabled("text=Delete"), false);

  await reload();
  assert.ok((await presetNames()).includes("Mine"));
  await page.selectOption("#inputs select:first-of-type", "Default");
  assert.equal(await page.inputValue("#field-star-mass"), "sun_mass");
  await page.selectOption("#inputs select:first-of-type", "Mine");
  assert.equal(await page.inputValue("#field-star-mass"), "sun_mass/3");
  assert.equal(await page.inputValue("#field-initial-speed"), "0.95");

  await simulate();
  assert.equal(await errorMessage(), null);

  await deletePreset("Mine");
  await reload();
  assert.ok(!(await presetNames()).includes("Mine"));
});

test("the presets can be edited as text, and invalid text is refused", async () => {
  await page.click("text=Edit…");
  await page.fill("#presets-text", '[presets]\n"Typed" = { bases = ["Nope"] }\n');
  await page.click("#presets-save");
  await page.waitForFunction(() => document.getElementById("presets-error").textContent);
  assert.match(await page.textContent("#presets-error"), /unknown base 'Nope'/);
  assert.equal(await page.isVisible("#edit-presets"), true);

  await page.fill("#presets-text", '[constants]\nmy_mass = 3.0e30\n[presets]\n"Typed" = { bases = ["Default"], "star mass" = "my_mass" }\n');
  await page.click("#presets-save");
  await page.waitForSelector("#edit-presets", { state: "hidden" });

  await page.selectOption("#inputs select:first-of-type", "Typed");
  assert.equal(await page.inputValue("#field-star-mass"), "my_mass");
  await simulate();
  assert.equal(await errorMessage(), null, "the constant from the edited text can be used");

  await deletePreset("Typed");
});

test("the presets can be exported and imported", async () => {
  await page.fill("#field-star-mass", "2*sun_mass");
  await savePresetAs("Exported");

  const [download] = await Promise.all([page.waitForEvent("download"), page.click("#preset-buttons >> text=Export")]);
  assert.equal(download.suggestedFilename(), "user_presets.toml");
  const text = await readFile(await download.path(), "utf8");
  assert.match(text, /"Exported"/);

  await deletePreset("Exported");

  page.once("dialog", (dialog) => dialog.accept());
  await page.setInputFiles("#import-presets", { name: "user_presets.toml", mimeType: "text/plain", buffer: Buffer.from(text) });
  await page.waitForFunction(() => [...document.querySelectorAll("#inputs select:first-of-type option")].some((o) => o.value === "Exported"));

  await deletePreset("Exported");
});
