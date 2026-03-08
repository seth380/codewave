import math
import pygame
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


# ------------------------------------------------------------------ #
#  HSV helper (no external deps)
# ------------------------------------------------------------------ #
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


# ------------------------------------------------------------------ #
#  Base token colors — now expressed as HSV hues so they can drift
# ------------------------------------------------------------------ #
TOKEN_HSV = {
    "keyword":   (0.02, 0.55, 1.00),   # warm coral-red
    "function":  (0.58, 0.55, 1.00),   # sky blue
    "class":     (0.13, 0.50, 1.00),   # amber
    "string":    (0.38, 0.50, 0.95),   # mint green
    "comment":   (0.62, 0.28, 0.55),   # muted slate
    "number":    (0.08, 0.50, 1.00),   # orange
    "operator":  (0.70, 0.20, 0.92),   # near-white lavender
    "default":   (0.67, 0.15, 0.88),   # soft blue-white
}


def token_hsv(token):
    if token in Token.Keyword:        return TOKEN_HSV["keyword"]
    if token in Token.Name.Function:  return TOKEN_HSV["function"]
    if token in Token.Name.Class:     return TOKEN_HSV["class"]
    if token in Token.String:         return TOKEN_HSV["string"]
    if token in Token.Comment:        return TOKEN_HSV["comment"]
    if token in Token.Number:         return TOKEN_HSV["number"]
    if token in Token.Operator:       return TOKEN_HSV["operator"]
    return TOKEN_HSV["default"]


class Particle:
    """Tiny spark emitted when a keyword is first revealed."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "hue")

    def __init__(self, x, y, hue):
        import random
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.4, 2.2)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 0.6
        self.life = 1.0
        self.max_life = random.uniform(0.6, 1.0)
        self.hue = hue

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.08   # gravity
        self.life -= 0.035
        self.hue  = (self.hue + 0.004) % 1.0

    @property
    def alive(self):
        return self.life > 0


class CodeLayer:
    def __init__(self, path, width, height):
        pygame.font.init()

        self.width  = width
        self.height = height

        self.font       = pygame.font.SysFont("consolas", 22)
        self.font_small = pygame.font.SysFont("consolas", 16)
        self.line_height = 28

        self.panel_x = 40
        self.panel_y = 34
        self.panel_w = self.width - 80
        self.panel_h = int(self.height * 0.29)

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))
        self.items   = []
        self.particles: list[Particle] = []

        self.scroll_y  = -20.0
        self.time      = 0.0
        self.hue_base  = 0.0          # global hue drift, synced from spectrum

        self.total_chars   = 0
        self.reveal_chars  = 0.0
        self.typing_done   = False
        self.cursor_phase  = 0.0

        # Track which items have already spawned particles
        self._sparked: set = set()

        self._build_layout()

    def _build_layout(self):
        x0 = self.panel_x + 30
        y0 = self.panel_y + 26
        x  = x0
        y  = y0

        for token, text in self.tokens:
            parts = text.split("\n")

            for idx, part in enumerate(parts):
                if part:
                    hsv  = token_hsv(token)
                    w, _ = self.font.size(part)
                    seed = (x * 0.012) + (y * 0.017) + (len(part) * 0.19)

                    self.items.append({
                        "token":      token,
                        "text":       part,
                        "base_hsv":   hsv,
                        "x":          x,
                        "y":          y,
                        "seed":       seed,
                        "char_start": self.total_chars,
                        "char_len":   len(part),
                    })

                    self.total_chars += len(part)
                    x += w

                if idx < len(parts) - 1:
                    y += self.line_height
                    x  = x0
                    self.total_chars += 1

        self.total_height = max(0, y - y0) + self.line_height

    # ------------------------------------------------------------------ #
    #  Per-token behaviour tables
    # ------------------------------------------------------------------ #
    def _token_motion_scale(self, token):
        if token in Token.Keyword:        return 1.00
        if token in Token.Name.Function:  return 1.08
        if token in Token.Name.Class:     return 1.02
        if token in Token.Operator:       return 0.90
        if token in Token.Comment:        return 0.42
        if token in Token.String:         return 0.65
        return 0.55

    def _token_hue_drift(self, token):
        """How much the token's hue shifts with the global hue_base."""
        if token in Token.Keyword:        return 0.85   # heavily entrains
        if token in Token.Name.Function:  return 0.70
        if token in Token.Name.Class:     return 0.60
        if token in Token.Operator:       return 0.50
        if token in Token.Comment:        return 0.15   # stays muted
        if token in Token.String:         return 0.40
        return 0.30

    def _token_is_shimmered(self, token):
        return (
            token in Token.Keyword
            or token in Token.Name.Function
            or token in Token.Operator
            or token in Token.Name.Class
        )

    def _token_sparks_on_reveal(self, token):
        return token in Token.Keyword or token in Token.Name.Function

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _visible_subtext(self, item, reveal_index):
        start = item["char_start"]
        end   = start + item["char_len"]
        if reveal_index <= start:   return ""
        if reveal_index >= end:     return item["text"]
        return item["text"][: max(0, reveal_index - start)]

    def _get_cursor_position(self, reveal_index):
        for item in self.items:
            start = item["char_start"]
            end   = start + item["char_len"]
            if start <= reveal_index <= end:
                partial = item["text"][: max(0, reveal_index - start)]
                return item["x"] + self.font.size(partial)[0], item["y"]
        if self.items:
            last = self.items[-1]
            return last["x"] + self.font.size(last["text"])[0], last["y"]
        return self.panel_x + 40, self.panel_y + 40

    # ------------------------------------------------------------------ #
    #  Main draw
    # ------------------------------------------------------------------ #
    def draw(self, screen, spectrum, mode_name="PLASMA"):
        bass   = float(spectrum[2])  if len(spectrum) > 2  else 0.0
        mids   = float(spectrum[8])  if len(spectrum) > 8  else bass
        highs  = float(spectrum[20]) if len(spectrum) > 20 else mids
        energy = bass * 0.50 + mids * 0.35 + highs * 0.15

        dt = 0.016
        self.time         += dt
        self.cursor_phase += dt * 3.2

        # Global hue drifts with music — bass accelerates it
        self.hue_base = (self.hue_base + 0.0015 + bass * 0.004) % 1.0

        if not self.typing_done:
            cps = 18 + bass * 22 + mids * 10
            self.reveal_chars += cps * dt
            self.scroll_y     += 0.06 + bass * 0.07

            if self.reveal_chars >= self.total_chars:
                self.reveal_chars = float(self.total_chars)
                self.typing_done  = True
        else:
            self.scroll_y += 0.16 + bass * 0.22

        reveal_index = int(self.reveal_chars)

        # ---- Panel background ----------------------------------------
        # Panel height breathes with bass
        breath      = int(bass * 18)
        panel_h_now = self.panel_h + breath

        panel = pygame.Surface((self.panel_w, panel_h_now), pygame.SRCALPHA)
        panel.fill((9, 13, 22, 96))
        pygame.draw.line(panel, (120, 150, 210, 55), (0, 0), (self.panel_w, 0), 2)
        pygame.draw.line(panel, (70, 90, 140, 26),   (0, 1), (self.panel_w, 1), 1)
        pygame.draw.rect(panel, (85, 110, 160, 28), panel.get_rect(), 1, border_radius=10)
        screen.blit(panel, (self.panel_x, self.panel_y))

        # Panel border hue-cycles
        border_col = hsv_to_rgb(self.hue_base, 0.55, 0.70)
        pygame.draw.rect(
            screen, border_col,
            pygame.Rect(self.panel_x, self.panel_y, self.panel_w, panel_h_now),
            1, border_radius=10
        )

        label = self.font_small.render(f"CODEWAVE // {mode_name}", True, (150, 170, 210))
        label.set_alpha(170)
        screen.blit(label, (self.panel_x + 18, self.panel_y + 6))

        clip_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, panel_h_now)
        old_clip  = screen.get_clip()
        screen.set_clip(clip_rect)

        # ---- Token rendering -----------------------------------------
        for idx, item in enumerate(self.items):
            token = item["token"]
            bh, bs, bv = item["base_hsv"]
            x     = item["x"]
            y     = item["y"] - self.scroll_y
            seed  = item["seed"]

            if y < self.panel_y - 40 or y > self.panel_y + panel_h_now + 20:
                continue

            text = self._visible_subtext(item, reveal_index)
            if not text:
                continue

            # Spawn particles on first full reveal of spark tokens
            if (self._token_sparks_on_reveal(token)
                    and idx not in self._sparked
                    and len(text) == item["char_len"]):
                self._sparked.add(idx)
                spark_hue = (self.hue_base + bh * 0.5) % 1.0
                mid_x = x + self.font.size(text)[0] // 2
                for _ in range(7):
                    self.particles.append(Particle(mid_x, y, spark_hue))

            motion_scale = self._token_motion_scale(token)
            hue_drift    = self._token_hue_drift(token)

            dx = math.sin(self.time * 1.15 + seed * 1.35) * (0.35 + bass  * 0.90) * motion_scale
            dy = math.cos(self.time * 0.92 + seed * 1.10) * (0.18 + mids  * 0.45) * motion_scale

            # Hue: base token hue + global drift weighted by token type
            hue = (bh + self.hue_base * hue_drift
                   + math.sin(self.time * 0.8 + seed) * 0.04 * (1 + energy)) % 1.0

            # Saturation and brightness pulse with energy
            sat = min(1.0, bs + energy * 0.30 + highs * 0.18)
            bri = min(1.0, bv + energy * 0.18 + bass  * 0.10)

            color = hsv_to_rgb(hue, sat, bri)

            # Soft glow pass (offset, low alpha)
            glow_col = hsv_to_rgb((hue + 0.05) % 1.0, sat * 0.7, 1.0)
            glow     = self.font.render(text, True, glow_col)
            glow.set_alpha(22 + int(highs * 35 + bass * 20))
            screen.blit(glow, (x + dx + 0.9, y + dy + 0.6))

            if self._token_is_shimmered(token):
                char_x = x + dx
                for ci, ch in enumerate(text):
                    char_seed = seed + ci * 0.31
                    char_dx = math.sin(self.time * 2.1 + char_seed * 2.4) * (0.25 + highs * 0.9)
                    char_dy = math.cos(self.time * 1.7 + char_seed * 1.9) * (0.12 + mids  * 0.45)

                    # Per-character hue micro-variation
                    ch_hue = (hue + ci * 0.03 + math.sin(self.time * 3.0 + char_seed) * 0.06) % 1.0
                    ch_sat = min(1.0, sat + math.sin(self.time * 2.4 + char_seed) * 0.12)
                    ch_bri = min(1.0, bri + math.sin(self.time * 2.0 + char_seed * 1.2) * 0.10)
                    ch_col = hsv_to_rgb(ch_hue, ch_sat, ch_bri)

                    # Chromatic aberration on heavy hits
                    if energy > 0.4:
                        ab = int(energy * 2.5)
                        ab_col = hsv_to_rgb((ch_hue + 0.33) % 1.0, 1.0, 1.0)
                        ab_surf = self.font.render(ch, True, ab_col)
                        ab_surf.set_alpha(int(energy * 45))
                        screen.blit(ab_surf, (char_x + char_dx + ab, y + char_dy))
                        screen.blit(ab_surf, (char_x + char_dx - ab, y + char_dy))

                    ch_glow = self.font.render(ch, True, (
                        min(255, ch_col[0] + 22),
                        min(255, ch_col[1] + 22),
                        min(255, ch_col[2] + 22),
                    ))
                    ch_glow.set_alpha(18 + int(highs * 30))
                    screen.blit(ch_glow, (char_x + char_dx + 0.7, y + char_dy + 0.4))

                    ch_surf = self.font.render(ch, True, ch_col)
                    screen.blit(ch_surf, (char_x + char_dx, y + char_dy))
                    char_x += self.font.size(ch)[0]
            else:
                surf = self.font.render(text, True, color)
                screen.blit(surf, (x + dx, y + dy))

        # ---- Particles -----------------------------------------------
        alive = []
        for p in self.particles:
            p.update()
            if p.alive:
                py_screen = p.y - self.scroll_y + self.panel_y - (self.panel_y - self.panel_y)
                # keep particles within panel clip
                col  = hsv_to_rgb(p.hue, 0.9, 1.0)
                size = max(1, int(p.life * 3))
                pygame.draw.circle(screen, col, (int(p.x), int(p.y - self.scroll_y + self.panel_y - self.items[0]["y"] + self.panel_y)), size)
                alive.append(p)
        self.particles = alive

        # ---- Cursor --------------------------------------------------
        if not self.typing_done or math.sin(self.cursor_phase) > 0:
            cx, cy = self._get_cursor_position(reveal_index)
            cy -= self.scroll_y

            if self.panel_y <= cy <= self.panel_y + panel_h_now:
                cursor_col = hsv_to_rgb(self.hue_base, 0.3, 1.0)
                cursor_h   = self.line_height - 6
                cursor     = pygame.Surface((2, cursor_h), pygame.SRCALPHA)
                cursor.fill((*cursor_col, 210))
                screen.blit(cursor, (cx + 1, cy + 3))

        screen.set_clip(old_clip)

        if self.scroll_y > self.total_height + 60:
            self.scroll_y    = -self.panel_h * 0.45
            self.reveal_chars = 0.0
            self.typing_done  = False
            self._sparked.clear()
            self.particles.clear()
