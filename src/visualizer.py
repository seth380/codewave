"""
visualizer.py  —  CodeWave visualizer
Three layers rendered together every frame:
  1. Plasma background (right panel, lava-lamp speed)
  2. Spectrum bars  (radiate outward from sphere centre)
  3. 3-D wireframe ellipsoid (spins, breathes, colour-shifts with music)
"""

import math
import pygame
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
#  Colour helpers
# ──────────────────────────────────────────────────────────────────────────────
def hsv_to_rgb(h, s, v):
    h = h % 1.0
    if s == 0.0:
        c = int(v * 255); return (c, c, c)
    i = int(h * 6); f = (h * 6) - i
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    i %= 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


# ──────────────────────────────────────────────────────────────────────────────
#  3-D wireframe sphere  (pure numpy, no OpenGL)
# ──────────────────────────────────────────────────────────────────────────────
class WireSphere:
    """
    Latitudes × longitudes vertex grid projected with a simple perspective
    camera.  Vertices are displaced outward by spectrum bins so the mesh
    'breathes' with the music.
    """
    LAT  = 18   # latitude rings  (north→south)
    LON  = 36   # longitude spokes (east→west)

    def __init__(self, cx, cy, base_r=110):
        self.cx     = cx
        self.cy     = cy
        self.base_r = base_r
        self.rot_x  = 0.0   # current rotation angles (radians)
        self.rot_y  = 0.0
        self.rot_z  = 0.0
        self._build_base_verts()

    def _build_base_verts(self):
        """Unit-sphere vertices in (lat, lon) order."""
        verts = []
        for la in range(self.LAT + 1):
            phi = math.pi * la / self.LAT          # 0 … π
            row = []
            for lo in range(self.LON):
                theta = 2 * math.pi * lo / self.LON
                x = math.sin(phi) * math.cos(theta)
                y = math.cos(phi)
                z = math.sin(phi) * math.sin(theta)
                row.append((x, y, z))
            verts.append(row)
        self.base_verts = verts   # list[LAT+1][LON] of (x,y,z) unit sphere

    # ── rotation matrices ────────────────────────────────────────────────────
    @staticmethod
    def _rot_x(p, a):
        x, y, z = p
        c, s = math.cos(a), math.sin(a)
        return (x, y * c - z * s, y * s + z * c)

    @staticmethod
    def _rot_y(p, a):
        x, y, z = p
        c, s = math.cos(a), math.sin(a)
        return (x * c + z * s, y, -x * s + z * c)

    @staticmethod
    def _rot_z(p, a):
        x, y, z = p
        c, s = math.cos(a), math.sin(a)
        return (x * c - y * s, x * s + y * c, z)

    def _project(self, p, fov=600):
        """Simple perspective projection → (screen_x, screen_y, depth)."""
        x, y, z = p
        z_cam = z + 3.5                 # push camera back
        if z_cam < 0.01: z_cam = 0.01
        scale = fov / z_cam
        return (int(self.cx + x * scale), int(self.cy + y * scale), z_cam)

    def update(self, dt, bass, mids, highs):
        # Slow base rotation; highs add a little jitter
        self.rot_y += dt * (0.28 + bass  * 0.35)
        self.rot_x += dt * (0.12 + mids  * 0.18)
        self.rot_z += dt * (0.06 + highs * 0.10)

    def draw(self, screen, spectrum, hue_base, bass, mids, highs, alpha_surf):
        """
        alpha_surf: a pre-created SRCALPHA surface the same size as screen,
                    used so we can draw semi-transparent edges without a new
                    alloc every frame.
        """
        energy = bass * 0.5 + mids * 0.3 + highs * 0.2
        n_bins = len(spectrum)

        # Build displaced, rotated, projected vertex grid
        proj = []
        for la_i, row in enumerate(self.base_verts):
            prow = []
            for lo_i, (bx, by, bz) in enumerate(row):
                # Map lon index → spectrum bin
                bin_i = int(lo_i / self.LON * n_bins) % n_bins
                disp  = spectrum[bin_i] * (0.35 + bass * 0.25)

                # Squash on Z to give ellipsoid shape (like the reference)
                r = self.base_r * (1.0 + disp)
                sx = bx * r
                sy = by * r * 0.55          # flatten vertically
                sz = bz * r * 0.70

                p = (sx, sy, sz)
                p = self._rot_x(p, self.rot_x)
                p = self._rot_y(p, self.rot_y)
                p = self._rot_z(p, self.rot_z)

                prow.append(self._project(p))
            proj.append(prow)

        alpha_surf.fill((0, 0, 0, 0))

        # Draw latitude rings
        for la_i in range(len(proj)):
            row = proj[la_i]
            lat_frac = la_i / self.LAT
            for lo_i in range(self.LON):
                a = row[lo_i]
                b = row[(lo_i + 1) % self.LON]

                depth_avg = (a[2] + b[2]) * 0.5
                # Depth-cue brightness: closer = brighter
                depth_bri = max(0.15, min(1.0, 1.0 - (depth_avg - 3.0) / 2.5))

                hue = (hue_base + lat_frac * 0.4 + lo_i / self.LON * 0.3) % 1.0
                sat = 0.75 + energy * 0.25
                bri = depth_bri * (0.55 + energy * 0.45)
                col = hsv_to_rgb(hue, sat, bri)

                lw  = 2 if depth_avg < 4.0 else 1
                alpha = int(depth_bri * (160 + energy * 80))
                pygame.draw.line(alpha_surf, (*col, alpha),
                                 (a[0], a[1]), (b[0], b[1]), lw)

        # Draw longitude spokes
        for lo_i in range(self.LON):
            lon_frac = lo_i / self.LON
            for la_i in range(self.LAT):
                a = proj[la_i][lo_i]
                b = proj[la_i + 1][lo_i]

                depth_avg = (a[2] + b[2]) * 0.5
                depth_bri = max(0.15, min(1.0, 1.0 - (depth_avg - 3.0) / 2.5))

                hue = (hue_base + 0.5 + lon_frac * 0.4) % 1.0
                sat = 0.70 + energy * 0.30
                bri = depth_bri * (0.40 + energy * 0.40)
                col = hsv_to_rgb(hue, sat, bri)

                lw    = 1
                alpha = int(depth_bri * (100 + energy * 60))
                pygame.draw.line(alpha_surf, (*col, alpha),
                                 (a[0], a[1]), (b[0], b[1]), lw)

        screen.blit(alpha_surf, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
#  Main visualizer
# ──────────────────────────────────────────────────────────────────────────────
class SpectrumVisualizer:
    PANEL_FRAC = 0.36

    def __init__(self, width, height):
        self.width  = width
        self.height = height
        self.mode   = "combined"   # always combined now; kept for key compat

        self.bar_count = 64
        self.spectrum  = np.zeros(self.bar_count, dtype=float)
        self.peak      = np.zeros(self.bar_count, dtype=float)

        self.panel_x  = int(width * self.PANEL_FRAC)
        self.panel_w  = width - self.panel_x
        self.cx       = self.panel_x + self.panel_w // 2
        self.center_y = int(height * 0.55)

        # Plasma low-res buffer
        self.plasma_scale = 6
        self.plasma_w     = max(1, self.panel_w // self.plasma_scale)
        self.plasma_h     = max(1, height // self.plasma_scale)
        self.plasma_small = pygame.Surface((self.plasma_w, self.plasma_h))

        self.time      = 0.0
        self.hue_base  = 0.0
        self.hue_speed = 0.0004
        self.beat_flash = 0.0
        self.last_bass  = 0.0

        self.peak_hue    = np.zeros(self.bar_count, dtype=float)
        self.ring_angles = np.linspace(0, 2 * math.pi, self.bar_count, endpoint=False)

        # 3-D sphere
        self.sphere = WireSphere(cx=self.cx, cy=self.center_y, base_r=105)

        # Reusable alpha surface for sphere edges (avoids per-frame alloc)
        self._alpha_surf = pygame.Surface((width, height), pygame.SRCALPHA)

        # Radial bar state
        self.bar_angles = np.linspace(0, 2 * math.pi, self.bar_count, endpoint=False)

    # ── public API ────────────────────────────────────────────────────────────
    def set_mode(self, mode):
        self.mode = mode   # kept for key compat, currently no-op branch

    def toggle_mode(self):
        pass   # single mode now; could cycle sub-modes later

    # ── spectrum update ───────────────────────────────────────────────────────
    def update(self, spectrum):
        if len(spectrum) < self.bar_count:
            return

        usable = spectrum[: max(self.bar_count * 8, self.bar_count)]
        chunks = np.array_split(usable, self.bar_count)

        new_vals = np.array([
            min(1.0, (float(np.mean(c)) * (1.0 - i / self.bar_count * 0.35)) ** 0.8)
            for i, c in enumerate(chunks)
        ])

        for i in range(self.bar_count):
            t = new_vals[i]
            if t > self.spectrum[i]:
                self.spectrum[i] = self.spectrum[i] * 0.78 + t * 0.22
            else:
                self.spectrum[i] = self.spectrum[i] * 0.94 + t * 0.06

        bass_now   = float(np.mean(self.spectrum[:4]))
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
        dt            = 0.016
        self.time    += 0.006 + bass_now * 0.012

        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))
        self.sphere.update(dt, bass, mids, highs)

    # ── draw ─────────────────────────────────────────────────────────────────
    def draw(self, screen):
        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))

        self._draw_plasma(screen, bass, mids, highs)
        self._draw_radial_bars(screen, bass, mids, highs)
        self.sphere.draw(screen, self.spectrum, self.hue_base,
                         bass, mids, highs, self._alpha_surf)
        self._draw_beat_flash(screen, bass)

    # ── plasma background ─────────────────────────────────────────────────────
    def _draw_plasma(self, screen, bass, mids, highs):
        px = pygame.PixelArray(self.plasma_small)
        for y in range(self.plasma_h):
            for x in range(self.plasma_w):
                v  = math.sin(x * 0.18 + self.time * (0.30 + bass  * 0.80))
                v += math.sin(y * 0.22 + self.time * (0.22 + mids  * 0.55))
                v += math.sin((x + y) * 0.12 + self.time * (0.26 + highs * 0.80))
                v += math.sin((x - y) * 0.09 + self.time * (0.18 + bass  * 0.55))
                cx_ = x - self.plasma_w / 2
                cy_ = y - self.plasma_h / 2
                v  += math.sin(math.sqrt(cx_*cx_ + cy_*cy_) * 0.24
                               - self.time * (0.40 + bass * 0.90))
                cx2 = x - self.plasma_w * (0.3 + 0.2 * math.sin(self.time * 0.07))
                cy2 = y - self.plasma_h * (0.6 + 0.15 * math.cos(self.time * 0.055))
                v  += math.sin(math.sqrt(cx2*cx2 + cy2*cy2) * 0.20
                               - self.time * (0.28 + mids * 0.60)) * 0.7
                v   = v / 5.5
                hue = (self.hue_base + (v + 1.0) * 0.45) % 1.0
                sat = 0.80 + highs * 0.20
                bri = min(1.0, 0.22 + (v + 1.0) * 0.35 + bass * 0.16)
                r, g, b = hsv_to_rgb(hue, sat, bri)
                if y % 2 == 0:
                    r, g, b = max(0, r - 18), max(0, g - 18), max(0, b - 18)
                px[x, y] = (r, g, b)
        del px

        plasma = pygame.transform.smoothscale(self.plasma_small, (self.panel_w, self.height))
        plasma.set_alpha(140)
        screen.blit(plasma, (self.panel_x, 0))

    # ── radial bars ───────────────────────────────────────────────────────────
    def _draw_radial_bars(self, screen, bass, mids, highs):
        """
        Bars shoot outward from the sphere centre in all directions,
        like a sunburst / magnetosphere spike field.
        """
        energy   = bass * 0.5 + mids * 0.3 + highs * 0.2
        inner_r  = 115 + int(bass * 20)   # just outside sphere surface
        max_len  = 180 + int(energy * 120)

        cx, cy = self.cx, self.center_y

        for i in range(self.bar_count):
            angle = self.bar_angles[i]
            val   = self.spectrum[i]
            bar_len = max(2, int(val * max_len))

            hue_pos = i / self.bar_count
            shimmer = math.sin(self.time * 0.5 + i * 0.18) * 0.03
            hue     = (self.hue_base + hue_pos * 0.8 + shimmer) % 1.0
            sat     = 0.72 + val * 0.28
            bri     = 0.25 + val * 0.75

            # Inner point (at sphere edge)
            x1 = cx + math.cos(angle) * inner_r
            y1 = cy + math.sin(angle) * inner_r

            # Outer tip
            x2 = cx + math.cos(angle) * (inner_r + bar_len)
            y2 = cy + math.sin(angle) * (inner_r + bar_len)

            col = hsv_to_rgb(hue, sat, bri)
            tip = hsv_to_rgb((hue + 0.1) % 1.0, 0.5, 1.0)

            # Main bar line
            pygame.draw.line(screen, col, (int(x1), int(y1)), (int(x2), int(y2)), 2)

            # Bright tip dot
            if val > 0.15:
                pygame.draw.circle(screen, tip, (int(x2), int(y2)), max(1, int(val * 4)))

            # Peak tick mark
            p_len = max(2, int(self.peak[i] * max_len))
            px_   = cx + math.cos(angle) * (inner_r + p_len)
            py_   = cy + math.sin(angle) * (inner_r + p_len)
            p_col = hsv_to_rgb(self.peak_hue[i] % 1.0, 0.9, 1.0)
            # Small perpendicular tick
            perp_angle = angle + math.pi / 2
            tx, ty = math.cos(perp_angle) * 4, math.sin(perp_angle) * 4
            pygame.draw.line(screen, p_col,
                             (int(px_ - tx), int(py_ - ty)),
                             (int(px_ + tx), int(py_ + ty)), 1)

    # ── beat flash ────────────────────────────────────────────────────────────
    def _draw_beat_flash(self, screen, bass):
        if self.beat_flash > 0.01:
            flash_col  = hsv_to_rgb(self.hue_base + 0.05, 0.7, self.beat_flash * 0.28)
            flash_surf = pygame.Surface((self.panel_w, self.height), pygame.SRCALPHA)
            flash_surf.fill((*flash_col, int(self.beat_flash * 45)))
            screen.blit(flash_surf, (self.panel_x, 0))
