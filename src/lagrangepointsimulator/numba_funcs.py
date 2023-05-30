# pylint: disable=missing-docstring, not-an-iterable, invalid-name

from math import sqrt

import numpy as np
from numba import njit, prange  # type: ignore

from .constants import G
from .sim_types import Array1D, Array2D


@njit(cache=True)
def inverse_norm_cubed(vector: Array1D) -> float:
    return sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]) ** -3


# pylint: disable=too-many-arguments, too-many-locals
@njit(cache=True)
def calc_acceleration(
    G_star: float,
    G_planet: float,
    star_pos: Array1D,
    planet_pos: Array1D,
    sat_pos: Array1D,
    star_accel: Array1D,
    planet_accel: Array1D,
    sat_accel: Array1D,
    planet_to_star: Array1D,
    sat_to_star: Array1D,
    sat_to_planet: Array1D,
) -> None:
    for j in range(3):
        planet_to_star[j] = star_pos[j] - planet_pos[j]
        sat_to_star[j] = star_pos[j] - sat_pos[j]
        sat_to_planet[j] = planet_pos[j] - sat_pos[j]

    d_planet_to_star_inverse_cubed = inverse_norm_cubed(planet_to_star)
    d_sat_to_star_inverse_cubed = inverse_norm_cubed(sat_to_star)
    d_sat_to_planet_inverse_cubed = inverse_norm_cubed(sat_to_planet)

    star_planet_coeff = G_planet * d_planet_to_star_inverse_cubed
    planet_star_coeff = G_star * d_planet_to_star_inverse_cubed
    sat_star_coeff = G_star * d_sat_to_star_inverse_cubed
    sat_planet_coeff = G_planet * d_sat_to_planet_inverse_cubed

    for j in range(3):
        star_accel[j] = -star_planet_coeff * planet_to_star[j]

        # note the lack of negative signs in the following lines
        planet_accel[j] = planet_star_coeff * planet_to_star[j]

        sat_accel[j] = sat_star_coeff * sat_to_star[j] + sat_planet_coeff * sat_to_planet[j]


# pylint: disable=too-many-arguments, too-many-locals
@njit(cache=True)
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
) -> None:
    star_accel = np.empty(3, dtype=np.double)
    planet_accel = np.empty_like(star_accel)
    sat_accel = np.empty_like(star_accel)

    star_intermediate_pos = np.empty_like(star_accel)
    planet_intermediate_pos = np.empty_like(star_accel)
    sat_intermediate_pos = np.empty_like(star_accel)

    planet_to_star = np.empty_like(star_accel)
    sat_to_star = np.empty_like(star_accel)
    sat_to_planet = np.empty_like(star_accel)

    half_time_step = 0.5 * time_step

    G_star = G * star_mass
    G_planet = G * planet_mass

    for k in range(1, num_steps + 1):
        for j in range(3):
            star_intermediate_pos[j] = star_pos[k - 1, j] + star_vel[k - 1, j] * half_time_step

            planet_intermediate_pos[j] = planet_pos[k - 1, j] + planet_vel[k - 1, j] * half_time_step

            sat_intermediate_pos[j] = sat_pos[k - 1, j] + sat_vel[k - 1, j] * half_time_step

        calc_acceleration(
            G_star,
            G_planet,
            star_intermediate_pos,
            planet_intermediate_pos,
            sat_intermediate_pos,
            star_accel,
            planet_accel,
            sat_accel,
            planet_to_star,
            sat_to_star,
            sat_to_planet,
        )

        for j in range(3):
            star_vel[k, j] = star_vel[k - 1, j] + star_accel[j] * time_step

            planet_vel[k, j] = planet_vel[k - 1, j] + planet_accel[j] * time_step

            sat_vel[k, j] = sat_vel[k - 1, j] + sat_accel[j] * time_step

            star_pos[k, j] = star_intermediate_pos[j] + star_vel[k, j] * half_time_step

            planet_pos[k, j] = planet_intermediate_pos[j] + planet_vel[k, j] * half_time_step

            sat_pos[k, j] = sat_intermediate_pos[j] + sat_vel[k, j] * half_time_step


@njit(parallel=True, cache=True)
def transform_to_corotating(pos_trans: Array2D, times: Array1D, angular_speed: float) -> Array2D:
    """Transforms pos_trans to a frame of reference that rotates at a rate of angular_speed counter-clockwise.
    pos_trans is an array of positions measured relative to the center of rotation.
    """

    # we do this by linearly transforming each position vector by
    # the inverse of the basis transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we apply the matrix R(-w*t) to the position vector

    num_steps = pos_trans.shape[0]

    pos_corotating = np.empty(dtype=pos_trans.dtype, shape=(num_steps, 2))

    for i in prange(pos_trans.shape[0]):
        time: float = times[i]

        angle = -angular_speed * time

        cos: float = np.cos(angle)
        sin: float = np.sin(angle)

        x, y = pos_trans[i, :2]

        pos_corotating[i, 0] = cos * x - sin * y

        pos_corotating[i, 1] = sin * x + cos * y

    return pos_corotating
