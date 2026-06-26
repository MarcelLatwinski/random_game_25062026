import pygame
from settings import (
    COLOR_PLATFORM,
    COLOR_PLATFORM_OUTLINE,
)

class Platform:
    def __init__(self, rect, platform_id):
        self.rect = pygame.Rect(rect)
        self.id = platform_id
        self.color = COLOR_PLATFORM
        self.outline_color = COLOR_PLATFORM_OUTLINE

    def draw(self, surface, image=None, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        if image:
            image_size = (self.rect.width, self.rect.height)
            scaled = pygame.transform.scale(image, image_size)
            surface.blit(scaled, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)
        pygame.draw.rect(surface, self.outline_color, draw_rect, 4)

