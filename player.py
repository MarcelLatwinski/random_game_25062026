import math
import json
from pathlib import Path

import pygame
import settings
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
    RELOAD_DURATION,
    RELOAD_PROMPT_DURATION,
    RELOAD_PROMPT_RISE,
    COLOR_PLAYER,
    COLOR_HURT,
)
from bullet import Bullet

AIM_ARM_STATES = ("idle", "walk")
AIM_BODY_FRAME_INDICES = {
    "idle": (0,),
    "walk": (1, 2, 3, 2),
    "run": (4, 5, 6, 7),
    "jump": (8, 9),
    "fall": (10, 11),
    "death": (12, 13, 14, 15),
}
AIM_BODY_FRAME_COUNT = 12
DEFAULT_BODY_SHOULDER_RATIO = pygame.math.Vector2(0.44, 0.40)
DEFAULT_ARM_PIVOT_RATIO = pygame.math.Vector2(0.08, 0.50)


def _vector2_from_sequence(value, fallback):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return pygame.math.Vector2(fallback)
    try:
        return pygame.math.Vector2(float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return pygame.math.Vector2(fallback)


def _default_body_shoulder_offsets(frame_width, frame_height):
    fallback = pygame.math.Vector2(
        DEFAULT_BODY_SHOULDER_RATIO.x * frame_width,
        DEFAULT_BODY_SHOULDER_RATIO.y * frame_height,
    )
    return {
        frame_index: pygame.math.Vector2(fallback)
        for frame_index in range(AIM_BODY_FRAME_COUNT)
    }


def _scaled_body_offsets(body_offsets, frame_width, frame_height):
    scale_x = PLAYER_WIDTH / frame_width if frame_width else 1
    scale_y = PLAYER_HEIGHT / frame_height if frame_height else 1
    return {
        frame_index: pygame.math.Vector2(offset.x * scale_x, offset.y * scale_y)
        for frame_index, offset in body_offsets.items()
    }


def _load_aim_config():
    """
    Load shoulder/pivot calibration from player_aim_config.json.

    The calibration tool (calibrate_aim.py) saves precise pixel coordinates
    for the shoulder joint and arm pivot point. These coordinates are
    critical for proper arm rotation around the shoulder without orbiting.

    If the config file doesn't exist, falls back to default values.

    Returns:
        (body_shoulder_offsets, frame_size, arm_pivot, arms_size), where body
        offsets and arm pivot are in their original unscaled asset spaces.
    """
    config_path = Path(__file__).parent / "assets" / "images" / "player_aim_config.json"

    default_frame_width = PLAYER_WIDTH
    default_frame_height = PLAYER_HEIGHT
    default_arms_width = PLAYER_WIDTH
    default_arms_height = PLAYER_HEIGHT
    default_body_offsets = _default_body_shoulder_offsets(
        default_frame_width,
        default_frame_height,
    )
    default_arm_pivot = pygame.math.Vector2(
        DEFAULT_ARM_PIVOT_RATIO.x * default_arms_width,
        DEFAULT_ARM_PIVOT_RATIO.y * default_arms_height,
    )

    if not config_path.exists():
        print(f"[AIM] Config not found at {config_path}, using defaults")
        return (
            default_body_offsets,
            (default_frame_width, default_frame_height),
            default_arm_pivot,
            (default_arms_width, default_arms_height),
        )

    try:
        with open(config_path) as f:
            config = json.load(f)

        frame_width = config.get("frame_width", PLAYER_WIDTH)
        frame_height = config.get("frame_height", PLAYER_HEIGHT)
        try:
            frame_width = float(frame_width)
            frame_height = float(frame_height)
        except (TypeError, ValueError):
            frame_width = PLAYER_WIDTH
            frame_height = PLAYER_HEIGHT

        arms_image_width = config.get("arms_width", 1254)
        arms_image_height = config.get("arms_height", 1254)
        try:
            arms_image_width = float(arms_image_width)
            arms_image_height = float(arms_image_height)
        except (TypeError, ValueError):
            arms_image_width = 1254
            arms_image_height = 1254

        fallback_body = pygame.math.Vector2(
            DEFAULT_BODY_SHOULDER_RATIO.x * frame_width,
            DEFAULT_BODY_SHOULDER_RATIO.y * frame_height,
        )
        single_body_shoulder = _vector2_from_sequence(
            config.get("body_shoulder_offset"),
            fallback_body,
        )

        body_shoulder_offsets = {}
        config_offsets = config.get("body_shoulder_offsets")
        for frame_index in range(AIM_BODY_FRAME_COUNT):
            frame_key = str(frame_index)
            if isinstance(config_offsets, dict) and frame_key in config_offsets:
                body_shoulder_offsets[frame_index] = _vector2_from_sequence(
                    config_offsets[frame_key],
                    single_body_shoulder,
                )
            else:
                body_shoulder_offsets[frame_index] = pygame.math.Vector2(single_body_shoulder)

        fallback_arm_pivot = pygame.math.Vector2(
            DEFAULT_ARM_PIVOT_RATIO.x * arms_image_width,
            DEFAULT_ARM_PIVOT_RATIO.y * arms_image_height,
        )
        arm_pivot_pixels = _vector2_from_sequence(config.get("arm_pivot"), fallback_arm_pivot)

        print(f"[AIM] Loaded calibration from {config_path}")
        print(f"[AIM] Body shoulder offsets: {len(body_shoulder_offsets)} frames")
        print(f"[AIM] Arm pivot: ({arm_pivot_pixels.x:.1f}, {arm_pivot_pixels.y:.1f}) in source image")

        return (
            body_shoulder_offsets,
            (frame_width, frame_height),
            arm_pivot_pixels,
            (arms_image_width, arms_image_height),
        )

    except Exception as e:
        print(f"[AIM] Error loading config: {e}, using defaults")
        return (
            default_body_offsets,
            (default_frame_width, default_frame_height),
            default_arm_pivot,
            (default_arms_width, default_arms_height),
        )


# Load calibration (will use config file if it exists, otherwise defaults)
(
    _body_shoulder_offsets_source,
    _body_frame_size,
    _arm_pivot_source,
    _arms_image_size,
) = _load_aim_config()

BODY_SHOULDER_OFFSETS = _scaled_body_offsets(
    _body_shoulder_offsets_source,
    _body_frame_size[0],
    _body_frame_size[1],
)
BODY_SHOULDER_OFFSET = BODY_SHOULDER_OFFSETS[0]
BODY_SHOULDER_OFFSET_RATIO = pygame.math.Vector2(
    _body_shoulder_offsets_source[0].x / _body_frame_size[0] if _body_frame_size[0] else DEFAULT_BODY_SHOULDER_RATIO.x,
    _body_shoulder_offsets_source[0].y / _body_frame_size[1] if _body_frame_size[1] else DEFAULT_BODY_SHOULDER_RATIO.y,
)
ARM_PIVOT = pygame.math.Vector2(_arm_pivot_source)
ARM_SOURCE_SIZE = _arms_image_size
ARM_PIVOT_RATIO = pygame.math.Vector2(
    ARM_PIVOT.x / ARM_SOURCE_SIZE[0] if ARM_SOURCE_SIZE[0] else DEFAULT_ARM_PIVOT_RATIO.x,
    ARM_PIVOT.y / ARM_SOURCE_SIZE[1] if ARM_SOURCE_SIZE[1] else DEFAULT_ARM_PIVOT_RATIO.y,
)

# Visible arm width as a ratio of player width. The full arms image is not
# cropped because ARM_PIVOT is calibrated in the original image space.
ARM_DRAW_WIDTH_RATIO = 0.49

# Muzzle position as ratio along the arm (for bullet spawn point)
MUZZLE_DISTANCE_RATIO = 0.42
DROP_THROUGH_CLEARANCE = 4
DROP_THROUGH_MAX_TIME = 0.7


def rotate_around_pivot(image, angle_degrees, image_pivot, target_pivot):
    """
    Rotate an image around an arbitrary local pivot and place that pivot at
    the requested target position in screen space.

    This is the CORRECT way to rotate an image with a custom pivot point.
    Pygame's default rotation rotates around the image center, which causes
    objects to orbit away instead of rotate smoothly in place.

    Why the math works:
    1. We rotate the image normally around its center
    2. We calculate the offset from image center to the desired pivot point
    3. We rotate that offset vector by the same angle (so it rotates WITH the image)
    4. We position the rotated image such that the rotated pivot lands exactly
       at the target screen position

    Example for the player aiming system:
    - image: the player_arms.png overlay (scaled)
    - angle_degrees: angle from shoulder to mouse cursor
    - image_pivot: pixel coordinates of shoulder joint INSIDE the arms image
    - target_pivot: screen-space shoulder position on the player body

    This ensures the arm pivots cleanly around the body shoulder at all angles.

    Args:
        image: pygame.Surface to rotate
        angle_degrees: Rotation angle in degrees
        image_pivot: Local pixel coordinates (Vector2) of pivot in unrotated image
        target_pivot: Screen-space coordinates (Vector2) for pivot placement

    Returns:
        (rotated_image, rotated_rect) tuple for blitting to screen
    """
    rotated_image = pygame.transform.rotate(image, -angle_degrees)

    image_rect = image.get_rect()
    image_center = pygame.math.Vector2(image_rect.center)

    # Vector from image center to the desired pivot point (in unrotated image space)
    pivot_offset = image_pivot - image_center

    # Rotate that offset by the same angle so it rotates WITH the rotated image
    rotated_pivot_offset = pivot_offset.rotate(angle_degrees)

    # Position the rotated image so the rotated pivot lands at target_pivot
    rotated_rect = rotated_image.get_rect(
        center=target_pivot - rotated_pivot_offset,
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

        # Calibrated shoulder positions on each body frame, scaled to the
        # runtime player draw size. Frame numbers follow the 4x4 body sheet.
        self.body_shoulder_offsets = {
            frame_index: pygame.math.Vector2(offset)
            for frame_index, offset in BODY_SHOULDER_OFFSETS.items()
        }
        self.body_shoulder_offset = pygame.math.Vector2(self.body_shoulder_offsets[0])

        # Calibrated arm pivot point. ARM_PIVOT is local to the original
        # unrotated player_arms.png; calculate_arm_pivot scales it to the
        # cached runtime arms surface without changing the image origin.
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
        self.reload_until = 0
        self.reload_prompt_age = None
        self.reload_font = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.color = COLOR_PLAYER
        self.drop_requested = False
        self.drop_through_platform_id = None
        self.drop_through_timer = 0.0
        self.previous_rect = self.rect.copy()

    def prepare_arms_image(self, arms_image):
        if arms_image is None:
            return None

        if arms_image.get_flags() & pygame.SRCALPHA == 0:
            arms_image = arms_image.convert_alpha()
        else:
            arms_image = arms_image.convert_alpha()

        opaque_bounds = arms_image.get_bounding_rect(min_alpha=1)
        source_visible_width = opaque_bounds.width or arms_image.get_width()
        target_visible_width = max(1, PLAYER_WIDTH * ARM_DRAW_WIDTH_RATIO)
        scale = target_visible_width / source_visible_width
        target_size = (
            max(1, int(round(arms_image.get_width() * scale))),
            max(1, int(round(arms_image.get_height() * scale))),
        )
        return pygame.transform.smoothscale(arms_image, target_size)

    def calculate_arm_pivot(self, arms_image):
        if arms_image is None:
            return pygame.math.Vector2()
        source_width, source_height = ARM_SOURCE_SIZE
        scale_x = arms_image.get_width() / source_width if source_width else 1
        scale_y = arms_image.get_height() / source_height if source_height else 1
        return pygame.math.Vector2(
            ARM_PIVOT.x * scale_x,
            ARM_PIVOT.y * scale_y,
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

    def current_body_frame_index(self):
        if not self.animator:
            return 0

        animation = self.animator.current_animation()
        if not animation:
            return 0

        frame_sequence = AIM_BODY_FRAME_INDICES.get(self.animator.current_state)
        if not frame_sequence:
            return 0

        animation_index = min(animation.current_index, len(frame_sequence) - 1)
        return frame_sequence[animation_index]

    def body_shoulder_offset_for_frame(self, frame_index=None):
        if frame_index is None:
            frame_index = self.current_body_frame_index()
        return pygame.math.Vector2(
            self.body_shoulder_offsets.get(
                frame_index,
                self.body_shoulder_offsets[0],
            )
        )

    def shoulder_offset(self, facing_right=None, frame_index=None):
        if facing_right is None:
            facing_right = self.facing_right
        base_offset = self.body_shoulder_offset_for_frame(frame_index)
        if facing_right:
            offset = pygame.math.Vector2(base_offset)
        else:
            offset = pygame.math.Vector2(
                PLAYER_WIDTH - base_offset.x,
                base_offset.y,
            )
        return offset

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
        self.reserve_ammo += amount
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
        if self.drop_through_timer > 0:
            self.drop_through_timer = max(0.0, self.drop_through_timer - dt)
        self.vx = 0
        if left:
            self.vx = -movement_speed
        if right:
            self.vx = movement_speed

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = -self.jump_strength
            self.on_ground = False
        elif self.drop_requested and self.on_ground and self.vy >= 0:
            self.start_drop_through(platforms)

        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False

        self.previous_rect = self.rect.copy()
        self.rect.x += self.vx
        self.collide_horizontal(platforms)

        self.vy += GRAVITY
        self.vy = min(self.vy, MAX_FALL_SPEED)
        self.rect.y += self.vy
        self.on_ground = False
        self.collide_vertical(platforms)
        self.clear_finished_drop_through(platforms)

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
            if getattr(platform, "drop_through", True):
                continue
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right

    def collide_vertical(self, platforms):
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            if getattr(platform, "drop_through", True):
                if self.should_ignore_drop_through_platform(platform):
                    continue
                if self.vy <= 0:
                    continue
                if self.previous_rect.bottom > platform.rect.top + 2:
                    continue

            if self.vy > 0:
                self.rect.bottom = platform.rect.top
                self.vy = 0
                self.on_ground = True
            elif self.vy < 0:
                self.rect.top = platform.rect.bottom
                self.vy = 0

    def start_drop_through(self, platforms):
        platform = self.platform_underfoot(platforms)
        if not platform:
            return

        self.drop_through_platform_id = platform.id
        self.drop_through_timer = DROP_THROUGH_MAX_TIME
        self.on_ground = False
        self.vy = max(self.vy, 4)

    def platform_underfoot(self, platforms):
        for platform in platforms:
            if not getattr(platform, "drop_through", True):
                continue
            if abs(self.rect.bottom - platform.rect.top) > 8:
                continue
            if self.rect.right <= platform.rect.left + 4:
                continue
            if self.rect.left >= platform.rect.right - 4:
                continue
            return platform
        return None

    def should_ignore_drop_through_platform(self, platform):
        if self.drop_through_platform_id == platform.id:
            return True
        return False

    def clear_finished_drop_through(self, platforms):
        if self.drop_through_platform_id is None:
            return

        for platform in platforms:
            if platform.id != self.drop_through_platform_id:
                continue
            if self.rect.top > platform.rect.bottom + DROP_THROUGH_CLEARANCE:
                self.drop_through_platform_id = None
                self.drop_through_timer = 0.0
            return

        if self.drop_through_timer == 0.0:
            self.drop_through_platform_id = None

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
        """
        Render the player's arm/gun overlay, rotated toward the target position.

        CALIBRATION SYSTEM:
        This system uses two calibrated pivot points to ensure the arm rotates
        cleanly around the shoulder joint without orbiting:

        1. BODY_SHOULDER_OFFSET_RATIO:
           - Defines WHERE the shoulder joint is on the player body sprite
           - In pixels: self.body_shoulder_offset
           - This is the screen-space position the arm pivot rotates around
           - Calibrated using calibrate_aim.py (red dot on body frame)

        2. ARM_PIVOT_RATIO:
           - Defines WHERE the shoulder joint is INSIDE the arms image
           - In pixels: self.arm_pivot
           - This is the local coordinate in the unrotated arms image
           - Calibrated using calibrate_aim.py (blue dot on arms image)

        WHY TWO PIVOTS?
        The body and arms are separate sprites. The body has one shoulder position,
        and the arms have a different coordinate system. To make them align:
        - Calculate screen-space shoulder from player position + body offset
        - Rotate arms around its internal pivot point
        - Position rotated arms so its pivot lands on the body's shoulder

        If these calibrations are wrong:
        - Arm orbits away from shoulder → recalibrate with calibrate_aim.py
        - Shoulder appears misaligned → adjust constants and re-calibrate
        """
        arms_image = self.arms_image if self.facing_right else self.flipped_arms_image
        if arms_image is None:
            return

        # Get shoulder position in screen space
        shoulder = self.aim_shoulder_screen(draw_rect)
        target = pygame.math.Vector2(target_pos)
        aim_vector = target - shoulder
        if aim_vector.length_squared() <= 0:
            return

        # Calculate angle from shoulder to target
        angle_degrees = math.degrees(math.atan2(aim_vector.y, aim_vector.x))
        if self.facing_right:
            pivot = self.arm_pivot
            draw_angle = angle_degrees
        else:
            pivot = self.flipped_arm_pivot
            draw_angle = angle_degrees - 180

        # Rotate arm image around its local pivot and place pivot at shoulder
        rotated_image, rotated_rect = rotate_around_pivot(
            arms_image,
            draw_angle,
            pivot,
            shoulder,
        )
        surface.blit(rotated_image, rotated_rect)

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

        if settings.DEBUG_AIM_PIVOT:
            shoulder = self.aim_shoulder_screen(draw_rect)
            shoulder_point = (round(shoulder.x), round(shoulder.y))
            frame_index = self.current_body_frame_index()
            offset = self.shoulder_offset(frame_index=frame_index)
            draw_offset = self.animator.current_draw_offset() if self.animator else (0, 0)
            facing = "RIGHT" if self.facing_right else "LEFT"

            # Get frame info
            current_frame = None
            frame_size = None
            if self.animator and hasattr(self.animator, 'current_frame'):
                current_frame = self.animator.current_frame()
                if current_frame:
                    frame_size = current_frame.get_size()

            print(f"DEBUG: facing={facing}, frame={frame_index}, draw_rect={draw_rect}, frame_size={frame_size}, shoulder_calc={offset}, shoulder_screen={shoulder_point}")

            # Draw shoulder circles
            pygame.draw.circle(surface, (255, 40, 40), shoulder_point, 6)
            pygame.draw.circle(surface, (40, 120, 255), shoulder_point, 4)

            # Also draw arm pivot position if arms are being drawn
            if self.should_draw_aim_arms() and self.arms_image:
                arm_image = self.arms_image if self.facing_right else self.flipped_arms_image
                if arm_image:
                    arm_pivot = self.arm_pivot if self.facing_right else self.flipped_arm_pivot
                    print(f"  ARM_INFO: arm_image_size={arm_image.get_size()}, arm_pivot={arm_pivot}, should_be_at_shoulder={shoulder_point}")

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
