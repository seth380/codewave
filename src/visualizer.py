import math
import pygame
import numpy as np


class SpectrumVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.mode = "bars"   # "bars" or "plasma"

        self.bar_count = 64
        self.spectrum = np.zeros(self.bar_count, dtype=float)
        self.peak = np.zeros(self.bar_count, dtype=float)

        self.floor_margin = 60
        self.center_y = int(height * 0.78)

        self.plasma_surface = pygame.Surface((width, height))
        self.plasma_scale = 8
        self.plasma_w = max(1, width // self.plasma_scale)
        self.plasma_h = max(1, height // self.plasma_scale)
        self.plasma_small = pygame.Surface((self.plasma_w, self.plasma_h))
        self.time = 0.0

    def set_mode(self, mode):
        if mode in ("bars", "plasma"):
            self.mode = mode

    def toggle_mode(self):
        self.mode = "plasma" if self.mode == "bars" else "bars"

    def update(self, spectrum):
        if len(spectrum) < self.bar_count:
            return

        usable = spectrum[: max(self.bar_count * 8, self.bar_count)]
        chunks = np.array_split(usable, self.bar_count)

        new_vals = []
        for i, chunk in enumerate(chunks):
            val = float(np.mean(chunk))
            bias = 1.0 - (i / self.bar_count) * 0.35
            val *= bias
            val = min(1.0, val ** 0.8)
            new_vals.append(val)

        new_vals = np.array(new_vals, dtype=float)

        for i in range(self.bar_count):
            target = new_vals[i]
            if target > self.spectrum[i]:
                self.spectrum[i] = self.spectrum[i] * 0.55 + target * 0.45
            else:
                self.spectrum[i] = self.spectrum[i] * 0.85 + target * 0.15

        self.peak = np.maximum(self.peak * 0.97, self.spectrum)
        self.time += 0.03 + float(np.mean(self.spectrum[:8])) * 0.08

    def draw(self, screen):
        if self.mode == "plasma":
            self.draw_plasma(screen)
        else:
            self.draw_bars(screen)

    def draw_bars(self, screen):
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

            x_right = self.width // 2 + i * (bar_width + bar_gap)
            x_left = self.width // 2 - (i + 1) * (bar_width + bar_gap)

            c1 = 90 + int(val * 120)
            c2 = 120 + int(val * 80)
            c3 = 255

            rect_right = pygame.Rect(x_right, self.center_y - h, bar_width, h * 2)
            rect_left = pygame.Rect(x_left, self.center_y - h, bar_width, h * 2)

            pygame.draw.rect(screen, (c1, c2, c3), rect_right, border_radius=3)
            pygame.draw.rect(screen, (c1, c2, c3), rect_left, border_radius=3)

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

            peak_y_top = self.center_y - peak_h
            peak_y_bottom = self.center_y + peak_h

            pygame.draw.line(screen, (255, 255, 255), (x_right, peak_y_top), (x_right + bar_width, peak_y_top), 2)
            pygame.draw.line(screen, (255, 255, 255), (x_right, peak_y_bottom), (x_right + bar_width, peak_y_bottom), 2)
            pygame.draw.line(screen, (255, 255, 255), (x_left, peak_y_top), (x_left + bar_width, peak_y_top), 2)
            pygame.draw.line(screen, (255, 255, 255), (x_left, peak_y_bottom), (x_left + bar_width, peak_y_bottom), 2)

    def draw_plasma(self, screen):
        bass = float(np.mean(self.spectrum[:6]))
        mids = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))

        px = pygame.PixelArray(self.plasma_small)

        for y in range(self.plasma_h):
            ny = y / max(1, self.plasma_h)
            for x in range(self.plasma_w):
                nx = x / max(1, self.plasma_w)

                v = 0.0
                v += math.sin((x * 0.18) + self.time * (1.6 + bass * 4.0))
                v += math.sin((y * 0.22) + self.time * (1.1 + mids * 3.0))
                v += math.sin((x + y) * 0.12 + self.time * (1.4 + highs * 4.5))

                cx = x - self.plasma_w / 2
                cy = y - self.plasma_h / 2
                dist = math.sqrt(cx * cx + cy * cy)
                v += math.sin(dist * 0.24 - self.time * (2.2 + bass * 5.0))

                v = v * 0.25
                glow = (v + 1.0) * 0.5

                r = int(40 + glow * 160 + bass * 120)
                g = int(60 + glow * 180 + mids * 110)
                b = int(120 + glow * 220 + highs * 140)

                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))

                px[x, y] = (r, g, b)

        del px

        plasma = pygame.transform.smoothscale(self.plasma_small, (self.width, self.height))
        plasma.set_alpha(150)
        screen.blit(plasma, (0, 0))

        ring_r = 120 + int(bass * 90)
        pygame.draw.circle(screen, (180, 210, 255), (self.width // 2, self.center_y), ring_r, 1)
        pygame.draw.circle(screen, (80, 110, 170), (self.width // 2, self.center_y), ring_r + 30, 1)
