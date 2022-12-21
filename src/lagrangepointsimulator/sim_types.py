"""This module contains type aliases for NDArray[np.double] which are used
to distinguish between 1 and 2 dimensional arrays."""
# TODO: move this to simulator.py and annotate.
from numpy import double
from numpy.typing import NDArray

Array1D = NDArray[double]

Array2D = NDArray[double]
