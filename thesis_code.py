# pylint: disable=invalid-name
"""Investigating L4 Lagrange Point
using the position Verlet algorithm"""

# to measure time taken in computing. for testing purposes only.
from functools import wraps
from time import perf_counter

# numpy allows us to compute common math functions and work with arrays.
import numpy as np

# plotting module.
import pyqtgraph as pg  # type: ignore
from numpy.linalg import norm
from pyqtgraph.Qt.QtCore import QTimer  # type: ignore

# cythonized version of integrate_py
# roughly 270x times faster
from cy_code import integrate_cy  # pylint: disable=no-name-in-module

pi = np.pi

# mass of sun in kilograms
sun_mass = 1.98847 * 10**30

# mass of earth in kilograms
earth_mass = 5.9722 * 10**24

# mass of satellite near in kilograms
# negligible compared to other masses
sat_mass = 1.0

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10 ** (-11)

# 1 Julian year in seconds
# serves as a conversion factor from years to seconds
years = 365.25 * 24 * 60 * 60

orbital_period = 1 * years

angular_speed = 2 * pi / orbital_period

# 1 AU in meters
# serves as a conversion factor from AUs to meters
AU = 1.495978707 * 10**11

hill_radius = 1 * AU * (earth_mass / (3 * sun_mass)) ** (1 / 3)

# Position of L1
L1 = 1 * AU * np.array((1, 0, 0)) - np.array((hill_radius, 0, 0))

# Position of L2
L2 = 1 * AU * np.array((1, 0, 0)) + np.array((hill_radius, 0, 0))

L3_dist = 1 * AU * 7 / 12 * earth_mass / sun_mass

# Position of L3
L3 = -1 * AU * np.array((1, 0, 0)) - np.array((L3_dist, 0, 0))

# Position of L4 Lagrange point.
# It is 1 AU from both Sun and Earth.
# It forms a 60 degree=pi/3 radians angle with the positive x-axis.
L4 = 1 * AU * np.array((np.cos(pi / 3), np.sin(pi / 3), 0))

# Position of L4 Lagrange point.
# It is 1 AU from both Sun and Earth.
# It forms a 60 degree=pi/3 radians angle with the positive x-axis.
L5 = 1 * AU * np.array((np.cos(pi / 3), -np.sin(pi / 3), 0))


def time_func(func):
    """Measures the time taken by a function"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        print(f"{func.__name__} took {end - start} seconds")
        return result

    return wrapper


@time_func
def main(
    num_years=10.0,
    num_steps=1 * 10**5,
    perturbation_size=0,
    perturbation_angle=None,
    speed=1,
    vel_angle=None,
    default_pos=L4,
    plot_conserved=False,
    integrate=integrate_cy,
):

    # this function will take ~3.5 seconds per 10**5 steps
    # the time may vary depending on your hardware

    default_pertubation_angle = np.arctan2(default_pos[1], default_pos[0])

    default_pertubation_angle = np.degrees(default_pertubation_angle)

    if perturbation_angle is None:

        perturbation_angle = default_pertubation_angle

    if vel_angle is None:

        vel_angle = default_pertubation_angle + 90

    sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel = calc_orbit(
        num_years,
        num_steps,
        perturbation_size,
        perturbation_angle,
        speed,
        vel_angle,
        default_pos,
        integrate,
    )

    # position of Center of Mass at each timestep
    CM_pos = calc_center_of_mass(sun_pos, earth_pos, sat_pos)

    plot_orbit(sun_pos, earth_pos, sat_pos)

    # converting num_years to seconds
    time_stop = num_years * years

    # array of num_steps+1 time points evenly spaced between 0 and time_stop
    times = np.linspace(0, time_stop, num_steps + 1)

    sun_pos_trans = transform_to_corotating(times, sun_pos, CM_pos)

    earth_pos_trans = transform_to_corotating(times, earth_pos, CM_pos)

    sat_pos_trans = transform_to_corotating(times, sat_pos, CM_pos)

    plot_corotating_orbit(default_pos, sun_pos_trans, earth_pos_trans, sat_pos_trans)

    if plot_conserved:
        (
            total_momentum,
            total_angular_momentum,
            total_energy,
        ) = conservation_calculations(
            sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel
        )

        earth_momentum = earth_mass * earth_vel[0]

        plot_conserved_func(
            times, earth_momentum, total_momentum, total_angular_momentum, total_energy
        )


def calc_orbit(
    num_years=10.0,
    num_steps=1 * 10**5,
    perturbation_size=0,
    perturbation_angle=None,
    speed=1,
    vel_angle=None,
    default_pos=L4,
    integrate=integrate_cy,
):
    default_pertubation_angle = np.arctan2(default_pos[1], default_pos[0])

    default_pertubation_angle = np.degrees(default_pertubation_angle)

    if perturbation_angle is None:

        perturbation_angle = default_pertubation_angle

    if vel_angle is None:

        vel_angle = default_pertubation_angle + 90

    sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel = initialization(
        num_steps, perturbation_size, perturbation_angle, speed, vel_angle, default_pos
    )

    # converting num_years to seconds
    time_stop = num_years * years

    time_step = time_stop / num_steps

    return integrate(
        time_step, num_steps, sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel
    )


def initialization(
    num_steps,
    perturbation_size,
    perturbation_angle,
    speed,
    vel_angle,
    default_pos=L4,
):
    """Initializes the arrays of positions and velocities
    so that their initial values correspond to the input parameters
    """

    # creating position and velocity vector arrays

    # array of position vectors for sun
    sun_pos = np.empty((num_steps + 1, 3), dtype=np.double)

    # array of velocity vectors for sun
    sun_vel = np.empty_like(sun_pos)

    # array of position vectors for earth
    earth_pos = np.empty_like(sun_pos)

    # array of velocity vectors for earth
    earth_vel = np.empty_like(sun_pos)

    # array of position vectors for satellite
    sat_pos = np.empty_like(sun_pos)

    # array of velocity vectors for satellite
    sat_vel = np.empty_like(sun_pos)

    # sun is initially at origin but its position is not fixed
    sun_pos[0] = np.array((0, 0, 0))

    # earth starts 1 AU from the sun (and origin) and lies on the positive x-axis
    earth_pos[0] = np.array((1 * AU, 0, 0))

    sat_pos[0] = default_pos

    # all 3 masses orbit about the Center of Mass at an angular_speed = 1 orbit/year =
    # 2 pi radians/year
    # we setup conditions so that the earth and sun have circular orbits
    # velocities have to be defined relative to the CM
    init_CM_pos = calc_center_of_mass(sun_pos[0], earth_pos[0], sat_pos[0])

    # orbits are counter clockwise so
    # angular velocity is in the positive z direction
    angular_vel = np.array((0, 0, angular_speed))

    # for a circular orbit velocity = cross_product(angular velocity, position)
    # where vec(position) is the position relative to the point being orbited
    # in this case the Center of Mass
    sun_vel[0] = np.cross(angular_vel, sun_pos[0] - init_CM_pos)

    earth_vel[0] = np.cross(angular_vel, earth_pos[0] - init_CM_pos)

    #    Perturbation    #

    perturbation_size = perturbation_size * AU

    perturbation_angle = np.radians(perturbation_angle)

    perturbation = perturbation_size * np.array(
        (np.cos(perturbation_angle), np.sin(perturbation_angle), 0)
    )

    speed = speed * norm(np.cross(angular_vel, sat_pos[0] - init_CM_pos))

    vel_angle = np.radians(vel_angle)

    sat_vel[0] = speed * np.array((np.cos(vel_angle), np.sin(vel_angle), 0))

    # perturbing the initial position of the satellite
    sat_pos[0] = sat_pos[0] + perturbation

    return sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel


# pure python version of integrate function
def integrate_py(
    time_step, num_steps, sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel
):

    for k in range(1, num_steps + 1):

        # intermediate position calculation
        intermediate_sun_pos = sun_pos[k - 1] + 0.5 * sun_vel[k - 1] * time_step

        intermediate_earth_pos = earth_pos[k - 1] + 0.5 * earth_vel[k - 1] * time_step

        intermediate_sat_pos = sat_pos[k - 1] + 0.5 * sat_vel[k - 1] * time_step

        # acceleration calculation
        sun_accel, earth_accel, sat_accel = calc_acceleration(
            intermediate_sun_pos, intermediate_earth_pos, intermediate_sat_pos
        )

        # velocity update
        sun_vel[k] = sun_vel[k - 1] + sun_accel * time_step

        earth_vel[k] = earth_vel[k - 1] + earth_accel * time_step

        sat_vel[k] = sat_vel[k - 1] + sat_accel * time_step

        # position update
        sun_pos[k] = intermediate_sun_pos + 0.5 * sun_vel[k] * time_step

        earth_pos[k] = intermediate_earth_pos + 0.5 * earth_vel[k] * time_step

        sat_pos[k] = intermediate_sat_pos + 0.5 * sat_vel[k] * time_step

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


def calc_center_of_mass(sun_pos, earth_pos, sat_pos):

    return (sun_mass * sun_pos + earth_mass * earth_pos + sat_mass * sat_pos) / (
        sun_mass + earth_mass + sat_mass
    )


timer = QTimer()


def plot_orbit(sun_pos, earth_pos, sat_pos):

    orbit_plot = pg.plot(title="Orbits of Masses")
    orbit_plot.setLabel("bottom", "x", units="AU")
    orbit_plot.setLabel("left", "y", units="AU")
    orbit_plot.addLegend()

    orbit_plot.setXRange(-1.2, 1.2)
    orbit_plot.setYRange(-1.2, 1.2)
    orbit_plot.setAspectLocked(True)

    # zoom into the sun until the axes are on the scale of a few micro-AU to see sun's orbit
    orbit_plot.plot(sun_pos[:, 0] / AU, sun_pos[:, 1] / AU, pen="y", name="Sun")

    orbit_plot.plot(
        earth_pos[:, 0] / AU, earth_pos[:, 1] / AU, pen=(50, 147, 168), name="Earth"
    )

    # overlaps with earth's orbit, cant be seen clearly
    orbit_plot.plot(sat_pos[:, 0] / AU, sat_pos[:, 1] / AU, pen="g", name="Satellite")

    anim_plot = pg.ScatterPlotItem()

    orbit_plot.addItem(anim_plot)

    idx = update_idx(sun_pos.shape[0])

    def update_plot():

        i = next(idx)

        anim_plot.clear()

        anim_plot.addPoints(
            [sun_pos[i, 0] / AU],
            [sun_pos[i, 1] / AU],
            pen="y",
            brush="y",
            size=10,
            name="Sun",
        )

        anim_plot.addPoints(
            [earth_pos[i, 0] / AU],
            [earth_pos[i, 1] / AU],
            pen="b",
            brush="b",
            size=7,
            name="Earth",
        )

        anim_plot.addPoints(
            [sat_pos[i, 0] / AU],
            [sat_pos[i, 1] / AU],
            pen="g",
            brush="g",
            size=7,
            name="Satellite",
        )

    # time in milliseconds between plot updates
    # making it small (=1) and having 2 animated plots leads to crashes
    period = 33

    timer.timeout.connect(update_plot)
    timer.start(period)


def update_idx(num_steps):
    """This function is used to"""

    i = 0

    # maximum rate of plot update is too slow
    # so instead step through arrays at a step of rate
    # TODO: replace '5' with some function of num_step and time_step
    # so that animation is always at correct speed regardless of num_step or time_step
    rate = 5

    while True:

        i = i + rate

        if i >= num_steps:
            i = 0

        yield i


timer_rotating = QTimer()


def transform_to_corotating(times, pos, CM_pos):
    # it is necessary to transform our coordinate system to one which
    # rotates with the system
    # we can do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is ( unit(x), unit(y) )-> R(w*t) * ( unit(x), unit(y) )
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we multiply the position vectors by the matrix R(-w*t)

    # first transform our coordinate system so that the Center of Mass
    # is the origin

    pos_trans = pos - CM_pos

    for i, t in enumerate(times):

        angle = -angular_speed * t

        rotation_matrix = np.array(
            (
                (np.cos(angle), -np.sin(angle), 0),
                (np.sin(angle), np.cos(angle), 0),
                (0, 0, 1),
            )
        )

        pos_trans[i] = rotation_matrix.dot(pos_trans[i])

    return pos_trans


def plot_corotating_orbit(default_pos, sun_pos_trans, earth_pos_trans, sat_pos_trans):

    # Animated plot of satellites orbit in co-rotating frame.
    transform_plot = pg.plot(title="Orbits in Co-Rotating Coordinate System")
    transform_plot.setLabel("bottom", "x", units="AU")
    transform_plot.setLabel("left", "y", units="AU")
    transform_plot.addLegend()

    transform_plot.setXRange(-1.5, 1.5)
    transform_plot.setYRange(-1.5, 1.5)
    transform_plot.setAspectLocked(True)

    anim_trans_plot = pg.ScatterPlotItem()

    transform_plot.addItem(anim_trans_plot)

    transform_plot.plot(
        sat_pos_trans[:, 0] / AU,
        sat_pos_trans[:, 1] / AU,
        pen=(66, 245, 105),
        name="Satellite orbit",
    )

    num_steps = sun_pos_trans.shape[0] - 1

    idx = update_idx(num_steps)

    def update_trans():

        j = next(idx)

        anim_trans_plot.clear()

        steps_per_year = int(num_steps / 10)

        anim_trans_plot.addPoints(
            [default_pos[0] / AU],
            [default_pos[1] / AU],
            pen="w",
            brush="w",
            size=5,
            name="initial position",
        )

        anim_trans_plot.addPoints(
            [sun_pos_trans[j, 0] / AU],
            [sun_pos_trans[j, 1] / AU],
            pen="y",
            brush="y",
            size=10,
            name="Sun",
        )

        anim_trans_plot.addPoints(
            [earth_pos_trans[j, 0] / AU],
            [earth_pos_trans[j, 1] / AU],
            pen="b",
            brush="b",
            size=7,
            name="Earth",
        )

        anim_trans_plot.addPoints(
            [sat_pos_trans[j, 0] / AU],
            [sat_pos_trans[j, 1] / AU],
            pen="g",
            brush="g",
            size=7,
            name="Satellite",
        )

        # plots where the satellite is after 1 year
        anim_trans_plot.addPoints(
            [sat_pos_trans[steps_per_year, 0] / AU],
            [sat_pos_trans[steps_per_year, 1] / AU],
            pen="g",
            brush="w",
            size=7,
            name="Satellite 1 yr",
        )

    # time in milliseconds between plot updates
    # making it small (=1) and having 2 animated plots leads to crashes
    period = 33

    timer_rotating.timeout.connect(update_trans)
    timer_rotating.start(period)


def conservation_calculations(sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel):

    total_momentum = sun_mass * sun_vel + earth_mass * earth_vel + sat_mass * sat_vel

    angular_momentum_sun = np.cross(sun_pos, sun_mass * sun_vel)

    angular_momentum_earth = np.cross(earth_pos, earth_mass * earth_vel)

    angular_momentum_sat = np.cross(sat_pos, sat_mass * sat_vel)

    total_angular_momentum = (
        angular_momentum_sun + angular_momentum_earth + angular_momentum_sat
    )

    # array of the distance between earth and sun at each timestep
    d_earth_to_sun = norm(sun_pos - earth_pos, axis=1)

    d_earth_to_sat = norm(sat_pos - earth_pos, axis=1)

    d_sun_to_sat = norm(sat_pos - sun_pos, axis=1)

    potential_energy = (
        -G * sun_mass * earth_mass / d_earth_to_sun
        + -G * sat_mass * earth_mass / d_earth_to_sat
        + -G * sat_mass * sun_mass / d_sun_to_sat
    )

    # array of the magnitude of the velocity of sun at each timestep
    mag_sun_vel = norm(sun_vel, axis=1)

    mag_earth_vel = norm(earth_vel, axis=1)

    mag_sat_vel = norm(sat_vel, axis=1)

    kinetic_energy = (
        0.5 * sun_mass * mag_sun_vel**2
        + 0.5 * earth_mass * mag_earth_vel**2
        + 0.5 * sat_mass * mag_sat_vel**2
    )

    total_energy = potential_energy + kinetic_energy

    return total_momentum, total_angular_momentum, total_energy


def plot_conserved_func(
    times, earth_momentum, total_momentum, total_angular_momentum, total_energy
):
    # sourcery skip: extract-duplicate-method

    times_in_years = times / years

    linear_momentum_plot = pg.plot(title="Normalized Linear Momentum vs Time")
    linear_momentum_plot.setLabel("bottom", "Time", units="years")
    linear_momentum_plot.setLabel("left", "Normalized Linear Momentum")

    linear_momentum_plot.addLegend()

    # total linear momentum is not conserved (likely due to floating point errors)
    # however the variation is insignificant compared to
    # the Sun's and Earth's individual linear momenta
    linear_momentum_plot.plot(
        times_in_years,
        total_momentum[:, 0] / norm(earth_momentum),
        pen="r",
        name="x",
    )

    linear_momentum_plot.plot(
        times_in_years,
        total_momentum[:, 1] / norm(earth_momentum),
        pen="g",
        name="y",
    )

    linear_momentum_plot.plot(
        times_in_years,
        total_momentum[:, 2] / norm(earth_momentum),
        pen="b",
        name="z",
    )

    angular_momentum_plot = pg.plot(title="Normalized Angular Momenta vs Time")
    angular_momentum_plot.setLabel("bottom", "Time", units="years")
    angular_momentum_plot.setLabel("left", "Normalized Angular Momentum")

    angular_momentum_plot.addLegend()

    # x and y components of angular momentum are 0
    # angular_momentum_plot.plot(
    #   times_in_years,
    #   total_angular_momentum[:, 0]/total_angular_momentum[0, 0]-1,
    #   pen='r',
    #   name='x'
    # )

    # angular_momentum_plot.plot(
    #   times_in_years,
    #   total_angular_momentum[:, 1]/total_angular_momentum[0, 1]-1,
    #   pen='g',
    #   name='y'
    # )

    angular_momentum_plot.plot(
        times_in_years,
        total_angular_momentum[:, 2] / total_angular_momentum[0, 2] - 1,
        pen="b",
        name="z",
    )

    energy_plot = pg.plot(title="Normalized Energy vs Time")
    energy_plot.setLabel("bottom", "Time", units="years")
    energy_plot.setLabel("left", "Normalized Energy")

    energy_plot.plot(times_in_years, total_energy / total_energy[0] - 1)


def calc_period(
    perturbation_size, perturbation_angle, speed, vel_angle, default_pos=L4
):

    sat_pos, sat_vel = get_sat_initial_conditions(
        perturbation_size, perturbation_angle, speed, vel_angle, default_pos
    )

    semi_major_axis = calc_semi_major_axis(sat_pos, sat_vel)

    period_squared = 4 * pi**2 * semi_major_axis**3 / (G * sun_mass)

    return np.sqrt(period_squared)


def get_sat_initial_conditions(
    perturbation_size, perturbation_angle, speed, vel_angle, default_pos=L4
):
    # pylint: disable=unused-variable
    *others, sat_pos, sat_vel = initialization(
        0, perturbation_size, perturbation_angle, speed, vel_angle, default_pos
    )

    init_sat_pos, init_sat_vel = sat_pos[0], sat_vel[0]

    return init_sat_pos, init_sat_vel


def calc_semi_major_axis(sat_pos, sat_vel):
    # sourcery skip: inline-immediately-returned-variable

    # Treating the influence of earth on satellite as negligible
    # Therefore we can apply the solution to the 2-body problem to the satellite

    # See "2 body analytic.docx" and "solve for orbital parameters.docx" for a derivation
    # of the following procedure

    unit_pos = sat_pos / norm(sat_pos)

    # 90 degrees
    angle = pi / 2

    # rotates by 90 degrees counter-clockwise
    rotation_matrix = np.array(
        (
            (np.cos(angle), -np.sin(angle), 0),
            (np.sin(angle), np.cos(angle), 0),
            (0, 0, 1),
        )
    )

    unit_angular = rotation_matrix.dot(unit_pos)

    radial_vel = np.dot(sat_vel, unit_pos)

    transverse_vel = np.dot(sat_vel, unit_angular)

    angular_momentum = np.cross(sat_pos, sat_mass * sat_vel)

    angular_momentum = norm(angular_momentum)

    gravitational_coefficient = G * sun_mass * sat_mass

    transverse_vel_prime = -(
        transverse_vel - gravitational_coefficient / angular_momentum
    )

    eccentricity_squared = (
        -angular_momentum / gravitational_coefficient * radial_vel
    ) ** 2 + (angular_momentum / gravitational_coefficient * transverse_vel_prime) ** 2

    reduced_mass = sun_mass * sat_mass / (sun_mass + sat_mass)

    semi_major_axis = angular_momentum**2 / (
        gravitational_coefficient * reduced_mass * (1 - eccentricity_squared)
    )

    return semi_major_axis
