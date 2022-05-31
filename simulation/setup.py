# pylint: disable=missing-docstring
from setuptools import Extension, setup  # type: ignore
from Cython.Build import cythonize  # type: ignore

ext_modules = [
    Extension(
        "cython_funcs",
        ["cython_funcs.pyx"],
        extra_compile_args=["/openmp"],
        extra_link_args=["/openmp"],
    ),
]

setup(
    ext_modules=cythonize(ext_modules, language_level=3),
)
