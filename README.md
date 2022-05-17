# thesis_code

Module which simulates orbits near Lagrange Points and plots the results.

## Installation

Download the repository.
If you use Pip open your command line and enter "pip install -r requirements.txt". This will install all the packages these scripts depend on. If you use Poetry then a .lock file is provided.

If you are familiar with Cython then you can use the provided setup.py file to build the extensions for a speedup. This is optional.

## Usage

The thesis_code module is meant to be used by calling its main function.

```
thesis_code.main simulates a satellite's orbit corresponding to the following parameters.
It then plots the orbit in inertial and corotating frames.

All parameters have default values.

It takes the following parameters:

num_years: Number of years to simulate. The default is 100.0.
num_steps: Number of steps to simulate. Must be an integer. The default is 10**6.

perturbation_size: Size of perturbation in AU. The default is 0.
perturbation_angle: Angle of perturbation relative to positive x axis in degrees.
The default is None.
If None, then perturbation_size has the effect of
moving the satellite away or towards the origin.

speed: Initial speed of satellite as a factor of the planet's speed.
i.e. speed = 1 -> satellite has the same speed as the planet.
the default is 1.

vel_angle: Angle of satellite's initial velocity relative to positive x axis in degrees.
The default is None.
If None, then vel_angle is perpendicular to the satellite's default position.

default_pos: Non-perturbed position of satellite.
The default is L4 but L1, L2, L3, L5 can be used if imported from thesis_code.

plot_conserved: If True, plots the conserved quantities:
energy, angular momentum, linear momentum.
The default is False.

thesis_code.main will take ~0.46 seconds per 10**6 steps if
the Cythonized extensions are available.
1.4 seconds if not.
The time may vary depending on your hardware.
It will take longer than usual on the first call.
```

This is the docstring of thesis_code.main which can be seen at any time by using "help(thesis_code.main)" in Python.

# testing

testing is used to collect data by simulating random orbits. The data is then saved to "data.csv".

## Usage

testing also has a main function.

```
testing.main creates samples of random parameters, simulates the
corresponding orbits, and collects data from them. This data is then saved to "data.csv".

It has the following parameters:

num_years: number of years to simulate. The default is 100.0.
num_steps: number of steps to simulate. Must be an integer. The default is 10**6.

num_samples: number of samples to generate. Must be an integer. The default is 500.

Note that a large fraction of orbits are rejected because they get too close to the planet.

testing.main will take 280 (4 min 20 sec) seconds when called with default arguments
assuming the Cythonized functions are available and 680 (11 min 20 sec) seconds if not.

The time taken is linear in both num_steps and num_samples.
```
