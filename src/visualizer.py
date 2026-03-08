import pygame
import numpy as np


class SpectrumVisualizer:

    def __init__(self, width, height):

        self.width = width
        self.height = height

        self.bar_count = 60
        self.spectrum = np.zeros(self.bar_count)


    def update(self, spectrum):

        step = len(spectrum) // self.bar_count

        for i in range(self.bar_count):

            val = np.mean(spectrum[i*step:(i+1)*step])

            # smoothing
            self.spectrum[i] = self.spectrum[i]*0.7 + val*0.3


    def draw(self, screen):

        bar_width = self.width / self.bar_count

        for i, val in enumerate(self.spectrum):

            h = val * self.height * 0.8

            x = i * bar_width

            rect = pygame.Rect(
                x,
                self.height - h,
                bar_width - 2,
                h
            )

            color = (80 + int(val*175), 120, 255)

            pygame.draw.rect(screen, color, rect)
