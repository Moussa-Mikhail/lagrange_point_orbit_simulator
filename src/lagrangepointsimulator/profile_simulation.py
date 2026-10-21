"""Create a profile of the simulate method."""

import cProfile
import pstats

from lagrangepointsimulator.simulator import Simulator

sim = Simulator()

sim.simulate()

cProfile.runctx("sim.simulate()", globals(), locals(), "Profile.prof")

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("cumtime").print_stats(20)
