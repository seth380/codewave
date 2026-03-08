import math
import pygame
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


def token_color(token):
    if token in Token.Keyword:
        return (255, 140, 110)
    if token in Token.Name.Function:
        return (120, 200, 255)
    if token in Token.Name.Class:
        return (255, 210, 120)
    if token in Token.String:
        return (140, 220, 160)
    if token in Token.Comment:
        return (120, 130, 140)
    if token in Token.Number:
        return (255, 190, 120)
    if token in Token.Operator:
        return (220, 220, 220)
    return (210, 210, 210)


class CodeLayer:
    def __init__(self, path, width, height):
        pygame.font.init()

        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("consolas", 22)
        self.line_height = 28

        self.panel_x = 40
        self.panel_y = 35
        self.panel_w = self.width - 80
        self.panel_h = int(self.height * 0.30)

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))
        self.items = []
        self.scroll_y = 0.0
        self.time = 0.0

        self._build_layout()

    def _build_layout(self):
        x0 = self.panel_x + 28
        y0 = self.panel_y + 24
        x = x0
        y = y0

        for token, text in self.tokens:
            parts = text.split("\n")

            for idx, part in enumerate(parts):
                if part:
                    base = token_color(token)
                    width, _ = self.font.size(part)

                    # per-token seed from position + token identity
                    seed = (x * 0.013) + (y * 0.021) + (len(part) * 0.17)

                    self.items.append({
                        "token": token,
                        "text": part,
                        "base_color": base,
                        "x": x,
                        "y": y,
                        "seed": seed,
                    })

                    x += width

                if idx < len(parts) - 1:
                    y += self.line_height
                    x = x0

        self.total_height = max(0, y - y0) + self.line_height

    def _token_motion_scale(self, token):
        if token in Token.Keyword:
            return 1.15
        if token in Token.Name.Function:
            return 1.25
        if token in Token.Name.Class:
            return 1.15
        if token in Token.Operator:
            return 0.95
        if token in Token.Comment:
            return 0.55
        if token in Token.String:
            return 0.80
        return 0.70

    def draw(self, screen, spectrum):
        bass = float(spectrum[2]) if len(spectrum) > 2 else 0.0
        mids = float(spectrum[8]) if len(spectrum) > 8 else bass
        highs = float(spectrum[20]) if len(spectrum) > 20 else mids

        energy = (bass * 0.5) + (mids * 0.35) + (highs * 0.15)

        self.time += 0.016
        self.scroll_y += 0.16 + bass * 0.30

        panel = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel.fill((10, 14, 22, 118))
        screen.blit(panel, (self.panel_x, self.panel_y))

        clip_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for item in self.items:
            token = item["token"]
            text = item["text"]
            base = item["base_color"]
            x = item["x"]
            y = item["y"] - self.scroll_y
            seed = item["seed"]

            if y < self.panel_y - 40 or y > self.panel_y + self.panel_h + 20:
                continue

            motion_scale = self._token_motion_scale(token)

            # subtle spatial motion
            dx = math.sin(self.time * 1.6 + seed * 1.7) * (0.9 + bass * 2.8) * 0.35 * motion_scale
            dy = math.cos(self.time * 1.2 + seed * 1.3) * (0.6 + mids * 1.8) * 0.22 * motion_scale

            # rgb noise by token type + position
            r_shift = math.sin(self.time * 1.8 + x * 0.011 + y * 0.017 + seed) * (10 + 28 * highs)
            g_shift = math.sin(self.time * 1.5 + x * 0.009 + y * 0.013 + seed * 1.2) * (8 + 20 * mids)
            b_shift = math.sin(self.time * 2.0 + x * 0.015 + y * 0.010 + seed * 0.8) * (12 + 26 * bass)

            pulse = 10 + int(24 * energy)

            color = (
                max(0, min(255, int(base[0] + r_shift + pulse))),
                max(0, min(255, int(base[1] + g_shift + pulse))),
                max(0, min(255, int(base[2] + b_shift + pulse))),
            )

            # soft ghost layer for shimmer
            ghost_color = (
                min(255, color[0] + 18),
                min(255, color[1] + 18),
                min(255, color[2] + 18),
            )

            ghost = self.font.render(text, True, ghost_color)
            ghost.set_alpha(40 + int(highs * 50))
            screen.blit(ghost, (x + dx + 1.2, y + dy + 0.8))

            surf = self.font.render(text, True, color)
            screen.blit(surf, (x + dx, y + dy))

        screen.set_clip(old_clip)

        if self.scroll_y > self.total_height + 50:
            self.scroll_y = -self.panel_h * 0.45
