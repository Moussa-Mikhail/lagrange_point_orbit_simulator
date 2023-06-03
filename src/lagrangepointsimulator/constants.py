# pylint: disable=invalid-name, missing-docstring

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10**-11

# 1 AU in meters
AU = 1.495978707 * 10**11

HOURS = 60 * 60

YEARS = 365.25 * 24 * HOURS

# Masses in kilograms
SUN_MASS: float = 1.98847 * 10**30

EARTH_MASS = 5.9722 * 10**24

MOON_MASS = 7.34767309 * 10**22

JUPITER_MASS: float = 1.89813 * 10**27

# Distances in Astronomical Units
SUN_EARTH_DIST = 0.9954

SUN_JUPITER_DIST = 4.953

EARTH_MOON_DIST = 0.002617

CONSTANTS: dict[str, float | int] = {
    "G": G,
    "AU": AU,
    "years": YEARS,
    "hours": HOURS,
    "sun_mass": SUN_MASS,
    "earth_mass": EARTH_MASS,
    "moon_mass": MOON_MASS,
    "jupiter_mass": JUPITER_MASS,
    "sun_earth_dist": SUN_EARTH_DIST,
    "sun_jupiter_dist": SUN_JUPITER_DIST,
    "earth_moon_dist": EARTH_MOON_DIST,
}
