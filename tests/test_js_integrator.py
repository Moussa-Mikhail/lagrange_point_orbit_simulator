"""Checks web/integrator.js against the Python integrator, which is the reference.

The two do the same arithmetic but Math.pow and libm round differently, and orbits amplify that, so results agree to
rounding error for short runs and not bit for bit. The tolerances below are about 100x what was measured. A real
difference, such as a wrong sign, coefficient or half step, is many orders of magnitude larger.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from lagrangepointsimulator import Simulator
from lagrangepointsimulator.constants import EARTH_MASS, G
from lagrangepointsimulator.numba_funcs import HAS_NUMBA, integrate

RUNNER = Path(__file__).parent / "run_js_integrator.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

# the pure Python function behind the Numba one, or the function itself when Numba isn't installed
python_integrate = getattr(integrate, "py_func", integrate)

MOON_MASS = 7.34767309e22

# name: (Simulator parameters, tolerance against Python, tolerance on the change in conserved quantities)
CASES = {
    "L4": ({"num_years": 1, "perturbation_size": 0.01}, 1e-9, 1e-10),
    "L1 backwards": (
        {"num_years": 2, "lagrange_label": "L1", "perturbation_size": 0.001, "time_step": -2.0},
        1e-9,
        1e-10,
    ),
    # Many orbits per year, so rounding differences and the integrator's own error grow the most here.
    "Earth Moon L2": (
        {
            "num_years": 1,
            "lagrange_label": "L2",
            "star_mass": EARTH_MASS,
            "planet_mass": MOON_MASS,
            "planet_distance": 0.00257,
            "speed": 1.01,
        },
        1e-6,
        5e-8,
    ),
}

STATE_NAMES = ("star_pos", "star_vel", "planet_pos", "planet_vel", "sat_pos", "sat_vel")


def run_js(sim: Simulator, step: int, g_planet_scale: float = 1.0) -> np.ndarray:
    case = {
        "timeStep": sim.time_step_in_seconds,
        "numSteps": sim.num_steps,
        "gStar": G * sim.star_mass,
        "gPlanet": G * sim.planet_mass * g_planet_scale,
        "state": np.concatenate([getattr(sim, name)[0] for name in STATE_NAMES]).tolist(),
        "step": step,
    }
    result = subprocess.run(
        ["node", str(RUNNER)],
        input=json.dumps(case),
        capture_output=True,
        text=True,
        check=True,
    )
    return np.array(json.loads(result.stdout)).reshape(-1, 18)


def run_python(sim: Simulator) -> np.ndarray:
    """Every row of the integration with the Python kernel, one column per state variable."""
    sim._initialize_arrays()
    python_integrate(
        sim.time_step_in_seconds,
        sim.num_steps,
        sim.star_mass,
        sim.planet_mass,
        sim.star_pos,
        sim.star_vel,
        sim.planet_pos,
        sim.planet_vel,
        sim.sat_pos,
        sim.sat_vel,
    )
    return np.concatenate([getattr(sim, name) for name in STATE_NAMES], axis=1)


def max_relative_difference(expected: np.ndarray, actual: np.ndarray) -> float:
    """Largest difference in any column, relative to that column's largest value."""
    scale = np.abs(expected).max(axis=0)
    scale[scale == 0] = 1
    return float((np.abs(expected - actual) / scale).max())


@pytest.mark.parametrize("step", [1, 7])
@pytest.mark.parametrize("name", CASES)
def test_matches_python(name: str, step: int) -> None:
    params, tolerance, _ = CASES[name]
    sim = Simulator(**params)

    expected = run_python(sim)[::step]
    actual = run_js(sim, step)

    assert actual.shape == expected.shape
    assert max_relative_difference(expected, actual) < tolerance


@pytest.mark.skipif(not HAS_NUMBA, reason="the desktop app's arithmetic is Numba's")
@pytest.mark.parametrize("name", CASES)
def test_identical_to_the_numba_integrator(name: str) -> None:
    # The same results to the last bit, so that the conserved quantities, which are rounding error, are the same
    # curves on the web page as in the desktop app. Math.pow(r, -3) breaks this within a few dozen steps.
    params, _, _ = CASES[name]
    sim = Simulator(**params)

    sim.simulate()
    expected = np.concatenate([getattr(sim, state_name) for state_name in STATE_NAMES], axis=1)
    actual = run_js(sim, 1)

    assert np.array_equal(expected, actual)


def test_tolerances_catch_a_physics_change() -> None:
    # A 1e-6 error in the planet's mass must be well outside the tolerance, or the tolerance is too loose to be useful.
    params, tolerance, _ = CASES["L4"]
    sim = Simulator(**params)

    expected = run_python(sim)
    wrong = run_js(sim, 1, g_planet_scale=1 + 1e-6)

    assert max_relative_difference(expected, wrong) > 10 * tolerance


@pytest.mark.parametrize("name", CASES)
def test_conserves_energy_and_momentum(name: str) -> None:
    params, _, tolerance = CASES[name]
    sim = Simulator(**params)
    sim._initialize_arrays()

    rows = run_js(sim, 1)
    for i, state_name in enumerate(STATE_NAMES):
        setattr(sim, state_name, np.ascontiguousarray(rows[:, 3 * i : 3 * i + 3]))

    momentum, angular_momentum, energy = sim.calc_conserved_quantities()

    # the total momentum is about 0, so it's measured against the planet's, as the plots do
    planet_momentum = np.linalg.norm(sim.planet_mass * sim.planet_vel[0])
    assert np.abs(momentum).max() / planet_momentum < tolerance
    assert np.abs(angular_momentum[:, 2] / angular_momentum[0, 2] - 1).max() < tolerance
    assert np.abs(energy / energy[0] - 1).max() < tolerance
