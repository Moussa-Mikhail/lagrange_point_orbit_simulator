#cython: language_level=3

import numpy as np

import cython

from libc.math cimport sqrt, cos, sin

from cython.parallel import prange

cdef double G

from constants import G

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.embedsignature(True)
@cython.initializedcheck(False)
cpdef void integrate(
    const double time_step,
    const long num_steps,
    const double star_mass,
    const double planet_mass,
    double [:, ::1] star_pos,
    double [:, ::1] star_vel,
    double [:, ::1] planet_pos,
    double [:, ::1] planet_vel,
    double [:, ::1] sat_pos,
    double [:, ::1] sat_vel,
) nogil:


    cdef double star_intermediate_pos[3]

    cdef double planet_intermediate_pos[3]

    cdef double sat_intermediate_pos[3]

    cdef double star_accel[3]

    cdef double planet_accel[3]

    cdef double sat_accel[3]

    cdef Py_ssize_t k, j

    for k in range(1, num_steps + 1):

        for j in range(3):

            # intermediate position calculation
            star_intermediate_pos[j] = star_pos[k - 1, j] + 0.5 * star_vel[k - 1, j] * time_step

            planet_intermediate_pos[j] = planet_pos[k - 1, j] + 0.5 * planet_vel[k - 1, j] * time_step

            sat_intermediate_pos[j] = sat_pos[k - 1, j] + 0.5 * sat_vel[k - 1, j] * time_step

        # acceleration calculation
        # calc_acceleration changes the values in the accel arrays
        calc_acceleration(
            star_mass,
            planet_mass,
            star_intermediate_pos,
            planet_intermediate_pos,
            sat_intermediate_pos,
            star_accel,
            planet_accel,
            sat_accel
        )

        for j in range(3):
            
            # velocity update
            star_vel[k, j] = star_vel[k - 1, j] + star_accel[j] * time_step

            planet_vel[k, j] = planet_vel[k - 1, j] + planet_accel[j] * time_step

            sat_vel[k, j] = sat_vel[k - 1, j] + sat_accel[j] * time_step

            # position update
            star_pos[k, j] = star_intermediate_pos[j] + 0.5 * star_vel[k, j] * time_step

            planet_pos[k, j] = planet_intermediate_pos[j] + 0.5 * planet_vel[k, j] * time_step

            sat_pos[k, j] = sat_intermediate_pos[j] + 0.5 * sat_vel[k, j] * time_step

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.initializedcheck(False)
cdef void calc_acceleration(
    const double star_mass,
    const double planet_mass,
    const double * const star_pos,
    const double * const planet_pos,
    const double * const sat_pos,
    double *star_accel,
    double *planet_accel,
    double *sat_accel
) nogil:

    cdef double r_planet_to_star[3]

    cdef double r_sat_to_star[3]

    cdef double r_sat_to_planet[3]

    cdef Py_ssize_t j
    
    for j in range(3):

        # vector from planet to star
        r_planet_to_star[j] = star_pos[j] - planet_pos[j]

        r_sat_to_star[j] = star_pos[j] - sat_pos[j]
        
        r_sat_to_planet[j] = planet_pos[j] - sat_pos[j]

    # distance between planet and star
    cdef double d_planet_to_star = norm(r_planet_to_star)
    
    cdef double d_sat_to_star = norm(r_sat_to_star)

    cdef double d_sat_to_planet = norm(r_sat_to_planet)

    for j in range(3):

        star_accel[j] = -G * planet_mass * r_planet_to_star[j] / d_planet_to_star**3
        
        # note the lack of negative sign in the following lines
        planet_accel[j] = G * star_mass * r_planet_to_star[j] / d_planet_to_star**3

        sat_accel[j] = G * star_mass * r_sat_to_star[j] / d_sat_to_star**3\
                     + G * planet_mass * r_sat_to_planet[j] / d_sat_to_planet**3

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.initializedcheck(False)
cdef double norm(const double * const arr) nogil:
    
    return sqrt(arr[0]*arr[0] + arr[1]*arr[1] + arr[2]*arr[2])

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.embedsignature(True)
@cython.initializedcheck(False)
cpdef transform_to_corotating(double[::1] times, const double angular_speed, double [:, ::1] pos_trans):
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

    cdef double[:, ::1] pos_rotated_view = pos_rotated
    
    cdef Py_ssize_t i

    cdef double time, angle, c, s, pos_trans_x, pos_trans_y

    for i in prange(times.shape[0], nogil=True):

        time = times[i]

        angle = -angular_speed * time

        c = cos(angle)

        s = sin(angle)

        pos_trans_x = pos_trans[i, 0]

        pos_trans_y = pos_trans[i, 1]

        pos_rotated_view[i, 0] = c * pos_trans_x - s * pos_trans_y

        pos_rotated_view[i, 1] = s * pos_trans_x + c * pos_trans_y
    
    pos_rotated[:, 2] = pos_trans[:, 2]

    return pos_rotated