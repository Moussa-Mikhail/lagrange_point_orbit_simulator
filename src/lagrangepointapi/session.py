"""What a front-end needs from the simulator, as plain data: the form description, simulations, plot data and presets.

The Qt GUI and the web page both talk to this, so the two don't each reimplement validating the inputs and preparing
the plots. Results are dicts of numbers, text, lists and NumPy arrays, and a failure is {"error": message}.
"""

from collections.abc import Callable, Mapping
from math import ceil
from typing import Any

import numpy as np
from numpy.linalg import norm

from lagrangepointinputs import user_presets
from lagrangepointinputs.parameters import (
    DEFAULT_LAGRANGE_LABEL,
    LABEL_TO_ATTRIBUTE,
    LAGRANGE_LABEL,
    LAGRANGE_LABELS,
    PARAMETER_GROUPS,
)
from lagrangepointinputs.presets import read_presets
from lagrangepointinputs.safe_eval import safe_eval
from lagrangepointsimulator import Simulator
from lagrangepointsimulator.constants import AU, HOURS, YEARS, G
from lagrangepointsimulator.numba_funcs import transform_to_corotating

MAX_POINTS = 10**5

type Result = dict[str, Any]


def presets_spec() -> Result:
    """The presets as {name: {parameter label: field text}}, and the names of the user's own."""
    presets, _ = read_presets()
    # field text as the form shows it, e.g. "1.0" and not 1
    presets = {
        name: {label: value if label == "bases" else str(value) for label, value in preset.items()}
        for name, preset in presets.items()
    }
    return {"presets": presets, "userPresets": user_presets.user_preset_names()}


def get_spec() -> Result:
    """The description of the form and the presets."""
    return {
        "groups": {
            name: [{"label": p.label, "default": p.default, "unit": p.unit} for p in params]
            for name, params in PARAMETER_GROUPS.items()
        },
        "lagrangeLabel": LAGRANGE_LABEL,
        "lagrangeLabels": list(LAGRANGE_LABELS),
        "defaultLagrangeLabel": DEFAULT_LAGRANGE_LABEL,
        **presets_spec(),
    }


# Each function that changes the user's presets returns the new text of the presets file, so that a front-end without
# a persistent file system can keep it, or {"error": message}.


def _presets_changed(change: Callable[[], None]) -> Result:
    try:
        change()
    except user_presets.PresetError as e:
        return {"error": str(e)}

    return {"text": user_presets.read_text(), **presets_spec()}


def get_presets_text() -> Result:
    return {"text": user_presets.read_text() or user_presets.EXAMPLE_TEXT}


def set_presets_text(text: str) -> Result:
    return _presets_changed(lambda: user_presets.save_text(text))


def save_preset(name: str, values: Mapping[str, str]) -> Result:
    return _presets_changed(lambda: user_presets.save_preset(name, dict(values)))


def delete_preset(name: str) -> Result:
    return _presets_changed(lambda: user_presets.delete_preset(name))


class Session:
    """A Simulator and the plot data of its last simulation."""

    def __init__(self) -> None:
        self.sim = Simulator()
        self._simulated = False

    def apply_inputs(self, inputs: Mapping[str, str]) -> str | None:
        """Evaluate the field text, which maps parameter labels to text, and set it on the simulator.

        Returns an error message, or None.
        """
        values: dict[str, Any] = {}
        for label, text in inputs.items():
            if label == LAGRANGE_LABEL:
                values[label] = text
                continue

            try:
                values[label] = safe_eval(text)
            except (ValueError, TypeError) as e:
                return f"Invalid expression in field '{label}'.\n{e}"

        try:
            for label, value in values.items():
                setattr(self.sim, LABEL_TO_ATTRIBUTE[label], value)
        except (TypeError, ValueError) as e:
            msg = str(e)
            # replace attribute names with parameter labels
            for label, attribute in LABEL_TO_ATTRIBUTE.items():
                msg = msg.replace(attribute, label)

            return msg

        return None

    def simulate(self, inputs: Mapping[str, str]) -> Result:
        """Run the whole simulation with the integrator of this process, and return the plot data."""
        if (error := self.apply_inputs(inputs)) is not None:
            return {"error": error}

        self.sim.simulate()
        self._keep_every_step_th_row(self.array_step())

        return self.plot_data()

    def initial_state(self) -> Result:
        """Set up the first row of a simulation for an integrator elsewhere, such as web/integrator.js.

        Call apply_inputs first, then set_rows with the integrated rows.
        """
        sim = self.sim
        # only the first row is needed here, the integration happens elsewhere
        sim.star_pos, sim.star_vel, sim.planet_pos, sim.planet_vel, sim.sat_pos, sim.sat_vel = (
            np.empty((1, 3)) for _ in range(6)
        )
        sim._set_initial_conditions()

        state = np.concatenate(
            [arr[0] for arr in (sim.star_pos, sim.star_vel, sim.planet_pos, sim.planet_vel, sim.sat_pos, sim.sat_vel)]
        )

        return {
            "state": state,
            "timeStep": sim.time_step_in_seconds,
            "numSteps": sim.num_steps,
            "gStar": G * sim.star_mass,
            "gPlanet": G * sim.planet_mass,
            "step": self.array_step(),
        }

    def set_rows(self, flat: np.ndarray) -> None:
        """Take every array_step()-th row, 18 numbers each, integrated elsewhere."""
        sim = self.sim
        flat = np.asarray(flat).reshape(-1, 18)
        sim.star_pos, sim.star_vel, sim.planet_pos, sim.planet_vel, sim.sat_pos, sim.sat_vel = (
            np.ascontiguousarray(flat[:, 3 * i : 3 * i + 3]) for i in range(6)
        )
        self._simulated = True

    def array_step(self, max_points: int = MAX_POINTS) -> int:
        """No need to plot all points: plot every array_step()-th one so there are at most max_points."""
        return int((self.sim.num_steps + 1) / max_points) or 1

    def animation_rate(self) -> int:
        """How many steps the animation advances per frame, inversely proportional to the time step so that the
        animated motion is the same whatever num_steps or num_years is. Counts steps of the full simulation.
        """
        sim = self.sim
        if sim.time_step_in_seconds == 0:
            return 1

        return ceil(100 / 3 * HOURS / abs(sim.time_step_in_seconds) * sim.orbital_period / YEARS)

    def _keep_every_step_th_row(self, step: int) -> None:
        # The conserved quantities are calculated for each row on its own, so these rows are all that's needed.
        sim = self.sim
        sim.star_pos, sim.star_vel, sim.planet_pos, sim.planet_vel, sim.sat_pos, sim.sat_vel = (
            np.ascontiguousarray(arr[::step])
            for arr in (sim.star_pos, sim.star_vel, sim.planet_pos, sim.planet_vel, sim.sat_pos, sim.sat_vel)
        )
        self._simulated = True

    def plot_data(self) -> Result:
        """The orbits in both frames, in AU, for the last simulation. Holds every array_step()-th row."""
        sim = self.sim
        step = self.array_step()

        times = sim.time_points()[::step]
        angular_speed = sim.angular_speed * np.sign(sim.time_step_in_seconds)

        def xy(arr: np.ndarray) -> dict[str, np.ndarray]:
            # separate 1D arrays, so they arrive in JS as plain typed arrays
            return {"x": np.ascontiguousarray(arr[:, 0] / AU), "y": np.ascontiguousarray(arr[:, 1] / AU)}

        def corotating_xy(arr: np.ndarray) -> dict[str, np.ndarray]:
            corotating = transform_to_corotating(arr, times, angular_speed) / AU
            return {"x": np.ascontiguousarray(corotating[:, 0]), "y": np.ascontiguousarray(corotating[:, 1])}

        bodies = (sim.star_pos, sim.planet_pos, sim.sat_pos)

        return {
            "inertial": [xy(arr) for arr in bodies],
            "corotating": [corotating_xy(arr) for arr in bodies],
            "lagrangePoint": [float(v) for v in sim.lagrange_point_trans[:2] / AU],
            "lagrangeLabel": sim.lagrange_label,
            "step": step,
            "numSteps": sim.num_steps,
            "animationRate": self.animation_rate(),
        }

    def conserved(self) -> Result:
        """Relative change in the conserved quantities of the last simulation."""
        if not self._simulated:
            return {"error": "No data to plot."}

        sim = self.sim
        total_momentum, total_angular_momentum, total_energy = sim.calc_conserved_quantities()

        times = np.ascontiguousarray(sim.time_points_in_years()[:: self.array_step()])

        # The total linear momentum is initially approx. 0, so any variation would seem like it isn't conserved. It's
        # normalized by the planet's initial momentum instead.
        init_planet_momentum = norm(sim.planet_mass * sim.planet_vel[0])
        linear = total_momentum / init_planet_momentum

        # The x and y components of the angular momentum are always 0, so the division gives NaN there.
        with np.errstate(invalid="ignore"):
            angular = total_angular_momentum / total_angular_momentum[0] - 1
        angular = np.nan_to_num(angular, nan=0.0)

        energy = total_energy / total_energy[0] - 1

        def components(arr: np.ndarray) -> list[np.ndarray]:
            return [np.ascontiguousarray(arr[:, i]) for i in range(3)]

        return {
            "times": times,
            "linearMomentum": components(linear),
            "angularMomentum": components(angular),
            "energy": np.ascontiguousarray(energy),
        }
