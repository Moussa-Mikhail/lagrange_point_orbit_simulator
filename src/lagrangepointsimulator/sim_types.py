"""This module contains type aliases for NDArray[np.double] which are used
to distinguish between 1 and 2-dimensional arrays."""
from typing import TypeAlias

from numpy import double
from numpy.typing import NDArray

Array1D: TypeAlias = NDArray[double]  # pylint: disable=invalid-name

Array2D: TypeAlias = NDArray[double]  # pylint: disable=invalid-name
