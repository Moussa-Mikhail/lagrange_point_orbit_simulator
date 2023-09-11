"""Holds descriptor factory functions"""

from validateddescriptor import ValidatedDescriptor, value_check_factory

is_positive = value_check_factory(lambda x: x > 0, "positive")

is_non_negative = value_check_factory(lambda x: x >= 0, "non-negative")


def non_negative_int() -> ValidatedDescriptor[int]:
    return ValidatedDescriptor[int](int, [is_non_negative])


def non_negative_float() -> ValidatedDescriptor[float | int]:
    return ValidatedDescriptor[float | int](float | int, [is_non_negative])


def positive_float() -> ValidatedDescriptor[float | int]:
    return ValidatedDescriptor[float | int](float | int, [is_positive])


def bool_desc() -> ValidatedDescriptor[bool]:
    return ValidatedDescriptor[bool](bool)


def float_desc() -> ValidatedDescriptor[float | int]:
    return ValidatedDescriptor[float | int](float | int)


def optional_float_desc() -> ValidatedDescriptor[float | int | None]:
    return ValidatedDescriptor[float | int | None](float | int | None)


lagrange_labels = ("L1", "L2", "L3", "L4", "L5")

is_lagrange_label = value_check_factory(lambda x: x in lagrange_labels, f"one of {lagrange_labels}")


def lagrange_label_desc() -> ValidatedDescriptor[str]:
    return ValidatedDescriptor[str](str, [is_lagrange_label])
