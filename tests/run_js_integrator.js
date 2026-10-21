// Runs web/integrator.js on the case given as JSON on stdin and prints the result as JSON.
// Used by test_js_integrator.py.
const path = require("node:path");
const { integrate } = require(path.join(__dirname, "..", "web", "integrator.js"));

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const { timeStep, numSteps, gStar, gPlanet, state, step } = JSON.parse(input);
  const rows = integrate(timeStep, numSteps, gStar, gPlanet, Float64Array.from(state), step);
  process.stdout.write(JSON.stringify(Array.from(rows)));
});
