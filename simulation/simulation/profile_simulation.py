import pstats

import cProfile

from simulation import Simulation

sim = Simulation()

cProfile.runctx("sim.simulate()", globals(), locals(), "Profile.prof")

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("cumtime").print_stats(20)
