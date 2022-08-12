""""This module contains type aliases for NDArray[np.double] which are used
to distinguish between different 1 and 2 dimensional arrays."""
from numpy import double
from numpy.typing import NDArray

Array1D = NDArray[double]

Array2D = NDArray[double]
