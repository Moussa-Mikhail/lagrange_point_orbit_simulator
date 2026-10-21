"""Module which contains common type annotations"""

from numpy import double
from numpy.typing import NDArray

type Array1D = NDArray[double]

type Array2D = NDArray[double]

type Vec3 = tuple[float, float, float]
