"""This script measures how long a simulation takes to run."""
import time

from simulation import Simulator

sim = Simulator()

start = time.perf_counter()

NUM_SAMPLES = 400

for _ in range(NUM_SAMPLES):
    sim.simulate()

end = time.perf_counter()

print(f"Without reallocation: {(end - start) / NUM_SAMPLES} seconds per simulation")
