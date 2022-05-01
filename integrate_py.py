# pylint: disable=missing-docstring
from thesis_code import G, sun_mass, earth_mass, norm


# pure python version of integrate function
def integrate(
    time_step, num_steps, sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel
):

    for k in range(1, num_steps + 1):

        # intermediate position calculation
        sun_intermediate_pos = sun_pos[k - 1] + 0.5 * sun_vel[k - 1] * time_step

        earth_intermediate_pos = earth_pos[k - 1] + 0.5 * earth_vel[k - 1] * time_step

        sat_intermediate_pos = sat_pos[k - 1] + 0.5 * sat_vel[k - 1] * time_step

        # acceleration calculation
        sun_accel, earth_accel, sat_accel = calc_acceleration(
            sun_intermediate_pos, earth_intermediate_pos, sat_intermediate_pos
        )

        # velocity update
        sun_vel[k] = sun_vel[k - 1] + sun_accel * time_step

        earth_vel[k] = earth_vel[k - 1] + earth_accel * time_step

        sat_vel[k] = sat_vel[k - 1] + sat_accel * time_step

        # position update
        sun_pos[k] = sun_intermediate_pos + 0.5 * sun_vel[k] * time_step

        earth_pos[k] = earth_intermediate_pos + 0.5 * earth_vel[k] * time_step

        sat_pos[k] = sat_intermediate_pos + 0.5 * sat_vel[k] * time_step

    return sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel


def calc_acceleration(sun_pos, earth_pos, sat_pos):

    # vector from earth to sun
    r_earth_to_sun = sun_pos - earth_pos

    # distance between earth and sun
    d_sun_to_earth = norm(r_earth_to_sun)

    # gravity of satellite can be ignored
    sun_accel = -G * earth_mass * r_earth_to_sun / d_sun_to_earth**3

    # note the lack of negative sign in the following line
    earth_accel = G * sun_mass * r_earth_to_sun / d_sun_to_earth**3

    r_sun_to_sat = sat_pos - sun_pos

    d_sun_to_sat = norm(r_sun_to_sat)

    r_earth_to_sat = sat_pos - earth_pos

    d_earth_to_sat = norm(r_earth_to_sat)

    sat_accel = (
        -G * sun_mass * r_sun_to_sat / d_sun_to_sat**3
        + -G * earth_mass * r_earth_to_sat / d_earth_to_sat**3
    )

    return sun_accel, earth_accel, sat_accel
