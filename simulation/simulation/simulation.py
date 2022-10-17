# pylint: disable=invalid-name, missing-function-docstring
"""This module contains the simulation class which simulates
orbits near Lagrange points using the position Verlet algorithm.
It assumes that both the star and planet are undergoing uniform circular motion.
"""


from math import ceil, sqrt

# numpy allows us to compute common math functions and work with arrays.
import numpy as np

# plotting module.
from numpy import pi

# shortens function call
from numpy.linalg import norm
from numpy.typing import NDArray
from PyQt6.QtCore import QTimer  # pylint: disable=no-name-in-module

from simulation.constants import AU, G, earth_mass, sat_mass, sun_mass, years

from . import descriptors
from .numba_funcs import integrate, transform_to_corotating
from .sim_types import Array2D, Array1D


def array_of_norms(arr_2d: Array2D) -> Array1D:
    """Returns an array of the norm of each element of the input array"""

    return norm(arr_2d, axis=1)


def unit_vector(angle: float) -> Array1D:

    return np.array([np.cos(angle), np.sin(angle), 0])


def calc_period_from_semi_major_axis(
    semi_major_axis: float, star_mass: float, planet_mass: float
) -> float:

    period_squared = (
        4 * pi**2 * semi_major_axis**3 / (G * (star_mass + planet_mass))
    )

    return sqrt(period_squared)


class Simulation:
    """Simulates orbits near Lagrange points using the position Verlet algorithm.

    Takes the following parameters:

    #### Simulation Parameters

    num_years: float. Number of years to simulate. The default is 100.0.

    num_steps: int. Number of steps to simulate. The default is 10**6.

    a ratio of 10**4 steps per year is recommended.

    #### Initial Conditions

    perturbation_size: float. Size of perturbation away from the Lagrange point in AU.
    The default is 0.0.

    perturbation_angle: float Angle of perturbation relative to positive x axis in degrees.
    The default is None.
    If None, then perturbations are away or toward the origin.

    speed: float. Initial speed of satellite as a factor of the planet's speed.
    i.e. speed = 1.0 -> satellite has the same speed as the planet.
    the default is 1.0.

    vel_angle: float. Angle of satellite's initial velocity relative to positive x axis in degrees.
    The default is None.
    If None, then vel_angle is perpendicular to the satellite's
    default position relative to the star.

    lagrange_point: string. Non-perturbed position of satellite. Must be a string.
    The default is 'L4' but 'L1', 'L2', 'L3', and 'L5' can also be used.

    #### System Parameters

    star_mass: float. Mass of the star in kilograms. The default is the mass of the Sun.

    planet_mass: float. Mass of the planet in kilograms. The default is the mass of the Earth.
    The constants sun_mass and earth_mass may be imported from the file constants.py.

    planet_distance: float. Distance between the planet and the star in AU. The default is 1.0.

    This function will take ~0.42 seconds per 10**6 steps.
    The time may vary depending on your hardware.
    It will take longer than usual on the first call.
    """

    num_years = descriptors.float_desc()
    num_steps = descriptors.positive_int()
    perturbation_size = descriptors.float_desc()
    perturbation_angle = descriptors.optional_float_desc()
    speed = descriptors.float_desc()
    vel_angle = descriptors.optional_float_desc()
    star_mass = descriptors.non_negative_float()
    planet_mass = descriptors.non_negative_float()
    planet_distance = descriptors.positive_float()
    lagrange_label = descriptors.lagrange_label_desc()

    def __init__(
        self,
        num_years: float = 100.0,
        num_steps: int = 10**6,
        perturbation_size: float = 0.0,
        perturbation_angle: float | None = None,
        speed: float = 1.0,
        vel_angle: float | None = None,
        star_mass: float = sun_mass,
        planet_mass: float = earth_mass,
        planet_distance: float = 1.0,
        lagrange_label: str = "L4",
    ):

        self.num_years = num_years

        self.num_steps = num_steps

        self.perturbation_size = perturbation_size

        self.speed = speed

        self.star_mass = star_mass

        self.planet_mass = planet_mass

        self.planet_distance = planet_distance

        self.lagrange_label = lagrange_label

        self.lagrange_point_trans: Array1D = np.empty(3, dtype=np.double)

        self.perturbation_angle = perturbation_angle

        self.vel_angle = vel_angle

        self.star_pos: Array2D = np.empty((0, 3), dtype=np.double)

        self.star_vel: Array2D = np.empty_like(self.star_pos)

        self.planet_pos: Array2D = np.empty_like(self.star_pos)

        self.planet_vel: Array2D = np.empty_like(self.star_pos)

        self.sat_pos: Array2D = np.empty_like(self.star_pos)

        self.sat_vel: Array2D = np.empty_like(self.star_pos)

        self.timer = QTimer()

    @property
    def sim_stop(self):

        return self.num_years * years

    @property
    def time_step(self):

        return self.sim_stop / self.num_steps

    @property
    def times(self):

        return np.linspace(0, self.sim_stop, self.num_steps + 1)

    @property
    def lagrange_point(self):

        return self.calc_lagrange_point()

    def calc_lagrange_point(self) -> Array1D:

        planet_distance = self.planet_distance * AU

        hill_radius: float = planet_distance * (
            self.planet_mass / (3 * self.star_mass)
        ) ** (1 / 3)

        match self.lagrange_label:

            case "L1":
                return planet_distance * np.array((1, 0, 0)) - np.array(
                    (hill_radius, 0, 0)
                )

            case "L2":
                return planet_distance * np.array((1, 0, 0)) + np.array(
                    (hill_radius, 0, 0)
                )

            case "L3":
                L3_dist = planet_distance * 7 / 12 * self.planet_mass / self.star_mass

                return -planet_distance * np.array((1, 0, 0)) - np.array(
                    (L3_dist, 0, 0)
                )

            case "L4":

                return planet_distance * unit_vector(pi / 3)

            case "L5":

                return planet_distance * unit_vector(-pi / 3)

            case _:
                raise ValueError(
                    "Invalid Lagrange point label. Must be one of ('L1', 'L2', 'L3', 'L4', 'L5')"
                )

    @property
    def default_perturbation_angle(self):

        return {"L1": 0.0, "L2": 0.0, "L3": 180.0, "L4": 60.0, "L5": -60.0}[
            self.lagrange_label
        ]

    @property
    def actual_perturbation_angle(self):

        return self.perturbation_angle or self.default_perturbation_angle

    @property
    def actual_vel_angle(self):

        return self.vel_angle or self.default_perturbation_angle + 90

    @property
    def orbital_period(self):

        return self.calc_orbital_period()

    def calc_orbital_period(self) -> float:

        return calc_period_from_semi_major_axis(
            self.planet_distance * AU, self.star_mass, self.planet_mass
        )

    @property
    def angular_speed(self):

        return 2 * pi / self.orbital_period

    def simulate(self):

        self.initialize_system()

        self.integrate()

    def initialize_system(self):

        """Initializes the arrays of positions and velocities
        so that their initial values correspond to the input parameters
        """

        if len(self.star_pos) != self.num_steps + 1:

            self.allocate_arrays()

        self.initialize_positions()

        # we setup conditions so that the star and planet have circular orbits
        # about the center of mass
        # velocities have to be defined relative to the CM
        init_CM_pos = self.calc_center_of_mass_pos_or_vel(
            self.star_pos[0], self.planet_pos[0], self.sat_pos[0]
        )

        self.initialize_velocities(init_CM_pos)

        self.transform_to_CM_ref_frame(init_CM_pos)

    def allocate_arrays(self):

        self.star_pos = np.empty((self.num_steps + 1, 3), dtype=np.double)

        self.star_vel = np.empty_like(self.star_pos)

        self.planet_pos = np.empty_like(self.star_pos)

        self.planet_vel = np.empty_like(self.star_pos)

        self.sat_pos = np.empty_like(self.star_pos)

        self.sat_vel = np.empty_like(self.star_pos)

    def initialize_positions(self):

        self.star_pos[0] = np.array((0, 0, 0))

        self.planet_pos[0] = np.array((self.planet_distance * AU, 0, 0))

        # Perturbation of satellite's position #

        perturbation_size = self.perturbation_size * AU

        perturbation_angle = np.radians(self.actual_perturbation_angle)

        perturbation = perturbation_size * np.array(
            (np.cos(perturbation_angle), np.sin(perturbation_angle), 0)
        )

        self.sat_pos[0] = self.lagrange_point + perturbation

    def initialize_velocities(self, init_CM_pos: Array1D):

        # orbits are counter clockwise so
        # angular velocity is in the positive z direction
        angular_vel = np.array((0, 0, self.angular_speed), dtype=np.double)

        # for a circular orbit velocity = cross_product(angular velocity, position)
        # where vec(position) is the position relative to the point being orbited
        # in this case the Center of Mass
        self.star_vel[0] = np.cross(angular_vel, self.star_pos[0] - init_CM_pos)

        self.planet_vel[0] = np.cross(angular_vel, self.planet_pos[0] - init_CM_pos)

        speed = self.speed * norm(self.planet_vel[0])

        vel_angle = np.radians(self.actual_vel_angle)

        self.sat_vel[0] = speed * unit_vector(vel_angle)

    def transform_to_CM_ref_frame(self, init_CM_pos: Array1D):

        self.star_pos[0] -= init_CM_pos
        self.planet_pos[0] -= init_CM_pos
        self.sat_pos[0] -= init_CM_pos

        self.lagrange_point_trans = self.lagrange_point - init_CM_pos

    def integrate(self):

        integrate(
            self.time_step,
            self.num_steps,
            self.star_mass,
            self.planet_mass,
            self.star_pos,
            self.star_vel,
            self.planet_pos,
            self.planet_vel,
            self.sat_pos,
            self.sat_vel,
        )

    def calc_center_of_mass_pos_or_vel(
        self,
        star_pos_or_vel: NDArray[np.floating],
        planet_pos_or_vel: NDArray[np.floating],
        sat_pos_or_vel: NDArray[np.floating],
    ) -> NDArray[np.floating]:

        return (
            self.star_mass * star_pos_or_vel
            + self.planet_mass * planet_pos_or_vel
            + sat_mass * sat_pos_or_vel
        ) / (self.star_mass + self.planet_mass + sat_mass)

    def transform_to_corotating(self, pos_trans: Array2D) -> Array2D:

        return transform_to_corotating(self.times, self.angular_speed, pos_trans)

    def array_step(self, num_points_to_plot: int = 10**5) -> int:

        # no need to plot all points

        # step size when plotting
        # i.e. if points_plotted_step = 10 then plot every 10th point
        points_plotted_step = int((self.num_steps + 1) / num_points_to_plot)

        if points_plotted_step == 0:
            points_plotted_step = 1

        return points_plotted_step

    def idx_gen(self):
        """This function is used to update the index of the plots"""

        i = 0

        time_step_default = 10 * years / 10**5

        # maximum rate of plot update is too slow
        # so instead step through arrays
        # inversely proportional to time_step so that
        # animated motion is the same regardless of
        # num_steps or num_years
        rate = ceil(50 * time_step_default / abs(self.time_step))

        while True:

            i = i + rate

            if i >= self.num_steps:
                i = 0

            yield i

    def conservation_calculations(self) -> tuple[Array2D, Array2D, Array1D]:

        total_momentum = self.calc_total_linear_momentum()

        total_angular_momentum = self.calc_total_angular_momentum()

        total_energy = self.calc_total_energy()

        return total_momentum, total_angular_momentum, total_energy

    def calc_total_linear_momentum(self) -> Array2D:

        return (
            self.star_mass * self.star_vel
            + self.planet_mass * self.planet_vel
            + sat_mass * self.sat_vel
        )

    def calc_total_angular_momentum(
        self,
    ) -> Array2D:

        angular_momentum_star: Array2D = np.cross(
            self.star_pos, self.star_mass * self.star_vel
        )

        angular_momentum_planet = np.cross(
            self.planet_pos, self.planet_mass * self.planet_vel
        )

        angular_momentum_sat = np.cross(self.sat_pos, sat_mass * self.sat_vel)

        return angular_momentum_star + angular_momentum_planet + angular_momentum_sat

    def calc_total_energy(self) -> Array1D:

        d_planet_to_star = array_of_norms(self.star_pos - self.planet_pos)

        d_planet_to_sat = array_of_norms(self.sat_pos - self.planet_pos)

        d_star_to_sat = array_of_norms(self.sat_pos - self.star_pos)

        potential_energy = (
            -G * self.star_mass * self.planet_mass / d_planet_to_star
            + -G * sat_mass * self.planet_mass / d_planet_to_sat
            + -G * sat_mass * self.star_mass / d_star_to_sat
        )

        mag_star_vel = array_of_norms(self.star_vel)

        mag_planet_vel = array_of_norms(self.planet_vel)

        mag_sat_vel = array_of_norms(self.sat_vel)

        kinetic_energy = (
            0.5 * self.star_mass * mag_star_vel**2
            + 0.5 * self.planet_mass * mag_planet_vel**2
            + 0.5 * sat_mass * mag_sat_vel**2
        )

        return potential_energy + kinetic_energy
