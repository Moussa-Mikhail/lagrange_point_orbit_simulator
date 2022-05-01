#cython: language_level=3

import numpy as np

cimport cython

from libc.math cimport sqrt

import numpy as np

cdef double sun_mass

cdef double earth_mass

cdef double sat_mass

cdef double G

from thesis_code import sun_mass, earth_mass, sat_mass, G

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
def integrate(
    const double time_step,
    const long num_steps,
    sun_pos,
    sun_vel,
    earth_pos,
    earth_vel,
    sat_pos,
    sat_vel
):

    cdef double[:, ::1] sun_pos_view = sun_pos

    cdef double[:, ::1] sun_vel_view = sun_vel

    cdef double[:, ::1] earth_pos_view = earth_pos

    cdef double[:, ::1] earth_vel_view = earth_vel

    cdef double[:, ::1] sat_pos_view = sat_pos

    cdef double[:, ::1] sat_vel_view = sat_vel


    cdef double[::1] sun_intermediate_pos = np.empty(3, dtype=np.double)

    cdef double[::1] earth_intermediate_pos = np.empty_like(sun_intermediate_pos)

    cdef double[::1] sat_intermediate_pos = np.empty_like(sun_intermediate_pos)

    cdef double[::1] r_earth_to_sun = np.empty_like(sun_intermediate_pos)

    cdef double[::1] r_sat_to_sun = np.empty_like(sun_intermediate_pos)

    cdef double[::1] r_sat_to_earth = np.empty_like(sun_intermediate_pos)

    cdef double[::1] sun_accel = np.empty_like(sun_intermediate_pos)

    cdef double[::1] earth_accel = np.empty_like(sun_intermediate_pos)

    cdef double[::1] sat_accel = np.empty_like(sun_intermediate_pos)

    cdef Py_ssize_t k

    cdef Py_ssize_t j

    for k in range(1, num_steps + 1):

        for j in range(3):

            # intermediate position calculation
            sun_intermediate_pos[j] = sun_pos_view[k - 1, j] + 0.5 * sun_vel_view[k - 1, j] * time_step

            earth_intermediate_pos[j] = earth_pos_view[k - 1, j] + 0.5 * earth_vel_view[k - 1, j] * time_step

            sat_intermediate_pos[j] = sat_pos_view[k - 1, j] + 0.5 * sat_vel_view[k - 1, j] * time_step

        # acceleration calculation
        calc_acceleration(
            sun_intermediate_pos,
            earth_intermediate_pos,
            sat_intermediate_pos,
            r_earth_to_sun,
            r_sat_to_sun,
            r_sat_to_earth,
            sun_accel,
            earth_accel,
            sat_accel,
        )

        for j in range(3):
            
            # velocity update
            sun_vel_view[k, j] = sun_vel_view[k - 1, j] + sun_accel[j] * time_step

            earth_vel_view[k, j] = earth_vel_view[k - 1, j] + earth_accel[j] * time_step

            sat_vel_view[k, j] = sat_vel_view[k - 1, j] + sat_accel[j] * time_step

            # position update
            sun_pos_view[k, j] = sun_intermediate_pos[j] + 0.5 * sun_vel_view[k, j] * time_step

            earth_pos_view[k, j] = earth_intermediate_pos[j] + 0.5 * earth_vel_view[k, j] * time_step

            sat_pos_view[k, j] = sat_intermediate_pos[j] + 0.5 * sat_vel_view[k, j] * time_step

    return sun_pos, sun_vel, earth_pos, earth_vel, sat_pos, sat_vel

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
cdef void calc_acceleration(
    const double[::1] sun_pos,
    const double[::1] earth_pos,
    const double[::1] sat_pos,
    double[::1] r_earth_to_sun,
    double[::1] r_sat_to_sun,
    double[::1] r_sat_to_earth,
    double[::1] sun_accel,
    double[::1] earth_accel,
    double[::1] sat_accel
):

    cdef Py_ssize_t j
    
    for j in range(3):

        # vector from earth to sun
        r_earth_to_sun[j] = sun_pos[j] - earth_pos[j]

        r_sat_to_sun[j] = sun_pos[j] - sat_pos[j]
        
        r_sat_to_earth[j] = earth_pos[j] - sat_pos[j]

    # distance between earth and sun
    cdef double d_earth_to_sun = norm(r_earth_to_sun)
    
    cdef double d_sat_to_sun = norm(r_sat_to_sun)

    cdef double d_sat_to_earth = norm(r_sat_to_earth)

    for j in range(3):

        sun_accel[j] = -G * earth_mass * r_earth_to_sun[j] / d_earth_to_sun**3
        
        # note the lack of negative sign in the following lines
        earth_accel[j] = G * sun_mass * r_earth_to_sun[j] / d_earth_to_sun**3

        sat_accel[j] = G * sun_mass * r_sat_to_sun[j] / d_sat_to_sun**3\
                     + G * earth_mass * r_sat_to_earth[j] / d_sat_to_earth**3

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
cdef inline double norm(const double[::1] mem_view):
    
    return sqrt(mem_view[0]*mem_view[0] + mem_view[1]*mem_view[1] + mem_view[2]*mem_view[2])
