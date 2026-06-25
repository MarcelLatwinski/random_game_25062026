import pygame
from settings import PLATFORMS, COLOR_PLATFORM

class Platform:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.color = COLOR_PLATFORM

    def draw(self, surface, image=None):
        if image:
            image_size = (self.rect.width, self.rect.height)
            scaled = pygame.transform.scale(image, image_size)
            surface.blit(scaled, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
