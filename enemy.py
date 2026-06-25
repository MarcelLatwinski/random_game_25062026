import pygame
import random
from settings import (
    GRAVITY,
    MAX_FALL_SPEED,
    WALKER_HP,
    WALKER_SPEED,
    WALKER_DAMAGE,
    WALKER_JUMP_INTERVAL,
    WALKER_JUMP_STRENGTH,
    WALKER_WIDTH,
    WALKER_HEIGHT,
    TANK_HP,
    TANK_SPEED,
    TANK_DAMAGE,
    TANK_JUMP_INTERVAL,
    TANK_JUMP_STRENGTH,
    TANK_WIDTH,
    TANK_HEIGHT,
    FLYING_HP,
    FLYING_SPEED,
    FLYING_DAMAGE,
    FLYING_WIDTH,
    FLYING_HEIGHT,
    COLOR_WALKER,
    COLOR_TANK,
    COLOR_FLYING,
)

class Enemy:
    def __init__(self, x, y, width, height, hp, speed, damage, image=None, color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.hp = hp
        self.speed = speed
        self.damage = damage
        self.image = image
        self.color = color
        self.vx = 0
        self.vy = 0
        self.on_ground = False

    def take_damage(self, amount):
        self.hp -= amount

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)

class GroundZombie(Enemy):
    def __init__(self, x, y, width, height, hp, speed, damage, jump_interval, jump_strength, image=None, color=(255, 255, 255)):
        super().__init__(x, y, width, height, hp, speed, damage, image=image, color=color)
        self.jump_timer = random.uniform(*jump_interval)
        self.jump_interval = jump_interval
        self.jump_strength = jump_strength

    def update(self, player, platforms, dt):
        if player.rect.centerx > self.rect.centerx + 5:
            self.vx = self.speed
        elif player.rect.centerx < self.rect.centerx - 5:
            self.vx = -self.speed
        else:
            self.vx = 0

        self.rect.x += self.vx
        self.collide_horizontal(platforms)

        self.vy += GRAVITY
        self.vy = min(self.vy, MAX_FALL_SPEED)
        self.rect.y += self.vy
        self.on_ground = False
        self.collide_vertical(platforms)

        self.jump_timer -= dt
        if self.jump_timer <= 0:
            self.try_jump(player)
            self.jump_timer = random.uniform(*self.jump_interval)

    def try_jump(self, player):
        if self.on_ground and player.rect.centery + 20 < self.rect.centery:
            self.vy = -self.jump_strength
            self.on_ground = False

    def collide_horizontal(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right

    def collide_vertical(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:
                    self.rect.bottom = platform.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = platform.rect.bottom
                    self.vy = 0

class WalkerZombie(GroundZombie):
    def __init__(self, x, y, image=None):
        super().__init__(x, y, WALKER_WIDTH, WALKER_HEIGHT, WALKER_HP, WALKER_SPEED, WALKER_DAMAGE, WALKER_JUMP_INTERVAL, WALKER_JUMP_STRENGTH, image=image, color=COLOR_WALKER)

class TankZombie(GroundZombie):
    def __init__(self, x, y, image=None):
        super().__init__(x, y, TANK_WIDTH, TANK_HEIGHT, TANK_HP, TANK_SPEED, TANK_DAMAGE, TANK_JUMP_INTERVAL, TANK_JUMP_STRENGTH, image=image, color=COLOR_TANK)

class FlyingZombie(Enemy):
    def __init__(self, x, y, image=None):
        super().__init__(x, y, FLYING_WIDTH, FLYING_HEIGHT, FLYING_HP, FLYING_SPEED, FLYING_DAMAGE, image=image, color=COLOR_FLYING)

    def update(self, player, platforms, dt):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance > 0:
            self.rect.x += int((dx / distance) * self.speed)
            self.rect.y += int((dy / distance) * self.speed)
