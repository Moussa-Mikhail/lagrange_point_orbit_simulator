# pylint: disable=missing-function-docstring
"""Holds descriptor factory functions"""

from validateddescriptor import ValidatedDescriptor, value_check_factory

is_positive = value_check_factory(lambda x: x > 0, "positive")

is_non_negative = value_check_factory(lambda x: x >= 0, "non-negative")


def positive_int() -> ValidatedDescriptor[int]:

    return ValidatedDescriptor(int, [is_positive])


def non_negative_float() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor(float, [is_non_negative])


def positive_float() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor(float, [is_positive])


def bool_desc() -> ValidatedDescriptor[bool]:

    return ValidatedDescriptor(bool)


def float_desc() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor(float)


def optional_float_desc() -> ValidatedDescriptor[float | None]:
    return ValidatedDescriptor(float | None)


lagrange_labels = ("L1", "L2", "L3", "L4", "L5")


is_lagrange_label = value_check_factory(
    lambda x: x in lagrange_labels, f"one of {lagrange_labels}"
)


def lagrange_label_desc() -> ValidatedDescriptor[str]:

    return ValidatedDescriptor(str, [is_lagrange_label])
