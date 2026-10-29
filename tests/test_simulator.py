import numpy as np
import pytest

from lagrangepointsimulator import Simulator
from lagrangepointsimulator.constants import AU, YEARS
from lagrangepointsimulator.numba_funcs import HAS_NUMBA, _transform_to_corotating_numpy, transform_to_corotating


@pytest.fixture(scope="module")
def l4_sim() -> Simulator:
    sim = Simulator(num_years=10)
    sim.simulate()
    return sim


def test_conserved_quantities_are_conserved(l4_sim: Simulator) -> None:
    _, angular_momentum, energy = l4_sim.calc_conserved_quantities()

    assert np.abs(angular_momentum[:, 2] / angular_momentum[0, 2] - 1).max() < 1e-11
    assert np.abs(energy / energy[0] - 1).max() < 1e-11


def test_unperturbed_satellite_stays_near_l4(l4_sim: Simulator) -> None:
    corotating = l4_sim.transform_to_corotating(l4_sim.sat_pos)

    drift = np.linalg.norm(corotating - l4_sim.lagrange_point_trans[:2], axis=1).max() / AU

    assert drift < 1e-3


def test_negative_time_step_runs_backwards() -> None:
    forwards = Simulator(num_years=0.1)
    forwards.simulate()
    backwards = Simulator(num_years=0.1, time_step=-1.0)
    backwards.simulate()

    assert forwards.planet_pos[-1][1] > 0
    assert backwards.planet_pos[-1][1] == pytest.approx(-forwards.planet_pos[-1][1])


def test_num_steps_follows_time_step() -> None:
    sim = Simulator(num_years=1.0, time_step=24.0)

    assert sim.num_steps in (365, 366)
    assert len(sim.time_points()) == sim.num_steps + 1


@pytest.mark.parametrize(
    ("num_years", "time_step"), [(1.0, 24.0), (1.0, 7.0), (3.3, 1.0), (2.0, -5.0), (0.1, 24.0), (1.0, 0.0)]
)
@pytest.mark.parametrize("step", [1, 2, 3, 7, 10, 1000])
def test_time_points_are_those_of_linspace(num_years: float, time_step: float, step: int) -> None:
    sim = Simulator(num_years=num_years, time_step=time_step)

    expected = np.linspace(0, sim.sim_time, sim.num_steps + 1)[::step]

    np.testing.assert_array_equal(sim.time_points(step), expected)
    np.testing.assert_array_equal(sim.time_points_in_years(step), expected / YEARS)


def test_lagrange_points_are_where_expected() -> None:
    def position(label: str) -> np.ndarray:
        return Simulator(lagrange_label=label).calc_lagrange_point() / AU

    assert 0 < position("L1")[0] < 1 < position("L2")[0]
    assert position("L3")[0] < -1
    assert position("L4") == pytest.approx((0.5, np.sqrt(3) / 2, 0))
    assert position("L5") == pytest.approx((0.5, -np.sqrt(3) / 2, 0))


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"num_years": -1}, ValueError),
        ({"planet_distance": 0}, ValueError),
        ({"planet_mass": -1.0}, ValueError),
        ({"lagrange_label": "L9"}, ValueError),
        ({"time_step": "x"}, TypeError),
    ],
)
def test_invalid_parameters_are_rejected(kwargs: dict, error: type[Exception]) -> None:
    with pytest.raises(error):
        Simulator(**kwargs)


@pytest.mark.skipif(not HAS_NUMBA, reason="the NumPy version is the only one without Numba")
def test_numpy_corotating_transform_matches_numba(l4_sim: Simulator) -> None:
    times = l4_sim.time_points()

    expected = transform_to_corotating(l4_sim.sat_pos, times, l4_sim.angular_speed)
    actual = _transform_to_corotating_numpy(l4_sim.sat_pos, times, l4_sim.angular_speed)

    assert actual == pytest.approx(expected, abs=1e-3)
