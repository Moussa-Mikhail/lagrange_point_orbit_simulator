import numpy as np
import pytest

from lagrangepointsimulator import Simulator
from lagrangepointsimulator.analytics import summarize
from lagrangepointsimulator.constants import YEARS


def test_unperturbed_satellite_stays_at_l4() -> None:
    sim = Simulator(num_years=10)
    sim.simulate()

    summary = summarize(sim)

    assert summary.initial_distance == pytest.approx(0, abs=1e-9)
    assert summary.max_distance < 1e-3
    assert 0 <= summary.time_of_max_distance <= 10
    assert summary.planet_period == pytest.approx(1, rel=1e-3)


def test_the_run_starts_the_perturbation_away_from_the_lagrange_point() -> None:
    sim = Simulator(num_years=5, perturbation_size=0.05)
    sim.simulate()

    summary = summarize(sim)

    assert summary.initial_distance == pytest.approx(0.05, rel=1e-6)
    assert summary.max_distance >= summary.initial_distance
    assert summary.max_distance >= summary.final_distance


def test_conserved_quantities_barely_change() -> None:
    sim = Simulator(num_years=10)
    sim.simulate()

    summary = summarize(sim)

    assert summary.max_energy_change < 1e-11
    assert summary.max_angular_momentum_change < 1e-11
    assert summary.max_linear_momentum_change < 1e-9


def test_a_run_that_leaves_the_lagrange_point_is_seen() -> None:
    stable = Simulator(num_years=20, lagrange_label="L1", perturbation_size=0.001)
    stable.simulate()

    # the collinear points are unstable, so the satellite drifts far away from the point it started next to
    assert summarize(stable).max_distance > 100 * 0.001


def test_summarising_before_simulating_is_refused() -> None:
    with pytest.raises(ValueError, match="simulate"):
        summarize(Simulator())


def test_the_time_of_the_largest_distance_is_in_years() -> None:
    sim = Simulator(num_years=2, perturbation_size=0.05)
    sim.simulate()

    summary = summarize(sim)

    assert summary.time_of_max_distance <= sim.sim_time / YEARS
    assert np.isfinite(summary.time_of_max_distance)
