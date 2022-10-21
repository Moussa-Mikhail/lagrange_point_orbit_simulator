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

allowed_chars = set("0123456789.+-*/()[]{}")


def safe_eval(expr: str) -> int | float:
    """safe eval function used on expressions that contain the above constants.
    Raises a ValueError if the expression contains anything other than
    the above constants, digits, operators, parens, or scientific notation.
    """

    expr_translated = translate_input(expr)

    expr_no_constants = remove_constants(expr_translated)

    chars_in_expr = set(expr_no_constants)

    if not chars_in_expr.issubset(allowed_chars):

        not_allowed = chars_in_expr.difference(allowed_chars)

        raise ValueError(f"{not_allowed} are not allowed.")

    try:

        res = eval(expr_translated)  # pylint: disable=eval-used

    except (NameError, SyntaxError, ZeroDivisionError) as e:

        raise ValueError(str(e)) from e

    if not isinstance(res, (int, float)):

        raise ValueError("Result is not a number.")

    return res


def translate_input(expr: str) -> str:
    """Translates constant names in user input from lowercase to uppercase."""

    expr_translated = expr

    for constant in CONSTANT_NAMES:

        expr_translated = expr_translated.replace(constant.lower(), constant)

    return expr_translated


def remove_constants(expr: str) -> str:

    """Removes constants from an expression."""

    expr_no_constants = expr

    for constant in CONSTANT_NAMES:

        expr_no_constants = expr_no_constants.replace(constant, "")

    return expr_no_constants
