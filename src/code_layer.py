import pygame
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


TOKEN_COLORS = {
    Token.Keyword: (255,120,120),
    Token.Name: (220,220,220),
    Token.Comment: (120,140,120),
    Token.String: (140,220,140),
    Token.Number: (255,200,120)
}


class CodeLayer:

    def __init__(self, path, width, height):

        pygame.font.init()

        self.font = pygame.font.SysFont("consolas", 20)

        with open(path, "r") as f:
            code = f.read()

        self.tokens = list(lex(code, PythonLexer()))

        self.width = width
        self.height = height


    def draw(self, screen, spectrum):

        x = 40
        y = 40

        energy = spectrum[3] if len(spectrum) > 3 else 0

        brightness = int(180 + energy*75)

        for token, text in self.tokens:

            color = TOKEN_COLORS.get(token, (200,200,200))

            color = tuple(min(255, c + brightness//6) for c in color)

            lines = text.split("\n")

            for i, line in enumerate(lines):

                surf = self.font.render(line, True, color)

                screen.blit(surf, (x, y))

                if i < len(lines)-1:
                    y += 24
                    x = 40
                else:
                    x += surf.get_width()

        # reset position next frame
