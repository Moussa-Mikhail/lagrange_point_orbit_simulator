from dataclasses import dataclass

import numpy as np

from lagrangepointsimulator.constants import AU, YEARS
from lagrangepointsimulator.simulator import Simulator, array_of_norms


@dataclass(frozen=True)
class RunSummary:
    """Numbers that summarise a simulated run."""

    planet_period: float
    """Orbital period of the planet around the star, in years."""

    initial_distance: float
    """Distance of the satellite from the Lagrange point at the start, in AU, in the co-rotating frame."""

    final_distance: float
    """Distance of the satellite from the Lagrange point at the end, in AU."""

    max_distance: float
    """Largest distance of the satellite from the Lagrange point, in AU."""

    time_of_max_distance: float
    """Time of the largest distance, in years from the start."""

    max_energy_change: float
    """Largest relative change of the total energy from its initial value."""

    max_angular_momentum_change: float
    """Largest relative change of the total angular momentum from its initial value."""

    max_linear_momentum_change: float
    """Largest size of the total linear momentum, relative to the planet's initial momentum. It starts at about 0."""


def summarize(sim: Simulator) -> RunSummary:
    """Summarise the last run of sim, which needs every step of it, so it must be done right after simulate()."""
    if len(sim.sat_pos) != sim.num_steps + 1:
        msg = "there is no simulation to summarise: call simulate() first"
        raise ValueError(msg)

    corotating = sim.transform_to_corotating(sim.sat_pos)
    distance = array_of_norms(corotating - sim.lagrange_point_trans[:2]) / AU
    furthest = int(distance.argmax())

    linear_momentum, angular_momentum, energy = sim.calc_conserved_quantities()
    angular_momentum_z = angular_momentum[:, 2]
    initial_planet_momentum = np.linalg.norm(sim.planet_mass * sim.planet_vel[0])

    return RunSummary(
        planet_period=sim.orbital_period / YEARS,
        initial_distance=float(distance[0]),
        final_distance=float(distance[-1]),
        max_distance=float(distance[furthest]),
        time_of_max_distance=float(sim.time_points()[furthest] / YEARS),
        max_energy_change=float(np.abs(energy / energy[0] - 1).max()),
        max_angular_momentum_change=float(np.abs(angular_momentum_z / angular_momentum_z[0] - 1).max()),
        max_linear_momentum_change=float(array_of_norms(linear_momentum).max() / initial_planet_momentum),
    )
