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

# mass of Earth in kilograms
EARTH_MASS = 5.9722 * 10**24

CONSTANTS = {
    "SUN_MASS": SUN_MASS,
    "EARTH_MASS": EARTH_MASS,
}
