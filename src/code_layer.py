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

        self.scroll_y = -20.0
        self.time = 0.0

        self.total_chars = 0
        self.reveal_chars = 0.0
        self.typing_done = False
        self.cursor_phase = 0.0

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
                        "char_start": self.total_chars,
                        "char_len": len(part),
                    })

                    self.total_chars += len(part)
                    x += width

                if idx < len(parts) - 1:
                    y += self.line_height
                    x = x0
                    self.total_chars += 1

        self.total_height = max(0, y - y0) + self.line_height

    def _token_motion_scale(self, token):
        if token in Token.Keyword:
            return 1.00
        if token in Token.Name.Function:
            return 1.08
        if token in Token.Name.Class:
            return 1.02
        if token in Token.Operator:
            return 0.90
        if token in Token.Comment:
            return 0.42
        if token in Token.String:
            return 0.65
        return 0.55

    def _token_is_shimmered(self, token):
        return (
            token in Token.Keyword
            or token in Token.Name.Function
            or token in Token.Operator
            or token in Token.Name.Class
        )

    def _visible_subtext(self, item, reveal_index):
        start = item["char_start"]
        end = start + item["char_len"]

        if reveal_index <= start:
            return ""
        if reveal_index >= end:
            return item["text"]

        visible_count = max(0, reveal_index - start)
        return item["text"][:visible_count]

    def _get_cursor_position(self, reveal_index):
        for item in self.items:
            start = item["char_start"]
            end = start + item["char_len"]

            if start <= reveal_index <= end:
                partial = item["text"][: max(0, reveal_index - start)]
                partial_width = self.font.size(partial)[0]
                return item["x"] + partial_width, item["y"]

        if self.items:
            last = self.items[-1]
            return last["x"] + self.font.size(last["text"])[0], last["y"]

        return self.panel_x + 40, self.panel_y + 40

    def draw(self, screen, spectrum, mode_name="PLASMA"):
        bass = float(spectrum[2]) if len(spectrum) > 2 else 0.0
        mids = float(spectrum[8]) if len(spectrum) > 8 else bass
        highs = float(spectrum[20]) if len(spectrum) > 20 else mids
        energy = (bass * 0.50) + (mids * 0.35) + (highs * 0.15)

        dt = 0.016
        self.time += dt
        self.cursor_phase += dt * 3.2

        if not self.typing_done:
            cps = 18 + bass * 22 + mids * 10
            self.reveal_chars += cps * dt

            # slow ambient scroll while typing
            self.scroll_y += 0.06 + bass * 0.07

            if self.reveal_chars >= self.total_chars:
                self.reveal_chars = float(self.total_chars)
                self.typing_done = True
        else:
            # stronger scroll once typing is finished
            self.scroll_y += 0.16 + bass * 0.22

        reveal_index = int(self.reveal_chars)

        panel = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel.fill((9, 13, 22, 96))
        pygame.draw.line(panel, (120, 150, 210, 55), (0, 0), (self.panel_w, 0), 2)
        pygame.draw.line(panel, (70, 90, 140, 26), (0, 1), (self.panel_w, 1), 1)
        pygame.draw.rect(panel, (85, 110, 160, 28), panel.get_rect(), 1, border_radius=10)
        screen.blit(panel, (self.panel_x, self.panel_y))

        label = self.font_small.render(f"CODEWAVE // {mode_name}", True, (150, 170, 210))
        label.set_alpha(170)
        screen.blit(label, (self.panel_x + 18, self.panel_y + 6))

        clip_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for item in self.items:
            token = item["token"]
            base = item["base_color"]
            x = item["x"]
            y = item["y"] - self.scroll_y
            seed = item["seed"]

            if y < self.panel_y - 40 or y > self.panel_y + self.panel_h + 20:
                continue

            text = self._visible_subtext(item, reveal_index)
            if not text:
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

            glow = self.font.render(text, True, (
                min(255, color[0] + 10),
                min(255, color[1] + 10),
                min(255, color[2] + 10),
            ))
            glow.set_alpha(26 + int(highs * 28))
            screen.blit(glow, (x + dx + 0.8, y + dy + 0.5))

            if self._token_is_shimmered(token):
                char_x = x + dx
                for idx, ch in enumerate(text):
                    char_seed = seed + idx * 0.31
                    char_dx = math.sin(self.time * 2.1 + char_seed * 2.4) * (0.25 + highs * 0.9)
                    char_dy = math.cos(self.time * 1.7 + char_seed * 1.9) * (0.12 + mids * 0.45)

                    rr = int(color[0] + math.sin(self.time * 2.4 + char_seed) * (4 + highs * 16))
                    gg = int(color[1] + math.sin(self.time * 2.0 + char_seed * 1.2) * (3 + mids * 10))
                    bb = int(color[2] + math.sin(self.time * 2.7 + char_seed * 0.9) * (5 + bass * 14))

                    ch_color = (
                        max(0, min(255, rr)),
                        max(0, min(255, gg)),
                        max(0, min(255, bb)),
                    )

                    ch_glow = self.font.render(ch, True, (
                        min(255, ch_color[0] + 18),
                        min(255, ch_color[1] + 18),
                        min(255, ch_color[2] + 18),
                    ))
                    ch_glow.set_alpha(20 + int(highs * 24))
                    screen.blit(ch_glow, (char_x + char_dx + 0.7, y + char_dy + 0.4))

                    ch_surf = self.font.render(ch, True, ch_color)
                    screen.blit(ch_surf, (char_x + char_dx, y + char_dy))

                    char_x += self.font.size(ch)[0]
            else:
                surf = self.font.render(text, True, color)
                screen.blit(surf, (x + dx, y + dy))

        if not self.typing_done or math.sin(self.cursor_phase) > 0:
            cx, cy = self._get_cursor_position(reveal_index)
            cy -= self.scroll_y

            if self.panel_y <= cy <= self.panel_y + self.panel_h:
                cursor_h = self.line_height - 6
                cursor = pygame.Surface((2, cursor_h), pygame.SRCALPHA)
                cursor.fill((190, 220, 255, 210))
                screen.blit(cursor, (cx + 1, cy + 3))

        screen.set_clip(old_clip)

        if self.scroll_y > self.total_height + 60:
            self.scroll_y = -self.panel_h * 0.45
            self.reveal_chars = 0.0
            self.typing_done = False
