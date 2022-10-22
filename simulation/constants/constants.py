# pylint: disable=invalid-name, missing-docstring

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10**-11

# 1 AU in meters
# serves as a conversion factor from AUs to meters
AU = 1.495978707 * 10**11

# 1 Julian year in seconds
# serves as a conversion factor from years to seconds
YEARS = 365.25 * 24 * 60 * 60

HOURS = 60 * 60

# mass of Sun in kilograms
SUN_MASS: float = 1.98847 * 10**30

EARTH_MASS = 5.9722 * 10**24

MOON_MASS = 7.34767309 * 10**22

JUPITER_MASS = 1.89813 * 10**27

# distance between Earth and Sun in AU
SUN_EARTH_DISTANCE = 0.9954

SUN_JUPITER_DISTANCE = 4.953

EARTH_MOON_DISTANCE = 0.002617


CONSTANTS = {
    "SUN_MASS": SUN_MASS,
    "EARTH_MASS": EARTH_MASS,
    "MOON_MASS": MOON_MASS,
    "JUPITER_MASS": JUPITER_MASS,
    "SUN_EARTH_DISTANCE": SUN_EARTH_DISTANCE,
    "SUN_JUPITER_DISTANCE": SUN_JUPITER_DISTANCE,
    "EARTH_MOON_DISTANCE": EARTH_MOON_DISTANCE,
}
