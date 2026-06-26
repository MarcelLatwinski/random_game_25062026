import pygame
from settings import (
    PLATFORMS,
    COLOR_PLATFORM,
    COLOR_PLATFORM_OUTLINE,
)

class Platform:
    def __init__(self, rect, platform_id):
        self.rect = pygame.Rect(rect)
        self.id = platform_id
        self.color = COLOR_PLATFORM
        self.outline_color = COLOR_PLATFORM_OUTLINE

    def draw(self, surface, image=None):
        if image:
            image_size = (self.rect.width, self.rect.height)
            scaled = pygame.transform.scale(image, image_size)
            surface.blit(scaled, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, self.outline_color, self.rect, 4)


