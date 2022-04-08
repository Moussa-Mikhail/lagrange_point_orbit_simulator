# pylint: disable=missing-docstring
from distutils.core import setup
from Cython.Build import cythonize  # type: ignore
import numpy

setup(
    name="cy_code",
    ext_modules=cythonize("cy_code.pyx", language_level=3),
    include_dirs=[numpy.get_include()],
)
