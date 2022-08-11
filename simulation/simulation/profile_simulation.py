import pstats

import cProfile

import simulation

_ = simulation.simulate()

cProfile.runctx("simulation.main()", globals(), locals(), "Profile.prof")

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("cumtime").print_stats(20)
