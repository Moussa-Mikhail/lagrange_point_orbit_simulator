# pylint: disable=missing-docstring

from numpy.linalg import norm

from thesis_code import G, planet_mass, star_mass


# pure python version of integrate function
def integrate(
    time_step, num_steps, star_pos, star_vel, planet_pos, planet_vel, sat_pos, sat_vel
):

    for k in range(1, num_steps + 1):

        # intermediate position calculation
        star_intermediate_pos = star_pos[k - 1] + 0.5 * star_vel[k - 1] * time_step

        planet_intermediate_pos = (
            planet_pos[k - 1] + 0.5 * planet_vel[k - 1] * time_step
        )

        sat_intermediate_pos = sat_pos[k - 1] + 0.5 * sat_vel[k - 1] * time_step

        # acceleration calculation
        star_accel, planet_accel, sat_accel = calc_acceleration(
            star_intermediate_pos, planet_intermediate_pos, sat_intermediate_pos
        )

        # velocity update
        star_vel[k] = star_vel[k - 1] + star_accel * time_step

        planet_vel[k] = planet_vel[k - 1] + planet_accel * time_step

        sat_vel[k] = sat_vel[k - 1] + sat_accel * time_step

        # position update
        star_pos[k] = star_intermediate_pos + 0.5 * star_vel[k] * time_step

        planet_pos[k] = planet_intermediate_pos + 0.5 * planet_vel[k] * time_step

        sat_pos[k] = sat_intermediate_pos + 0.5 * sat_vel[k] * time_step

    return star_pos, star_vel, planet_pos, planet_vel, sat_pos, sat_vel


def calc_acceleration(star_pos, planet_pos, sat_pos):

    # vector from planet to star
    r_planet_to_star = star_pos - planet_pos

    # distance between planet and star
    d_star_to_planet = norm(r_planet_to_star)

    # gravity of satellite can be ignored
    star_accel = -G * planet_mass * r_planet_to_star / d_star_to_planet**3

    # note the lack of negative sign in the following line
    planet_accel = G * star_mass * r_planet_to_star / d_star_to_planet**3

    r_star_to_sat = sat_pos - star_pos

    d_star_to_sat = norm(r_star_to_sat)

    r_planet_to_sat = sat_pos - planet_pos

    d_planet_to_sat = norm(r_planet_to_sat)

    sat_accel = (
        -G * star_mass * r_star_to_sat / d_star_to_sat**3
        + -G * planet_mass * r_planet_to_sat / d_planet_to_sat**3
    )

    return star_accel, planet_accel, sat_accel
