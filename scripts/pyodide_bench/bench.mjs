// Runs bench.py in Pyodide under Node.
// Usage: node bench.mjs <wheel_dir> [num_years] [repeats]
// Every .whl in wheel_dir is installed without resolving dependencies. numpy comes from the Pyodide package list.
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const [wheelDir, numYears = "10", repeats = "5"] = process.argv.slice(2);
if (!wheelDir) {
  console.error("usage: node bench.mjs <wheel_dir> [num_years] [repeats]");
  process.exit(2);
}

const here = dirname(fileURLToPath(import.meta.url));
const pyodide = await loadPyodide();
await pyodide.loadPackage("numpy");

for (const name of readdirSync(wheelDir).filter((f) => f.endsWith(".whl"))) {
  // unpackArchive rejects a Node Buffer, so copy it into a plain Uint8Array
  await pyodide.unpackArchive(new Uint8Array(readFileSync(join(wheelDir, name))), "wheel");
}

pyodide.globals.set("bench_source", readFileSync(join(here, "bench.py"), "utf8"));
pyodide.globals.set("bench_args", ["bench.py", numYears, repeats]);
try {
  pyodide.runPython(`
import sys
sys.argv = list(bench_args)
exec(compile(bench_source, "bench.py", "exec"))
`);
} catch (error) {
  // the default stack trace is dominated by Pyodide's own minified source
  console.error(error.message);
  process.exit(1);
}
