# pylint: disable=invalid-name, missing-docstring
import numpy as np
import pandas as pd  # type: ignore
from numpy.linalg import norm

from thesis_code import (
    AU,
    L4,
    calc_center_of_mass,
    calc_orbit,
    calc_period_from_initial_conditions,
    calc_period_from_position_data,
    time_func,
    transform_to_corotating,
    years,
)


# in A.U.
perturbation_size_low = 0

perturbation_size_high = 0.05

# in degrees
perturbation_angle_low = 0

perturbation_angle_high = 360

# in factors of Earth's speed
speed_avg = 1.0

speed_range = 0.05

speed_low = speed_avg - speed_range

speed_high = speed_avg + speed_range

# in degrees
vel_angle_avg = 150

vel_angle_range = 20

vel_angle_low = vel_angle_avg - vel_angle_range

vel_angle_high = vel_angle_avg + vel_angle_range


@time_func
def main(num_years=100, num_steps=10**6, num_samples=100):

    # this function will take 80 seconds when called with default arguments
    # the time taken is linear in both num_steps and num_samples

    df = pd.DataFrame()

    # this line initializes the num_years column and sets the number of rows to num_samples
    df["num_years"] = [num_years] * num_samples

    # this line initializes the num_steps column
    df["num_steps"] = num_steps

    generate_inputs(df)

    collect_data(df)

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

    num_samples = len(df)

    num_steps = df["num_steps"][0]

    num_years = df["num_years"][0]

    # converting num_years to seconds
    time_stop = num_years * years

    # array of num_steps+1 time points evenly spaced between 0 and time_stop
    times = np.linspace(0, time_stop, num_steps + 1)

    df["predicted_period"] = None

    df["actual_period"] = None

    df["inconsistency"] = None

    df["instability"] = None

    params = [
        "perturbation_size",
        "perturbation_angle",
        "speed",
        "vel_angle",
    ]

    for i in range(num_samples):

        inputs = df.loc[i, params]

        inputs = dict(inputs)

        sun_pos, _, earth_pos, _, sat_pos, _ = calc_orbit(
            num_years, num_steps, **inputs
        )

        df.loc[i, "inconsistency"] = measure_inconsistency(sat_pos, num_years) / AU

        df.loc[i, "predicted_period"] = (
            calc_period_from_initial_conditions(**inputs) / years
        )

        CM_pos = calc_center_of_mass(sun_pos, earth_pos, sat_pos)

        df.loc[i, "actual_period"] = (
            calc_period_from_position_data(sat_pos, CM_pos) / years
        )

        df.loc[i, "instability"] = measure_instability(times, sat_pos, CM_pos)

    # absolute difference from 1 year
    df["period_diff"] = np.abs(df["actual_period"] - 1)


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


def measure_instability(times, sat_pos, CM_pos):

    sat_pos_trans = transform_to_corotating(times, sat_pos, CM_pos)

    distances_from_L4 = norm(sat_pos_trans - L4, axis=1)

    max_distance = max(distances_from_L4)

    min_distance = min(distances_from_L4)

    init_distance = distances_from_L4[0]

    return (max_distance - min_distance) / init_distance
