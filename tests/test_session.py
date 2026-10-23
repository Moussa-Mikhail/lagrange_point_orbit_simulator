from pathlib import Path

import numpy as np
import pytest

from lagrangepointapi import session
from lagrangepointinputs import presets


@pytest.fixture(autouse=True)
def user_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "user_presets.toml"
    monkeypatch.setattr(presets, "user_presets_path", path)
    monkeypatch.setattr(presets, "legacy_user_presets_path", tmp_path / "legacy" / "user_presets.toml")
    return path


def default_inputs() -> dict[str, str]:
    spec = session.get_spec()
    inputs = {p["label"]: p["default"] for params in spec["groups"].values() for p in params}
    inputs[spec["lagrangeLabel"]] = spec["defaultLagrangeLabel"]
    return inputs


def test_spec_describes_the_form_and_the_presets() -> None:
    spec = session.get_spec()

    assert list(spec["groups"]) == ["Simulation Parameters", "System Parameters", "Satellite Parameters"]
    assert spec["lagrangeLabels"] == ["L1", "L2", "L3", "L4", "L5"]
    assert "Default" in spec["presets"]
    assert spec["presets"]["Sun Earth"]["planet distance"] == "1.0"
    assert spec["userPresets"] == []


def test_simulate_returns_plot_data_for_both_frames() -> None:
    inputs = default_inputs() | {"simulation time": "0.5"}

    result = session.Session().simulate(inputs)

    assert "error" not in result
    assert len(result["inertial"]) == len(result["corotating"]) == 3
    n = len(result["inertial"][0]["x"])
    assert n == -(-(result["numSteps"] + 1) // result["step"])
    assert all(len(body["y"]) == n for body in result["inertial"] + result["corotating"])
    assert result["lagrangeLabel"] == "L4"


def test_a_satellite_at_l4_stays_at_l4_in_the_corotating_frame() -> None:
    result = session.Session().simulate(default_inputs() | {"simulation time": "1.0"})

    satellite = result["corotating"][2]
    assert np.ptp(satellite["x"]) < 1e-3
    assert np.ptp(satellite["y"]) < 1e-3
    assert satellite["x"][0] == pytest.approx(result["lagrangePoint"][0], abs=1e-3)


def test_long_simulations_are_decimated() -> None:
    result = session.Session().simulate(default_inputs() | {"simulation time": "50"})

    assert result["step"] > 1
    # the step is rounded down, so up to twice the maximum is plotted. That is how the plots always behaved
    assert len(result["inertial"][0]["x"]) < 2 * session.MAX_POINTS


def test_conserved_quantities_are_small_for_the_default_system() -> None:
    s = session.Session()
    assert s.conserved() == {"error": "No data to plot."}

    s.simulate(default_inputs() | {"simulation time": "1.0"})
    result = s.conserved()

    assert len(result["times"]) == len(result["energy"]) == len(result["linearMomentum"][0])
    assert abs(result["energy"]).max() < 1e-6
    assert [len(c) for c in result["angularMomentum"]] == [len(result["times"])] * 3


@pytest.mark.parametrize(
    ("field", "text", "message"),
    [
        ("star mass", "not_a_constant", "Invalid expression in field 'star mass'"),
        ("simulation time", "-1", "simulation time"),
        ("Lagrange label", "L9", "Lagrange label"),
    ],
)
def test_bad_inputs_are_reported_with_the_field_label(field: str, text: str, message: str) -> None:
    result = session.Session().simulate(default_inputs() | {field: text})

    assert message in result["error"]


def test_the_web_path_gives_the_same_plot_data() -> None:
    """The browser integrates elsewhere and hands back every step-th row. Here that's the Python integrator."""
    inputs = default_inputs() | {"simulation time": "2.0"}

    direct = session.Session().simulate(inputs)

    via_rows = session.Session()
    assert via_rows.apply_inputs(inputs) is None
    state = via_rows.initial_state()
    assert state["step"] == direct["step"]
    reference = session.Session()
    reference.apply_inputs(inputs)
    reference.sim.simulate()
    rows = np.hstack(
        [
            arr[:: state["step"]]
            for arr in (
                reference.sim.star_pos,
                reference.sim.star_vel,
                reference.sim.planet_pos,
                reference.sim.planet_vel,
                reference.sim.sat_pos,
                reference.sim.sat_vel,
            )
        ]
    )
    via_rows.set_rows(rows)
    result = via_rows.plot_data()

    for frame in ("inertial", "corotating"):
        for got, want in zip(result[frame], direct[frame], strict=True):
            np.testing.assert_allclose(got["x"], want["x"])
            np.testing.assert_allclose(got["y"], want["y"])
    assert result["animationRate"] == direct["animationRate"]


def test_presets_can_be_saved_and_deleted_through_the_api(user_file: Path) -> None:
    saved = session.save_preset("Mine", {"star mass": "1"})
    assert "Mine" in saved["userPresets"]
    assert saved["presets"]["Mine"] == {"star mass": "1"}
    assert user_file.read_text() == saved["text"]
    assert session.get_presets_text()["text"] == saved["text"]

    assert "Mine" not in session.delete_preset("Mine")["presets"]
    assert "error" in session.delete_preset("Default")
    assert "error" in session.set_presets_text("[presets")
    assert session.get_presets_text()["text"]  # the example text when there is no file or it is empty


def test_a_zero_time_step_does_not_break_the_animation_rate() -> None:
    result = session.Session().simulate(default_inputs() | {"time step": "0"})

    assert result["numSteps"] == 0
    assert result["animationRate"] == 1
