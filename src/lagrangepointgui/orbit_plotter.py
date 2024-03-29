"""Contains the Plotter class which is responsible for plotting
the orbits of the system simulated by an instance of the Simulator class.
"""
from collections.abc import Callable, Generator
from contextlib import suppress
from math import ceil
from typing import TypeAlias, cast

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from numpy.linalg import norm
from PyQt6.QtCore import QTimer

from src.lagrangepointsimulator import Simulator
from src.lagrangepointsimulator.constants import AU, HOURS, YEARS
from src.lagrangepointsimulator.sim_types import Array1D, Array2D

PlotArgs: TypeAlias = dict[str, str | int]

AnimatePlotFunc: TypeAlias = Callable[[], None]


def _create_orbit_plot(title: str) -> pg.PlotWidget:
    plot = pg.PlotWidget(title=title)
    plot.setLabel("bottom", "x", units="AU")
    plot.setLabel("left", "y", units="AU")

    return plot


COMPONENT_TO_PLOT_ARGS: dict[str, tuple[int, str]] = {
    "x": (0, "r"),
    "y": (1, "g"),
    "z": (2, "b"),
}


def _plot_components(plot: pg.PlotWidget, arr: Array2D, times: Array1D) -> None:
    for component, (idx, pen) in COMPONENT_TO_PLOT_ARGS.items():
        arr_component = arr[:, idx]
        plot.plot(times, arr_component, name=component, pen=pen)


def _create_conserved_plot(quantity_name: str) -> pg.PlotWidget:
    """Initializes the plot axes and title for the conserved quantities plots."""
    plot = pg.PlotWidget(title=f"Relative Change in {quantity_name} vs Time")

    plot.setLabel("bottom", "Time", units="years")
    plot.setLabel("left", f"Relative Change in {quantity_name}")
    plot.addLegend()

    return plot


class Plotter:
    """Plots the orbits produced by a Simulator."""

    def __init__(self, sim: Simulator) -> None:
        self.sim = sim

        self.inertial_plot = _create_orbit_plot("Orbit in Inertial Coordinate System")
        self.inertial_plot.setAspectLocked(True)

        self.corotating_plot = _create_orbit_plot("Orbit in Co-Rotating Coordinate System")
        self.corotating_plot.setAspectLocked(True)

        self.timer = QTimer()
        # 33 milliseconds -> 30 fps
        self.timer.setInterval(33)

        self._total_momentum: Array2D = np.array([[]])
        self._total_angular_momentum: Array2D = np.empty_like(self._total_momentum)
        self._total_energy: Array1D = np.array([])

        self.linear_momentum_plot = _create_conserved_plot("Linear Momentum")
        self.angular_momentum_plot = _create_conserved_plot("Angular Momentum")
        self.energy_plot = _create_conserved_plot("Energy")

    def toggle_animation(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()

    def stop_animation(self) -> None:
        self.timer.stop()

    # noinspection PyUnresolvedReferences
    def plot_orbit_inertial_and_corotating(self) -> None:
        animate_inertial = self.plot_inertial_orbit()
        animate_corotating = self.plot_corotating_orbit()

        with suppress(TypeError):
            self.timer.timeout.disconnect()

        self.timer.timeout.connect(animate_inertial)
        self.timer.timeout.connect(animate_corotating)

    def plot_index_generator(self) -> Generator[int, None, None]:
        """This generator yields the index of the next point to plot."""
        time_step_default = 1 * HOURS

        # maximum rate of plot update is too slow
        # so instead step through arrays
        # inversely proportional to time_step so that
        # animated motion is the same regardless of
        # num_steps or num_years
        rate = ceil(
            100 / 3 * time_step_default / abs(self.sim.time_step_in_seconds) * self.sim.orbital_period / (1 * YEARS),
        )
        i = 0
        while True:
            i = i + rate

            if i >= self.sim.num_steps:
                i = 0

            yield i

    def array_step(self, num_points_to_plot: int = 10**5) -> int:
        # no need to plot all points
        # step size when plotting
        # i.e. if points_plotted_step = 10 then plot every 10th point
        points_plotted_step = int((self.sim.num_steps + 1) / num_points_to_plot)

        return points_plotted_step or 1

    def plot_orbit(
        self,
        plot: pg.PlotWidget,
        star_pos: Array2D,
        planet_pos: Array2D,
        sat_pos: Array2D,
    ) -> AnimatePlotFunc:
        """Plotting logic common to both inertial and corotating plots.
        Returns a function which is called by the timer to animate the plot.
        """

        plot.clear()
        plot.disableAutoRange()

        legend: pg.LegendItem = plot.addLegend()
        legend.clear()

        star_args: PlotArgs = {
            "pen": "y",
            "brush": "y",
            "size": 10,
            "name": "Star",
        }

        planet_args: PlotArgs = {
            "pen": "b",
            "brush": "b",
            "size": 10,
            "name": "Planet",
        }

        sat_args: PlotArgs = {
            "pen": "g",
            "brush": "g",
            "size": 10,
            "name": "Satellite",
        }

        arrays_and_args = ((star_pos, star_args), (planet_pos, planet_args), (sat_pos, sat_args))

        arr_step = self.array_step()
        for arr, args in arrays_and_args:
            plot.plot(arr[::arr_step, :2] / AU, **args)

        anim_plot = pg.ScatterPlotItem()

        plot.addItem(anim_plot)

        # The purpose of this is to add the bodies to the plot legend
        # and plot their initial positions
        for arr, args in arrays_and_args:
            Plotter.plot_point(anim_plot, arr[0], args)

        plot.autoRange()

        idx_gen = self.plot_index_generator()

        def animate_plot() -> None:
            i = next(idx_gen)

            anim_plot.clear()
            # noinspection PyShadowingNames
            for arr, args in arrays_and_args:
                Plotter.plot_point(anim_plot, arr[i], args)

        return animate_plot

    @staticmethod
    def plot_point(scatter_plot: pg.ScatterPlotItem, pos: Array1D, args: PlotArgs) -> None:
        """Plots pos on scatter_plot.
        pos can be any subscript-able list with length >= 2. Only the first 2 elements are plotted.
        """
        scatter_plot.addPoints(
            pos=[pos[:2] / AU],
            **args,
        )

    def plot_inertial_orbit(self) -> AnimatePlotFunc:
        return self.plot_orbit(self.inertial_plot, self.sim.star_pos, self.sim.planet_pos, self.sim.sat_pos)

    def plot_corotating_orbit(self) -> AnimatePlotFunc:
        """Plots the orbits of the system simulated in the corotating frame."""
        star_pos_corotating = self.sim.transform_to_corotating(self.sim.star_pos)
        planet_pos_corotating = self.sim.transform_to_corotating(self.sim.planet_pos)
        sat_pos_corotating = self.sim.transform_to_corotating(self.sim.sat_pos)

        animate_corotating_plot = self.plot_orbit(
            self.corotating_plot,
            star_pos_corotating,
            planet_pos_corotating,
            sat_pos_corotating,
        )

        self._add_lagrange_point_to_corotating_plot()

        return animate_corotating_plot

    def _add_lagrange_point_to_corotating_plot(self) -> None:
        lagrange_point_plot = pg.ScatterPlotItem()

        self.corotating_plot.addItem(lagrange_point_plot)

        lagrange_point = self.sim.lagrange_point_trans

        lagrange_point_plot.addPoints(
            pos=[lagrange_point[:2] / AU],
            pen="w",
            brush="w",
            size=10,
            name="Lagrange Point",
        )

        plot_data_item = pg.PlotDataItem(pen="w")

        legend: pg.LegendItem = self.corotating_plot.addLegend()

        legend.addItem(plot_data_item, self.sim.lagrange_label)

    def plot_conserved_quantities(self) -> None:
        """Plots the relative change in the conserved quantities:
        linear and angular momenta, and energy.
        """
        # slice the arrays so that we only plot at most 10**5 points.
        arr_step = self.array_step()

        times_in_years = self.sim.time_points_in_years()[::arr_step]

        self.linear_momentum_plot.clear()
        self.angular_momentum_plot.clear()
        self.energy_plot.clear()

        total_momentum = self._total_momentum[::arr_step]
        self.plot_relative_change_in_linear_momentum(total_momentum, times_in_years)

        total_angular_momentum = self._total_angular_momentum[::arr_step]
        self.plot_relative_change_in_angular_momentum(total_angular_momentum, times_in_years)

        total_energy = self._total_energy[::arr_step]
        self.plot_relative_change_in_energy(total_energy, times_in_years)

    def get_conserved_quantities(self) -> None:
        (
            total_momentum,
            total_angular_momentum,
            total_energy,
        ) = self.sim.calc_conserved_quantities()

        self._total_momentum = total_momentum
        self._total_angular_momentum = total_angular_momentum
        self._total_energy = total_energy

    def plot_relative_change_in_linear_momentum(
        self,
        total_momentum: Array2D,
        times_in_years: Array1D,
    ) -> None:
        # total linear momentum is initially approx. 0.
        # due to this any variation will make it seem as if it is not conserved.
        # however the variation is insignificant compared to
        # the star and planet's individual linear momenta.
        # That suggests that the variation is due to floating point error
        # or the error of the integration method.

        # to avoid this we normalize the total linear momentum
        # by the initial linear momentum of the planet.

        init_planet_momentum = cast(float, (norm(self.sim.planet_mass * self.sim.planet_vel[0])))
        normalized_linear_momentum: Array2D = total_momentum / init_planet_momentum

        _plot_components(self.linear_momentum_plot, normalized_linear_momentum, times_in_years)

    def plot_relative_change_in_angular_momentum(
        self,
        total_angular_momentum: Array2D,
        times_in_years: Array1D,
    ) -> None:
        # Ignore 0/0 division warning
        with np.errstate(invalid="ignore"):
            normalized_angular_momentum: Array2D = total_angular_momentum / total_angular_momentum[0] - 1

        # X and Y components of the angular momentum are always 0.
        # The above division results in NaN values for the normalized X and Y components.
        # For our purposes a normalized value of 0 makes more sense.
        normalized_angular_momentum = np.nan_to_num(normalized_angular_momentum, nan=0.0)

        _plot_components(self.angular_momentum_plot, normalized_angular_momentum, times_in_years)

    def plot_relative_change_in_energy(self, total_energy: Array1D, times_in_years: Array1D) -> None:
        self.energy_plot.plot(times_in_years, total_energy / total_energy[0] - 1)
