#cython: language_level=3

import numpy as np

cimport cython

from libc.math cimport sqrt

cdef double star_mass

cdef double planet_mass

cdef double G

from thesis_code import G, planet_mass, star_mass


@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.embedsignature(True)
@cython.initializedcheck(False)
cpdef integrate(
    const double time_step,
    const long num_steps,
    star_pos,
    star_vel,
    planet_pos,
    planet_vel,
    sat_pos,
    sat_vel
):

    cdef double[:, ::1] star_pos_view = star_pos

    cdef double[:, ::1] star_vel_view = star_vel

    cdef double[:, ::1] planet_pos_view = planet_pos

    cdef double[:, ::1] planet_vel_view = planet_vel

    cdef double[:, ::1] sat_pos_view = sat_pos

    cdef double[:, ::1] sat_vel_view = sat_vel


    cdef double[::1] star_intermediate_pos = np.empty(3, dtype=np.double)

    cdef double[::1] planet_intermediate_pos = np.empty_like(star_intermediate_pos)

    cdef double[::1] sat_intermediate_pos = np.empty_like(star_intermediate_pos)

    cdef double[::1] star_accel = np.empty_like(star_intermediate_pos)

    cdef double[::1] planet_accel = np.empty_like(star_intermediate_pos)

    cdef double[::1] sat_accel = np.empty_like(star_intermediate_pos)

    cdef Py_ssize_t k

    cdef Py_ssize_t j

    for k in range(1, num_steps + 1):

        for j in range(3):

            # intermediate position calculation
            star_intermediate_pos[j] = star_pos_view[k - 1, j] + 0.5 * star_vel_view[k - 1, j] * time_step

            planet_intermediate_pos[j] = planet_pos_view[k - 1, j] + 0.5 * planet_vel_view[k - 1, j] * time_step

            sat_intermediate_pos[j] = sat_pos_view[k - 1, j] + 0.5 * sat_vel_view[k - 1, j] * time_step

        # acceleration calculation
        # calc_acceleration changes the values in the accel arrays
        calc_acceleration(
            star_intermediate_pos,
            planet_intermediate_pos,
            sat_intermediate_pos,
            star_accel,
            planet_accel,
            sat_accel
        )

        for j in range(3):
            
            # velocity update
            star_vel_view[k, j] = star_vel_view[k - 1, j] + star_accel[j] * time_step

            planet_vel_view[k, j] = planet_vel_view[k - 1, j] + planet_accel[j] * time_step

            sat_vel_view[k, j] = sat_vel_view[k - 1, j] + sat_accel[j] * time_step

            # position update
            star_pos_view[k, j] = star_intermediate_pos[j] + 0.5 * star_vel_view[k, j] * time_step

            planet_pos_view[k, j] = planet_intermediate_pos[j] + 0.5 * planet_vel_view[k, j] * time_step

            sat_pos_view[k, j] = sat_intermediate_pos[j] + 0.5 * sat_vel_view[k, j] * time_step

    return star_pos, star_vel, planet_pos, planet_vel, sat_pos, sat_vel

@cython.cdivision(True)
@cython.nonecheck(False)
@cython.wraparound(False)
@cython.boundscheck(False)
@cython.initializedcheck(False)
cdef void calc_acceleration(
    const double[::1] star_pos,
    const double[::1] planet_pos,
    const double[::1] sat_pos,
    double[::1] star_accel,
    double[::1] planet_accel,
    double[::1] sat_accel
):

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
cdef double norm(const double *arr):
    
    return sqrt(arr[0]*arr[0] + arr[1]*arr[1] + arr[2]*arr[2])
