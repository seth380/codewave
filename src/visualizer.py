import math
import pygame
import numpy as np


def hsv_to_rgb(h, s, v):
    h = h % 1.0
    if s == 0.0:
        c = int(v * 255)
        return (c, c, c)
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


class SpectrumVisualizer:
    # Right panel starts at this fraction of total screen width
    PANEL_FRAC = 0.36

    def __init__(self, width, height):
        self.width  = width
        self.height = height

        self.mode = "bars"

        self.bar_count = 64
        self.spectrum  = np.zeros(self.bar_count, dtype=float)
        self.peak      = np.zeros(self.bar_count, dtype=float)

        # Right panel geometry
        self.panel_x = int(width * self.PANEL_FRAC)
        self.panel_w = width - self.panel_x

        # Visualizer anchor: horizontally centred in the right panel
        self.cx       = self.panel_x + self.panel_w // 2
        self.center_y = int(height * 0.60)

        self.plasma_scale = 6
        self.plasma_w     = max(1, self.panel_w // self.plasma_scale)
        self.plasma_h     = max(1, height // self.plasma_scale)
        self.plasma_small = pygame.Surface((self.plasma_w, self.plasma_h))
        self.time         = 0.0

        self.hue_base  = 0.0
        self.hue_speed = 0.0004
        self.beat_flash = 0.0
        self.last_bass  = 0.0

        self.peak_hue   = np.zeros(self.bar_count, dtype=float)
        self.ring_angles = np.linspace(0, 2 * math.pi, self.bar_count, endpoint=False)

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
            val  = float(np.mean(chunk))
            bias = 1.0 - (i / self.bar_count) * 0.35
            val  = min(1.0, (val * bias) ** 0.8)
            new_vals.append(val)

        new_vals = np.array(new_vals, dtype=float)

        for i in range(self.bar_count):
            t = new_vals[i]
            if t > self.spectrum[i]:
                self.spectrum[i] = self.spectrum[i] * 0.78 + t * 0.22
            else:
                self.spectrum[i] = self.spectrum[i] * 0.94 + t * 0.06

        bass_now  = float(np.mean(self.spectrum[:4]))
        bass_delta = bass_now - self.last_bass
        if bass_delta > 0.08:
            self.beat_flash = min(1.0, self.beat_flash + bass_delta * 1.4)
            self.hue_speed  = 0.0012 + bass_delta * 0.014
        else:
            self.hue_speed  = max(0.0004, self.hue_speed * 0.985)
        self.beat_flash = max(0.0, self.beat_flash - 0.018)
        self.last_bass  = bass_now

        for i in range(self.bar_count):
            if self.spectrum[i] >= self.peak[i]:
                self.peak_hue[i] = self.hue_base + i / self.bar_count * 0.5
        self.peak = np.maximum(self.peak * 0.993, self.spectrum)

        self.hue_base = (self.hue_base + self.hue_speed + bass_now * 0.0008) % 1.0
        self.time    += 0.006 + bass_now * 0.012

    # ------------------------------------------------------------------ #
    #  BARS — drawn only in the right panel
    # ------------------------------------------------------------------ #
    def draw_bars(self, screen):
        bass   = float(np.mean(self.spectrum[:6]))
        mids   = float(np.mean(self.spectrum[6:20]))
        highs  = float(np.mean(self.spectrum[20:40]))
        energy = bass * 0.5 + mids * 0.35 + highs * 0.15

        # Beat flash — right panel only
        if self.beat_flash > 0.01:
            flash_col  = hsv_to_rgb(self.hue_base + 0.05, 0.7, self.beat_flash * 0.28)
            flash_surf = pygame.Surface((self.panel_w, self.height), pygame.SRCALPHA)
            flash_surf.fill((*flash_col, int(self.beat_flash * 55)))
            screen.blit(flash_surf, (self.panel_x, 0))

        # Baseline
        pygame.draw.line(screen, (35, 40, 55),
                         (self.panel_x, self.center_y), (self.width, self.center_y), 1)

        half_count = self.bar_count // 2
        bar_gap    = 4
        bar_width  = max(4, (self.panel_w // 2 - 60) // half_count - bar_gap)
        max_height = self.height * 0.42

        for i in range(half_count):
            val      = self.spectrum[i]
            peak_val = self.peak[i]

            h      = max(2, int(val      * max_height))
            peak_h = max(2, int(peak_val * max_height))

            # Bars spread left/right from the right-panel centre
            x_right = self.cx + i * (bar_width + bar_gap)
            x_left  = self.cx - (i + 1) * (bar_width + bar_gap)

            hue_pos = (i / half_count) * 0.72
            shimmer = math.sin(self.time * 0.5 + i * 0.18) * 0.03
            hue     = (self.hue_base + hue_pos + shimmer) % 1.0
            sat     = 0.72 + val * 0.28
            bri     = 0.30 + val * 0.70
            bar_col = hsv_to_rgb(hue, sat, bri)

            tip_col = hsv_to_rgb((hue + 0.08 + val * 0.12) % 1.0, 0.55, 1.0)

            for x in (x_right, x_left):
                pygame.draw.rect(screen, bar_col,
                                 pygame.Rect(x, self.center_y - h, bar_width, h * 2),
                                 border_radius=3)
                gw = max(1, bar_width // 4)
                pygame.draw.rect(screen, tip_col,
                                 pygame.Rect(x + 1, self.center_y - h, gw, h * 2),
                                 border_radius=2)

                if energy > 0.35:
                    ab_off  = int(energy * 4)
                    ab_col  = hsv_to_rgb((hue + 0.33) % 1.0, 1.0, 0.9)
                    ab_surf = pygame.Surface((gw, h * 2), pygame.SRCALPHA)
                    ab_surf.fill((*ab_col, int(energy * 55)))
                    screen.blit(ab_surf, (x + 1 + ab_off, self.center_y - h))

                p_col = hsv_to_rgb(self.peak_hue[i] % 1.0, 0.85, 1.0)
                pygame.draw.line(screen, p_col,
                                 (x, self.center_y - peak_h), (x + bar_width, self.center_y - peak_h), 2)
                pygame.draw.line(screen, p_col,
                                 (x, self.center_y + peak_h), (x + bar_width, self.center_y + peak_h), 2)

        self._draw_waveform_ring(screen, bass, mids, highs)

    def _draw_waveform_ring(self, screen, bass, mids, highs):
        base_r = 88 + int(bass * 30)

        pts_outer, pts_inner = [], []
        for i in range(self.bar_count):
            angle = self.ring_angles[i] - math.pi / 2
            val   = self.spectrum[i]
            spoke = val * (22 + bass * 28)
            pts_outer.append((self.cx + math.cos(angle) * (base_r + spoke),
                               self.center_y + math.sin(angle) * (base_r + spoke)))
            pts_inner.append((self.cx + math.cos(angle) * (base_r - spoke * 0.4),
                               self.center_y + math.sin(angle) * (base_r - spoke * 0.4)))

        n = self.bar_count
        for i in range(n):
            a, b  = pts_outer[i], pts_outer[(i + 1) % n]
            hue   = (self.hue_base + i / n * 0.8) % 1.0
            col   = hsv_to_rgb(hue, 0.9, 0.9 + self.spectrum[i] * 0.1)
            pygame.draw.line(screen, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 2)

        for i in range(n):
            a, b  = pts_inner[i], pts_inner[(i + 1) % n]
            hue   = (self.hue_base + 0.5 + i / n * 0.8) % 1.0
            col   = hsv_to_rgb(hue, 0.7, 0.5)
            pygame.draw.line(screen, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1)

    # ------------------------------------------------------------------ #
    #  PLASMA — right panel only
    # ------------------------------------------------------------------ #
    def draw_plasma(self, screen):
        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))

        if self.beat_flash > 0.01:
            flash_col  = hsv_to_rgb(self.hue_base, 0.8, self.beat_flash * 0.35)
            flash_surf = pygame.Surface((self.panel_w, self.height), pygame.SRCALPHA)
            flash_surf.fill((*flash_col, int(self.beat_flash * 70)))
            screen.blit(flash_surf, (self.panel_x, 0))

        px = pygame.PixelArray(self.plasma_small)

        for y in range(self.plasma_h):
            for x in range(self.plasma_w):
                v  = math.sin(x * 0.18 + self.time * (0.30 + bass  * 0.80))
                v += math.sin(y * 0.22 + self.time * (0.22 + mids  * 0.55))
                v += math.sin((x + y) * 0.12 + self.time * (0.26 + highs * 0.80))
                v += math.sin((x - y) * 0.09 + self.time * (0.18 + bass  * 0.55))

                cx = x - self.plasma_w / 2
                cy = y - self.plasma_h / 2
                v += math.sin(math.sqrt(cx*cx + cy*cy) * 0.24 - self.time * (0.40 + bass * 0.90))

                cx2 = x - self.plasma_w * (0.3 + 0.2 * math.sin(self.time * 0.07))
                cy2 = y - self.plasma_h * (0.6 + 0.15 * math.cos(self.time * 0.055))
                v += math.sin(math.sqrt(cx2*cx2 + cy2*cy2) * 0.20
                              - self.time * (0.28 + mids * 0.60)) * 0.7

                v   = v / 5.5
                hue = (self.hue_base + (v + 1.0) * 0.45) % 1.0
                sat = 0.80 + highs * 0.20
                bri = min(1.0, 0.25 + (v + 1.0) * 0.375 + bass * 0.18)

                r, g, b = hsv_to_rgb(hue, sat, bri)
                if y % 2 == 0:
                    r, g, b = max(0, r - 18), max(0, g - 18), max(0, b - 18)
                px[x, y] = (r, g, b)

        del px

        plasma = pygame.transform.smoothscale(self.plasma_small, (self.panel_w, self.height))
        plasma.set_alpha(165)
        screen.blit(plasma, (self.panel_x, 0))

        for r_off, hue_off, alpha, lw in [(0, 0.00, 220, 2), (28, 0.25, 110, 1),
                                           (56, 0.50, 55,  1), (-18, 0.75, 80, 1)]:
            ring_r = 120 + int(bass * 40) + r_off
            hue    = (self.hue_base + hue_off + self.time * 0.008) % 1.0
            col    = hsv_to_rgb(hue, 0.85, 1.0)
            rs     = pygame.Surface((self.panel_w, self.height), pygame.SRCALPHA)
            # Ring centre is cx relative to panel surface
            pygame.draw.circle(rs, (*col, alpha),
                                (self.cx - self.panel_x, self.center_y), ring_r, lw)
            screen.blit(rs, (self.panel_x, 0))

        self._draw_waveform_ring(screen, bass, mids, float(np.mean(self.spectrum[20:40])))

    def draw(self, screen):
        if self.mode == "plasma":
            self.draw_plasma(screen)
        else:
            self.draw_bars(screen)
