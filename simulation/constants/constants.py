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

CONSTANT_NAMES = {
    "SUN_MASS",
    "EARTH_MASS",
}


def safe_eval(expr: str) -> int | float:
    """safe eval function used on expressions that contain the above constants.
    Raises a ValueError if the expression contains anything other than
    the above constants, digits, operators, parens, or scientific notation.
    """

    expr = expr.upper()

    exprNoConstants = expr

    for constant in CONSTANT_NAMES:

        exprNoConstants = exprNoConstants.replace(constant, "")

    chars = set(exprNoConstants)

    if not chars.issubset("0123456789.+-*/()[]{}e"):

        raise ValueError(f"{expr} is an invalid expression")

    try:

        res = eval(expr)  # pylint: disable=eval-used

    except NameError as e:

        raise ValueError(f"{expr} is an invalid expression") from e

    if not isinstance(res, (int, float)):

        raise ValueError(f"{expr} is an invalid expression")

    return res
