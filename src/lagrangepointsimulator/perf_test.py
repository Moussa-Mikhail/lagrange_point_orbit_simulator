"""This script measures how long a simulation takes to run."""

from timeit import timeit

NUM_SAMPLES = 3000


# average time = 0.025 seconds
def simulate_without_reallocation() -> None:
    print(
        timeit(
            "sim.simulate()",
            setup="from src.lagrangepointsimulator.simulator import Simulator; sim = Simulator(); sim.simulate()",
            number=NUM_SAMPLES,
        )
        / NUM_SAMPLES
    )


def simulate_with_reallocation() -> None:
    print(
        timeit(
            "sim.time_step *= 1 - 1 / (NUM_SAMPLES * 100); sim.simulate()",
            setup="from src.lagrangepointsimulator.simulator import Simulator; sim = Simulator(); sim.simulate()",
            number=NUM_SAMPLES,
        )
        / NUM_SAMPLES
    )


simulate_without_reallocation()
