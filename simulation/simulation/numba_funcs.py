# pylint: disable=missing-docstring, not-an-iterable, invalid-name

import numpy as np

from numba import njit, prange  # type: ignore

from simulation.constants import G
from .typing import DoubleArray


@njit()
def norm(vector: DoubleArray) -> float:

    return np.sqrt(
        vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]
    )


@njit()
def calc_acceleration(
    star_mass: float,
    planet_mass: float,
    star_pos: DoubleArray,
    planet_pos: DoubleArray,
    sat_pos: DoubleArray,
    star_accel: DoubleArray,
    planet_accel: DoubleArray,
    sat_accel: DoubleArray,
    r_planet_to_star: DoubleArray,
    r_sat_to_star: DoubleArray,
    r_sat_to_planet: DoubleArray,
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
    star_pos: DoubleArray,
    star_vel: DoubleArray,
    planet_pos: DoubleArray,
    planet_vel: DoubleArray,
    sat_pos: DoubleArray,
    sat_vel: DoubleArray,
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
    times: DoubleArray, angular_speed: float, pos_trans: DoubleArray
):
    # it is necessary to transform our coordinate system to one which
    # rotates with the system
    # we can do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we multiply the position vectors by the matrix R(-w*t)

    # pos_trans is the position relative to the center of mass

    pos_rotated = np.empty_like(pos_trans)

    for i in prange(pos_trans.shape[0]):

        time: float = times[i]

        angle = -angular_speed * time

        c: float = np.cos(angle)

        s: float = np.sin(angle)

        pos_trans_x: float = pos_trans[i, 0]

        pos_trans_y: float = pos_trans[i, 1]

        pos_rotated[i, 0] = c * pos_trans_x - s * pos_trans_y

        pos_rotated[i, 1] = s * pos_trans_x + c * pos_trans_y

    pos_rotated[:, 2] = pos_trans[:, 2]

    return pos_rotated
