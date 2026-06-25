import pygame
from settings import (
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    PLAYER_SPEED,
    PLAYER_JUMP_STRENGTH,
    GRAVITY,
    MAX_FALL_SPEED,
    PLAYER_BASE_DAMAGE,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_BULLET_SPEED,
    PLAYER_MAX_HEALTH,
    PLAYER_START_HEALTH,
    HURT_INVINCIBILITY,
    COLOR_PLAYER,
    COLOR_HURT,
)
from bullet import Bullet

class Player:
    def __init__(self, x, y, image=None, bullet_image=None):
        self.image = image
        self.bullet_image = bullet_image
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.max_health = PLAYER_MAX_HEALTH
        self.health = PLAYER_START_HEALTH
        self.damage_multiplier = 1.0
        self.fire_cooldown = PLAYER_FIRE_COOLDOWN
        self.bullet_speed = PLAYER_BULLET_SPEED
        self.speed = PLAYER_SPEED
        self.jump_strength = PLAYER_JUMP_STRENGTH
        self.hurt_timer = 0
        self.hurt_cooldown = HURT_INVINCIBILITY
        self.next_fire = 0
        self.color = COLOR_PLAYER

    @property
    def damage(self):
        return int(PLAYER_BASE_DAMAGE * self.damage_multiplier)

    def can_shoot(self, now):
        return now >= self.next_fire

    def shoot(self, target_pos, now):
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist <= 0:
            return None
        direction = (dx / dist, dy / dist)
        self.next_fire = now + self.fire_cooldown
        return Bullet(self.rect.center, direction, self.bullet_speed, self.damage, image=self.bullet_image)

    def apply_upgrade(self, effect_id):
        if effect_id == "bigger_heart":
            self.max_health += 25
            self.health = min(self.health + 25, self.max_health)
        elif effect_id == "stronger_bullets":
            self.damage_multiplier *= 1.2
        elif effect_id == "faster_trigger":
            self.fire_cooldown = max(0.05, self.fire_cooldown * 0.85)
        elif effect_id == "runners_boots":
            self.speed *= 1.1
        elif effect_id == "spring_legs":
            self.jump_strength *= 1.08
        elif effect_id == "quick_rounds":
            self.bullet_speed *= 1.15
        elif effect_id == "medkit":
            self.health = min(self.health + 50, self.max_health)

    def apply_hurt(self, amount, now):
        if now >= self.hurt_timer:
            self.health -= amount
            self.hurt_timer = now + self.hurt_cooldown

    def update(self, keys, platforms, now):
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        self.vx = 0
        if left:
            self.vx = -self.speed
        if right:
            self.vx = self.speed

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = -self.jump_strength
            self.on_ground = False

        self.rect.x += self.vx
        self.collide_horizontal(platforms)

        self.vy += GRAVITY
        self.vy = min(self.vy, MAX_FALL_SPEED)
        self.rect.y += self.vy
        self.on_ground = False
        self.collide_vertical(platforms)

        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > 1280:
            self.rect.right = 1280

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

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            color = self.color
            if self.hurt_timer > pygame.time.get_ticks() / 1000:
                color = COLOR_HURT
            pygame.draw.rect(surface, color, self.rect)
