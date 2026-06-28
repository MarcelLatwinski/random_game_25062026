import math

import pygame


PICKUP_FLOAT_AMPLITUDE = 6
PICKUP_FLOAT_SPEED = 2.8


class Pickup:
    def __init__(self, pickup_type, x, y, width, height, amount, image=None):
        self.type = pickup_type
        self.amount = amount
        self.image = image
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.midbottom = (x, y)
        self.collected = False
        self.float_age = (x * 0.013 + y * 0.017) % (math.pi * 2)
        self.float_offset_y = 0

    def update(self, dt=0):
        self.float_age += PICKUP_FLOAT_SPEED * dt
        self.float_offset_y = round(math.sin(self.float_age) * PICKUP_FLOAT_AMPLITUDE)

    def check_collision_with_player(self, player):
        return self.rect.colliderect(player.rect)

    def collect(self, player):
        if self.type == "ammo":
            added = player.add_reserve_ammo(self.amount)
            self.collected = added > 0
        elif self.type == "health":
            healed = player.heal(self.amount)
            self.collected = healed > 0
        return self.collected

    def draw(self, surface, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        draw_rect.y += self.float_offset_y
        if self.image:
            surface.blit(self.image, draw_rect)
            return

        color = (230, 190, 60) if self.type == "ammo" else (230, 70, 70)
        pygame.draw.rect(surface, color, draw_rect)
