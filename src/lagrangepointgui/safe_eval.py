"""Contains a function to safely evaluate input expressions."""
from src.lagrangepointgui.presets import read_presets
from src.lagrangepointsimulator.constants import CONSTANTS

ALLOWED_CHARS = set("0123456789.+-*/()e")


def safe_eval(expr: str) -> int | float | None:
    """safe eval function used on expressions that contain developer and user defined constants.
    Returns the result of the expression as a float or int. If the expression is empty, returns None.
    Raises a ValueError if the expression contains anything other than
    the constants, digits, the usual arithmetic operators, parens, or scientific notation.
    """

    if not expr:
        return None

    expr = expr.strip()

    _, user_constants = read_presets()

    all_constants = CONSTANTS | user_constants

    _validate_expr(expr, all_constants)

    try:
        res = eval(expr, all_constants)
    except (NameError, SyntaxError, ZeroDivisionError) as err:
        raise ValueError(str(err)) from err

    if not isinstance(res, int | float):
        msg = "Result is not a real number."
        raise TypeError(msg)

    return res


def _validate_expr(expr: str, constants: dict[str, float | int]) -> None:
    """Ensures that the expression only contains constants, digits,
    the usual arithmetic operators, parens, or scientific notation.
    """
    cleaned_expr = _remove_constants(expr, constants)
    chars_in_expr = set(cleaned_expr)
    if not chars_in_expr.issubset(ALLOWED_CHARS):
        msg = "invalid constant or syntax in expression."
        raise ValueError(msg)


def _remove_constants(expr: str, constants: dict[str, float | int]) -> str:
    """remove constants in the expression"""

    for constant_name in constants:
        expr = expr.replace(constant_name, "")

    return expr
