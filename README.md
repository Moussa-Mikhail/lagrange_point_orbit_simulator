# thesis_code
Python code which simulates orbits near Lagrange Points

## Installation
Download the repository.
If you use pip open your command line and enter "pip install -r requirements.txt". This will install all the packages these scripts depend on.

If you have problems related to to the integrate_cy module then you can simply enter "integrate=integrate_py" as an argument to main and comment out the import. This will result in a slowdown in computing the orbits. Running the main function found in testing.py is not recommended as it will take very long.

Alternatively you can install the Cython package and compile integrate_cy using the command "python setup.py build_ext --inplace".
