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
