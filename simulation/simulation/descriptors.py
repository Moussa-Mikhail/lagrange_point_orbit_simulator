# pylint: disable=attribute-defined-outside-init, missing-docstring
from numbers import Real
from typing import Any

from validateddescriptor import (
    ValidatedDescriptor,
    is_bool,
    is_integer,
    is_non_negative,
    is_positive,
    is_string,
    type_check_factory,
)


def numsteps():

    return ValidatedDescriptor([is_integer, is_positive])


def mass():

    return ValidatedDescriptor([is_non_negative])


def distance():

    return ValidatedDescriptor([is_positive])


def bool_desc():

    return ValidatedDescriptor([is_bool])


is_real = type_check_factory(Real)


def real():

    return ValidatedDescriptor([is_real])


def is_lagrange_label(descriptor: ValidatedDescriptor, value: Any) -> None:

    lagrange_labels = ["L1", "L2", "L3", "L4", "L5"]

    if value not in lagrange_labels:
        raise ValueError(f"{descriptor.public_name} must be one of {lagrange_labels}")


def lagrange_label():

    return ValidatedDescriptor([is_string, is_lagrange_label])
