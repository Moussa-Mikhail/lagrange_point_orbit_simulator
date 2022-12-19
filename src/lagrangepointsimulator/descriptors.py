# pylint: disable=missing-function-docstring
"""Holds descriptor factory functions"""

from validateddescriptor import ValidatedDescriptor, value_check_factory

is_positive = value_check_factory(lambda x: x > 0, "positive")

is_non_negative = value_check_factory(lambda x: x >= 0, "non-negative")


def non_negative_int():
    return ValidatedDescriptor[int](int, [is_non_negative])


def non_negative_float():
    return ValidatedDescriptor[float](float, [is_non_negative])


def positive_float():
    return ValidatedDescriptor[float](float, [is_positive])


def bool_desc():
    return ValidatedDescriptor(bool)


def float_desc():
    return ValidatedDescriptor[float](float)


def optional_float_desc():
    return ValidatedDescriptor[float | None](float | None)


lagrange_labels = ("L1", "L2", "L3", "L4", "L5")

is_lagrange_label = value_check_factory(
    lambda x: x in lagrange_labels, f"one of {lagrange_labels}"
)


def lagrange_label_desc():
    return ValidatedDescriptor[str](str, [is_lagrange_label])
