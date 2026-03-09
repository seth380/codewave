"""
visualizer.py  —  CodeWave visualizer
Layers (right panel):
  1. Dark fluid ink background  — swirling tendrils, mostly black negative space
  2. Spectrum bars              — horizontal, centred at top of panel
  3. 3-D wireframe ellipsoid    — centred in lower portion of panel
All in a slowly-shifting monochromatic palette (one hue + analogue accents).
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
    if i == 0:   r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


def mono_palette(hue_base, offset=0.0, sat=0.55, val=1.0):
    return hsv_to_rgb((hue_base + offset) % 1.0, sat, val)


# ──────────────────────────────────────────────────────────────────────────────
#  Dark fluid ink background  (sparse swirl particles + curl noise streaks)
# ──────────────────────────────────────────────────────────────────────────────
class InkFluid:
    """
    A fixed set of 'ink drop' trail points that curl slowly through the panel.
    Drawn as fading line segments — mostly black with coloured tendrils.
    """
    N_TRAILS  = 20
    TRAIL_LEN = 70

    def __init__(self, panel_x, panel_w, height):
        self.px = panel_x
        self.pw = panel_w
        self.h  = height
        rng = np.random.default_rng(42)

        # Each trail: list of (x, y) positions, initialised randomly
        self.trails = []
        for _ in range(self.N_TRAILS):
            x = panel_x + rng.uniform(0, panel_w)
            y = rng.uniform(0, height)
            self.trails.append([(x, y)] * self.TRAIL_LEN)

        self.time  = 0.0
        self.speeds = rng.uniform(0.4, 1.2, self.N_TRAILS)

    def _curl(self, x, y, t, bass):
        """Curl-noise-ish vector field."""
        nx = x * 0.003
        ny = y * 0.003
        angle = (math.sin(nx + t * 0.18) * math.cos(ny * 0.9 + t * 0.12)
                 + math.sin(nx * 1.7 - t * 0.09) * 0.5) * math.pi * 2
        speed = 1.1 + bass * 1.4
        return math.cos(angle) * speed, math.sin(angle) * speed

    def update(self, dt, bass):
        self.time += dt * (0.6 + bass * 1.2)
        for i, trail in enumerate(self.trails):
            hx, hy = trail[0]
            dx, dy = self._curl(hx, hy, self.time, bass)
            dx *= self.speeds[i]
            dy *= self.speeds[i]
            nx = hx + dx
            ny = hy + dy
            # Wrap within panel
            if nx < self.px:           nx += self.pw
            if nx > self.px + self.pw: nx -= self.pw
            if ny < 0:                 ny += self.h
            if ny > self.h:            ny -= self.h
            self.trails[i] = [(nx, ny)] + trail[:-1]

    def draw(self, screen, hue_base, energy):
        for i, trail in enumerate(self.trails):
            n = len(trail)
            for j in range(n - 1):
                # Age fraction: 0 = newest, 1 = oldest
                age  = j / (n - 1)
                a_frac = (1.0 - age) ** 2.2   # quadratic fade

                # Only draw if bright enough
                if a_frac < 0.04:
                    continue

                # Monochromatic: slight hue offset per trail for analogue warmth
                hue_off = (i / self.N_TRAILS) * 0.05 - 0.025
                col = mono_palette(hue_base, hue_off,
                                   sat=0.42 + energy * 0.10,
                                   val=a_frac * (0.30 + energy * 0.22))
                alpha = int(a_frac * (80 + energy * 100))

                x1, y1 = trail[j]
                x2, y2 = trail[j + 1]
                # Draw as a short alpha line on screen directly
                # (we skip a surface per segment for perf — direct draw at low alpha)
                pygame.draw.line(screen, col, (int(x1), int(y1)), (int(x2), int(y2)), 1)


# ──────────────────────────────────────────────────────────────────────────────
#  3-D wireframe ellipsoid
# ──────────────────────────────────────────────────────────────────────────────
class WireSphere:
    LAT = 16
    LON = 32

    def __init__(self, cx, cy, base_r=108):
        self.cx     = cx
        self.cy     = cy
        self.base_r = base_r
        self.rot_x  = 0.0
        self.rot_y  = 0.0
        self.rot_z  = 0.0
        self._build_base()

    def _build_base(self):
        self.verts = []
        for la in range(self.LAT + 1):
            phi = math.pi * la / self.LAT
            row = []
            for lo in range(self.LON):
                theta = 2 * math.pi * lo / self.LON
                row.append((
                    math.sin(phi) * math.cos(theta),
                    math.cos(phi),
                    math.sin(phi) * math.sin(theta),
                ))
            self.verts.append(row)

    @staticmethod
    def _rx(p, a):
        x, y, z = p; c, s = math.cos(a), math.sin(a)
        return (x, y*c - z*s, y*s + z*c)

    @staticmethod
    def _ry(p, a):
        x, y, z = p; c, s = math.cos(a), math.sin(a)
        return (x*c + z*s, y, -x*s + z*c)

    @staticmethod
    def _rz(p, a):
        x, y, z = p; c, s = math.cos(a), math.sin(a)
        return (x*c - y*s, x*s + y*c, z)

    def _proj(self, p, fov=580):
        x, y, z = p
        zc = z + 3.5
        if zc < 0.01: zc = 0.01
        sc = fov / zc
        return (int(self.cx + x * sc), int(self.cy + y * sc), zc)

    def update(self, dt, bass, mids, highs):
        self.rot_y += dt * (0.16 + bass  * 0.18)
        self.rot_x += dt * (0.06 + mids  * 0.09)
        self.rot_z += dt * (0.025 + highs * 0.05)

    def draw(self, screen, spectrum, hue_base, bass, mids, highs, asurf):
        energy  = bass * 0.5 + mids * 0.3 + highs * 0.2
        n_bins  = len(spectrum)

        # Build projected grid
        proj = []
        for la_i, row in enumerate(self.verts):
            prow = []
            for lo_i, (bx, by, bz) in enumerate(row):
                bin_i = int(lo_i / self.LON * n_bins) % n_bins
                disp  = spectrum[bin_i] * (0.32 + bass * 0.22)
                r     = self.base_r * (1.0 + disp)
                # Ellipsoid squash
                p = (bx * r, by * r * 0.52, bz * r * 0.68)
                p = self._rx(p, self.rot_x)
                p = self._ry(p, self.rot_y)
                p = self._rz(p, self.rot_z)
                prow.append(self._proj(p))
            proj.append(prow)

        asurf.fill((0, 0, 0, 0))

        def draw_edge(a, b, hue_off, bri_scale):
            depth = (a[2] + b[2]) * 0.5
            # Back-face dimming: far edges nearly invisible
            depth_bri = max(0.0, min(1.0, 1.0 - (depth - 3.0) / 2.8))
            if depth_bri < 0.05:
                return
            col   = mono_palette(hue_base, hue_off,
                                  sat=0.80 + energy * 0.20,
                                  val=depth_bri * bri_scale * (0.5 + energy * 0.5))
            alpha = int(depth_bri * (130 + energy * 110))
            lw    = 2 if depth < 3.8 else 1
            pygame.draw.line(asurf, (*col, alpha),
                             (a[0], a[1]), (b[0], b[1]), lw)

        # Latitude rings — base hue
        for la_i in range(len(proj)):
            row = proj[la_i]
            lat_off = (la_i / self.LAT) * 0.04 - 0.02   # ±0.05 warm→cool
            for lo_i in range(self.LON):
                draw_edge(row[lo_i], row[(lo_i + 1) % self.LON],
                          hue_off=lat_off, bri_scale=0.95)

        # Longitude spokes — slight complementary nudge for depth contrast
        for lo_i in range(self.LON):
            lon_off = 0.025 * math.sin(lo_i / self.LON * math.pi * 2)
            for la_i in range(self.LAT):
                draw_edge(proj[la_i][lo_i], proj[la_i + 1][lo_i],
                          hue_off=lon_off, bri_scale=0.75)

        screen.blit(asurf, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
#  Smoke particle system  — blue/white wisps drifting around the sphere
# ──────────────────────────────────────────────────────────────────────────────
class SmokeSystem:
    """
    Thin drifting wisps that originate near the sphere and shear upward.
    Less bubbly than circular additive puffs.
    """
    MAX_PARTICLES = 90
    SPAWN_RATE = 1.4

    def __init__(self, cx, cy, sphere_r):
        self.cx = cx
        self.cy = cy
        self.sphere_r = sphere_r
        self.particles = []
        self._rng = np.random.default_rng(7)
        self._accum = 0.0
        self._stamps = {}

    def _get_stamp(self, w, h):
        key = (max(8, int(w)), max(6, int(h)))
        if key not in self._stamps:
            sw, sh = key
            surf = pygame.Surface((sw, sh), pygame.SRCALPHA)

            cx = sw // 2
            cy = sh // 2
            max_r = max(sw, sh) * 0.5

            for y in range(sh):
                for x in range(sw):
                    dx = (x - cx) / max(1, sw * 0.5)
                    dy = (y - cy) / max(1, sh * 0.5)

                    # Elliptical falloff
                    d = dx * dx + dy * dy
                    if d >= 1.0:
                        continue

                    # Softer core, thinner edges
                    a = int((1.0 - d) ** 2.3 * 90)
                    surf.set_at((x, y), (255, 255, 255, a))

            self._stamps[key] = surf
        return self._stamps[key]

    def _spawn(self, bass, energy):
        rng = self._rng

        # Spawn from a narrower lower-side band around the sphere
        angle = rng.uniform(math.pi * 0.15, math.pi * 0.85)
        spread = rng.uniform(0.92, 1.08)

        x = self.cx + math.cos(angle) * self.sphere_r * spread
        y = self.cy + math.sin(angle) * self.sphere_r * spread * 0.50

        vx = rng.uniform(-0.12, 0.12)
        vy = -rng.uniform(0.22 + bass * 0.18, 0.48 + bass * 0.28)

        w = rng.uniform(18, 30 + energy * 10)
        h = rng.uniform(8, 14 + energy * 5)
        life = rng.uniform(2.8, 4.6)

        self.particles.append({
            "x": x, "y": y,
            "vx": vx, "vy": vy,
            "life": life, "max_life": life,
            "w": w, "h": h,
            "rot": rng.uniform(-0.35, 0.35),
            "rot_v": rng.uniform(-0.015, 0.015),
            "seed": rng.uniform(0.0, 1000.0),
        })

    def update(self, dt, bass, energy):
        self._accum += (self.SPAWN_RATE + energy * 1.8) * dt
        while self._accum >= 1.0 and len(self.particles) < self.MAX_PARTICLES:
            self._spawn(bass, energy)
            self._accum -= 1.0

        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue

            t = 1.0 - (p["life"] / p["max_life"])

            # Very gentle horizontal meander
            p["vx"] += math.sin(p["seed"] + p["y"] * 0.018 + t * 3.5) * 0.0025
            p["vx"] *= 0.992

            # Slow rise, light drag
            p["vy"] *= 0.998
            p["x"] += p["vx"] * 60 * dt
            p["y"] += p["vy"] * 60 * dt

            # Stretch slightly over lifetime, not balloon
            p["w"] *= 1.002
            p["h"] *= 1.0008
            p["rot"] += p["rot_v"]

            alive.append(p)

        self.particles = alive

    def draw(self, screen, hue_base):
        for p in self.particles:
            age = p["life"] / p["max_life"]  # 1 -> 0

            # Ease in, then slow fade
            if age > 0.82:
                alpha_frac = (1.0 - age) / 0.18
            else:
                alpha_frac = age ** 0.8

            if alpha_frac < 0.03:
                continue

            stamp = self._get_stamp(p["w"], p["h"])

            # Keep smoke nearly neutral with tiny hue bias
            col = mono_palette(hue_base, offset=0.015, sat=0.12, val=0.92)
            tinted = stamp.copy()
            tinted.fill((*col, 0), special_flags=pygame.BLEND_RGBA_MULT)
            tinted.set_alpha(int(alpha_frac * 72))

            rotated = pygame.transform.rotate(tinted, math.degrees(p["rot"]))
            rect = rotated.get_rect(center=(int(p["x"]), int(p["y"])))
            screen.blit(rotated, rect.topleft)


# ──────────────────────────────────────────────────────────────────────────────
#  Main visualizer
# ──────────────────────────────────────────────────────────────────────────────
class SpectrumVisualizer:
    PANEL_FRAC = 0.36

    def __init__(self, width, height):
        self.width  = width
        self.height = height
        self.mode   = "combined"

        self.bar_count = 64
        self.spectrum  = np.zeros(self.bar_count, dtype=float)
        self.peak      = np.zeros(self.bar_count, dtype=float)

        self.panel_x  = int(width * self.PANEL_FRAC)
        self.panel_w  = width - self.panel_x

        # Sphere sits in the lower-centre of the right panel
        self.cx       = self.panel_x + self.panel_w // 2
        self.sphere_y = int(height * 0.60)

        # Bars sit in the upper portion
        self.bars_y   = int(height * 0.22)   # midline of the bar graph

        self.time      = 0.0
        self.hue_base  = 0.0          # drifts slowly — whole palette shifts
        self.hue_speed = 0.0003
        self.beat_flash = 0.0
        self.last_bass  = 0.0

        self.peak_hue  = np.zeros(self.bar_count, dtype=float)

        # Sub-objects
        self.ink    = InkFluid(self.panel_x, self.panel_w, height)
        self.sphere = WireSphere(cx=self.cx, cy=self.sphere_y, base_r=108)
        self.smoke  = SmokeSystem(cx=self.cx, cy=self.sphere_y, sphere_r=108)
        self._asurf = pygame.Surface((width, height), pygame.SRCALPHA)

    # ── public API ────────────────────────────────────────────────────────────
    def set_mode(self, mode):   self.mode = mode
    def toggle_mode(self):      pass

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
            self.spectrum[i] = (self.spectrum[i] * (0.78 if t <= self.spectrum[i] else 0.60)
                                + t * (0.22 if t <= self.spectrum[i] else 0.40))

        bass_now   = float(np.mean(self.spectrum[:4]))
        bass_delta = bass_now - self.last_bass
        if bass_delta > 0.08:
            self.beat_flash = min(1.0, self.beat_flash + bass_delta * 1.2)
            self.hue_speed  = 0.0010 + bass_delta * 0.010
        else:
            self.hue_speed  = max(0.0003, self.hue_speed * 0.988)
        self.beat_flash = max(0.0, self.beat_flash - 0.015)
        self.last_bass  = bass_now

        for i in range(self.bar_count):
            if self.spectrum[i] >= self.peak[i]:
                self.peak_hue[i] = self.hue_base
        self.peak = np.maximum(self.peak * 0.993, self.spectrum)

        # Hue drifts slowly like a lava lamp — full cycle takes ~50 s at rest
        self.hue_base = (self.hue_base + self.hue_speed + bass_now * 0.0006) % 1.0
        self.time    += 0.016

        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))
        self.sphere.update(0.016, bass, mids, highs)
        self.ink.update(0.016, bass)
        self.smoke.update(0.016, bass, bass * 0.5 + mids * 0.3 + highs * 0.2)

    # ── draw ─────────────────────────────────────────────────────────────────
    def draw(self, screen):
        bass  = float(np.mean(self.spectrum[:6]))
        mids  = float(np.mean(self.spectrum[6:20]))
        highs = float(np.mean(self.spectrum[20:40]))
        energy = bass * 0.5 + mids * 0.3 + highs * 0.2

        # 1 ── Dark ink fluid (swirl tendrils on black)
        self.ink.draw(screen, self.hue_base, energy)

        # 2 ── Smoke wisps (blue/white, additive blend, behind bars + sphere)
        self.smoke.draw(screen, self.hue_base)

        # 3 ── Horizontal spectrum bars (top of right panel)
        self._draw_bars(screen, bass, mids, highs)

        # 4 ── 3-D ellipsoid
        self.sphere.draw(screen, self.spectrum, self.hue_base,
                         bass, mids, highs, self._asurf)

        # 4 ── Beat flash
        if self.beat_flash > 0.01:
            fc = mono_palette(self.hue_base, 0.04, sat=0.6, val=self.beat_flash * 0.22)
            fs = pygame.Surface((self.panel_w, self.height), pygame.SRCALPHA)
            fs.fill((*fc, int(self.beat_flash * 18)))
            screen.blit(fs, (self.panel_x, 0))

    # ── horizontal bars ───────────────────────────────────────────────────────
    def _draw_bars(self, screen, bass, mids, highs):
        half   = self.bar_count // 2
        gap    = 3
        bw     = max(3, (self.panel_w // 2 - 40) // half - gap)
        max_h  = int(self.height * 0.16)   # max bar height — compact strip
        cy     = self.bars_y

        # Subtle baseline
        pygame.draw.line(screen, (30, 30, 35),
                         (self.panel_x, cy), (self.width, cy), 1)

        for i in range(half):
            val     = self.spectrum[i]
            peak_v  = self.peak[i]
            h       = max(2, int(val   * max_h))
            ph      = max(2, int(peak_v * max_h))

            x_r = self.cx + i * (bw + gap)
            x_l = self.cx - (i + 1) * (bw + gap)

            # Monochromatic: inner bars = base hue, outer = warm accent
            warmth  = (i / half) * 0.04          # 0 → +0.08 hue shift outward
            hue_off = warmth - 0.02
            sat     = 0.50 + val * 0.14
            bri     = 0.20 + val * 0.62
            col     = mono_palette(self.hue_base, hue_off, sat, bri)
            tip_col = mono_palette(self.hue_base, hue_off + 0.02, 0.28, 0.86)

            for x in (x_r, x_l):
                # Body
                pygame.draw.rect(screen, col,
                                 pygame.Rect(x, cy - h, bw, h * 2), border_radius=2)
                # Bright edge stripe
                gw = max(1, bw // 3)
                pygame.draw.rect(screen, tip_col,
                                 pygame.Rect(x + 1, cy - h, gw, h * 2), border_radius=1)
                # Peak tick
                p_col = mono_palette(self.peak_hue[i], 0.03, 0.35, 0.82)
                pygame.draw.line(screen, p_col,
                                 (x, cy - ph), (x + bw, cy - ph), 1)
                pygame.draw.line(screen, p_col,
                                 (x, cy + ph), (x + bw, cy + ph), 1)
