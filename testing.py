# pylint: disable=invalid-name
import numpy as np
import pandas as pd  # type: ignore
from numpy.linalg import norm

from thesis_code import (
    AU,
    calc_orbit,
    calc_period,
    time_func,
    years,
)


# in A.U.
perturbation_size_low = 0

perturbation_size_high = 0.01

# in degrees
perturbation_angle_low = 0

perturbation_angle_high = 360

# in factors of Earth's speed
speed_avg = 1.0

speed_range = 0.01

speed_low = speed_avg - speed_range

speed_high = speed_avg + speed_range

# in degrees
vel_angle_avg = 150

vel_angle_range = 20

vel_angle_low = vel_angle_avg - vel_angle_range

vel_angle_high = vel_angle_avg + vel_angle_range


@time_func
def main(num_years=100, num_steps=10**6, num_samples=100):

    # this function will take 26 seconds when called with default arguments
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

    num_years = df["num_years"][0]

    df["period"] = None

    df["period_diff"] = None

    df["variation"] = None

    orbit_params = [
        "num_years",
        "num_steps",
        "perturbation_size",
        "perturbation_angle",
        "speed",
        "vel_angle",
    ]

    period_params = ["perturbation_size", "perturbation_angle", "speed", "vel_angle"]

    for i in range(num_samples):

        inputs = df.loc[i, orbit_params]

        inputs = dict(inputs)

        # before this line this value was a float, now it's an int
        inputs["num_steps"] = int(inputs["num_steps"])

        *_, sat_pos, _ = calc_orbit(**inputs)

        df.loc[i, "variation"] = measure_variation(sat_pos, num_years) / AU

        period_inputs = df.loc[i, period_params]

        period_inputs = dict(period_inputs)

        df.loc[i, "period"] = calc_period(**period_inputs) / years

    # absolute difference from 1 year
    df["period_diff"] = np.abs(df["period"] - 1)


def measure_variation(sat_pos, num_years):

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
