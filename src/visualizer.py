import pygame
import numpy as np


class SpectrumVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.bar_count = 64
        self.spectrum = np.zeros(self.bar_count, dtype=float)
        self.peak = np.zeros(self.bar_count, dtype=float)

        self.floor_margin = 60
        self.center_y = int(height * 0.72)

    def update(self, spectrum):
        if len(spectrum) < self.bar_count:
            return

        usable = spectrum[: max(self.bar_count * 8, self.bar_count)]
        chunks = np.array_split(usable, self.bar_count)

        new_vals = []
        for i, chunk in enumerate(chunks):
            val = float(np.mean(chunk))

            # Slight bias so lower bands feel stronger
            bias = 1.0 - (i / self.bar_count) * 0.35
            val *= bias

            # Mild non-linear boost
            val = min(1.0, val ** 0.8)
            new_vals.append(val)

        new_vals = np.array(new_vals, dtype=float)

        # Smooth attack / release
        for i in range(self.bar_count):
            target = new_vals[i]
            if target > self.spectrum[i]:
                self.spectrum[i] = self.spectrum[i] * 0.55 + target * 0.45
            else:
                self.spectrum[i] = self.spectrum[i] * 0.85 + target * 0.15

        # Peak hold with decay
        self.peak = np.maximum(self.peak * 0.97, self.spectrum)

    def draw(self, screen):
        # Center guide line
        pygame.draw.line(
            screen,
            (35, 40, 55),
            (0, self.center_y),
            (self.width, self.center_y),
            1,
        )

        half_count = self.bar_count // 2
        bar_gap = 4
        bar_width = max(4, (self.width // 2 - 120) // half_count - bar_gap)
        max_height = self.height * 0.42

        for i in range(half_count):
            val = self.spectrum[i]
            peak_val = self.peak[i]

            h = max(2, int(val * max_height))
            peak_h = max(2, int(peak_val * max_height))

            # Bars radiate outward from center
            x_right = self.width // 2 + i * (bar_width + bar_gap)
            x_left = self.width // 2 - (i + 1) * (bar_width + bar_gap)

            # Color shifts slightly with energy
            c1 = 90 + int(val * 120)
            c2 = 120 + int(val * 80)
            c3 = 255

            # Main bars
            rect_right = pygame.Rect(x_right, self.center_y - h, bar_width, h * 2)
            rect_left = pygame.Rect(x_left, self.center_y - h, bar_width, h * 2)

            pygame.draw.rect(screen, (c1, c2, c3), rect_right, border_radius=3)
            pygame.draw.rect(screen, (c1, c2, c3), rect_left, border_radius=3)

            # Inner glow strips
            glow_w = max(1, bar_width // 4)
            pygame.draw.rect(
                screen,
                (200, 220, 255),
                pygame.Rect(x_right + 1, self.center_y - h, glow_w, h * 2),
                border_radius=2,
            )
            pygame.draw.rect(
                screen,
                (200, 220, 255),
                pygame.Rect(x_left + 1, self.center_y - h, glow_w, h * 2),
                border_radius=2,
            )

            # Peak markers
            peak_y_top = self.center_y - peak_h
            peak_y_bottom = self.center_y + peak_h

            pygame.draw.line(
                screen,
                (255, 255, 255),
                (x_right, peak_y_top),
                (x_right + bar_width, peak_y_top),
                2,
            )
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (x_right, peak_y_bottom),
                (x_right + bar_width, peak_y_bottom),
                2,
            )

            pygame.draw.line(
                screen,
                (255, 255, 255),
                (x_left, peak_y_top),
                (x_left + bar_width, peak_y_top),
                2,
            )
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (x_left, peak_y_bottom),
                (x_left + bar_width, peak_y_bottom),
                2,
            )
