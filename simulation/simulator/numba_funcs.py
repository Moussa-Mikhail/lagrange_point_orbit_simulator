# pylint: disable=missing-docstring, not-an-iterable, invalid-name

from math import sqrt

import numpy as np
from numba import njit, prange  # type: ignore

from .constants import G
from .sim_types import Array1D, Array2D


@njit()
def norm(vector: Array1D) -> float:

    return sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])


@njit()
def calc_acceleration(
    star_mass: float,
    planet_mass: float,
    star_pos: Array1D,
    planet_pos: Array1D,
    sat_pos: Array1D,
    star_accel: Array1D,
    planet_accel: Array1D,
    sat_accel: Array1D,
    r_planet_to_star: Array1D,
    r_sat_to_star: Array1D,
    r_sat_to_planet: Array1D,
):

    for j in range(3):

        # vector from planet to star
        r_planet_to_star[j] = star_pos[j] - planet_pos[j]

        r_sat_to_star[j] = star_pos[j] - sat_pos[j]

        r_sat_to_planet[j] = planet_pos[j] - sat_pos[j]

    # distance between star to planet
    d_planet_to_star = norm(r_planet_to_star)

    d_sat_to_star = norm(r_sat_to_star)

    d_sat_to_planet = norm(r_sat_to_planet)

    for j in range(3):

        star_accel[j] = -G * planet_mass * r_planet_to_star[j] / d_planet_to_star**3

        # note the lack of negative sign in the following lines
        planet_accel[j] = G * star_mass * r_planet_to_star[j] / d_planet_to_star**3

        sat_accel[j] = (
            G * star_mass * r_sat_to_star[j] / d_sat_to_star**3
            + G * planet_mass * r_sat_to_planet[j] / d_sat_to_planet**3
        )


@njit()
def integrate(
    time_step: float,
    num_steps: int,
    star_mass: float,
    planet_mass: float,
    star_pos: Array2D,
    star_vel: Array2D,
    planet_pos: Array2D,
    planet_vel: Array2D,
    sat_pos: Array2D,
    sat_vel: Array2D,
):

    star_accel = np.empty(3, dtype=np.double)

    planet_accel = np.empty_like(star_accel)

    sat_accel = np.empty_like(star_accel)

    star_intermediate_pos = np.empty_like(star_accel)

    planet_intermediate_pos = np.empty_like(star_accel)

    sat_intermediate_pos = np.empty_like(star_accel)

    r_planet_to_star = np.empty_like(star_accel)

    r_sat_to_star = np.empty_like(star_accel)

    r_sat_to_planet = np.empty_like(star_accel)

    for k in range(1, num_steps + 1):

        for j in range(3):

            # intermediate position calculation
            star_intermediate_pos[j] = (
                star_pos[k - 1, j] + 0.5 * star_vel[k - 1, j] * time_step
            )

            planet_intermediate_pos[j] = (
                planet_pos[k - 1, j] + 0.5 * planet_vel[k - 1, j] * time_step
            )

            sat_intermediate_pos[j] = (
                sat_pos[k - 1, j] + 0.5 * sat_vel[k - 1, j] * time_step
            )

        # acceleration calculation
        calc_acceleration(
            star_mass,
            planet_mass,
            star_intermediate_pos,
            planet_intermediate_pos,
            sat_intermediate_pos,
            star_accel,
            planet_accel,
            sat_accel,
            r_planet_to_star,
            r_sat_to_star,
            r_sat_to_planet,
        )

        for j in range(3):

            # velocity update
            star_vel[k, j] = star_vel[k - 1, j] + star_accel[j] * time_step

            planet_vel[k, j] = planet_vel[k - 1, j] + planet_accel[j] * time_step

            sat_vel[k, j] = sat_vel[k - 1, j] + sat_accel[j] * time_step

            # position update
            star_pos[k, j] = star_intermediate_pos[j] + 0.5 * star_vel[k, j] * time_step

            planet_pos[k, j] = (
                planet_intermediate_pos[j] + 0.5 * planet_vel[k, j] * time_step
            )

            sat_pos[k, j] = sat_intermediate_pos[j] + 0.5 * sat_vel[k, j] * time_step


@njit(parallel=True)
def transform_to_corotating(
    pos_trans: Array2D, times: Array1D, angular_speed: float
) -> Array2D:
    """Transforms pos_trans to a frame of reference that rotates at a rate of angular_speed.
    pos_trans is an array of positions measured relative to the center of rotation.
    """

    # we do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we apply the matrix R(-w*t) to the position vector

    pos_corotating = np.empty_like(pos_trans)

    for i in prange(pos_trans.shape[0]):

        time: float = times[i]

        angle = -angular_speed * time

        c: float = np.cos(angle)

        s: float = np.sin(angle)

        pos_trans_x: float = pos_trans[i, 0]

        pos_trans_y: float = pos_trans[i, 1]

        pos_corotating[i, 0] = c * pos_trans_x - s * pos_trans_y

        pos_corotating[i, 1] = s * pos_trans_x + c * pos_trans_y

    pos_corotating[:, 2] = pos_trans[:, 2]

    return pos_corotating
