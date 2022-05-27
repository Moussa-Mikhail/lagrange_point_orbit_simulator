# pylint: disable=invalid-name, missing-function-docstring
"""Generate random parameters and simulates them.
Data is collected from each simulation and then written to a file name "data.csv"
"""
import numpy as np
import pandas as pd  # type: ignore
from numpy.linalg import norm

from thesis_code import (
    AU,
    G,
    Simulation,
    calc_period_from_semi_major_axis,
    sun_mass,
    earth_mass,
    sat_mass,
    time_func,
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
def main(
    num_samples=500,
    num_years=100.0,
    num_steps=10**6,
    star_mass=sun_mass,
    planet_mass=earth_mass,
    planet_distance=1.0,
    filename="data.csv",
):
    """main creates samples of random parameters, simulates the
    corresponding orbits, and collects data from them. This data is then saved to "data.csv".

    It has the following parameters:

    num_samples: number of samples to generate. Must be an integer. The default is 500.

    #### Simulation parameters
    num_years: number of years to simulate. The default is 100.0.
    num_steps: number of steps to simulate. Must be an integer. The default is 10**6.

    It is recommended that the ratio of num_steps to num_years
    remains close to the ratio of default values.

    #### System parameters
    star_mass: mass of the star in kg. The default is the mass of the Sun.

    planet_mass: mass of the planet in kg. The default is the mass of the Earth.

    The constants sun_mass and earth_mass may be imported from the file constants.py.

    planet_distance: distance from the star to the planet in AU. The default is 1.0.


    filename: name of the file to save the data to. The default is "data.csv".

    Note that a large fraction of orbits are rejected because they get too close to the planet.
    This means that the number of samples recorded will be less than num_samples.

    This function will take 4 minutes when called with default arguments
    assuming the pyd functions are available.
    10 minutes if they aren't.

    The time taken is linear in both num_steps and num_samples.
    """

    data_collection = DataCollection(
        num_years,
        num_steps,
        num_samples,
        star_mass,
        planet_mass,
        planet_distance,
        filename,
    )

    data_collection.main()


class DataCollection:
    def __init__(
        self,
        num_years=100.0,
        num_steps=10**6,
        num_samples=500,
        star_mass=sun_mass,
        planet_mass=earth_mass,
        planet_distance=1.0,
        filename="data.csv",
    ):

        self.num_years = num_years

        self.num_steps = num_steps

        self.num_samples = num_samples

        self.star_mass = star_mass

        self.planet_mass = planet_mass

        self.planet_distance = planet_distance

        self.sim = Simulation(
            num_years,
            num_steps,
            star_mass=star_mass,
            planet_mass=planet_mass,
            planet_distance=planet_distance,
        )

        self.filename = filename

        self.df = pd.DataFrame()

        # this line initializes the num_years column and sets the number of rows to num_samples
        self.df["num_years"] = [num_years] * num_samples

        # this line initializes the num_steps column
        self.df["num_steps"] = num_steps

    def main(self):

        self.generate_inputs()

        self.collect_data()

        self.remove_empty_rows()

        self.df.to_csv("data.csv")

    def generate_inputs(self):

        self.df["perturbation_size"] = np.random.uniform(
            perturbation_size_low, perturbation_size_high, self.num_samples
        )

        self.df["perturbation_angle"] = np.random.uniform(
            perturbation_angle_low, perturbation_angle_high, self.num_samples
        )

        self.df["speed"] = np.random.uniform(speed_low, speed_high, self.num_samples)

        self.df["vel_angle"] = np.random.uniform(
            vel_angle_low, vel_angle_high, self.num_samples
        )

    def collect_data(self):
        # sourcery skip: hoist-statement-from-loop, use-assigned-variable

        self.df["predicted period"] = None

        self.df["actual period"] = None

        # absolute difference between actual period and 1 year (period of planet's orbit)
        self.df["absolute period difference"] = None

        self.df["inconsistency"] = None

        self.df["instability"] = None

        params = [
            "perturbation_size",
            "perturbation_angle",
            "speed",
            "vel_angle",
        ]

        for idx in range(self.num_samples):

            inputs = self.df.loc[idx, params]

            inputs = dict(inputs)

            for k, v in inputs.items():
                setattr(self.sim, k, v)

            star_pos, _, planet_pos, _, sat_pos, _ = self.sim.calc_orbit()

            if not self.is_valid_orbit(planet_pos, sat_pos):
                # this results in empty rows

                continue

            self.df.loc[idx, "inconsistency"] = (
                measure_inconsistency(sat_pos, self.num_years) / AU
            )

            self.df.loc[idx, "predicted period"] = (
                self.calc_period_from_parameters() / years
            )

            CM_pos = self.sim.calc_center_of_mass(star_pos, planet_pos, sat_pos)

            sat_pos_trans = sat_pos - CM_pos

            self.df.loc[idx, "actual period"] = (
                self.calc_period_from_position_data(sat_pos_trans) / years
            )

            self.df.loc[idx, "instability"] = (
                self.measure_instability(sat_pos_trans) / AU
            )

        # absolute difference from orbital period
        self.df["absolute period difference"] = np.abs(
            self.df["actual period"] - self.sim.orbital_period / years
        )

    def is_valid_orbit(self, planet_pos, sat_pos):

        # this function checks if the orbit is valid
        # if the satellite ever enters the planets Hill Sphere, the orbit is invalid

        distances = norm(planet_pos - sat_pos, axis=1)

        hill_radius = (
            self.planet_distance
            * AU
            * (self.planet_mass / (3 * self.star_mass)) ** (1 / 3)
        )

        return min(distances) > hill_radius

    def remove_empty_rows(self):

        for idx in range(self.num_samples):

            if self.df.loc[idx, "predicted period"] is None:

                self.df.drop(idx, inplace=True)

        self.df.reset_index(drop=True, inplace=True)

    def calc_period_from_parameters(self):

        (
            init_sat_pos,
            init_sat_vel,
            init_star_pos,
            init_star_vel,
        ) = self.get_initial_conditions()

        semi_major_axis = self.calc_semi_major_axis_from_initial_conditions(
            init_sat_pos, init_sat_vel, init_star_pos, init_star_vel
        )

        return calc_period_from_semi_major_axis(
            semi_major_axis, self.star_mass, self.planet_mass
        )

    def get_initial_conditions(self):

        self.sim.num_steps = 0

        star_pos, star_vel, _, _, sat_pos, sat_vel = self.sim.initialization()

        self.sim.num_steps = self.num_steps

        init_sat_pos, init_sat_vel = sat_pos[0], sat_vel[0]

        init_star_pos, init_star_vel = star_pos[0], star_vel[0]

        return init_sat_pos, init_sat_vel, init_star_pos, init_star_vel

    def calc_semi_major_axis_from_initial_conditions(
        self, sat_pos, sat_vel, star_pos, star_vel
    ):

        # Assuming the influence of planet on the satellite as negligible
        # we can apply the solution to the 2-body problem to the satellite

        diff_vel = sat_vel - star_vel

        reduced_mass = (self.star_mass * sat_mass) / (self.star_mass + sat_mass)

        kinetic_energy = 0.5 * reduced_mass * diff_vel.dot(diff_vel)

        gravitational_coefficient = G * self.star_mass * sat_mass

        distance = norm(sat_pos - star_pos)

        potential_energy = -gravitational_coefficient / distance

        total_energy = kinetic_energy + potential_energy

        return (
            -gravitational_coefficient
            / total_energy
            * self.star_mass
            / (self.star_mass + sat_mass)
            / 2  # This 2 leads to the right results and I dont know why
        )

    def calc_period_from_position_data(self, sat_pos_trans):

        semi_major_axis = calc_semi_major_axis_from_position_data(sat_pos_trans)

        return calc_period_from_semi_major_axis(
            semi_major_axis, self.star_mass, self.planet_mass
        )

    def measure_instability(self, sat_pos_trans):

        sat_pos_rotated = self.sim.transform_to_corotating(sat_pos_trans)

        distances_from_L4 = norm(sat_pos_rotated - self.sim.lagrange_point, axis=1)

        return np.amax(distances_from_L4)


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


def calc_semi_major_axis_from_position_data(sat_pos_trans):

    distances = norm(sat_pos_trans, axis=1)

    perihelion = np.amin(distances)

    aphelion = np.amax(distances)

    return (perihelion + aphelion) / 2
