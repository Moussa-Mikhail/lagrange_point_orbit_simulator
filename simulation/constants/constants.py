# pylint: disable=invalid-name, missing-docstring

# universal gravitational constant in meters^3*1/kilograms*1/seconds^2
G = 6.67430 * 10**-11

# 1 AU in meters
# serves as a conversion factor from AUs to meters
AU = 1.495978707 * 10**11

# 1 Julian year in seconds
# serves as a conversion factor from years to seconds
years = 365.25 * 24 * 60 * 60

# mass of Sun in kilograms
sun_mass: float = 1.98847 * 10**30

# mass of Earth in kilograms
earth_mass = 5.9722 * 10**24

# mass of satellite in kilograms
# must be negligible compared to other masses
sat_mass = 1.0

constants_names = {
    "sun_mass",
    "earth_mass",
    "sat_mass",
}


def safe_eval(expr: str) -> int | float:
    """safe eval function used on expressions that contain the above constants"""

    exprNoConstants = expr

    for constant in constants_names:

        exprNoConstants = exprNoConstants.replace(constant, "")

    chars = set(exprNoConstants)

    if not chars.issubset("0123456789.+-*/()e"):

        raise ValueError(f"{expr} is an invalid expression")

    return eval(expr)  # pylint: disable=eval-used
