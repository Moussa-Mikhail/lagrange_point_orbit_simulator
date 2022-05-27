# pylint: disable=unused-import, missing-docstring, invalid-name
from numpy import pi  # noqa: F401

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10**-11

# 1 AU in meters
# serves as a conversion factor from AUs to meters
AU = 1.495978707 * 10**11

# 1 Julian year in seconds
# serves as a conversion factor from years to seconds
years = 365.25 * 24 * 60 * 60

# mass of Sun in kilograms
sun_mass = 1.98847 * 10**30

# mass of Earth in kilograms
earth_mass = 5.9722 * 10**24
# planet_mass = star_mass

# mass of satellite in kilograms
# must be negligible compared to other masses
sat_mass = 1.0

constants_names = {
    "sun_mass",
    "earth_mass",
    "sat_mass",
}
