import pygame


class Pickup:
    def __init__(self, pickup_type, x, y, width, height, amount, image=None):
        self.type = pickup_type
        self.amount = amount
        self.image = image
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.midbottom = (x, y)
        self.collected = False

    def update(self):
        pass

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
        if self.image:
            surface.blit(self.image, draw_rect)
            return

        color = (230, 190, 60) if self.type == "ammo" else (230, 70, 70)
        pygame.draw.rect(surface, color, draw_rect)
