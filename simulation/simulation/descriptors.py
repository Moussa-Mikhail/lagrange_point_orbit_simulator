# pylint: disable=missing-function-docstring
"""Holds descriptor factory functions"""

from validateddescriptor import ValidatedDescriptor, value_check_factory

is_positive = value_check_factory(lambda x: x > 0, "positive")

is_non_negative = value_check_factory(lambda x: x >= 0, "non-negative")


def positive_int() -> ValidatedDescriptor[int]:

    return ValidatedDescriptor([is_positive], int)


def non_negative_float() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor([is_non_negative], float)


def positive_float() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor([is_positive], float)


def bool_desc() -> ValidatedDescriptor[bool]:

    return ValidatedDescriptor(type_=bool)


def float_desc() -> ValidatedDescriptor[float]:

    return ValidatedDescriptor(type_=float)


lagrange_labels = ("L1", "L2", "L3", "L4", "L5")


is_lagrange_label = value_check_factory(
    lambda x: x in lagrange_labels, f"one of {lagrange_labels}"
)


def lagrange_label_desc() -> ValidatedDescriptor[str]:

    return ValidatedDescriptor([is_lagrange_label], str)
