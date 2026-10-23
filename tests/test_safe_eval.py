import pytest

from lagrangepointsimulator.constants import SUN_MASS
from lagrangepointsimulator.safe_eval import safe_eval


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("1+2*3", 7),
        ("(1+2)*3", 9),
        ("2.5e3", 2500.0),
        ("-4/8", -0.5),
        (" 7 ", 7),
        ("sun_mass/2", SUN_MASS / 2),
    ],
)
def test_evaluates_arithmetic_and_constants(expr: str, expected: float) -> None:
    assert safe_eval(expr) == pytest.approx(expected)


def test_empty_expression_is_none() -> None:
    assert safe_eval("") is None


@pytest.mark.parametrize(
    "expr",
    ["__import__('os')", "abc", "1+a", "open('x')", "1;2", "[1]", "1/0", "(1"],
)
def test_rejects_anything_but_arithmetic(expr: str) -> None:
    with pytest.raises(ValueError):
        safe_eval(expr)
