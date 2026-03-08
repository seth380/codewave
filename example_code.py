import math
import time
import numpy as np


class PlasmaField:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.phase = 0.0

    def sample(self, x: float, y: float) -> float:
        a = math.sin(x * 0.018 + self.phase)
        b = math.sin(y * 0.022 + self.phase * 1.3)
        c = math.sin((x + y) * 0.014 + self.phase * 0.7)
        d = math.sin(math.sqrt(x * x + y * y) * 0.028 - self.phase * 1.1)
        return (a + b + c + d) * 0.25

    def update(self, dt: float, energy: float) -> None:
        self.phase += dt * (0.9 + energy * 2.2)


def normalize(values: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(values)) + 1e-6
    return values / peak


def render_frame(field: PlasmaField, t: float, bass: float) -> float:
    field.update(1 / 60, bass)
    value = field.sample(320 + math.sin(t) * 40, 180 + math.cos(t * 0.8) * 30)
    return float(value)


if __name__ == "__main__":
    field = PlasmaField(640, 360)

    for i in range(120):
        t = i / 60.0
        bass = 0.5 + math.sin(t * 2.0) * 0.5
        print(render_frame(field, t, bass))
        time.sleep(1 / 60)
