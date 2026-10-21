from math import sqrt

import numpy as np

from lagrangepointsimulator.constants import G
from lagrangepointsimulator.sim_types import Array1D, Array2D, Vec3

try:
    from numba import njit, prange  # type: ignore[import-untyped]

    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    # Numba is optional. Without it the functions below run as plain Python.
    prange = range  # ty:ignore[invalid-assignment]

    def njit(*args, **_kwargs):
        """No-op stand-in for numba.njit. Usable as @njit and as @njit(...) with any options."""
        if len(args) == 1 and callable(args[0]):
            return args[0]

        return lambda func: func


@njit(inline="always")
def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


@njit(inline="always")
def _advance(pos: Vec3, vel: Vec3, time: float) -> Vec3:
    return (pos[0] + vel[0] * time, pos[1] + vel[1] * time, pos[2] + vel[2] * time)


@njit(inline="always")
def inverse_norm_cubed(vector: Vec3) -> float:
    return sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]) ** -3


@njit(inline="always")
def calc_acceleration(
    g_star: float,
    g_planet: float,
    star_pos: Vec3,
    planet_pos: Vec3,
    sat_pos: Vec3,
) -> tuple[Vec3, Vec3, Vec3]:
    """Return the accelerations of the star, planet and satellite."""
    planet_to_star = _sub(star_pos, planet_pos)
    sat_to_star = _sub(star_pos, sat_pos)
    sat_to_planet = _sub(planet_pos, sat_pos)

    d_planet_to_star_inverse_cubed = inverse_norm_cubed(planet_to_star)
    d_sat_to_star_inverse_cubed = inverse_norm_cubed(sat_to_star)
    d_sat_to_planet_inverse_cubed = inverse_norm_cubed(sat_to_planet)

    star_planet_coeff = -g_planet * d_planet_to_star_inverse_cubed
    planet_star_coeff = g_star * d_planet_to_star_inverse_cubed
    sat_star_coeff = g_star * d_sat_to_star_inverse_cubed
    sat_planet_coeff = g_planet * d_sat_to_planet_inverse_cubed

    star_accel = (
        star_planet_coeff * planet_to_star[0],
        star_planet_coeff * planet_to_star[1],
        star_planet_coeff * planet_to_star[2],
    )

    # note the lack of negative signs in the following lines
    planet_accel = (
        planet_star_coeff * planet_to_star[0],
        planet_star_coeff * planet_to_star[1],
        planet_star_coeff * planet_to_star[2],
    )

    sat_accel = (
        sat_star_coeff * sat_to_star[0] + sat_planet_coeff * sat_to_planet[0],
        sat_star_coeff * sat_to_star[1] + sat_planet_coeff * sat_to_planet[1],
        sat_star_coeff * sat_to_star[2] + sat_planet_coeff * sat_to_planet[2],
    )

    return star_accel, planet_accel, sat_accel


@njit(cache=True)
def integrate(
    time_step: float,
    num_steps: int,
    star_mass: float,
    planet_mass: float,
    star_pos: Array2D,
    star_vel: Array2D,
    planet_pos: Array2D,
    planet_vel: Array2D,
    sat_pos: Array2D,
    sat_vel: Array2D,
) -> None:
    half_time_step = 0.5 * time_step

    g_star = G * star_mass
    g_planet = G * planet_mass

    # The state is carried in tuples so the loop doesn't read back from the arrays.
    star_p: Vec3 = (star_pos[0, 0], star_pos[0, 1], star_pos[0, 2])
    star_v: Vec3 = (star_vel[0, 0], star_vel[0, 1], star_vel[0, 2])
    planet_p: Vec3 = (planet_pos[0, 0], planet_pos[0, 1], planet_pos[0, 2])
    planet_v: Vec3 = (planet_vel[0, 0], planet_vel[0, 1], planet_vel[0, 2])
    sat_p: Vec3 = (sat_pos[0, 0], sat_pos[0, 1], sat_pos[0, 2])
    sat_v: Vec3 = (sat_vel[0, 0], sat_vel[0, 1], sat_vel[0, 2])

    for k in range(1, num_steps + 1):
        star_p = _advance(star_p, star_v, half_time_step)
        planet_p = _advance(planet_p, planet_v, half_time_step)
        sat_p = _advance(sat_p, sat_v, half_time_step)

        star_accel, planet_accel, sat_accel = calc_acceleration(g_star, g_planet, star_p, planet_p, sat_p)

        star_v = _advance(star_v, star_accel, time_step)
        planet_v = _advance(planet_v, planet_accel, time_step)
        sat_v = _advance(sat_v, sat_accel, time_step)

        star_p = _advance(star_p, star_v, half_time_step)
        planet_p = _advance(planet_p, planet_v, half_time_step)
        sat_p = _advance(sat_p, sat_v, half_time_step)

        for j in range(3):
            star_pos[k, j] = star_p[j]
            star_vel[k, j] = star_v[j]
            planet_pos[k, j] = planet_p[j]
            planet_vel[k, j] = planet_v[j]
            sat_pos[k, j] = sat_p[j]
            sat_vel[k, j] = sat_v[j]


@njit(parallel=True, cache=True)
def transform_to_corotating(position: Array2D, times: Array1D, angular_speed: float) -> Array2D:
    """Transform pos_trans to a frame of reference that rotates at a rate of angular_speed counter-clockwise.
    pos_trans is assumed to be an array of positions measured relative to the center of rotation.
    """
    # w is the angular speed, t is the time
    # we transform pos_trans by linearly transforming each position vector by the inverse of the basis transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we apply the matrix R(-w*t) to the position vector

    num_steps: int = position.shape[0]

    corotating_position = np.empty(dtype=position.dtype, shape=(num_steps, 2))

    for i in prange(num_steps):  # ty:ignore[not-iterable]
        i: int
        time: float = times[i]

        angle = -angular_speed * time

        cos: float = np.cos(angle)
        sin: float = np.sin(angle)

        x, y = position[i, :2]

        corotating_position[i, 0] = cos * x - sin * y

        corotating_position[i, 1] = sin * x + cos * y

    return corotating_position


def _transform_to_corotating_numpy(position: Array2D, times: Array1D, angular_speed: float) -> Array2D:
    """Vectorized transform_to_corotating, used when Numba isn't installed since a Python loop is slow."""
    angle = -angular_speed * times
    cos = np.cos(angle)
    sin = np.sin(angle)

    x = position[:, 0]
    y = position[:, 1]

    corotating_position = np.empty(dtype=position.dtype, shape=(position.shape[0], 2))
    corotating_position[:, 0] = cos * x - sin * y
    corotating_position[:, 1] = sin * x + cos * y

    return corotating_position


if not HAS_NUMBA:
    transform_to_corotating = _transform_to_corotating_numpy
