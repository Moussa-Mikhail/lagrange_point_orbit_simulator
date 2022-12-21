"""This script measures how long a simulation takes to run."""
# pylint: disable=missing-docstring
import time

from .simulator import Simulator

NUM_SAMPLES = 1000


def simulate_without_reallocation():
    sim = Simulator()
    start = time.perf_counter()
    for _ in range(NUM_SAMPLES):
        sim.simulate()
    end = time.perf_counter()
    print(f"Without reallocation: {(end - start) / NUM_SAMPLES} seconds per simulation")


def simulate_with_reallocation():
    sim = Simulator()
    start = time.perf_counter()
    for _ in range(NUM_SAMPLES):
        sim.time_step *= 1 - 1e-4
        sim.simulate()
    end = time.perf_counter()
    print(f"With reallocation: {(end - start) / NUM_SAMPLES} seconds per simulation")


simulate_without_reallocation()

simulate_with_reallocation()
