# pylint: disable=missing-docstring

from math import sqrt

import numpy as np

from numba import njit  # type: ignore

from thesis_code import G, planet_mass, star_mass


@njit()
def norm(vector):

    return sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)


@njit()
def calc_acceleration(
    star_pos,
    planet_pos,
    sat_pos,
    star_accel,
    planet_accel,
    sat_accel,
    r_star_to_sat,
    r_star_to_planet,
    r_planet_to_sat,
):

    # vector from star to satellite

    for j in range(3):
        r_star_to_sat[j] = sat_pos[j] - star_pos[j]

        r_star_to_planet[j] = planet_pos[j] - star_pos[j]

        r_planet_to_sat[j] = sat_pos[j] - planet_pos[j]

    # distance between star to planet
    d_star_to_planet = norm(r_star_to_planet)

    d_star_to_sat = norm(r_star_to_sat)

    d_planet_to_sat = norm(r_planet_to_sat)

    for j in range(3):
        # gravity of satellite can be ignored
        # note the lack of negative sign in the following line
        star_accel[j] = G * planet_mass * r_star_to_planet[j] / d_star_to_planet**3

        planet_accel[j] = -G * star_mass * r_star_to_planet[j] / d_star_to_planet**3

        sat_accel[j] = (
            -G * star_mass * r_star_to_sat[j] / d_star_to_sat**3
            + -G * planet_mass * r_planet_to_sat[j] / d_planet_to_sat**3
        )


@njit()
def integrate(
    time_step, num_steps, star_pos, star_vel, planet_pos, planet_vel, sat_pos, sat_vel
):

    star_accel = np.empty(3, dtype=np.double)

    planet_accel = np.empty_like(star_accel)

    sat_accel = np.empty_like(star_accel)

    star_intermediate_pos = np.empty_like(star_accel)

    planet_intermediate_pos = np.empty_like(star_accel)

    sat_intermediate_pos = np.empty_like(star_accel)

    r_star_to_sat = np.empty_like(star_accel)

    r_star_to_planet = np.empty_like(star_accel)

    r_planet_to_sat = np.empty_like(star_accel)

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
            star_intermediate_pos,
            planet_intermediate_pos,
            sat_intermediate_pos,
            star_accel,
            planet_accel,
            sat_accel,
            r_star_to_sat,
            r_star_to_planet,
            r_planet_to_sat,
        )

        # velocity update
        star_vel[k] = star_vel[k - 1] + star_accel * time_step

        planet_vel[k] = planet_vel[k - 1] + planet_accel * time_step

        sat_vel[k] = sat_vel[k - 1] + sat_accel * time_step

        # position update
        star_pos[k] = star_intermediate_pos + 0.5 * star_vel[k] * time_step

        planet_pos[k] = planet_intermediate_pos + 0.5 * planet_vel[k] * time_step

        sat_pos[k] = sat_intermediate_pos + 0.5 * sat_vel[k] * time_step
