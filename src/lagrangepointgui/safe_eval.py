"""Contains a function to safely evaluate input expressions."""
from src.lagrangepointsimulator.constants import CONSTANTS  # noqa: F401
from src.lagrangepointgui.presets import read_presets

allowed_chars = set("0123456789.+-*/()e")


def safe_eval(expr: str) -> int | float | None:
    """safe eval function used on expressions that contain developer and user defined constants.
    Raises a ValueError if the expression contains anything other than
    the constants, digits, the usual arithmetic operators, parens, or scientific notation.
    """

    if not expr:
        return None

    _, defined_constants = read_presets()

    all_constants = CONSTANTS | defined_constants

    _validate_expr(expr, all_constants)

    try:
        res = eval(expr, all_constants)  # pylint: disable=eval-used
    except (NameError, SyntaxError, ZeroDivisionError) as err:
        raise ValueError(str(err)) from err

    if not isinstance(res, (int, float)):
        raise ValueError("Result is not a real number.")

    return res


def _validate_expr(expr: str, constants: dict[str, float | int]) -> None:
    cleaned_expr = _remove_constants(expr, constants)
    chars_in_expr = set(cleaned_expr)
    if not chars_in_expr.issubset(allowed_chars):
        raise ValueError("invalid constant or operator in expression.")


def _remove_constants(expr: str, constants: dict[str, float | int]) -> str:
    """remove constants in the expression"""

    for constant_name in constants:
        expr = expr.replace(constant_name, "")

    return expr
