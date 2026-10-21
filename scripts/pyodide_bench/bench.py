"""Times a representative simulation. Run natively with python or inside Pyodide by bench.mjs.

Usage: bench.py [num_years] [repeats]
Prints one line of JSON.
"""

import json
import sys
import time

from lagrangepointsimulator import Simulator
from lagrangepointsimulator import numba_funcs as nf

num_years = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
repeats = int(sys.argv[2]) if len(sys.argv) > 2 else 5

sim = Simulator(num_years=num_years, perturbation_size=0.01)

# The first call is kept separate because Numba compiles (or loads its cache) on it.
start = time.perf_counter()
sim.simulate()
first_simulate = time.perf_counter() - start

simulate_times = []
transform_times = []
for _ in range(repeats):
    start = time.perf_counter()
    sim.simulate()
    simulate_times.append(time.perf_counter() - start)

    # the GUI transforms all three bodies after each simulation
    start = time.perf_counter()
    for positions in (sim.star_pos, sim.planet_pos, sim.sat_pos):
        sim.transform_to_corotating(positions)
    transform_times.append(time.perf_counter() - start)

start = time.perf_counter()
sim.calc_conserved_quantities()
conserved = time.perf_counter() - start

print(
    json.dumps(
        {
            "num_years": num_years,
            "num_steps": sim.num_steps,
            "numba": nf.HAS_NUMBA,
            "first_simulate_s": first_simulate,
            "simulate_best_s": min(simulate_times),
            "transform_x3_best_s": min(transform_times),
            "conserved_s": conserved,
            "final_sat_pos": [float(v) for v in sim.sat_pos[-1]],
        }
    )
)
