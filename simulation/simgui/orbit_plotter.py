"""This module contains the OrbitPlotter class which is responsible for plotting
the orbits of the system simulated by an instance of the Simulation class.
"""
from typing import Callable

import pyqtgraph as pg  # type: ignore
from numpy.linalg import norm
from PyQt6.QtCore import QTimer  # pylint: disable=no-name-in-module
from simulation import Simulation
from simulation.constants import AU, years
from simulation.simulation.sim_types import Array1D, Array2D


class Plotter:
    """Plots the data produced by a Simulation"""

    def __init__(self, sim: Simulation):
        self.sim = sim

        self.timer = QTimer()

    def plot_orbit(self):
        """Plots the orbit of the satellite in both inertial and corotating frames"""

        inertial_plot, update_inertial = self.plot_inertial_orbit()

        self.timer.timeout.connect(update_inertial)

        star_pos_rotated = self.sim.transform_to_corotating(self.sim.star_pos)

        planet_pos_rotated = self.sim.transform_to_corotating(self.sim.planet_pos)

        sat_pos_rotated = self.sim.transform_to_corotating(self.sim.sat_pos)

        corotating_plot, update_corotating = self.plot_corotating_orbit(
            star_pos_rotated,
            planet_pos_rotated,
            sat_pos_rotated,
        )

        self.timer.timeout.connect(update_corotating)  # type: ignore # pylint: disable=no-member

        # time in milliseconds between plot updates
        period = 33

        self.timer.start(period)

    def plot_inertial_orbit(self):
        """Plots the orbits of the system simulated by the simulation"""

        orbit_plot = pg.plot(title="Orbits of Masses")
        orbit_plot.setLabel("bottom", "x", units="AU")
        orbit_plot.setLabel("left", "y", units="AU")
        orbit_plot.addLegend()

        orbit_plot.setXRange(
            -1.2 * self.sim.planet_distance, 1.2 * self.sim.planet_distance
        )
        orbit_plot.setYRange(
            -1.2 * self.sim.planet_distance, 1.2 * self.sim.planet_distance
        )
        orbit_plot.setAspectLocked(True)

        arr_step = self.sim.array_step()

        # Sun has an orbit on the scale of micro-AU under normal Earth-Sun conditions
        # Zoom in to see it
        orbit_plot.plot(
            self.sim.star_pos[::arr_step, :2] / AU,
            pen="y",
            name="Star",
        )

        orbit_plot.plot(
            self.sim.planet_pos[::arr_step, :2] / AU,
            pen="b",
            name="Planet",
        )

        orbit_plot.plot(
            self.sim.sat_pos[::arr_step, :2] / AU,
            pen="g",
            name="Satellite",
        )

        anim_plot = pg.ScatterPlotItem()

        # The purpose of this is to add the bodies to the plot legend
        # and plot their initial positions
        anim_plot.addPoints(
            [self.sim.star_pos[0, 0] / AU],
            [self.sim.star_pos[0, 1] / AU],
            pen="y",
            brush="y",
            size=10,
        )

        anim_plot.addPoints(
            [self.sim.planet_pos[0, 0] / AU],
            [self.sim.planet_pos[0, 1] / AU],
            pen="b",
            brush="b",
            size=10,
        )

        anim_plot.addPoints(
            [self.sim.sat_pos[0, 0] / AU],
            [self.sim.sat_pos[0, 1] / AU],
            pen="g",
            brush="g",
            size=10,
        )

        orbit_plot.addItem(anim_plot)

        idx_gen = self.sim.idx_gen()

        def update_plot():

            i = next(idx_gen)

            anim_plot.clear()

            anim_plot.addPoints(
                [self.sim.star_pos[i, 0] / AU],
                [self.sim.star_pos[i, 1] / AU],
                pen="y",
                brush="y",
                size=10,
                name="Star",
            )

            anim_plot.addPoints(
                [self.sim.planet_pos[i, 0] / AU],
                [self.sim.planet_pos[i, 1] / AU],
                pen="b",
                brush="b",
                size=10,
                name="Planet",
            )

            anim_plot.addPoints(
                [self.sim.sat_pos[i, 0] / AU],
                [self.sim.sat_pos[i, 1] / AU],
                pen="g",
                brush="g",
                size=10,
                name="Satellite",
            )

        return orbit_plot, update_plot

    def plot_corotating_orbit(
        self,
        star_pos_rotated: Array2D,
        planet_pos_rotated: Array2D,
        sat_pos_rotated: Array2D,
    ) -> tuple[pg.PlotWidget, Callable[[], None]]:
        """Plots the orbits of the system simulated by the simulation in the corotating frame"""

        # Animated plot of satellites orbit in co-rotating frame.
        corotating_plot = pg.plot(title="Orbits in Co-Rotating Coordinate System")
        corotating_plot.setLabel("bottom", "x", units="AU")
        corotating_plot.setLabel("left", "y", units="AU")
        corotating_plot.addLegend()

        min_x = star_pos_rotated[0, 0] / AU - 0.2 * self.sim.planet_distance

        max_x = planet_pos_rotated[0, 0] / AU + 0.2 * self.sim.planet_distance

        min_y = -0.5 * self.sim.planet_distance

        max_y = self.sim.lagrange_point_trans[1] / AU + 0.5 * self.sim.planet_distance

        corotating_plot.setXRange(min_x, max_x)
        corotating_plot.setYRange(min_y, max_y)
        corotating_plot.setAspectLocked(True)

        anim_rotated_plot = pg.ScatterPlotItem()

        corotating_plot.addItem(anim_rotated_plot)

        arr_step = self.sim.array_step()

        corotating_plot.plot(
            sat_pos_rotated[::arr_step, 0] / AU,
            sat_pos_rotated[::arr_step, 1] / AU,
            pen="g",
        )

        # The purpose of this is to add the bodies to the plot legend
        # and plot their initial positions
        corotating_plot.plot(
            [star_pos_rotated[0, 0] / AU],
            [star_pos_rotated[0, 1] / AU],
            name="Star",
            pen="k",
            symbol="o",
            symbolPen="y",
            symbolBrush="y",
        )

        corotating_plot.plot(
            [planet_pos_rotated[0, 0] / AU],
            [planet_pos_rotated[0, 1] / AU],
            name="Planet",
            pen="k",
            symbol="o",
            symbolPen="b",
            symbolBrush="b",
        )

        corotating_plot.plot(
            [sat_pos_rotated[0, 0] / AU],
            [sat_pos_rotated[0, 1] / AU],
            name="Satellite",
            pen="k",
            symbol="o",
            symbolPen="g",
            symbolBrush="g",
        )

        corotating_plot.plot(
            [self.sim.lagrange_point_trans[0] / AU],
            [self.sim.lagrange_point_trans[1] / AU],
            name="Lagrange Point",
            pen="k",
            symbol="o",
            symbolPen="w",
            symbolBrush="w",
        )

        idx_gen = self.sim.idx_gen()

        def update_corotating():

            j = next(idx_gen)

            anim_rotated_plot.clear()

            anim_rotated_plot.addPoints(
                [star_pos_rotated[j, 0] / AU],
                [star_pos_rotated[j, 1] / AU],
                pen="y",
                brush="y",
                size=10,
                name="Star",
            )

            anim_rotated_plot.addPoints(
                [planet_pos_rotated[j, 0] / AU],
                [planet_pos_rotated[j, 1] / AU],
                pen="b",
                brush="b",
                size=10,
                name="Planet",
            )

            anim_rotated_plot.addPoints(
                [sat_pos_rotated[j, 0] / AU],
                [sat_pos_rotated[j, 1] / AU],
                pen="g",
                brush="g",
                size=10,
                name="Satellite",
            )

        return corotating_plot, update_corotating

    def plot_conserved_quantities(self):
        """Plots the relative change in the conserved quantities:
        linear and angular momenta, and energy"""

        (
            total_momentum,
            total_angular_momentum,
            total_energy,
        ) = self.sim.conservation_calculations()

        init_planet_momentum = norm(self.sim.planet_mass * self.sim.planet_vel[0])

        # step through the array so that we only plot at most 10**5 points.
        arr_step = self.sim.array_step()

        times_in_years = self.sim.times[::arr_step] / years

        self.plot_linear_momentum(
            total_momentum, init_planet_momentum, times_in_years, arr_step
        )

        self.plot_angular_momentum(total_angular_momentum, times_in_years, arr_step)

        self.plot_energy(total_energy, times_in_years, arr_step)

    def plot_linear_momentum(
        self,
        total_momentum: Array2D,
        init_planet_momentum: float,
        times_in_years: Array1D,
        arr_step: int,
    ):
        """Plots the relative change in the linear momentum"""

        linear_momentum_plot = self.initialize_conserved_plot("Linear Momentum")

        # total linear momentum is not conserved (likely due to floating point errors)
        # however the variation is insignificant compared to
        # the star's and planet's individual linear momenta
        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[::arr_step, 0] / init_planet_momentum,
            pen="r",
            name="x",
        )

        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[::arr_step, 1] / init_planet_momentum,
            pen="g",
            name="y",
        )

        linear_momentum_plot.plot(
            times_in_years,
            total_momentum[::arr_step, 2] / init_planet_momentum,
            pen="b",
            name="z",
        )

    def plot_angular_momentum(
        self, total_angular_momentum: Array2D, times_in_years: Array1D, arr_step
    ):
        """Plots the relative change in the angular momentum.
        Doesn't plot the x and y components of the angular momentum, because they are always 0"""

        angular_momentum_plot = self.initialize_conserved_plot("Angular Momentum")

        # x and y components of angular momentum are 0
        # angular_momentum_plot.plot(
        #   times_in_years,
        #   total_angular_momentum[::arr_step, 0]/total_angular_momentum[0, 0]-1,
        #   pen='r',
        #   name='x'
        # )

        # angular_momentum_plot.plot(
        #   times_in_years,
        #   total_angular_momentum[::arr_step, 1]/total_angular_momentum[0, 1]-1,
        #   pen='g',
        #   name='y'
        # )

        angular_momentum_plot.plot(
            times_in_years,
            total_angular_momentum[::arr_step, 2] / total_angular_momentum[0, 2] - 1,
            pen="b",
            name="z",
        )

    def plot_energy(
        self, total_energy: Array1D, times_in_years: Array1D, arr_step: int
    ):
        """Plots the relative change in the energy"""

        energy_plot = self.initialize_conserved_plot("Energy")

        energy_plot.plot(times_in_years, total_energy[::arr_step] / total_energy[0] - 1)

    @staticmethod
    def initialize_conserved_plot(quantity_name: str):
        """Initializes the plot axes and title for the conserved quantities"""

        plot = pg.plot(title=f"Relative Change in {quantity_name} vs Time")

        plot.setLabel("bottom", "Time", units="years")

        plot.setLabel("left", f"Relative Change in {quantity_name}")

        plot.addLegend()

        return plot
