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


def test_instability_is_the_ratio_of_the_largest_to_the_starting_distance() -> None:
    sim = Simulator(num_years=5, perturbation_size=0.05)
    sim.simulate()

    summary = summarize(sim)

    assert summary.instability == pytest.approx(summary.max_distance / summary.initial_distance)
    assert summary.instability is not None
    assert summary.instability >= 1


def test_instability_is_undefined_when_the_satellite_starts_at_the_lagrange_point() -> None:
    sim = Simulator(num_years=1)
    sim.simulate()

    summary = summarize(sim)

    assert summary.instability is None
    assert dict(summary.rows("L4"))["Instability (largest ÷ starting distance)"] == "n/a, it starts at L4"


def test_rows_name_the_lagrange_point() -> None:
    sim = Simulator(num_years=1, lagrange_label="L5")
    sim.simulate()

    names = [name for name, _ in summarize(sim).rows("L5")]

    assert "Distance from L5 at the start" in names
    assert all("L4" not in name for name in names)


def test_every_nth_row_gives_nearly_the_summary_of_all_of_them() -> None:
    step = 8
    full = Simulator(num_years=20, perturbation_size=0.02, speed=1.006, vel_angle=152, planet_mass=7.4e28)
    full.simulate()
    kept = Simulator(num_years=20, perturbation_size=0.02, speed=1.006, vel_angle=152, planet_mass=7.4e28)
    kept.simulate()
    for name in ("star_pos", "star_vel", "planet_pos", "planet_vel", "sat_pos", "sat_vel"):
        setattr(kept, name, getattr(kept, name)[::step])

    expected = summarize(full)
    actual = summarize(kept, step)

    assert actual.planet_period == expected.planet_period
    assert actual.initial_distance == expected.initial_distance
    assert actual.max_distance == pytest.approx(expected.max_distance, rel=1e-3)
    assert actual.max_distance <= expected.max_distance
    assert actual.final_distance == pytest.approx(expected.final_distance, rel=1e-2)
    assert actual.max_energy_change <= expected.max_energy_change


def test_rows_that_dont_match_the_step_are_refused() -> None:
    sim = Simulator(num_years=1)
    sim.simulate()

    with pytest.raises(ValueError, match="simulate"):
        summarize(sim, 8)
