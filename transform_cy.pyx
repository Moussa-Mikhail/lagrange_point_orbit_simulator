#cython: language_level=3

import numpy as np

import cython

from libc.math cimport cos, sin

from cython.parallel import prange

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.embedsignature(True)
@cython.initializedcheck(False)
cpdef transform_to_corotating(times, const double angular_speed, pos_trans):
    # it is necessary to transform our coordinate system to one which
    # rotates with the system
    # we can do this by linearly transforming each position vector by
    # the inverse of the coordinate transform
    # the coordinate transform is unit(x) -> R(w*t)*unit(x), unit(y) -> R(w*t)*unit(y)
    # where R(w*t) is the rotation matrix with angle w*t about the z axis
    # the inverse is R(-w*t)
    # at each time t we multiply the position vectors by the matrix R(-w*t)

    # The origin of the coordinate system is the Center of Mass

    cdef double[:, ::1] pos_trans_view = pos_trans

    cdef double[::1] times_view = times

    pos_rotated = np.empty_like(pos_trans)

    cdef double[:, ::1] pos_rotated_view = pos_rotated
    
    cdef Py_ssize_t i

    cdef double time, angle, c, s, pos_trans_x, pos_trans_y

    for i in prange(times_view.shape[0], nogil=True, schedule='static'):

        time = times_view[i]

        angle = -angular_speed * time

        c = cos(angle)

        s = sin(angle)

        pos_trans_x = pos_trans_view[i, 0]

        pos_trans_y = pos_trans_view[i, 1]

        pos_rotated_view[i, 0] = c * pos_trans_x - s * pos_trans_y

        pos_rotated_view[i, 1] = s * pos_trans_x + c * pos_trans_y

    return pos_rotated