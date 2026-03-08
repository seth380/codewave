import numpy as np


def compute_wave(x):

    return np.sin(x) * np.cos(x * 0.5)


for i in range(100):

    value = compute_wave(i)

    print(value)
