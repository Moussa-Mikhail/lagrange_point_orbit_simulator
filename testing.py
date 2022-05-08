# pylint: disable=invalid-name, missing-function-docstring
"""Generate random parameters and simulates them.
Data is collected from each simulation and then written to a file name "data.csv"
"""
import numpy as np
import pandas as pd  # type: ignore
from numpy.linalg import norm

from thesis_code import (
    AU,
    L4,
    G,
    calc_center_of_mass,
    calc_orbit,
    calc_period_from_semi_major_axis,
    initialization,
    orbital_period,
    sat_mass,
    star_mass,
    time_func,
    transform_to_corotating,
    years,
)

# in A.U.
perturbation_size_low = 0.02

perturbation_size_high = 0.05

# in degrees
perturbation_angle_low = 0

perturbation_angle_high = 360

# in factors of planet's speed
speed_avg = 1.0

speed_range = 0.05

speed_low = speed_avg - speed_range

speed_high = speed_avg + speed_range

# in degrees
vel_angle_avg = 150

vel_angle_range = 10

vel_angle_low = vel_angle_avg - vel_angle_range

vel_angle_high = vel_angle_avg + vel_angle_range


@time_func
def main(num_years=100.0, num_steps=10**6, num_samples=500):
    """main creates samples of random parameters, simulates the
    corresponding orbits, and collects data from them. This data is then saved to "data.csv".

    It has the following parameters:

    num_years: number of years to simulate. The default is 100.0.
    num_steps: number of steps to simulate. Must be an integer. The default is 10**6.

    num_samples: number of samples to generate. Must be an integer. The default is 500.

    Note that a large fraction of orbits are rejected because they get too close to the planet.

    This function will take 280 seconds when called with default arguments
    assuming the Cythonized functions are available.
    It is not recommended to call this function with default arguments if they are not.

    The time taken is linear in both num_steps and num_samples.
    """

    df = pd.DataFrame()

    # this line initializes the num_years column and sets the number of rows to num_samples
    df["num_years"] = [num_years] * num_samples

    # this line initializes the num_steps column
    df["num_steps"] = num_steps

    generate_inputs(df)

    collect_data(df)

    remove_invalid_data(df)

    df.to_csv("data.csv")


def generate_inputs(df):

    num_samples = len(df)

    df["perturbation_size"] = np.random.uniform(
        perturbation_size_low, perturbation_size_high, num_samples
    )

    df["perturbation_angle"] = np.random.uniform(
        perturbation_angle_low, perturbation_angle_high, num_samples
    )

    df["speed"] = np.random.uniform(speed_low, speed_high, num_samples)

    df["vel_angle"] = np.random.uniform(vel_angle_low, vel_angle_high, num_samples)


def collect_data(df):
    # sourcery skip: hoist-statement-from-loop, use-assigned-variable

    num_samples = len(df)

    num_steps = df["num_steps"][0]

    num_years = df["num_years"][0]

    # converting num_years to seconds
    time_stop = num_years * years

    # array of num_steps+1 time points evenly spaced between 0 and time_stop
    times = np.linspace(0, time_stop, num_steps + 1)

    df["predicted period"] = None

    df["actual period"] = None

    # absolute difference between actual period and 1 year (period of planet's orbit)
    df["absolute period difference"] = None

    df["inconsistency"] = None

    df["instability"] = None

    params = [
        "perturbation_size",
        "perturbation_angle",
        "speed",
        "vel_angle",
    ]

    for idx in range(num_samples):

        inputs = df.loc[idx, params]

        inputs = dict(inputs)

        star_pos, _, planet_pos, _, sat_pos, _ = calc_orbit(
            num_years, num_steps, **inputs
        )

        if not is_valid_orbit(planet_pos, sat_pos):

            continue

        df.loc[idx, "inconsistency"] = measure_inconsistency(sat_pos, num_years) / AU

        df.loc[idx, "predicted period"] = calc_period_from_parameters(**inputs) / years

        CM_pos = calc_center_of_mass(star_pos, planet_pos, sat_pos)

        df.loc[idx, "actual period"] = (
            calc_period_from_position_data(sat_pos, CM_pos) / years
        )

        df.loc[idx, "instability"] = measure_instability(times, sat_pos, CM_pos) / AU

    # absolute difference from orbital period
    df["absolute period difference"] = np.abs(
        df["actual period"] - orbital_period / years
    )


def is_valid_orbit(planet_pos, sat_pos):

    # this function checks if the orbit is valid
    # if the distance between the planet and the satellite
    # is ever <= than 1/ 50 AU, the orbit is invalid
    # and it returns false

    distances = norm(planet_pos - sat_pos, axis=1)

    return min(distances) > 1 / 50 * AU


def measure_inconsistency(sat_pos, num_years):

    # This is meant to measure distance between points
    # in the satellites orbit in the corotating frame
    # Since distance between points is invariant to rotation
    # we can measure it without transforming the orbit

    num_steps = sat_pos.shape[0] - 1

    steps_per_year = int(num_steps / num_years)

    sat_pos_init = sat_pos[0]

    sat_pos_1yr = sat_pos[steps_per_year]

    # distance between its position after a year and its position at the beginning
    return norm(sat_pos_init - sat_pos_1yr)


def calc_period_from_parameters(
    perturbation_size, perturbation_angle, speed, vel_angle, default_pos=L4
):

    init_sat_pos, init_sat_vel, init_star_pos, init_star_vel = get_initial_conditions(
        perturbation_size, perturbation_angle, speed, vel_angle, default_pos
    )

    semi_major_axis = calc_semi_major_axis_from_initial_conditions(
        init_sat_pos, init_sat_vel, init_star_pos, init_star_vel
    )

    print(f"{semi_major_axis/AU=}")

    return calc_period_from_semi_major_axis(semi_major_axis)


def get_initial_conditions(
    perturbation_size, perturbation_angle, speed, vel_angle, default_pos=L4
):

    star_pos, star_vel, _, _, sat_pos, sat_vel = initialization(
        0, perturbation_size, perturbation_angle, speed, vel_angle, default_pos
    )

    init_sat_pos, init_sat_vel = sat_pos[0], sat_vel[0]

    init_star_pos, init_star_vel = star_pos[0], star_vel[0]

    return init_sat_pos, init_sat_vel, init_star_pos, init_star_vel


def calc_semi_major_axis_from_initial_conditions(sat_pos, sat_vel, star_pos, star_vel):

    # Assuming the influence of planet on the satellite as negligible
    # Therefore we can apply the solution to the 2-body problem to the satellite

    diff_vel = sat_vel - star_vel

    reduced_mass = (star_mass * sat_mass) / (star_mass + sat_mass)

    kinetic_energy = 0.5 * reduced_mass * diff_vel.dot(diff_vel)

    gravitational_coefficient = G * star_mass * sat_mass

    distance = norm(sat_pos - star_pos)

    potential_energy = -gravitational_coefficient / distance

    total_energy = kinetic_energy + potential_energy

    return (
        -gravitational_coefficient
        / total_energy
        * star_mass
        / (star_mass + sat_mass)
        / 2  # This 2 leads to the right answer and I dont know why
    )


def calc_period_from_position_data(sat_pos, CM_pos):

    semi_major_axis = calc_semi_major_axis_from_position_data(sat_pos, CM_pos)

    return calc_period_from_semi_major_axis(semi_major_axis)


def calc_semi_major_axis_from_position_data(sat_pos, CM_pos):

    sat_pos = sat_pos - CM_pos

    distances = norm(sat_pos, axis=1)

    perihelion = np.amin(distances)

    aphelion = np.amax(distances)

    return (perihelion + aphelion) / 2


def measure_instability(times, sat_pos, CM_pos):

    sat_pos_trans = transform_to_corotating(times, sat_pos, CM_pos)

    distances_from_L4 = norm(sat_pos_trans - L4, axis=1)

    return max(distances_from_L4)


def remove_invalid_data(df):

    num_samples = len(df)

    for idx in range(num_samples):

        if df.loc[idx, "predicted period"] is None:

            df.drop(idx, inplace=True)
