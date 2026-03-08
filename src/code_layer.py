import math
import pygame
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


def token_color(token):
    if token in Token.Keyword:
        return (255, 150, 120)
    if token in Token.Name.Function:
        return (120, 210, 255)
    if token in Token.Name.Class:
        return (255, 220, 140)
    if token in Token.String:
        return (150, 225, 175)
    if token in Token.Comment:
        return (115, 125, 138)
    if token in Token.Number:
        return (255, 195, 130)
    if token in Token.Operator:
        return (220, 224, 232)
    return (214, 218, 228)


class CodeLayer:
    def __init__(self, path, width, height):
        pygame.font.init()

        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("consolas", 22)
        self.font_small = pygame.font.SysFont("consolas", 16)
        self.line_height = 28

        self.panel_x = 40
        self.panel_y = 34
        self.panel_w = self.width - 80
        self.panel_h = int(self.height * 0.29)

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))
        self.items = []
        self.scroll_y = 0.0
        self.time = 0.0

        self._build_layout()

    def _build_layout(self):
        x0 = self.panel_x + 30
        y0 = self.panel_y + 26
        x = x0
        y = y0

        for token, text in self.tokens:
            parts = text.split("\n")

            for idx, part in enumerate(parts):
                if part:
                    base = token_color(token)
                    width, _ = self.font.size(part)
                    seed = (x * 0.012) + (y * 0.017) + (len(part) * 0.19)

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
            return 1.00
        if token in Token.Name.Function:
            return 1.08
        if token in Token.Name.Class:
            return 1.02
        if token in Token.Operator:
            return 0.85
        if token in Token.Comment:
            return 0.45
        if token in Token.String:
            return 0.65
        return 0.55

    def draw(self, screen, spectrum, mode_name="PLASMA"):
        bass = float(spectrum[2]) if len(spectrum) > 2 else 0.0
        mids = float(spectrum[8]) if len(spectrum) > 8 else bass
        highs = float(spectrum[20]) if len(spectrum) > 20 else mids
        energy = (bass * 0.50) + (mids * 0.35) + (highs * 0.15)

        self.time += 0.016
        self.scroll_y += 0.11 + bass * 0.18

        panel = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel.fill((9, 13, 22, 96))

        # soft top highlight
        pygame.draw.line(panel, (120, 150, 210, 55), (0, 0), (self.panel_w, 0), 2)
        pygame.draw.line(panel, (70, 90, 140, 26), (0, 1), (self.panel_w, 1), 1)

        # faint inner border
        pygame.draw.rect(panel, (85, 110, 160, 28), panel.get_rect(), 1, border_radius=10)

        screen.blit(panel, (self.panel_x, self.panel_y))

        # tiny label
        label = self.font_small.render(f"CODEWAVE // {mode_name}", True, (150, 170, 210))
        label.set_alpha(170)
        screen.blit(label, (self.panel_x + 18, self.panel_y + 6))

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

            dx = math.sin(self.time * 1.15 + seed * 1.35) * (0.35 + bass * 0.90) * motion_scale
            dy = math.cos(self.time * 0.92 + seed * 1.10) * (0.18 + mids * 0.45) * motion_scale

            r_shift = math.sin(self.time * 1.20 + x * 0.007 + seed) * (5 + 8 * highs)
            g_shift = math.sin(self.time * 1.05 + y * 0.006 + seed * 1.1) * (4 + 6 * mids)
            b_shift = math.sin(self.time * 1.35 + x * 0.008 + y * 0.005 + seed * 0.9) * (6 + 10 * bass)

            pulse = 6 + int(16 * energy)

            color = (
                max(0, min(255, int(base[0] + r_shift + pulse))),
                max(0, min(255, int(base[1] + g_shift + pulse))),
                max(0, min(255, int(base[2] + b_shift + pulse))),
            )

            # elegant soft glow
            glow = self.font.render(text, True, (
                min(255, color[0] + 10),
                min(255, color[1] + 10),
                min(255, color[2] + 10),
            ))
            glow.set_alpha(26 + int(highs * 28))
            screen.blit(glow, (x + dx + 0.8, y + dy + 0.5))

            surf = self.font.render(text, True, color)
            screen.blit(surf, (x + dx, y + dy))

        screen.set_clip(old_clip)

        if self.scroll_y > self.total_height + 40:
            self.scroll_y = -self.panel_h * 0.42
