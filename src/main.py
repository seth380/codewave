import pygame
from .audio import AudioEngine
from .visualizer import SpectrumVisualizer
from .code_layer import CodeLayer


WIDTH = 1400
HEIGHT = 820


def draw_background(screen, width, height, t):
    screen.fill((6, 8, 14))

    for i in range(0, height, 3):
        amt = i / max(1, height)
        color = (
            int(8 + amt * 10),
            int(10 + amt * 18),
            int(18 + amt * 28),
        )
        pygame.draw.line(screen, color, (0, i), (width, i))

    cx = width // 2
    cy = int(height * 0.72)
    r = 90 + int((t % 120) * 0.35)
    pygame.draw.circle(screen, (22, 28, 42), (cx, cy), r, 1)
    pygame.draw.circle(screen, (16, 22, 34), (cx, cy), r + 40, 1)


def run():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CodeWave")

    clock = pygame.time.Clock()

    audio = AudioEngine()
    vis = SpectrumVisualizer(WIDTH, HEIGHT)
    code = CodeLayer("example_code.py", WIDTH, HEIGHT)

    running = True
    frame = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    vis.set_mode("bars")
                elif event.key == pygame.K_2:
                    vis.set_mode("plasma")
                elif event.key == pygame.K_SPACE:
                    vis.toggle_mode()

        spectrum = audio.get_spectrum()
        vis.update(spectrum)

        draw_background(screen, WIDTH, HEIGHT, frame)
        vis.draw(screen)
        code.draw(screen, spectrum)

        pygame.display.flip()
        clock.tick(60)
        frame += 1

    pygame.quit()
