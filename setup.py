# pylint: disable=missing-docstring
from distutils.core import setup
from Cython.Build import cythonize  # type: ignore
import numpy

setup(
    name="integrate_cy",
    ext_modules=cythonize("integrate_cy.pyx", language_level=3),
    include_dirs=[numpy.get_include()],
)
