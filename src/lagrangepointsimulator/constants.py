# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10**-11

HOURS = 60 * 60

YEARS = 365.25 * 24 * HOURS

# Masses in kilograms
SUN_MASS: float = 1.98847 * 10**30

EARTH_MASS = 5.9722 * 10**24

# 1 AU in meters
AU = 1.495978707 * 10**11

CONSTANTS: dict[str, float | int] = {
    "G": G,
    "AU": AU,
    "years": YEARS,
    "hours": HOURS,
    "sun_mass": SUN_MASS,
    "earth_mass": EARTH_MASS,
}
