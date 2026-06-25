import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BULLET

class Bullet:
    def __init__(self, center, direction, speed, damage, image=None):
        self.image = image
        self.speed = speed
        self.damage = damage
        self.vx = direction[0] * speed
        self.vy = direction[1] * speed
        self.rect = pygame.Rect(0, 0, 12, 6)
        self.rect.center = center

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        return self.is_on_screen()

    def is_on_screen(self):
        return (
            -50 < self.rect.right
            and self.rect.left < SCREEN_WIDTH + 50
            and -50 < self.rect.bottom
            and self.rect.top < SCREEN_HEIGHT + 50
        )

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            pygame.draw.rect(surface, COLOR_BULLET, self.rect)
