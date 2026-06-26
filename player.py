import pygame
from animation import AnimatedSprite
from settings import (
    SCREEN_WIDTH,
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
    MAGAZINE_SIZE,
    STARTING_MAG_AMMO,
    STARTING_RESERVE_AMMO,
    MAX_RESERVE_AMMO,
    RELOAD_DURATION,
    RELOAD_PROMPT_DURATION,
    RELOAD_PROMPT_RISE,
    COLOR_PLAYER,
    COLOR_HURT,
)
from bullet import Bullet

class Player:
    def __init__(self, x, y, image=None, bullet_image=None, animations=None, bullet_animations=None):
        self.image = image
        self.bullet_image = bullet_image
        self.animator = AnimatedSprite(animations, "idle") if animations else None
        self.bullet_animations = bullet_animations
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.max_health = PLAYER_MAX_HEALTH
        self.health = PLAYER_START_HEALTH
        self.damage_multiplier = 1.0
        self.picked_upgrades = []
        self.facing_right = True
        self.fire_cooldown = PLAYER_FIRE_COOLDOWN
        self.bullet_speed = PLAYER_BULLET_SPEED
        self.speed = PLAYER_SPEED
        self.jump_strength = PLAYER_JUMP_STRENGTH
        self.hurt_timer = 0
        self.hurt_cooldown = HURT_INVINCIBILITY
        self.next_fire = 0
        self.magazine_size = MAGAZINE_SIZE
        self.current_ammo_in_gun = STARTING_MAG_AMMO
        self.reserve_ammo = STARTING_RESERVE_AMMO
        self.max_reserve_ammo = MAX_RESERVE_AMMO
        self.reload_until = 0
        self.reload_prompt_age = None
        self.color = COLOR_PLAYER

    @property
    def damage(self):
        return int(PLAYER_BASE_DAMAGE * self.damage_multiplier)

    def is_reloading(self, now):
        return now < self.reload_until

    def can_shoot(self, now):
        return (
            now >= self.next_fire
            and not self.is_reloading(now)
            and self.current_ammo_in_gun > 0
        )

    def shoot(self, target_pos, now):
        if self.current_ammo_in_gun <= 0:
            self.show_reload_prompt()
            return None
        if not self.can_shoot(now):
            return None

        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist <= 0:
            return None
        direction = (dx / dist, dy / dist)
        self.current_ammo_in_gun -= 1
        self.next_fire = now + self.fire_cooldown
        self.play_action("shoot")
        return Bullet(
            self.rect.center,
            direction,
            self.bullet_speed,
            self.damage,
            image=self.bullet_image,
            animations=self.bullet_animations,
        )

    def reload(self, now):
        missing_ammo = self.magazine_size - self.current_ammo_in_gun
        if missing_ammo <= 0 or self.reserve_ammo <= 0:
            return False

        ammo_to_load = min(missing_ammo, self.reserve_ammo)
        self.current_ammo_in_gun += ammo_to_load
        self.reserve_ammo -= ammo_to_load
        self.reload_until = now + RELOAD_DURATION
        return True

    def show_reload_prompt(self):
        self.reload_prompt_age = 0.0

    def update_reload_prompt(self, dt):
        if self.reload_prompt_age is None:
            return

        self.reload_prompt_age += dt
        if self.reload_prompt_age >= RELOAD_PROMPT_DURATION:
            self.reload_prompt_age = None

    def add_reserve_ammo(self, amount):
        old_reserve = self.reserve_ammo
        self.reserve_ammo = min(self.max_reserve_ammo, self.reserve_ammo + amount)
        return self.reserve_ammo - old_reserve

    def heal(self, amount):
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - old_health

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
            self.play_action("hurt")

    def update(self, keys, platforms, now, dt=0, world_width=SCREEN_WIDTH):
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

        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False

        self.rect.x += self.vx
        self.collide_horizontal(platforms)

        self.vy += GRAVITY
        self.vy = min(self.vy, MAX_FALL_SPEED)
        self.rect.y += self.vy
        self.on_ground = False
        self.collide_vertical(platforms)

        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > world_width:
            self.rect.right = world_width

        self.update_animation(dt)
        self.update_reload_prompt(dt)

    def play_action(self, state):
        if self.animator:
            self.animator.play_once(state)

    def update_animation(self, dt):
        if not self.animator:
            return

        if not self.animator.is_playing_once():
            if not self.on_ground:
                self.animator.play("jump")
            elif abs(self.vx) > 0:
                self.animator.play("run")
            else:
                self.animator.play("idle")

        self.animator.update(dt)

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

    def draw(self, surface, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        image = self.animator.current_frame() if self.animator else self.image
        if image:
            if not self.facing_right:
                image = pygame.transform.flip(image, True, False)
            surface.blit(image, draw_rect)
        else:
            color = self.color
            if self.hurt_timer > pygame.time.get_ticks() / 1000:
                color = COLOR_HURT
            pygame.draw.rect(surface, color, draw_rect)
        self.draw_reload_prompt(surface, draw_rect)

    def draw_reload_prompt(self, surface, draw_rect):
        if self.reload_prompt_age is None:
            return

        progress = min(1.0, self.reload_prompt_age / RELOAD_PROMPT_DURATION)
        alpha = max(0, int(255 * (1.0 - progress)))
        rise = int(RELOAD_PROMPT_RISE * progress)
        font = pygame.font.SysFont("Segoe UI", 28, bold=True)
        text_surface = font.render("RELOAD", True, (255, 50, 50))
        text_surface.set_alpha(alpha)
        text_x = draw_rect.centerx - text_surface.get_width() // 2
        text_y = draw_rect.top - 24 - rise
        surface.blit(text_surface, (text_x, text_y))
