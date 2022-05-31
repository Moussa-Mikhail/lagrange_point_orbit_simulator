# thesis_code

Python code used to investigate the stability of orbits near L4.

## Installation

Download the repository.
If you use Pip open your command line and enter "pip install -r requirements.txt". This will install all the packages these scripts depend on. If you use Poetry then a .lock file is provided.

If you are familiar with Cython then you can use the provided setup.py file to build the extensions for a speedup. This is optional.

## Usage

The simulation.py module is meant to be used by calling its main function.

```
main simulates a satellite's orbit corresponding to the following parameters.
It then plots the orbit in inertial and corotating frames.

All parameters have default values.

It takes the following parameters:

#### Simulation parameters
num_years: Number of years to simulate. The default is 100.0.
num_steps: Number of steps to simulate. Must be an integer. The default is 10**6.

It is recommended that the ratio of num_steps to num_years
remains close to the ratio of default values.

#### Satellite parameters
perturbation_size: Size of perturbation in AU. The default is 0.0.
perturbation_angle: Angle of perturbation relative to positive x axis in degrees.
The default is None.

If None, then perturbation_size has the effect of
moving the satellite away or towards the origin.

speed: Initial speed of satellite as a factor of the planet's speed.
i.e. speed = 1.0 -> satellite has the same speed as the planet.
the default is 1.0.

vel_angle: Angle of satellite's initial velocity relative to positive x axis in degrees.
The default is None.

If None, then vel_angle is perpendicular to the satellite's
default position relative to the center of mass.

lagrange_point: Non-perturbed position of satellite. String.
The default is 'L4' but the others can also be used.

#### System parameters
star_mass: Mass of the star in kilograms. The default is the mass of the Sun.

planet_mass: Mass of the planet in kilograms. The default is the mass of the Earth.

The constants sun_mass and earth_mass may be imported from the file constants.py.

planet_distance: Distance between the planet and the star in AU. The default is 1.0.

plot_conserved: If True, plots the conserved quantities:
energy, angular momentum, linear momentum.
The default is False.

This function will take ~0.42 seconds per 10**6 steps if
The time may vary depending on your hardware.
It will take longer than usual on the first call.
```

This is the docstring of simulation.main which can be seen at any time by using "help(simulation.main)" or "help(main)" in Python.

# collect_data

thesis/collect_data.py is used to collect data by simulating random orbits. The data is then saved to "data.csv".

## Usage

collect_data also has a main function.

```
main creates samples of random parameters, simulates the
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

This function will take 3 minutes when called with default arguments

The time taken is linear in both num_steps and num_samples.
```
