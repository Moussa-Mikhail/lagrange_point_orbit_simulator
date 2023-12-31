"""This script measures how long a simulation takes to run."""

from timeit import timeit

SETUP = "from src.lagrangepointsimulator.simulator import Simulator; sim = Simulator(num_years=400); sim.simulate()"

NUM_SAMPLES = 3000


# average time: 0.0994 seconds
# with record arrays: 0.0987 seconds
def simulate_without_reallocation() -> None:
    print(
        timeit(
            "sim.simulate()",
            setup=SETUP,
            number=NUM_SAMPLES,
        )
        / NUM_SAMPLES
    )


def simulate_with_reallocation() -> None:
    print(
        timeit(
            "sim.time_step *= 1 - 1 / (NUM_SAMPLES * 100); sim.simulate()",
            setup=SETUP,
            number=NUM_SAMPLES,
        )
        / NUM_SAMPLES
    )


simulate_without_reallocation()
