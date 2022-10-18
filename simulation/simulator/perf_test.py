import time
from simulation import Simulator

sim = Simulator()

start = time.perf_counter()

num = 400

for _ in range(num):
    sim.simulate()

end = time.perf_counter()

print(f"Without reallocation: {(end - start)/num} seconds per simulation")

start = time.perf_counter()

for _ in range(num):

    sim._allocate_arrays()

    sim.simulate()

end = time.perf_counter()

print(f"With reallocation: {(end - start)/num} seconds per simulation")
