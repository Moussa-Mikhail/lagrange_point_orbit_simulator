# Pyodide benchmark

Runs `bench.py` natively or inside Pyodide (pinned in `package.json`) under Node.

```bash
npm ci
uv build --wheel -o wheels .                      # this project
# validateddescriptor is not in the Pyodide package list, so its wheel is built from its git repo
git clone https://github.com/Moussa-Mikhail/validated-descriptor.git /tmp/vd
uv build --wheel -o wheels /tmp/vd
node bench.mjs wheels 10 5                        # Pyodide: 10 simulated years, 5 repeats
PYTHONPATH=../../src python bench.py 10 5         # native
```

Wheels are installed without resolving dependencies. `numpy` comes from the Pyodide package list.
