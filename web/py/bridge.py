"""Python side of the web UI. Runs inside Pyodide in a Web Worker.

The parameter table and the plot preparation mirror src/lagrangepointgui/sim_gui.py and orbit_plotter.py, which can't
be imported here because they depend on Qt.
"""

from math import ceil

import numpy as np
from js import Object
from numpy.linalg import norm
from pyodide.ffi import to_js

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

_sim = Simulator()
_simulated = False


def _to_js(obj):
    return to_js(obj, dict_converter=Object.fromEntries)


def get_spec():
    presets, _ = read_presets()
    # field text as the desktop GUI shows it, e.g. "1.0" and not 1
    presets = {
        name: {label: value if label == "bases" else str(value) for label, value in preset.items()}
        for name, preset in presets.items()
    }
    return _to_js(
        {
            "groups": {
                name: [{"label": p.label, "default": p.default, "unit": p.unit} for p in params]
                for name, params in PARAMETER_GROUPS.items()
            },
            "lagrangeLabel": LAGRANGE_LABEL,
            "lagrangeLabels": list(LAGRANGE_LABELS),
            "defaultLagrangeLabel": DEFAULT_LAGRANGE_LABEL,
            "presets": presets,
        }
    )


def _array_step() -> int:
    # no need to plot all points, see Plotter.array_step
    return int((_sim.num_steps + 1) / MAX_POINTS) or 1


def _animation_rate() -> int:
    # see Plotter.plot_index_generator
    return ceil(100 / 3 * HOURS / abs(_sim.time_step_in_seconds) * _sim.orbital_period / YEARS)


def prepare(inputs):
    """Validate the inputs and set up the first row of the simulation. inputs maps parameter labels to field text.

    Returns what web/integrator.js needs to run the integration, or {"error": message}.
    """
    inputs = inputs.to_py()

    values = {}
    for label, text in inputs.items():
        if label == LAGRANGE_LABEL:
            values[label] = text
            continue

        try:
            values[label] = safe_eval(text)
        except (ValueError, TypeError) as e:
            return _to_js({"error": f"Invalid expression in field '{label}'.\n{e}"})

    try:
        for label, value in values.items():
            setattr(_sim, LABEL_TO_ATTRIBUTE[label], value)
    except (TypeError, ValueError) as e:
        msg = str(e)
        # replace attribute names with parameter labels
        for label, attribute in LABEL_TO_ATTRIBUTE.items():
            msg = msg.replace(attribute, label)

        return _to_js({"error": msg})

    # Only the first row is needed here, the integration happens in JS and only every step-th row comes back.
    _sim.star_pos, _sim.star_vel, _sim.planet_pos, _sim.planet_vel, _sim.sat_pos, _sim.sat_vel = (
        np.empty((1, 3)) for _ in range(6)
    )
    _sim._set_initial_conditions()

    state = np.concatenate(
        [arr[0] for arr in (_sim.star_pos, _sim.star_vel, _sim.planet_pos, _sim.planet_vel, _sim.sat_pos, _sim.sat_vel)]
    )

    return _to_js(
        {
            "state": state,
            "timeStep": _sim.time_step_in_seconds,
            "numSteps": _sim.num_steps,
            "gStar": G * _sim.star_mass,
            "gPlanet": G * _sim.planet_mass,
            "step": _array_step(),
        }
    )


def finish(rows):
    """Take the rows integrated in JS and prepare the data for the plots."""
    global _simulated

    flat = np.asarray(rows.to_py()).reshape(-1, 18)
    step = _array_step()

    # The arrays now hold every step-th row, which is all that's plotted. calc_conserved_quantities works on them
    # as they are because each row is independent.
    _sim.star_pos, _sim.star_vel, _sim.planet_pos, _sim.planet_vel, _sim.sat_pos, _sim.sat_vel = (
        np.ascontiguousarray(flat[:, 3 * i : 3 * i + 3]) for i in range(6)
    )
    _simulated = True

    times = _sim.time_points()[::step]
    angular_speed = _sim.angular_speed * np.sign(_sim.time_step_in_seconds)

    def xy(arr):
        # separate 1D arrays so they arrive in JS as plain typed arrays
        return {"x": np.ascontiguousarray(arr[:, 0] / AU), "y": np.ascontiguousarray(arr[:, 1] / AU)}

    def corotating_xy(arr):
        corotating = transform_to_corotating(arr, times, angular_speed) / AU
        return {"x": np.ascontiguousarray(corotating[:, 0]), "y": np.ascontiguousarray(corotating[:, 1])}

    bodies = (_sim.star_pos, _sim.planet_pos, _sim.sat_pos)

    return _to_js(
        {
            "inertial": [xy(arr) for arr in bodies],
            "corotating": [corotating_xy(arr) for arr in bodies],
            "lagrangePoint": [float(v) for v in _sim.lagrange_point_trans[:2] / AU],
            "lagrangeLabel": _sim.lagrange_label,
            "step": step,
            "numSteps": _sim.num_steps,
            "animationRate": _animation_rate(),
        }
    )


def conserved():
    """Relative change in the conserved quantities of the last simulation, see Plotter."""
    if not _simulated:
        return _to_js({"error": "No data to plot."})

    total_momentum, total_angular_momentum, total_energy = _sim.calc_conserved_quantities()

    times = np.ascontiguousarray(_sim.time_points_in_years()[:: _array_step()])

    # The total linear momentum is initially approx. 0, so it's normalized by the planet's initial momentum.
    init_planet_momentum = norm(_sim.planet_mass * _sim.planet_vel[0])
    linear = total_momentum / init_planet_momentum

    # The x and y components of the angular momentum are always 0, so the division gives NaN there.
    with np.errstate(invalid="ignore"):
        angular = total_angular_momentum / total_angular_momentum[0] - 1
    angular = np.nan_to_num(angular, nan=0.0)

    energy = total_energy / total_energy[0] - 1

    def components(arr):
        return [np.ascontiguousarray(arr[:, i]) for i in range(3)]

    return _to_js(
        {
            "times": times,
            "linearMomentum": components(linear),
            "angularMomentum": components(angular),
            "energy": np.ascontiguousarray(energy),
        }
    )
