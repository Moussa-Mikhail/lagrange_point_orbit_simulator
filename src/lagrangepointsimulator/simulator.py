"""This module contains the Simulator class
which takes parameters defining a satellites orbit near a Lagrange point and simulates
that orbit.
It ensures that both the star and planet are undergoing uniform circular motion.
"""

from math import ceil, sqrt
from typing import TypeVar, cast

import numpy as np
from numpy.linalg import norm

from src.lagrangepointsimulator import descriptors
from src.lagrangepointsimulator.constants import AU, EARTH_MASS, HOURS, SUN_MASS, YEARS, G
from src.lagrangepointsimulator.numba_funcs import integrate as nb_integrate
from src.lagrangepointsimulator.numba_funcs import transform_to_corotating as nb_transform_to_corotating
from src.lagrangepointsimulator.sim_types import Array1D, Array2D


def array_of_norms(arr_2d: Array2D) -> Array1D:
    """Returns an array of the norm of each element of the input array"""
    return norm(arr_2d, axis=1)


def unit_vector(angle: float) -> Array1D:
    """Takes an angle in radians and returns the corresponding unit vector"""
    return np.array([np.cos(angle), np.sin(angle), 0])


def calc_period_from_semi_major_axis(semi_major_axis: float, star_mass: float, planet_mass: float) -> float:
    period_squared = 4 * np.pi**2 * semi_major_axis**3 / (G * (star_mass + planet_mass))

    return sqrt(period_squared)


class Simulator:
    """This class holds parameters defining a satellites orbit and simulates it.
    Once an instance of the class has been created it can be used by calling the simulate method.
    The constructor takes the following parameters:

    #### Simulation Parameters

    num_years: positive float. Time to simulate in years. The default is 100.0.

    time_step: float. Time inbetween simulation steps in hours. the default is 1.0.
    A negative value will cause the simulation to run backwards in time.

    #### Satellite Parameters

    perturbation_size: float. Size of perturbation away from the Lagrange point in AU.
    The default is 0.0.

    perturbation_angle: float. Angle of perturbation relative to positive x-axis in degrees.
    The default is None.
    If None, then perturbations are away or toward the origin.

    speed: float. Initial speed of satellite as a factor of the planet's speed.
    e.g. speed = 1.0 -> satellite has the same speed as the planet.
    the default is 1.0.

    vel_angle: float. Angle of satellite's initial velocity relative to positive x-axis in degrees.
    The default is None.
    If None, then vel_angle is perpendicular to the satellite's
    default position relative to the star.

    lagrange_label: string. Non-perturbed position of satellite.
    The default is 'L4' but 'L1', 'L2', 'L3', and 'L5' can also be used.

    #### System Parameters

    star_mass: positive float. Mass of the star in kilograms. The default is the mass of the Sun.

    planet_mass: positive float. Mass of the planet in kilograms.
    The default is the mass of the Earth.

    The constants "SUN_MASS", "EARTH_MASS", and others maybe import from the constants module.

    planet_distance: positive float.
    Distance between the planet and the star in AU. The default is 1.0.

    The time to simulate will take longer than usual on the first call to the simulate method.
    """

    # mass of satellite in kilograms
    # must be negligible compared to other masses
    SAT_MASS = 1.0

    num_years = descriptors.positive_float()
    time_step = descriptors.float_desc()
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
        time_step: float = 1.0,
        perturbation_size: float = 0.0,
        perturbation_angle: float | None = None,
        speed: float = 1.0,
        vel_angle: float | None = None,
        lagrange_label: str = "L4",
        star_mass: float = SUN_MASS,
        planet_mass: float = EARTH_MASS,
        planet_distance: float = 1.0,
    ) -> None:
        self.num_years = num_years
        self.time_step = time_step

        self.perturbation_size = perturbation_size
        self.perturbation_angle = perturbation_angle
        self.speed = speed
        self.vel_angle = vel_angle
        self.lagrange_label = lagrange_label

        self.star_mass = star_mass
        self.planet_mass = planet_mass
        self.planet_distance = planet_distance

        self.lagrange_point_trans: Array1D = np.empty(3, dtype=np.double)

        self.star_pos: Array2D = cast(Array2D, np.empty((0, 3), dtype=np.double))
        self.star_vel: Array2D = np.empty_like(self.star_pos)
        self.planet_pos: Array2D = np.empty_like(self.star_pos)
        self.planet_vel: Array2D = np.empty_like(self.star_pos)
        self.sat_pos: Array2D = np.empty_like(self.star_pos)
        self.sat_vel: Array2D = np.empty_like(self.star_pos)

    @property
    def sim_time(self) -> float:
        """Time to simulate in seconds"""
        return self.num_years * YEARS

    @property
    def time_step_in_seconds(self) -> float:
        return self.time_step * HOURS

    @property
    def num_steps(self) -> int:
        return 0 if self.time_step_in_seconds == 0 else ceil(abs(self.sim_time / self.time_step_in_seconds))

    def time_points(self) -> Array1D:
        return np.linspace(0, self.sim_time, self.num_steps + 1)

    def time_points_in_years(self) -> Array1D:
        return self.time_points() / YEARS

    def calc_lagrange_point(self) -> Array1D:
        planet_distance_meters = self.planet_distance * AU

        hill_radius: float = planet_distance_meters * (self.planet_mass / (3 * self.star_mass)) ** (1 / 3)

        match self.lagrange_label:
            case "L1":
                return planet_distance_meters * np.array((1, 0, 0)) - np.array((hill_radius, 0, 0))

            case "L2":
                return planet_distance_meters * np.array((1, 0, 0)) + np.array((hill_radius, 0, 0))

            case "L3":
                l3_dist = planet_distance_meters * 7 / 12 * self.planet_mass / self.star_mass

                return -planet_distance_meters * np.array((1, 0, 0)) - np.array((l3_dist, 0, 0))

            case "L4":
                return planet_distance_meters * unit_vector(np.pi / 3)

            case "L5":
                return planet_distance_meters * unit_vector(-np.pi / 3)

            case _:
                msg = "Invalid Lagrange point label. Must be one of ('L1', 'L2', 'L3', 'L4', 'L5')"
                raise ValueError(msg)

    def default_perturbation_angle(self) -> float:
        return {"L1": 0.0, "L2": 0.0, "L3": 180.0, "L4": 60.0, "L5": -60.0}[self.lagrange_label]

    @property
    def actual_perturbation_angle(self) -> float:
        if self.perturbation_angle is None:
            return self.default_perturbation_angle()

        return self.perturbation_angle

    @property
    def actual_vel_angle(self) -> float:
        if self.vel_angle is None:
            return self.default_perturbation_angle() + 90.0

        return self.vel_angle

    @property
    def orbital_period(self) -> float:
        return calc_period_from_semi_major_axis(self.planet_distance * AU, self.star_mass, self.planet_mass)

    @property
    def angular_speed(self) -> float:
        return 2 * np.pi / self.orbital_period

    def simulate(self) -> None:
        self._initialize_arrays()
        self._integrate()

    def _initialize_arrays(self) -> None:
        # Initializes the arrays of positions and velocities
        # so that their initial values correspond to the input parameters

        if len(self.star_pos) != self.num_steps + 1:
            self._allocate_arrays()

        self._initialize_positions()

        # we set up conditions so that the star and planet have circular orbits about the center of mass
        # so velocities have to be defined relative to the CM
        init_cm_pos = self.calc_center_of_mass(self.star_pos[0], self.planet_pos[0], self.sat_pos[0])

        self._initialize_velocities(init_cm_pos)
        self._transform_to_cm_ref_frame(init_cm_pos)

    def _allocate_arrays(self) -> None:
        self.star_pos = np.empty((self.num_steps + 1, 3), dtype=np.double)
        self.star_vel = np.empty_like(self.star_pos)
        self.planet_pos = np.empty_like(self.star_pos)
        self.planet_vel = np.empty_like(self.star_pos)
        self.sat_pos = np.empty_like(self.star_pos)
        self.sat_vel = np.empty_like(self.star_pos)

    def _initialize_positions(self) -> None:
        self.star_pos[0] = np.array((0, 0, 0))

        self.planet_pos[0] = np.array((self.planet_distance * AU, 0, 0))

        # Perturbation of satellite's position away from the lagrange point
        perturbation_size = self.perturbation_size * AU
        perturbation_angle = np.radians(self.actual_perturbation_angle)

        perturbation = perturbation_size * np.array((np.cos(perturbation_angle), np.sin(perturbation_angle), 0))

        self.sat_pos[0] = self.calc_lagrange_point() + perturbation

    # noinspection PyUnreachableCode
    def _initialize_velocities(self, init_cm_pos: Array1D) -> None:
        # orbits are counterclockwise so angular velocity is in the positive z direction
        angular_vel = np.array((0, 0, self.angular_speed), dtype=np.double)

        # for a circular orbit velocity = cross_product(angular velocity, position)
        # where vec(position) is the position relative to the point being orbited
        # in this case the Center of Mass
        self.star_vel[0] = np.cross(angular_vel, self.star_pos[0] - init_cm_pos)

        self.planet_vel[0] = np.cross(angular_vel, self.planet_pos[0] - init_cm_pos)

        speed = self.speed * norm(self.planet_vel[0])

        vel_angle = float(np.radians(self.actual_vel_angle))

        self.sat_vel[0] = speed * unit_vector(vel_angle)

    def _transform_to_cm_ref_frame(self, init_cm_pos: Array1D) -> None:
        self.star_pos[0] -= init_cm_pos
        self.planet_pos[0] -= init_cm_pos
        self.sat_pos[0] -= init_cm_pos

        self.lagrange_point_trans = self.calc_lagrange_point() - init_cm_pos

    def _integrate(self) -> None:
        nb_integrate(
            self.time_step_in_seconds,
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

    A = TypeVar("A", Array1D, Array2D)

    def calc_center_of_mass(
        self,
        star_pos_or_vel: A,
        planet_pos_or_vel: A,
        sat_pos_or_vel: A,
    ) -> A:
        """Can be used to calculate either the position or velocity of the center of mass.
        The input arrays can be either 1D or 2D. If 2D, the first dimension should be time
        """

        return (
            self.star_mass * star_pos_or_vel + self.planet_mass * planet_pos_or_vel + self.SAT_MASS * sat_pos_or_vel
        ) / (self.star_mass + self.planet_mass + self.SAT_MASS)

    def transform_to_corotating(self, pos_trans: Array2D) -> Array2D:
        angular_speed = self.angular_speed * np.sign(self.time_step_in_seconds)
        return nb_transform_to_corotating(pos_trans, self.time_points(), angular_speed)

    def calc_conserved_quantities(self) -> tuple[Array2D, Array2D, Array1D]:
        total_momentum = self.calc_total_linear_momentum()
        total_angular_momentum = self.calc_total_angular_momentum()
        total_energy = self.calc_total_energy()

        return total_momentum, total_angular_momentum, total_energy

    def calc_total_linear_momentum(self) -> Array2D:
        return self.star_mass * self.star_vel + self.planet_mass * self.planet_vel + self.SAT_MASS * self.sat_vel

    # noinspection PyUnreachableCode,PyUnusedLocal
    def calc_total_angular_momentum(self) -> Array2D:
        star_angular_momentum = np.cross(self.star_pos, self.star_mass * self.star_vel)

        planet_angular_momentum = np.cross(self.planet_pos, self.planet_mass * self.planet_vel)

        sat_angular_momentum = np.cross(self.sat_pos, self.SAT_MASS * self.sat_vel)

        return star_angular_momentum + planet_angular_momentum + sat_angular_momentum  # type: ignore[return-value]

    def calc_total_energy(self) -> Array1D:
        planet_to_star_distance = array_of_norms(self.star_pos - self.planet_pos)
        planet_to_sat_distance = array_of_norms(self.sat_pos - self.planet_pos)
        star_to_sat_distance = array_of_norms(self.sat_pos - self.star_pos)

        potential_energy = -G * (
            self.star_mass * self.planet_mass / planet_to_star_distance
            + self.SAT_MASS * self.planet_mass / planet_to_sat_distance
            + self.SAT_MASS * self.star_mass / star_to_sat_distance
        )

        star_vel_magnitude = array_of_norms(self.star_vel)
        planet_vel_magnitude = array_of_norms(self.planet_vel)
        sat_vel_magnitude = array_of_norms(self.sat_vel)

        kinetic_energy = 0.5 * (
            self.star_mass * star_vel_magnitude**2
            + self.planet_mass * planet_vel_magnitude**2
            + self.SAT_MASS * sat_vel_magnitude**2
        )

        return potential_energy + kinetic_energy
