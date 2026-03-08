import pygame
from .audio import AudioEngine
from .visualizer import SpectrumVisualizer
from .code_layer import CodeLayer


WIDTH = 1200
HEIGHT = 700


def run():

    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CodeWave")

    clock = pygame.time.Clock()

    audio = AudioEngine()
    vis = SpectrumVisualizer(WIDTH, HEIGHT)
    code = CodeLayer("example_code.py", WIDTH, HEIGHT)

    running = True

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        spectrum = audio.get_spectrum()

        vis.update(spectrum)

        screen.fill((10,10,15))

        vis.draw(screen)
        code.draw(screen, spectrum)

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
