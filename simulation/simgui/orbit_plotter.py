# pylint: disable=missing-function-docstring
"""This module contains the Plotter class which is responsible for plotting
the orbits of the system simulated by an instance of the Simulator class.
"""
from math import ceil
from typing import Callable

import pyqtgraph as pg  # type: ignore
from PyQt6.QtCore import QTimer  # pylint: disable=no-name-in-module
from numpy.linalg import norm

from simulation import Simulator
from simulation.simulator.constants import AU, HOURS
from simulation.simulator.sim_types import Array1D, Array2D

AnimatePlotFunc = Callable[[], None]


class Plotter:
    """Plots the arrays produced by a Simulator"""

    component_to_plot_args: dict[str, tuple[int, str]] = {
        "x": (0, "r"),
        "y": (1, "g"),
        "z": (2, "b"),
    }

    def __init__(self, sim: Simulator):

        self.sim = sim

        self.inertial_plot = Plotter.make_plot(
            title="Orbits in Inertial Coordinate System"
        )

        self.inertial_plot.setAspectLocked(True)

        self.corotating_plot = Plotter.make_plot(
            title="Orbits in Co-Rotating Coordinate System"
        )

        self.corotating_plot.setAspectLocked(True)

        self.timer = QTimer()

        self.period_of_animation = 33

    def toggle_animation(self):
        if self.timer.isActive():

            self.timer.stop()

        else:

            self.timer.start(self.period_of_animation)

    @staticmethod
    def make_plot(title: str = "") -> pg.PlotWidget:

        plot = pg.PlotWidget(title=title)

        plot.setLabel("bottom", "x", units="AU")
        plot.setLabel("left", "y", units="AU")

        return plot

    # noinspection PyUnresolvedReferences
    def plot_orbits(self):

        animate_inertial = self.plot_inertial_orbits()
        animate_corotating = self.plot_corotating_orbits()

        self.timer = QTimer()
        self.timer.timeout.connect(animate_inertial)  # type: ignore
        self.timer.timeout.connect(animate_corotating)  # type: ignore

    def plot_index_generator(self):
        """This generator yields the index of the next point to plot."""

        i = 0

        time_step_default = 1 * HOURS

        # maximum rate of plot update is too slow
        # so instead step through arrays
        # inversely proportional to time_step so that
        # animated motion is the same regardless of
        # num_steps or num_years
        rate = ceil(50 * time_step_default / abs(self.sim.time_step_in_seconds))

        while True:

            i = i + rate

            if i >= self.sim.num_steps:
                i = 0

            yield i

    def array_step(self, num_points_to_plot: int = 10 ** 5) -> int:

        # no need to plot all points

        # step size when plotting
        # i.e. if points_plotted_step = 10 then plot every 10th point
        points_plotted_step = int((self.sim.num_steps + 1) / num_points_to_plot)

        return 1 if points_plotted_step == 0 else points_plotted_step

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

        legend = plot.addLegend()

        legend.clear()

        arr_step = self.array_step()

        plot.plot(
            star_pos[::arr_step, :2] / AU,
            pen="y",
            name="Star",
        )

        plot.plot(
            planet_pos[::arr_step, :2] / AU,
            pen="b",
            name="Planet",
        )

        plot.plot(
            sat_pos[::arr_step, :2] / AU,
            pen="g",
            name="Satellite",
        )

        anim_plot = pg.ScatterPlotItem()

        plot.addItem(anim_plot)

        star_args: dict[str, str | int] = {
            "pen": "y",
            "brush": "y",
            "size": 10,
            "name": "Star",
        }

        planet_args: dict[str, str | int] = {
            "pen": "b",
            "brush": "b",
            "size": 10,
            "name": "Planet",
        }

        sat_args: dict[str, str | int] = {
            "pen": "g",
            "brush": "g",
            "size": 10,
            "name": "Satellite",
        }

        # The purpose of this is to add the bodies to the plot legend
        # and plot their initial positions
        Plotter.plot_point(anim_plot, star_pos[0], **star_args)

        Plotter.plot_point(anim_plot, planet_pos[0], **planet_args)

        Plotter.plot_point(anim_plot, sat_pos[0], **sat_args)

        idx_gen = self.plot_index_generator()

        def animate_plot():
            i = next(idx_gen)

            anim_plot.clear()

            Plotter.plot_point(anim_plot, star_pos[i], **star_args)
            Plotter.plot_point(anim_plot, planet_pos[i], **planet_args)
            Plotter.plot_point(anim_plot, sat_pos[i], **sat_args)

        return animate_plot

    @staticmethod
    def plot_point(scatter_plot: pg.ScatterPlotItem, pos: Array1D, **kwargs):
        """Plots pos on scatter_plot.
        pos can be any subscript-able list with length >= 2. Only the first 2 elements are plotted.
        """

        scatter_plot.addPoints(
            pos=[pos[:2] / AU],
            **kwargs,
        )

    def plot_inertial_orbits(self) -> AnimatePlotFunc:

        return self.plot_orbit(
            self.inertial_plot, self.sim.star_pos, self.sim.planet_pos, self.sim.sat_pos
        )

    def plot_corotating_orbits(self) -> AnimatePlotFunc:
        """Plots the orbits of the system simulated in the corotating frame"""

        star_pos_corotating = self.sim.transform_to_corotating(self.sim.star_pos)
        planet_pos_corotating = self.sim.transform_to_corotating(self.sim.planet_pos)
        sat_pos_corotating = self.sim.transform_to_corotating(self.sim.sat_pos)

        animate_corotating_plot = self.plot_orbit(
            self.corotating_plot,
            star_pos_corotating,
            planet_pos_corotating,
            sat_pos_corotating,
        )

        self.add_lagrange_point_to_corotating_plot()

        return animate_corotating_plot

    def add_lagrange_point_to_corotating_plot(self):

        lagrange_point_plot = pg.ScatterPlotItem()

        self.corotating_plot.addItem(lagrange_point_plot)

        lagrange_point = self.sim.lagrange_point

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

    def plot_conserved_quantities(self):
        """Plots the relative change in the conserved quantities:
        linear and angular momenta, and energy"""

        (
            total_momentum,
            total_angular_momentum,
            total_energy,
        ) = self.sim.conservation_calculations()

        # Conversion to float is just to satisfy mypy
        init_planet_momentum = float(
            norm(self.sim.planet_mass * self.sim.planet_vel[0])
        )

        # slice the arrays so that we only plot at most 10**5 points.
        arr_step = self.array_step()

        times_in_years = self.sim.time_points_in_years()[::arr_step]

        total_momentum = total_momentum[::arr_step]
        self.plot_linear_momentum(total_momentum, init_planet_momentum, times_in_years)

        total_angular_momentum = total_angular_momentum[::arr_step]
        self.plot_angular_momentum(total_angular_momentum, times_in_years)

        total_energy = total_energy[::arr_step]
        self.plot_energy(total_energy, times_in_years)

    def plot_linear_momentum(
            self,
            total_momentum: Array2D,
            init_planet_momentum: float,
            times_in_years: Array1D,
    ):
        """Plots the relative change in the linear momentum"""

        linear_momentum_plot = self.initialize_conserved_plot("Linear Momentum")

        # total linear momentum is initially approx. 0.
        # due to this any variation will make it seem as if it is not conserved.
        # however the variation is insignificant compared to
        # the star and planet's individual linear momenta.
        # That suggests that the variation is due to floating point error
        # or the error of the numerical integration method.

        normalized_linear_momentum = total_momentum / init_planet_momentum

        for component in ("x", "y", "z"):
            Plotter.plot_component(
                linear_momentum_plot,
                times_in_years,
                normalized_linear_momentum,
                component,
            )

    def plot_angular_momentum(
            self, total_angular_momentum: Array2D, times_in_years: Array1D
    ):
        """Plots the relative change in the angular momentum."""

        angular_momentum_plot = self.initialize_conserved_plot("Angular Momentum")

        for component, (idx, _) in Plotter.component_to_plot_args.items():
            normalized_angular_momentum = (
                    total_angular_momentum[:, idx] / total_angular_momentum[0, idx] - 1
            )

            Plotter.plot_component(
                angular_momentum_plot,
                times_in_years,
                normalized_angular_momentum,
                component,
            )

    @staticmethod
    def plot_component(
            plot: pg.PlotWidget, times: Array1D, arr: Array2D, component: str
    ):
        """Plots a component of a 2D array against the times array.
        component must be one of the following: 'x', 'y', 'z'"""

        try:
            idx, pen = Plotter.component_to_plot_args[component]

        except KeyError as err:
            raise ValueError(
                f"component must be one of the following: x, y, z. Got {component}"
            ) from err

        arr = arr[:, idx]

        plot.plot(times, arr, name=component, pen=pen)

    def plot_energy(self, total_energy: Array1D, times_in_years: Array1D):
        """Plots the relative change in the energy"""

        energy_plot = self.initialize_conserved_plot("Energy")
        energy_plot.plot(times_in_years, total_energy / total_energy[0] - 1)

    @staticmethod
    def initialize_conserved_plot(quantity_name: str):
        """Initializes the plot axes and title for the conserved quantities plots"""

        plot = Plotter.make_plot(title=f"Relative Change in {quantity_name} vs Time")

        plot.setLabel("bottom", "Time", units="years")
        plot.setLabel("left", f"Relative Change in {quantity_name}")
        plot.addLegend()

        return plot
