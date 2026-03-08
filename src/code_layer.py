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

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))

    def draw(self, screen, spectrum):
        energy = float(spectrum[4]) if len(spectrum) > 4 else 0.0
        lift = int(energy * 35)

        panel = pygame.Surface((self.width - 80, int(self.height * 0.42)), pygame.SRCALPHA)
        panel.fill((12, 16, 24, 170))
        screen.blit(panel, (40, 35))

        x0 = 65
        y = 60
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
