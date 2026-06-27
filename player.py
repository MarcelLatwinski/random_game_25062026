import math

import pygame
from animation import AnimatedSprite, flipped_surface
from settings import (
    SCREEN_WIDTH,
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    PLAYER_SPEED,
    PLAYER_RUN_SPEED_MULTIPLIER,
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

AIM_ARM_STATES = ("idle", "walk")
DEBUG_AIM_PIVOT = False
BODY_SHOULDER_OFFSET_RATIO = pygame.math.Vector2(0.55, 0.34)
ARM_PIVOT_RATIO = pygame.math.Vector2(0.20, 0.50)
MUZZLE_DISTANCE_RATIO = 0.42
ARM_DRAW_WIDTH_RATIO = 0.70


def rotate_surface_around_pivot(image, angle_degrees, image_pivot, screen_pivot):
    rotation_angle = -angle_degrees
    rotated_image = pygame.transform.rotate(image, rotation_angle)
    pivot_to_center = pygame.math.Vector2(
        image.get_width() / 2 - image_pivot.x,
        image.get_height() / 2 - image_pivot.y,
    )
    rotated_center = pygame.math.Vector2(screen_pivot) + pivot_to_center.rotate(rotation_angle)
    rotated_rect = rotated_image.get_rect(
        center=(round(rotated_center.x), round(rotated_center.y)),
    )
    return rotated_image, rotated_rect


class Player:
    def __init__(
        self,
        x,
        y,
        image=None,
        bullet_image=None,
        animations=None,
        bullet_animations=None,
        arms_image=None,
    ):
        self.image = image
        self.bullet_image = bullet_image
        self.animator = AnimatedSprite(animations, "idle") if animations else None
        self.bullet_animations = bullet_animations
        self.arms_image = self.prepare_arms_image(arms_image)
        self.flipped_arms_image = flipped_surface(self.arms_image) if self.arms_image else None
        self.body_shoulder_offset = pygame.math.Vector2(
            PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x,
            PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y,
        )
        self.arm_pivot = self.calculate_arm_pivot(self.arms_image)
        self.flipped_arm_pivot = self.calculate_flipped_arm_pivot(self.arms_image)
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
        self.run_speed_multiplier = PLAYER_RUN_SPEED_MULTIPLIER
        self.is_running = False
        self.is_dying = False
        self.dead = False
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
        self.reload_font = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.color = COLOR_PLAYER
        self.drop_requested = False

    def prepare_arms_image(self, arms_image):
        if arms_image is None:
            return None

        bounds = arms_image.get_bounding_rect(min_alpha=1)
        if bounds.width > 0 and bounds.height > 0 and bounds.size != arms_image.get_size():
            cropped = pygame.Surface(bounds.size, pygame.SRCALPHA)
            cropped.blit(arms_image, (0, 0), bounds)
            arms_image = cropped

        target_width = max(1, int(round(PLAYER_WIDTH * ARM_DRAW_WIDTH_RATIO)))
        scale = target_width / arms_image.get_width()
        target_size = (
            target_width,
            max(1, int(round(arms_image.get_height() * scale))),
        )
        return pygame.transform.scale(arms_image, target_size)

    def calculate_arm_pivot(self, arms_image):
        if arms_image is None:
            return pygame.math.Vector2()
        return pygame.math.Vector2(
            arms_image.get_width() * ARM_PIVOT_RATIO.x,
            arms_image.get_height() * ARM_PIVOT_RATIO.y,
        )

    def calculate_flipped_arm_pivot(self, arms_image):
        if arms_image is None:
            return pygame.math.Vector2()
        return pygame.math.Vector2(
            arms_image.get_width() - self.arm_pivot.x,
            self.arm_pivot.y,
        )

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
            and not self.is_running
            and not self.is_dying
            and not self.dead
        )

    def shoot(self, target_pos, now):
        if self.current_ammo_in_gun <= 0:
            self.show_reload_prompt()
            return None
        if not self.can_shoot(now):
            return None

        self.facing_right = target_pos[0] >= self.rect.centerx
        origin, direction = self.aim_origin_and_direction(target_pos)
        if origin is None or direction is None:
            return None

        self.current_ammo_in_gun -= 1
        self.next_fire = now + self.fire_cooldown
        return Bullet(
            (round(origin.x), round(origin.y)),
            (direction.x, direction.y),
            self.bullet_speed,
            self.damage,
            image=self.bullet_image,
            animations=self.bullet_animations,
        )

    def aim_origin_and_direction(self, target_pos):
        target = pygame.math.Vector2(target_pos)
        shoulder = self.aim_shoulder_world(target)
        aim_vector = target - shoulder
        if aim_vector.length_squared() <= 0:
            return None, None

        direction = aim_vector.normalize()
        origin = shoulder + direction * (PLAYER_WIDTH * MUZZLE_DISTANCE_RATIO)
        return origin, direction

    def aim_shoulder_world(self, target_pos=None):
        if target_pos is None:
            facing_right = self.facing_right
        else:
            facing_right = target_pos.x >= self.rect.centerx
        offset = self.shoulder_offset(facing_right)
        return pygame.math.Vector2(
            self.rect.left + offset.x,
            self.rect.top + offset.y,
        )

    def shoulder_offset(self, facing_right=None):
        if facing_right is None:
            facing_right = self.facing_right
        if facing_right:
            return pygame.math.Vector2(self.body_shoulder_offset)
        return pygame.math.Vector2(
            PLAYER_WIDTH - self.body_shoulder_offset.x,
            self.body_shoulder_offset.y,
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
            if self.health <= 0:
                self.die()

    def die(self):
        if self.dead or self.is_dying:
            return

        self.health = 0
        self.is_running = False
        self.is_dying = True
        self.vx = 0
        self.vy = 0
        if self.animator and self.animator.has_state("death"):
            self.animator.play_once("death")
        else:
            self.dead = True

    def run_input_active(self, keys):
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        return bool(shift and (left or right))

    def update(self, keys, platforms, now, dt=0, world_width=SCREEN_WIDTH):
        if self.is_dying or self.dead:
            self.vx = 0
            self.update_death_animation(dt)
            self.update_reload_prompt(dt)
            return

        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        self.is_running = self.run_input_active(keys)
        movement_speed = self.speed
        if self.is_running:
            movement_speed *= self.run_speed_multiplier

        self.drop_requested = bool(keys[pygame.K_s] or keys[pygame.K_DOWN])
        self.vx = 0
        if left:
            self.vx = -movement_speed
        if right:
            self.vx = movement_speed

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = -self.jump_strength
            self.on_ground = False
        elif self.drop_requested and self.on_ground and self.vy >= 0:
            self.on_ground = False
            self.vy = 4

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
                if self.vy < 0:
                    self.animator.play("jump")
                else:
                    self.animator.play("fall")
            elif self.is_running and abs(self.vx) > 0:
                self.animator.play("run")
            elif abs(self.vx) > 0:
                self.animator.play("walk")
            else:
                self.animator.play("idle")

        self.animator.update(dt)

    def update_death_animation(self, dt):
        if self.dead:
            return
        if not self.animator or not self.animator.has_state("death"):
            self.dead = True
            return

        if self.animator.current_state != "death":
            self.animator.play_once("death")
        self.animator.update(dt)
        if self.animator.is_finished():
            self.dead = True

    def collide_horizontal(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right

    def collide_vertical(self, platforms):
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            if self.drop_requested and self.vy >= 0 and getattr(platform, "drop_through", True):
                return

            if self.vy > 0:
                self.rect.bottom = platform.rect.top
                self.vy = 0
                self.on_ground = True
            elif self.vy < 0:
                self.rect.top = platform.rect.bottom
                self.vy = 0

    def should_draw_aim_arms(self):
        if not self.arms_image or self.is_running or self.is_dying or self.dead:
            return False

        if self.animator:
            return self.animator.current_state in AIM_ARM_STATES
        return self.on_ground

    def aim_shoulder_screen(self, draw_rect):
        offset = self.shoulder_offset()
        return pygame.math.Vector2(
            draw_rect.left + offset.x,
            draw_rect.top + offset.y,
        )

    def draw_aim_arms(self, surface, draw_rect, target_pos):
        arms_image = self.arms_image if self.facing_right else self.flipped_arms_image
        if arms_image is None:
            return

        shoulder = self.aim_shoulder_screen(draw_rect)
        target = pygame.math.Vector2(target_pos)
        aim_vector = target - shoulder
        if aim_vector.length_squared() <= 0:
            return

        angle_degrees = math.degrees(math.atan2(aim_vector.y, aim_vector.x))
        if self.facing_right:
            pivot = self.arm_pivot
            draw_angle = angle_degrees
        else:
            pivot = self.flipped_arm_pivot
            draw_angle = angle_degrees - 180

        rotated_image, rotated_rect = rotate_surface_around_pivot(
            arms_image,
            draw_angle,
            pivot,
            shoulder,
        )
        surface.blit(rotated_image, rotated_rect)

        if DEBUG_AIM_PIVOT:
            pivot_point = (round(shoulder.x), round(shoulder.y))
            pygame.draw.circle(surface, (255, 40, 40), pivot_point, 4)
            pygame.draw.circle(surface, (40, 120, 255), pivot_point, 2)

    def draw(self, surface, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        draw_arms = self.should_draw_aim_arms()
        mouse_pos = pygame.mouse.get_pos()
        if draw_arms:
            self.facing_right = mouse_pos[0] >= draw_rect.centerx

        image = self.animator.current_frame() if self.animator else self.image
        if image:
            if not self.facing_right:
                image = flipped_surface(image)
            surface.blit(image, draw_rect)
        else:
            color = self.color
            if self.hurt_timer > pygame.time.get_ticks() / 1000:
                color = COLOR_HURT
            pygame.draw.rect(surface, color, draw_rect)

        if draw_arms:
            self.draw_aim_arms(surface, draw_rect, mouse_pos)
        self.draw_reload_prompt(surface, draw_rect)

    def draw_reload_prompt(self, surface, draw_rect):
        if self.reload_prompt_age is None:
            return

        progress = min(1.0, self.reload_prompt_age / RELOAD_PROMPT_DURATION)
        alpha = max(0, int(255 * (1.0 - progress)))
        rise = int(RELOAD_PROMPT_RISE * progress)
        text_surface = self.reload_font.render("RELOAD", True, (255, 50, 50))
        text_surface.set_alpha(alpha)
        text_x = draw_rect.centerx - text_surface.get_width() // 2
        text_y = draw_rect.top - 24 - rise
        surface.blit(text_surface, (text_x, text_y))
