import pygame
from .audio import AudioEngine
from .visualizer import SpectrumVisualizer
from .code_layer import CodeLayer

WIDTH  = 1400
HEIGHT = 820

# Fraction that separates left code column from right visualizer panel
SPLIT  = 0.36
SPLIT_X = int(WIDTH * SPLIT)


def draw_background(screen, width, height, split_x, t):
    """Dark gradient background across the full screen."""
    screen.fill((5, 7, 13))
    for i in range(0, height, 2):
        amt   = i / max(1, height)
        color = (
            int(8  + amt * 10),
            int(11 + amt * 16),
            int(18 + amt * 24),
        )
        pygame.draw.line(screen, color, (0, i), (width, i))

    pass  # atmosphere handled by ink fluid layer


def draw_vignette(screen, width, height):
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    steps = 18
    for i in range(steps):
        pad   = i * 14
        alpha = int(6 + i * 3.2)
        pygame.draw.rect(
            overlay,
            (4, 6, 10, alpha),
            pygame.Rect(pad, pad, width - pad * 2, height - pad * 2),
            width=18,
            border_radius=24,
        )
    screen.blit(overlay, (0, 0))


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CodeWave")
    clock = pygame.time.Clock()

    audio = AudioEngine()
    vis   = SpectrumVisualizer(WIDTH, HEIGHT)
    code  = CodeLayer("example_code.py", WIDTH, HEIGHT)

    running = True
    frame   = 0

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

        draw_background(screen, WIDTH, HEIGHT, SPLIT_X, frame)

        # Visualizer draws into the right panel (handles its own clipping)
        vis.draw(screen)

        draw_vignette(screen, WIDTH, HEIGHT)

        mode_name = "PLASMA" if vis.mode == "plasma" else "BARS"

        # Code column draws over everything on the left — semi-opaque bg
        # means the visualizer bleeds through subtly at the seam
        code.draw(screen, spectrum, mode_name=mode_name)

        pygame.display.flip()
        clock.tick(60)
        frame += 1

    pygame.quit()
