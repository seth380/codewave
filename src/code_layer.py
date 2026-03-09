import math
import pygame
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


# ------------------------------------------------------------------ #
#  HSV helper
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


TOKEN_HSV = {
    "keyword":  (0.02, 0.55, 1.00),
    "function": (0.58, 0.55, 1.00),
    "class":    (0.13, 0.50, 1.00),
    "string":   (0.38, 0.50, 0.95),
    "comment":  (0.62, 0.28, 0.55),
    "number":   (0.08, 0.50, 1.00),
    "operator": (0.70, 0.20, 0.92),
    "default":  (0.67, 0.15, 0.88),
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
    __slots__ = ("x", "y", "vx", "vy", "life", "hue")

    def __init__(self, x, y, hue):
        import random
        angle     = random.uniform(0, math.pi * 2)
        speed     = random.uniform(0.4, 2.0)
        self.x    = float(x)
        self.y    = float(y)
        self.vx   = math.cos(angle) * speed
        self.vy   = math.sin(angle) * speed - 0.5
        self.life = 1.0
        self.hue  = hue

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.vy  += 0.07
        self.life -= 0.032
        self.hue  = (self.hue + 0.004) % 1.0

    @property
    def alive(self):
        return self.life > 0


class CodeLayer:
    """Left-column code panel. COL_FRAC controls width as fraction of screen."""
    COL_FRAC = 0.36

    def __init__(self, path, width, height):
        pygame.font.init()

        self.width  = width
        self.height = height

        self.col_w   = int(width * self.COL_FRAC)
        self.col_h   = height
        self.col_x   = 0
        self.col_y   = 0
        self.pad_x   = 18
        self.pad_top = 34

        self.font        = pygame.font.SysFont("consolas", 17)
        self.font_small  = pygame.font.SysFont("consolas", 13)
        self.line_height = 22

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens       = list(lex(code, PythonLexer()))
        self.items        = []
        self.particles: list[Particle] = []

        self.scroll_y     = -20.0
        self.time         = 0.0
        self.hue_base     = 0.0
        self.total_chars  = 0
        self.reveal_chars = 0.0
        self.typing_done  = False
        self.cursor_phase = 0.0
        self._sparked: set = set()

        # Static semi-opaque background — drawn once per frame via blit
        self._col_bg = pygame.Surface((self.col_w, self.col_h), pygame.SRCALPHA)
        self._col_bg.fill((5, 8, 16, 200))

        self._build_layout()

    def _build_layout(self):
        x0    = self.col_x + self.pad_x
        y0    = self.col_y + self.pad_top
        x, y  = x0, y0
        max_x = self.col_x + self.col_w - self.pad_x

        for token, text in self.tokens:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    hsv  = token_hsv(token)
                    w, _ = self.font.size(part)
                    if x + w > max_x and x > x0:
                        y += self.line_height
                        x  = x0
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

    def _token_motion_scale(self, token):
        if token in Token.Keyword:        return 1.00
        if token in Token.Name.Function:  return 1.05
        if token in Token.Name.Class:     return 1.00
        if token in Token.Operator:       return 0.85
        if token in Token.Comment:        return 0.38
        if token in Token.String:         return 0.60
        return 0.50

    def _token_hue_drift(self, token):
        if token in Token.Keyword:        return 0.85
        if token in Token.Name.Function:  return 0.70
        if token in Token.Name.Class:     return 0.60
        if token in Token.Operator:       return 0.50
        if token in Token.Comment:        return 0.12
        if token in Token.String:         return 0.38
        return 0.28

    def _token_is_shimmered(self, token):
        return (token in Token.Keyword or token in Token.Name.Function
                or token in Token.Operator or token in Token.Name.Class)

    def _token_sparks_on_reveal(self, token):
        return token in Token.Keyword or token in Token.Name.Function

    def _visible_subtext(self, item, reveal_index):
        s, e = item["char_start"], item["char_start"] + item["char_len"]
        if reveal_index <= s: return ""
        if reveal_index >= e: return item["text"]
        return item["text"][: max(0, reveal_index - s)]

    def _get_cursor_position(self, reveal_index):
        for item in self.items:
            s, e = item["char_start"], item["char_start"] + item["char_len"]
            if s <= reveal_index <= e:
                partial = item["text"][: max(0, reveal_index - s)]
                return item["x"] + self.font.size(partial)[0], item["y"]
        if self.items:
            last = self.items[-1]
            return last["x"] + self.font.size(last["text"])[0], last["y"]
        return self.col_x + self.pad_x, self.col_y + self.pad_top

    def draw(self, screen, spectrum, mode_name="PLASMA"):
        bass   = float(spectrum[2])  if len(spectrum) > 2  else 0.0
        mids   = float(spectrum[8])  if len(spectrum) > 8  else bass
        highs  = float(spectrum[20]) if len(spectrum) > 20 else mids
        energy = bass * 0.50 + mids * 0.35 + highs * 0.15

        dt = 0.016
        self.time         += dt
        self.cursor_phase += dt * 3.2
        self.hue_base      = (self.hue_base + 0.0015 + bass * 0.004) % 1.0

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

        # ── Column background ────────────────────────────────────────────
        screen.blit(self._col_bg, (self.col_x, self.col_y))

        # Right-edge separator with hue-cycling glow
        sep_col = hsv_to_rgb(self.hue_base, 0.65, 0.85)
        pygame.draw.line(screen, sep_col,
                         (self.col_x + self.col_w - 1, 0),
                         (self.col_x + self.col_w - 1, self.col_h), 1)
        sep_glow = pygame.Surface((4, self.col_h), pygame.SRCALPHA)
        sep_glow.fill((*sep_col, 40))
        screen.blit(sep_glow, (self.col_x + self.col_w - 3, 0))

        # Header
        label_col = hsv_to_rgb((self.hue_base + 0.55) % 1.0, 0.40, 0.75)
        label = self.font_small.render(f"CODEWAVE // {mode_name}", True, label_col)
        screen.blit(label, (self.col_x + self.pad_x, self.col_y + 10))
        pygame.draw.line(screen, (*label_col, 50),
                         (self.col_x, self.col_y + self.pad_top - 4),
                         (self.col_x + self.col_w, self.col_y + self.pad_top - 4), 1)

        # ── Clip to text area ────────────────────────────────────────────
        clip_rect = pygame.Rect(self.col_x, self.col_y + self.pad_top,
                                self.col_w - 2, self.col_h - self.pad_top)
        old_clip  = screen.get_clip()
        screen.set_clip(clip_rect)

        # ── Token rendering ──────────────────────────────────────────────
        for idx, item in enumerate(self.items):
            token      = item["token"]
            bh, bs, bv = item["base_hsv"]
            x          = item["x"]
            y          = item["y"] - self.scroll_y
            seed       = item["seed"]

            if y < self.col_y - 40 or y > self.col_y + self.col_h + 20:
                continue

            text = self._visible_subtext(item, reveal_index)
            if not text:
                continue

            # Particle burst
            if (self._token_sparks_on_reveal(token)
                    and idx not in self._sparked
                    and len(text) == item["char_len"]):
                self._sparked.add(idx)
                spark_hue = (self.hue_base + bh * 0.5) % 1.0
                mid_x = x + self.font.size(text)[0] // 2
                for _ in range(6):
                    self.particles.append(Particle(mid_x, y, spark_hue))

            ms  = self._token_motion_scale(token)
            hd  = self._token_hue_drift(token)

            dx = math.sin(self.time * 1.15 + seed * 1.35) * (0.30 + bass * 0.70) * ms
            dy = math.cos(self.time * 0.92 + seed * 1.10) * (0.15 + mids * 0.35) * ms

            hue   = (bh + self.hue_base * hd + math.sin(self.time * 0.8 + seed) * 0.04 * (1 + energy)) % 1.0
            sat   = min(1.0, bs + energy * 0.28 + highs * 0.16)
            bri   = min(1.0, bv + energy * 0.16 + bass  * 0.08)
            color = hsv_to_rgb(hue, sat, bri)

            # Glow
            glow_col = hsv_to_rgb((hue + 0.05) % 1.0, sat * 0.7, 1.0)
            glow     = self.font.render(text, True, glow_col)
            glow.set_alpha(18 + int(highs * 28 + bass * 16))
            screen.blit(glow, (x + dx + 0.9, y + dy + 0.6))

            if self._token_is_shimmered(token):
                char_x = x + dx
                for ci, ch in enumerate(text):
                    cs  = seed + ci * 0.31
                    cdx = math.sin(self.time * 2.1 + cs * 2.4) * (0.22 + highs * 0.8)
                    cdy = math.cos(self.time * 1.7 + cs * 1.9) * (0.10 + mids  * 0.38)

                    ch_hue = (hue + ci * 0.03 + math.sin(self.time * 3.0 + cs) * 0.06) % 1.0
                    ch_sat = min(1.0, sat + math.sin(self.time * 2.4 + cs) * 0.12)
                    ch_bri = min(1.0, bri + math.sin(self.time * 2.0 + cs * 1.2) * 0.10)
                    ch_col = hsv_to_rgb(ch_hue, ch_sat, ch_bri)

                    if energy > 0.4:
                        ab      = int(energy * 2.2)
                        ab_col  = hsv_to_rgb((ch_hue + 0.33) % 1.0, 1.0, 1.0)
                        ab_surf = self.font.render(ch, True, ab_col)
                        ab_surf.set_alpha(int(energy * 40))
                        screen.blit(ab_surf, (char_x + cdx + ab, y + cdy))
                        screen.blit(ab_surf, (char_x + cdx - ab, y + cdy))

                    ch_glow = self.font.render(ch, True, (
                        min(255, ch_col[0] + 20), min(255, ch_col[1] + 20), min(255, ch_col[2] + 20)))
                    ch_glow.set_alpha(14 + int(highs * 24))
                    screen.blit(ch_glow, (char_x + cdx + 0.7, y + cdy + 0.4))
                    screen.blit(self.font.render(ch, True, ch_col), (char_x + cdx, y + cdy))
                    char_x += self.font.size(ch)[0]
            else:
                screen.blit(self.font.render(text, True, color), (x + dx, y + dy))

        # ── Particles ────────────────────────────────────────────────────
        alive = []
        for p in self.particles:
            p.update()
            if p.alive:
                col = hsv_to_rgb(p.hue, 0.9, 1.0)
                pygame.draw.circle(screen, col, (int(p.x), int(p.y)), max(1, int(p.life * 3)))
                alive.append(p)
        self.particles = alive

        # ── Cursor ───────────────────────────────────────────────────────
        if not self.typing_done or math.sin(self.cursor_phase) > 0:
            cx, cy = self._get_cursor_position(reveal_index)
            cy_s   = cy - self.scroll_y
            if clip_rect.top <= cy_s <= clip_rect.bottom:
                cursor_col = hsv_to_rgb(self.hue_base, 0.3, 1.0)
                cur        = pygame.Surface((2, self.line_height - 4), pygame.SRCALPHA)
                cur.fill((*cursor_col, 210))
                screen.blit(cur, (cx + 1, cy_s + 2))

        screen.set_clip(old_clip)

        # ── Top / bottom fade masks ───────────────────────────────────────
        fade_h = 36
        for fy, rev in [(self.col_y + self.pad_top, False),
                        (self.col_y + self.col_h - fade_h, True)]:
            for i in range(fade_h):
                a = int(200 * (i / fade_h)) if not rev else int(200 * (1 - i / fade_h))
                s = pygame.Surface((self.col_w - 2, 1), pygame.SRCALPHA)
                s.fill((5, 8, 16, a))
                screen.blit(s, (self.col_x, fy + i))

        # ── Loop / reset ─────────────────────────────────────────────────
        if self.scroll_y > self.total_height + 60:
            self.scroll_y     = -(self.col_h * 0.5)
            self.reveal_chars = 0.0
            self.typing_done  = False
            self._sparked.clear()
            self.particles.clear()
