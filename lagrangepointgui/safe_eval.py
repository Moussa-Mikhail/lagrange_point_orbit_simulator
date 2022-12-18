"""Contains a function to safely evaluate input expressions."""
from lagrangepointsimulator.constants import CONSTANTS  # noqa: F401

allowed_chars = set("0123456789.+-*/()")


def safe_eval(expr: str) -> int | float | None:
    """safe eval function used on expressions that contain the above constants.
    Raises a ValueError if the expression contains anything other than
    the above constants, digits, operators, parens, or scientific notation.
    """

    if not expr:
        return None

    cleaned_expr = remove_constants(expr)

    chars_in_expr = set(cleaned_expr)

    if not chars_in_expr.issubset(allowed_chars):
        raise ValueError("invalid name or operator in expression.")

    try:
        translated_expr = translate(expr)

        # codiga-disable
        res = eval(translated_expr, CONSTANTS)  # pylint: disable=eval-used

    except (NameError, SyntaxError, ZeroDivisionError) as err:

        raise ValueError(str(err)) from err

    if not isinstance(res, (int, float)):
        raise ValueError("Result is not a number.")

    return res


def translate(expr: str) -> str:
    """translate constants in the expression to uppercase"""

    for constant_name in CONSTANTS:
        expr = expr.replace(constant_name.lower(), constant_name)

    return expr


def remove_constants(expr: str) -> str:
    """remove constants in the expression"""

    for constant_name in CONSTANTS:
        expr = expr.replace(constant_name.lower(), "")

    return expr
