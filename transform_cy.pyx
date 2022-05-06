#cython: language_level=3

import numpy as np

cimport cython

from libc.math cimport cos, sin

import numpy as np

cdef double angular_speed

from thesis_code import angular_speed

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
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

    cdef double[:, ::1] pos_trans_view = pos_trans

    cdef double[::1] times_view = times
    
    cdef Py_ssize_t i

    cdef double angle

    cdef double pos_trans_x

    cdef double pos_trans_y

    for i in range(times_view.shape[0]):

        angle = -angular_speed * times_view[i]

        c = cos(angle)

        s = sin(angle)

        pos_trans_x = pos_trans_view[i, 0]

        pos_trans_y = pos_trans_view[i, 1]

        pos_trans_view[i, 0] = c * pos_trans_x - s * pos_trans_y

        pos_trans_view[i, 1] = s * pos_trans_x + c * pos_trans_y

    return pos_trans