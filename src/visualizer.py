import math
import pygame
import numpy as np


def hsv_to_rgb(h, s, v):
    """Convert HSV (0-1 each) to RGB (0-255 each)."""
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
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.mode = "bars"

        self.bar_count = 64
        self.spectrum = np.zeros(self.bar_count, dtype=float)
        self.peak = np.zeros(self.bar_count, dtype=float)

        self.floor_margin = 60
        self.center_y = int(height * 0.78)

        self.plasma_surface = pygame.Surface((width, height))
        self.plasma_scale = 6
        self.plasma_w = max(1, width // self.plasma_scale)
        self.plasma_h = max(1, height // self.plasma_scale)
        self.plasma_small = pygame.Surface((self.plasma_w, self.plasma_h))
        self.time = 0.0

        # Hue rotation state — bars and plasma have independent hue cycles
        self.hue_base = 0.0          # slowly drifts over time
        self.hue_speed = 0.0004      # base drift speed
        self.beat_flash = 0.0        # 0-1 flash intensity on bass hit
        self.last_bass = 0.0

        # Per-bar peak hue snapshot for colorful peak lines
        self.peak_hue = np.zeros(self.bar_count, dtype=float)

        # Waveform ring state
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
            val = float(np.mean(chunk))
            bias = 1.0 - (i / self.bar_count) * 0.35
            val *= bias
            val = min(1.0, val ** 0.8)
            new_vals.append(val)

        new_vals = np.array(new_vals, dtype=float)

        for i in range(self.bar_count):
            target = new_vals[i]
            if target > self.spectrum[i]:
                self.spectrum[i] = self.spectrum[i] * 0.78 + target * 0.22
            else:
                self.spectrum[i] = self.spectrum[i] * 0.94 + target * 0.06

        # Beat detection: sharp bass transient triggers flash + hue spike
        bass_now = float(np.mean(self.spectrum[:4]))
        bass_delta = bass_now - self.last_bass
        if bass_delta > 0.08:
            self.beat_flash = min(1.0, self.beat_flash + bass_delta * 1.4)
            self.hue_speed = 0.0012 + bass_delta * 0.014   # gentle tempo-surge
        else:
            self.hue_speed = max(0.0004, self.hue_speed * 0.985)
        self.beat_flash = max(0.0, self.beat_flash - 0.018)  # slow fade
        self.last_bass = bass_now

        # Update peak and snapshot hue when bar hits new peak
        for i in range(self.bar_count):
            if self.spectrum[i] >= self.peak[i]:
                self.peak_hue[i] = self.hue_base + i / self.bar_count * 0.5
        self.peak = np.maximum(self.peak * 0.993, self.spectrum)

        self.hue_base += self.hue_speed + bass_now * 0.0008
        self.time += 0.02 + bass_now * 0.08

    # ------------------------------------------------------------------ #
    #  BARS
    # ------------------------------------------------------------------ #
    def draw_bars(self, screen):
        bass = float(np.mean(self.spectrum[:6]))
        mids = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))
        energy = bass * 0.5 + mids * 0.35 + highs * 0.15

        # Subtle beat flash bloom on the background
        if self.beat_flash > 0.01:
            flash_col = hsv_to_rgb(self.hue_base + 0.05, 0.7, self.beat_flash * 0.28)
            flash_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash_surf.fill((*flash_col, int(self.beat_flash * 55)))
            screen.blit(flash_surf, (0, 0))

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
            x_left  = self.width // 2 - (i + 1) * (bar_width + bar_gap)

            # Each bar gets a hue offset: rainbow sweep across the spectrum
            # plus global hue drift and a shimmer wave
            hue_pos  = (i / half_count) * 0.72
            shimmer  = math.sin(self.time * 0.5 + i * 0.18) * 0.03
            hue      = (self.hue_base + hue_pos + shimmer) % 1.0
            sat      = 0.72 + val * 0.28
            bri      = 0.30 + val * 0.70

            bar_col  = hsv_to_rgb(hue, sat, bri)

            # Brighter tip
            tip_hue  = (hue + 0.08 + val * 0.12) % 1.0
            tip_col  = hsv_to_rgb(tip_hue, 0.55, 1.0)

            # Core bar
            rect_r = pygame.Rect(x_right, self.center_y - h, bar_width, h * 2)
            rect_l = pygame.Rect(x_left,  self.center_y - h, bar_width, h * 2)
            pygame.draw.rect(screen, bar_col, rect_r, border_radius=3)
            pygame.draw.rect(screen, bar_col, rect_l, border_radius=3)

            # Bright inner edge (glow stripe)
            glow_w = max(1, bar_width // 4)
            pygame.draw.rect(screen, tip_col,
                pygame.Rect(x_right + 1, self.center_y - h, glow_w, h * 2), border_radius=2)
            pygame.draw.rect(screen, tip_col,
                pygame.Rect(x_left  + 1, self.center_y - h, glow_w, h * 2), border_radius=2)

            # Chromatic aberration on heavy energy: offset R channel slightly
            if energy > 0.35:
                ab_offset = int(energy * 4)
                ab_col = hsv_to_rgb((hue + 0.33) % 1.0, 1.0, 0.9)
                ab_surf = pygame.Surface((glow_w, h * 2), pygame.SRCALPHA)
                ab_surf.fill((*ab_col, int(energy * 55)))
                screen.blit(ab_surf, (x_right + 1 + ab_offset, self.center_y - h))
                screen.blit(ab_surf, (x_left  + 1 - ab_offset, self.center_y - h))

            # Peak dots — use snapshotted hue for persistent rainbow trail
            p_hue = self.peak_hue[i] % 1.0
            p_col = hsv_to_rgb(p_hue, 0.85, 1.0)
            pygame.draw.line(screen, p_col,
                (x_right, self.center_y - peak_h), (x_right + bar_width, self.center_y - peak_h), 2)
            pygame.draw.line(screen, p_col,
                (x_right, self.center_y + peak_h), (x_right + bar_width, self.center_y + peak_h), 2)
            pygame.draw.line(screen, p_col,
                (x_left,  self.center_y - peak_h), (x_left  + bar_width, self.center_y - peak_h), 2)
            pygame.draw.line(screen, p_col,
                (x_left,  self.center_y + peak_h), (x_left  + bar_width, self.center_y + peak_h), 2)

        # Circular waveform ring in center — radius pulses with bass
        self._draw_waveform_ring(screen, bass, mids, highs)

    def _draw_waveform_ring(self, screen, bass, mids, highs):
        cx = self.width // 2
        cy = self.center_y
        base_r = 88 + int(bass * 30)
        spoke_count = self.bar_count

        pts_outer = []
        pts_inner = []

        for i in range(spoke_count):
            angle = self.ring_angles[i] - math.pi / 2
            val = self.spectrum[i % self.bar_count]
            spoke = val * (22 + bass * 28)

            r_out = base_r + spoke
            r_in  = base_r - spoke * 0.4

            pts_outer.append((
                cx + math.cos(angle) * r_out,
                cy + math.sin(angle) * r_out,
            ))
            pts_inner.append((
                cx + math.cos(angle) * r_in,
                cy + math.sin(angle) * r_in,
            ))

        # Draw outer ring segments with per-segment hue
        for i in range(spoke_count):
            a = pts_outer[i]
            b = pts_outer[(i + 1) % spoke_count]
            hue = (self.hue_base + i / spoke_count * 0.8) % 1.0
            col = hsv_to_rgb(hue, 0.9, 0.9 + self.spectrum[i] * 0.1)
            pygame.draw.line(screen, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 2)

        # Draw inner ring (dimmer, offset hue)
        for i in range(spoke_count):
            a = pts_inner[i]
            b = pts_inner[(i + 1) % spoke_count]
            hue = (self.hue_base + 0.5 + i / spoke_count * 0.8) % 1.0
            col = hsv_to_rgb(hue, 0.7, 0.5)
            pygame.draw.line(screen, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1)

    # ------------------------------------------------------------------ #
    #  PLASMA
    # ------------------------------------------------------------------ #
    def draw_plasma(self, screen):
        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))

        # Beat flash in plasma too
        if self.beat_flash > 0.01:
            flash_col = hsv_to_rgb(self.hue_base, 0.8, self.beat_flash * 0.35)
            flash_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash_surf.fill((*flash_col, int(self.beat_flash * 70)))
            screen.blit(flash_surf, (0, 0))

        px = pygame.PixelArray(self.plasma_small)

        for y in range(self.plasma_h):
            for x in range(self.plasma_w):
                nx = x / max(1, self.plasma_w)
                ny = y / max(1, self.plasma_h)

                # Richer field: 5 interfering waves instead of 4
                v  = math.sin((x * 0.18) + self.time * (0.30 + bass * 0.80))
                v += math.sin((y * 0.22) + self.time * (0.22 + mids * 0.55))
                v += math.sin((x + y) * 0.12 + self.time * (0.26 + highs * 0.80))
                v += math.sin((x - y) * 0.09 + self.time * (0.18 + bass * 0.55))

                cx = x - self.plasma_w / 2
                cy_f = y - self.plasma_h / 2
                dist = math.sqrt(cx * cx + cy_f * cy_f)
                v += math.sin(dist * 0.24 - self.time * (0.40 + bass * 0.90))

                # Second drifting ripple centre
                cx2 = x - self.plasma_w * (0.3 + 0.2 * math.sin(self.time * 0.07))
                cy2 = y - self.plasma_h * (0.6 + 0.15 * math.cos(self.time * 0.055))
                dist2 = math.sqrt(cx2 * cx2 + cy2 * cy2)
                v += math.sin(dist2 * 0.20 - self.time * (0.28 + mids * 0.60)) * 0.7

                v = v / 5.5  # normalise ~[-1, 1]

                # Map v → hue with global drift
                hue = (self.hue_base + (v + 1.0) * 0.45) % 1.0
                sat = 0.80 + highs * 0.20
                bri_base = (v + 1.0) * 0.5
                bri = 0.25 + bri_base * 0.75 + bass * 0.18

                r, g, b = hsv_to_rgb(hue, sat, min(1.0, bri))

                # Subtle scanline darkening every other row for depth
                if y % 2 == 0:
                    r = max(0, r - 18)
                    g = max(0, g - 18)
                    b = max(0, b - 18)

                px[x, y] = (r, g, b)

        del px

        plasma = pygame.transform.smoothscale(self.plasma_small, (self.width, self.height))
        plasma.set_alpha(165)
        screen.blit(plasma, (0, 0))

        # Multiple reactive rings with hue offsets
        cx = self.width // 2
        cy = self.center_y

        for ring_i, (r_offset, hue_off, alpha, width) in enumerate([
            (0,   0.00, 220, 2),
            (28,  0.25, 110, 1),
            (56,  0.50, 55,  1),
            (-18, 0.75, 80,  1),
        ]):
            ring_r = 120 + int(bass * 40) + r_offset
            hue = (self.hue_base + hue_off + self.time * 0.008) % 1.0
            col = hsv_to_rgb(hue, 0.85, 1.0)
            ring_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*col, alpha), (cx, cy), ring_r, width)
            screen.blit(ring_surf, (0, 0))

        # Waveform ring in plasma mode too
        self._draw_waveform_ring(screen, bass, mids, float(np.mean(self.spectrum[20:40])))

    def draw(self, screen):
        if self.mode == "plasma":
            self.draw_plasma(screen)
        else:
            self.draw_bars(screen)
