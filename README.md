# About

Python code used to simulate satellite orbits near Lagrange points. It is meant for the L4/L5 points but any of the 5 points can be used. The initial position and velocity of the satellite can be specified by the user. Additionally, the masses of the star, planet, and the distance between them can also be specified.

## Installation of source code

Download the repository.
If you use Pip open your command line in the repository directory and enter "pip install -r requirements.txt". This will install all the packages this code depends on. If you use Poetry then a .lock file is provided.

## Usage

```
This class holds parameters defining a satellites orbit and simulates it.
Once an instance of the class has been created it can be used by calling the simulate method.
The constructor takes the following parameters:

#### Simulation Parameters

num_years: positive float. Time to simulate in years. The default is 100.0.

time_step: float. Time inbetween simulation steps in hours. the default is 1.0.
A negative value will cause the simulation to run backwards in time.

#### Satellite Parameters

perturbation_size: float. Size of perturbation away from the Lagrange point in AU.
The default is 0.0.

perturbation_angle: float. Angle of perturbation relative to positive x axis in degrees.
The default is None.
If None, then perturbations are away or toward the origin.

speed: float. Initial speed of satellite as a factor of the planet's speed.
e.g. speed = 1.0 -> satellite has the same speed as the planet.
the default is 1.0.

vel_angle: float. Angle of satellite's initial velocity relative to positive x axis in degrees.
The default is None.
If None, then vel_angle is perpendicular to the satellite's
default position relative to the star.

lagrange_label: string. Non-perturbed position of satellite.
The default is 'L4' but 'L1', 'L2', 'L3', and 'L5' can also be used.

#### System Parameters

star_mass: positive float. Mass of the star in kilograms. The default is the mass of the Sun.

planet_mass: positive float. Mass of the planet in kilograms.
The default is the mass of the Earth.

The constants "SUN_MASS", "EARTH_MASS", and others maybe import from the constants module.

planet_distance: positive float.
Distance between the planet and the star in AU. The default is 1.0.

The time to simulate will take longer than usual on the first call to the simulate method.
 ```

This is the docstring of the Simulator class which can be seen at any time by using "help(Simulator)" in Python.
The attributes of an instance can be changed after creation.
