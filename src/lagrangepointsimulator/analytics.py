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

    @property
    def instability(self) -> float | None:
        """How many times further from the Lagrange point the satellite gets than it started, which is 1 for an
        orbit that never leaves its start. None when it starts at the point itself, so the ratio isn't defined.
        """
        return self.max_distance / self.initial_distance if self.initial_distance > 0 else None

    def rows(self, lagrange_label: str) -> list[tuple[str, str]]:
        """The (name, value) pairs of a report, with the values written the way they are shown."""
        instability = self.instability
        return [
            ("Orbital period of the planet", f"{self.planet_period:.4f} years"),
            (f"Distance from {lagrange_label} at the start", f"{self.initial_distance:.4g} AU"),
            (f"Distance from {lagrange_label} at the end", f"{self.final_distance:.4g} AU"),
            (
                f"Largest distance from {lagrange_label}",
                f"{self.max_distance:.4g} AU, after {self.time_of_max_distance:,.2f} years",
            ),
            (
                "Instability (largest ÷ starting distance)",
                f"{instability:.3g}" if instability is not None else f"n/a, it starts at {lagrange_label}",
            ),
            ("Largest change in energy", f"{self.max_energy_change:.2e}"),
            ("Largest change in angular momentum", f"{self.max_angular_momentum_change:.2e}"),
            ("Largest total linear momentum", f"{self.max_linear_momentum_change:.2e} × the planet's initial momentum"),
        ]


def summarize(sim: Simulator, step: int = 1) -> RunSummary:
    """Summarise the last run of sim. step is 1 when sim has every step of it, as after simulate(), or n when it has
    only every n-th row. Then the largest distance and changes are those of the rows, and the end is the last row.
    """
    if len(sim.sat_pos) != len(range(0, sim.num_steps + 1, step)):
        msg = "there is no simulation to summarise: call simulate() first"
        raise ValueError(msg)

    corotating = sim.transform_to_corotating(sim.sat_pos, step)
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
        time_of_max_distance=float(sim.time_points(step)[furthest] / YEARS),
        max_energy_change=float(np.abs(energy / energy[0] - 1).max()),
        max_angular_momentum_change=float(np.abs(angular_momentum_z / angular_momentum_z[0] - 1).max()),
        max_linear_momentum_change=float(array_of_norms(linear_momentum).max() / initial_planet_momentum),
    )
