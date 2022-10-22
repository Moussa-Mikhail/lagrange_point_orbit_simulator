# pylint: disable=missing-function-docstring
"""This module contains the Plotter class which is responsible for plotting
the orbits of the system simulated by an instance of the Simulator class.
"""
from math import ceil
from typing import Callable

import pyqtgraph as pg  # type: ignore
from numpy.linalg import norm
from PyQt6.QtCore import QTimer  # pylint: disable=no-name-in-module
from simulation import Simulator
from simulation.constants import AU, HOURS
from simulation.simulator.sim_types import Array1D, Array2D

AnimatePlotFuncT = Callable[[], None]


class Plotter:
    """Plots the arrays produced by a Simulator"""

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

    def plot_orbits(self):

        animate_inertial = self.plot_inertial_orbits()

        animate_corotating = self.plot_corotating_orbits()

        self.timer = QTimer()

        self.timer.timeout.connect(animate_inertial)

        self.timer.timeout.connect(animate_corotating)

    def idx_gen(self):
        """This function is used to update the index of the plots"""

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

    def array_step(self, num_points_to_plot: int = 10**5) -> int:

        # no need to plot all points

        # step size when plotting
        # i.e. if points_plotted_step = 10 then plot every 10th point
        points_plotted_step = int((self.sim.num_steps + 1) / num_points_to_plot)

        if points_plotted_step == 0:

            points_plotted_step = 1

        return points_plotted_step

    def plot_orbit(
        self,
        plot: pg.PlotWidget,
        star_pos: Array2D,
        planet_pos: Array2D,
        sat_pos: Array2D,
    ):
        """Plotting logic common to both inertial and corotating plots.
        Returns a function which is called by the timer to animate the plot.
        """

        plot.clear()

        plot.addLegend()

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

        # The purpose of this is to add the bodies to the plot legend
        # and plot their initial positions
        anim_plot.addPoints(
            [star_pos[0, 0] / AU],
            [star_pos[0, 1] / AU],
            pen="y",
            brush="y",
            size=10,
        )

        anim_plot.addPoints(
            [planet_pos[0, 0] / AU],
            [planet_pos[0, 1] / AU],
            pen="b",
            brush="b",
            size=10,
        )

        anim_plot.addPoints(
            [sat_pos[0, 0] / AU],
            [sat_pos[0, 1] / AU],
            pen="g",
            brush="g",
            size=10,
        )

        idx_gen = self.idx_gen()

        def animate_plot():

            i = next(idx_gen)

            anim_plot.clear()

            anim_plot.addPoints(
                [star_pos[i, 0] / AU],
                [star_pos[i, 1] / AU],
                pen="y",
                brush="y",
                size=10,
                name="Star",
            )

            anim_plot.addPoints(
                [planet_pos[i, 0] / AU],
                [planet_pos[i, 1] / AU],
                pen="b",
                brush="b",
                size=10,
                name="Planet",
            )

            anim_plot.addPoints(
                [sat_pos[i, 0] / AU],
                [sat_pos[i, 1] / AU],
                pen="g",
                brush="g",
                size=10,
                name="Satellite",
            )

        return animate_plot

    def plot_inertial_orbits(self) -> AnimatePlotFuncT:

        return self.plot_orbit(
            self.inertial_plot, self.sim.star_pos, self.sim.planet_pos, self.sim.sat_pos
        )

    def plot_corotating_orbits(self) -> AnimatePlotFuncT:
        """Plots the orbits of the system simulated in the corotating frame"""

        star_pos_corotating = self.sim.transform_to_corotating(self.sim.star_pos)

        planet_pos_corotating = self.sim.transform_to_corotating(self.sim.planet_pos)

        sat_pos_corotating = self.sim.transform_to_corotating(self.sim.sat_pos)

        return self.plot_orbit(
            self.corotating_plot,
            star_pos_corotating,
            planet_pos_corotating,
            sat_pos_corotating,
        )

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

        # total linear momentum is not conserved (likely due to floating point errors)
        # however the variation is insignificant compared to
        # the star's and planet's individual linear momenta
        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[0] / init_planet_momentum,
            pen="r",
            name="x",
        )

        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[1] / init_planet_momentum,
            pen="g",
            name="y",
        )

        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[2] / init_planet_momentum,
            pen="b",
            name="z",
        )

    def plot_angular_momentum(
        self, total_angular_momentum: Array2D, times_in_years: Array1D
    ):
        """Plots the relative change in the angular momentum.
        Doesn't plot the x and y components of the angular momentum, because they are always 0"""

        angular_momentum_plot = self.initialize_conserved_plot("Angular Momentum")

        # x and y components of angular momentum are 0
        # angular_momentum_plot.plot(
        #   times_in_years,
        #   total_angular_momentum[0]/total_angular_momentum[0, 0]-1,
        #   pen='r',
        #   name='x'
        # )

        # angular_momentum_plot.plot(
        #   times_in_years,
        #   total_angular_momentum[1]/total_angular_momentum[0, 1]-1,
        #   pen='g',
        #   name='y'
        # )

        angular_momentum_plot.plot(
            times_in_years,
            total_angular_momentum[2] / total_angular_momentum[0, 2] - 1,
            pen="b",
            name="z",
        )

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
