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
        self.panel_h = int(self.height * 0.42)

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))
        self.scroll_y = 0.0

    def draw(self, screen, spectrum):
        bass = float(spectrum[3]) if len(spectrum) > 3 else 0.0
        energy = float(spectrum[4]) if len(spectrum) > 4 else 0.0
        lift = int(energy * 35)

        self.scroll_y += 0.18 + bass * 0.35

        panel = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel.fill((12, 16, 24, 170))
        screen.blit(panel, (self.panel_x, self.panel_y))

        clip_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        x0 = self.panel_x + 25
        y = self.panel_y + 25 - self.scroll_y
        x = x0

        for token, text in self.tokens:
            base = token_color(token)
            color = tuple(min(255, c + lift) for c in base)

            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    surf = self.font.render(part, True, color)
                    screen.blit(surf, (x, y))
                    x += surf.get_width()

                if idx < len(parts) - 1:
                    y += self.line_height
                    x = x0

        screen.set_clip(old_clip)

        total_lines = sum(text.count("\n") for _, text in self.tokens) + 1
        total_height = total_lines * self.line_height

        if self.scroll_y > total_height + 40:
            self.scroll_y = -self.panel_h * 0.35
