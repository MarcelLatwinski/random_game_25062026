import pygame
from animation import AnimatedSprite
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BULLET, BULLET_WIDTH, BULLET_HEIGHT

class Bullet:
    def __init__(self, center, direction, speed, damage, image=None, animations=None):
        self.image = image
        self.animator = AnimatedSprite(animations, "travel") if animations else None
        self.speed = speed
        self.damage = damage
        self.vx = direction[0] * speed
        self.vy = direction[1] * speed
        self.rect = pygame.Rect(0, 0, BULLET_WIDTH, BULLET_HEIGHT)
        self.rect.center = center
        self.impacting = False
        self.removable = False

    def update(self, platforms, dt=0):
        if self.impacting:
            self.update_animation(dt)
            return not self.removable

        self.rect.x += self.vx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                self.start_impact()
                self.update_animation(dt)
                return not self.removable
        self.rect.y += self.vy
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                self.start_impact()
                self.update_animation(dt)
                return not self.removable

        if not self.is_on_screen():
            return False

        self.update_animation(dt)
        return True

    def start_impact(self):
        if self.impacting:
            return

        self.impacting = True
        self.vx = 0
        self.vy = 0
        if self.animator and self.animator.has_state("impact"):
            self.animator.play_once("impact")
        else:
            self.removable = True

    def update_animation(self, dt):
        if not self.animator:
            return

        if not self.impacting:
            self.animator.play("travel")
        self.animator.update(dt)
        if self.impacting and self.animator.is_finished():
            self.removable = True

    def is_on_screen(self):
        return (
            -50 < self.rect.right
            and self.rect.left < SCREEN_WIDTH + 50
            and -50 < self.rect.bottom
            and self.rect.top < SCREEN_HEIGHT + 50
        )

    def draw(self, surface):
        image = self.animator.current_frame() if self.animator else self.image
        if image:
            if self.vx < 0:
                image = pygame.transform.flip(image, True, False)
            surface.blit(image, self.rect)
        else:
            pygame.draw.rect(surface, COLOR_BULLET, self.rect)
