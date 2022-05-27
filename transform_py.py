# pylint: disable=invalid-name, missing-docstring
import numpy as np

from numba import njit  # type: ignore


def transform_to_corotating(sim, pos_trans):

    return _transform_to_corotating(sim.times, sim.angular_speed, pos_trans)


@njit(parallel=True)
def _transform_to_corotating(times, angular_speed, pos_trans):
    # it is necessary to transform our coordinate system to one which
    # rotates with the system
    # we can do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we multiply the position vectors by the matrix R(-w*t)

    # The origin of the coordinate system is the Center of Mass

    pos_rotated = np.empty_like(pos_trans)

    for i in range(pos_trans.shape[0]):

        t = times[i]

        angle = -angular_speed * t

        cos = np.cos(angle)

        sin = np.sin(angle)

        pos_trans_x = pos_trans[i, 0]

        pos_trans_y = pos_trans[i, 1]

        pos_rotated[i, 0] = cos * pos_trans_x - sin * pos_trans_y

        pos_rotated[i, 1] = sin * pos_trans_x + cos * pos_trans_y

    pos_rotated[:, 2] = 0

    return pos_rotated
