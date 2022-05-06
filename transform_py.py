# pylint: disable=invalid-name, missing-docstring
import numpy as np

from thesis_code import angular_speed


def transform_to_corotating(times, pos, CM_pos):
    # it is necessary to transform our coordinate system to one which
    # rotates with the system
    # we can do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we multiply the position vectors by the matrix R(-w*t)

    # first transform our coordinate system so that the Center of Mass
    # is the origin

    pos_trans = pos - CM_pos

    for i, t in enumerate(times):

        angle = -angular_speed * t

        cos = np.cos(angle)

        sin = np.sin(angle)

        pos_trans_x = pos_trans[i, 0]

        pos_trans_y = pos_trans[i, 1]

        pos_trans[i, 0] = cos * pos_trans_x - sin * pos_trans_y

        pos_trans[i, 1] = sin * pos_trans_x + cos * pos_trans_y

    return pos_trans
