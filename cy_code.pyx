#cython: language_level=3

import numpy as np

cimport cython

from libc.math cimport sqrt

import numpy as np

cimport numpy as np

# mass of sun in kilograms
cdef double sun_mass = 1.98847 * 10**30

# mass of earth in kilograms
cdef double earth_mass = 5.9722 * 10**24

# mass of satellite near in kilograms
# negligible compared to other masses
cdef double sat_mass = 1.0

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
cdef double G = 6.67430 * pow(10, -11)

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
cpdef integrate_cy(
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


    cdef double[::1] intermediate_sun_pos = np.empty(3, dtype=np.double)

    cdef double[::1] intermediate_earth_pos = np.empty_like(intermediate_sun_pos)

    cdef double[::1] intermediate_sat_pos = np.empty_like(intermediate_sun_pos)

    cdef double[::1] r_earth_to_sun = np.empty_like(intermediate_sun_pos)

    cdef double[::1] r_sat_to_sun = np.empty_like(intermediate_sun_pos)

    cdef double[::1] r_sat_to_earth = np.empty_like(intermediate_sun_pos)

    cdef double[::1] sun_accel = np.empty_like(intermediate_sun_pos)

    cdef double[::1] earth_accel = np.empty_like(intermediate_sun_pos)

    cdef double[::1] sat_accel = np.empty_like(intermediate_sun_pos)

    cdef size_t k

    cdef size_t j

    for k in range(1, num_steps + 1):

        for j in range(3):

            # intermediate position calculation
            intermediate_sun_pos[j] = sun_pos_view[k - 1, j] + 0.5 * sun_vel_view[k - 1, j] * time_step

            intermediate_earth_pos[j] = earth_pos_view[k - 1, j] + 0.5 * earth_vel_view[k - 1, j] * time_step

            intermediate_sat_pos[j] = sat_pos_view[k - 1, j] + 0.5 * sat_vel_view[k - 1, j] * time_step

        # acceleration calculation
        calc_acceleration(
            intermediate_sun_pos,
            intermediate_earth_pos,
            intermediate_sat_pos,
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
            sun_pos_view[k, j] = intermediate_sun_pos[j] + 0.5 * sun_vel_view[k, j] * time_step

            earth_pos_view[k, j] = intermediate_earth_pos[j] + 0.5 * earth_vel_view[k, j] * time_step

            sat_pos_view[k, j] = intermediate_sat_pos[j] + 0.5 * sat_vel_view[k, j] * time_step

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

    cdef size_t j
    
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