# pylint: disable=missing-docstring
from distutils.core import setup  # type: ignore
from Cython.Build import cythonize  # type: ignore

setup(
    name="integrate_cy",
    ext_modules=cythonize(["integrate_cy.pyx", "transform_cy.pyx"], language_level=3),
)
