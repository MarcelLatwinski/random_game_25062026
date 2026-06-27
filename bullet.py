import pygame
from animation import AnimatedSprite, flipped_surface
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BULLET, BULLET_WIDTH, BULLET_HEIGHT

MAX_IMPACT_TIME = 0.35


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
        self.impact_age = 0.0
        self.removable = False

    def update(self, platforms, dt=0, world_width=SCREEN_WIDTH):
        if self.impacting:
            self.impact_age += dt
            self.update_animation(dt)
            if self.impact_age >= MAX_IMPACT_TIME:
                self.removable = True
            return not self.removable

        self.rect.x += self.vx
        self.rect.y += self.vy

        if not self.is_in_world(world_width):
            return False

        self.update_animation(dt)
        return True

    def start_impact(self):
        if self.impacting:
            return

        self.impacting = True
        self.impact_age = 0.0
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

    def is_in_world(self, world_width):
        return (
            -50 < self.rect.right
            and self.rect.left < world_width + 50
            and -50 < self.rect.bottom
            and self.rect.top < SCREEN_HEIGHT + 50
        )

    def draw(self, surface, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        image = self.animator.current_frame() if self.animator else self.image
        if image:
            if self.vx < 0:
                image = flipped_surface(image)
            surface.blit(image, draw_rect)
        else:
            pygame.draw.rect(surface, COLOR_BULLET, draw_rect)
