import pygame
import math
from animation import AnimatedSprite
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
    SCREEN_WIDTH,
)
# platform detection is handled locally in GroundZombie

class Enemy:
    def __init__(self, x, y, width, height, hp, speed, damage, image=None, animations=None, color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.hp = hp
        self.speed = speed
        self.damage = damage
        self.image = image
        self.animator = AnimatedSprite(animations) if animations else None
        self.color = color
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.dead = False
        self.removable = False
        self.attack_state = "attack"

    def take_damage(self, amount):
        if self.dead:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        self.hp = 0
        self.dead = True
        self.vx = 0
        self.vy = 0
        if self.animator and self.animator.has_state("death"):
            self.animator.play_once("death")
        else:
            self.removable = True

    def start_attack(self):
        if self.dead:
            return
        if self.animator and self.animator.has_state(self.attack_state):
            self.animator.play_once(self.attack_state)

    def update_death_animation(self, dt):
        if not self.animator:
            self.removable = True
            return

        self.animator.play("death")
        self.animator.update(dt)
        if self.animator.is_finished():
            self.removable = True

    def update_animation(self, dt, movement_state):
        if not self.animator:
            return

        if not self.animator.is_playing_once():
            self.animator.play(movement_state)

        self.animator.update(dt)

    def move_x(self, amount):
        self.pos_x += amount
        self.rect.x = round(self.pos_x)

    def move_y(self, amount):
        self.pos_y += amount
        self.rect.y = round(self.pos_y)

    def sync_position(self):
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)

    def draw(self, surface):
        image = self.animator.current_frame() if self.animator else self.image
        if image:
            if not self.facing_right:
                image = pygame.transform.flip(image, True, False)
            surface.blit(image, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)

class GroundZombie(Enemy):
    def __init__(self, x, y, width, height, hp, speed, damage, jump_interval, jump_strength, image=None, animations=None, color=(255, 255, 255)):
        super().__init__(x, y, width, height, hp, speed, damage, image=image, animations=animations, color=color)
        self.jump_interval = jump_interval
        self.jump_strength = jump_strength
        self.jumping_toward_player = False
        self.platform_graph = None
        self.agent_type = None
        self.path = []
        self.current_path_index = 0
        self.current_edge_action = None
        self.repath_timer = 0.0
        self.stuck_timer = 0.0
        self.last_position = (x, y)
        self.emergency_jump_cooldown = 0.0
        self.jump_retry_cooldown = 0.0
        self.current_platform = None
        self.last_goal_platform_id = None

    def find_platform(self, rect, platforms):
        for platform in platforms:
            if rect.bottom <= platform.rect.top + 8 and rect.bottom >= platform.rect.top - 8:
                overlaps_platform_top = (
                    rect.right > platform.rect.left + 4
                    and rect.left < platform.rect.right - 4
                )
                if overlaps_platform_top:
                    return platform
        return None

    def update(self, player, platforms, dt):
        if self.dead:
            self.update_death_animation(dt)
            return

        self.current_platform = self.find_platform(self.rect, platforms) if self.on_ground else None
        player_platform = self.resolve_player_target_platform(player, platforms)

        if self.emergency_jump_cooldown > 0:
            self.emergency_jump_cooldown = max(0.0, self.emergency_jump_cooldown - dt)
        if self.jump_retry_cooldown > 0:
            self.jump_retry_cooldown = max(0.0, self.jump_retry_cooldown - dt)

        self.repath_timer = max(0.0, self.repath_timer - dt)

        should_follow_path = (
            self.platform_graph
            and player_platform
            and self.jump_retry_cooldown <= 0.0
            and (
                (self.current_platform and self.current_platform.id != player_platform.id)
                or (self.path and self.current_path_index < len(self.path))
            )
        )

        if should_follow_path:
            self.follow_platform_path(player, player_platform, platforms)
        else:
            self.chase_on_same_platform(player, platforms)

        self.move_x(self.vx)
        self.collide_horizontal(platforms)

        self.vy += GRAVITY
        self.vy = min(self.vy, MAX_FALL_SPEED)
        self.move_y(self.vy)
        self.on_ground = False
        self.collide_vertical(platforms)

        if self.on_ground:
            self.jumping_toward_player = False

        self.check_stuck(dt)
        movement_state = "walk" if abs(self.vx) > 0.1 else "idle"
        self.update_animation(dt, movement_state)

    def chase_on_same_platform(self, player, platforms):
        self.path = []
        self.current_path_index = 0
        self.current_edge_action = None

        direction = self.direction_to(player.rect.centerx)

        if direction and not self.can_step(direction, platforms):
            if self.should_drop_toward_player(player):
                self.vx = direction * self.speed
                return
            direction = 0

        self.vx = direction * self.speed

    def follow_platform_path(self, player, player_platform, platforms):
        if self.current_platform and (not self.path or self.repath_timer <= 0.0 or self.last_goal_platform_id != player_platform.id):
            self.repath_path(player_platform, player.rect.centerx)

        if not self.path or self.current_path_index >= len(self.path):
            self.chase_on_same_platform(player, platforms)
            return

        current_index = max(0, self.current_path_index - 1)
        current_node = self.platform_graph.get_node(self.path[current_index])
        next_node = self.platform_graph.get_node(self.path[self.current_path_index])
        self.current_edge_action = self.get_edge_action(current_node.id, next_node.id)

        if self.current_edge_action == "jump":
            self.handle_jump_edge(current_node, next_node, platforms)
        elif self.current_edge_action == "drop":
            self.handle_drop_edge(current_node)
        else:
            self.handle_walk_drop_edge(next_node)

        if self.current_edge_action in ["jump", "drop"]:
            if self.on_ground and self.current_platform and self.current_platform.id == next_node.platform_id:
                self.current_path_index += 1
        else:
            if self.current_platform and self.current_platform.id == next_node.platform_id and abs(self.rect.centerx - next_node.x) < 10:
                self.current_path_index += 1

        if self.current_path_index >= len(self.path):
            self.current_edge_action = None

    def get_edge_action(self, src_id, dest_id):
        for edge in self.platform_graph.get_edges(src_id):
            if edge.dest_id == dest_id:
                return edge.action
        return "walk"

    def handle_walk_drop_edge(self, next_node):
        self.set_vx_toward(next_node.x)

    def handle_drop_edge(self, current_node):
        direction = -1 if current_node.type == "left" else 1
        self.facing_right = direction > 0
        self.vx = direction * self.speed

    def handle_jump_edge(self, current_node, next_node, platforms):
        jump_speed = self.jump_horizontal_speed(current_node, next_node)
        jump_direction = self.jump_direction(current_node, next_node)
        dest_platform = self.find_platform_by_id(platforms, next_node.platform_id)
        on_launch_platform = (
            self.on_ground
            and self.current_platform
            and self.current_platform.id == current_node.platform_id
        )

        if on_launch_platform and abs(self.rect.centerx - current_node.x) > self.launch_tolerance():
            self.set_vx_toward(current_node.x, tolerance=self.launch_tolerance())
            return

        if on_launch_platform:
            self.vy = -self.jump_strength
            self.on_ground = False
            self.jumping_toward_player = True

        if self.should_hold_jump_horizontal(dest_platform):
            self.vx = self.jump_clearance_velocity(dest_platform, jump_direction, jump_speed)
            return

        self.set_vx_toward(next_node.x, speed=jump_speed)

    def launch_tolerance(self):
        return max(3, self.speed * 0.75)

    def jump_direction(self, current_node, next_node):
        if next_node.x > current_node.x:
            return 1
        if next_node.x < current_node.x:
            return -1
        return 0

    def find_platform_by_id(self, platforms, platform_id):
        for platform in platforms:
            if platform.id == platform_id:
                return platform
        return None

    def should_hold_jump_horizontal(self, dest_platform):
        if not dest_platform or not self.jumping_toward_player:
            return False
        return self.vy < 0 and self.rect.bottom > dest_platform.rect.top - 2

    def jump_clearance_velocity(self, dest_platform, direction, jump_speed):
        if direction == 0:
            return 0

        clearance = 3
        self.facing_right = direction > 0
        if direction > 0:
            safe_right = dest_platform.rect.left - clearance
            if self.rect.right < safe_right:
                return min(jump_speed, safe_right - self.rect.right)
            if self.rect.right > safe_right:
                return -min(self.speed, self.rect.right - safe_right)
        if direction < 0:
            safe_left = dest_platform.rect.right + clearance
            if self.rect.left > safe_left:
                return -min(jump_speed, self.rect.left - safe_left)
            if self.rect.left < safe_left:
                return min(self.speed, safe_left - self.rect.left)
        return 0

    def direction_to(self, target_x, tolerance=5):
        if target_x > self.rect.centerx + tolerance:
            self.facing_right = True
            return 1
        if target_x < self.rect.centerx - tolerance:
            self.facing_right = False
            return -1
        return 0

    def set_vx_toward(self, target_x, tolerance=5, speed=None):
        direction = self.direction_to(target_x, tolerance)
        self.vx = direction * (speed if speed is not None else self.speed)

    def jump_horizontal_speed(self, current_node, next_node):
        horizontal = abs(next_node.x - current_node.x)
        vertical = max(0, current_node.y - next_node.y)
        air_time = max(1.0, self.estimate_air_time(vertical))
        needed_speed = horizontal / air_time
        return max(self.speed, min(4.4, needed_speed + 0.8))

    def estimate_air_time(self, vertical):
        a = 0.5 * GRAVITY
        b = -self.jump_strength
        c = vertical
        discriminant = b * b - 4 * a * c
        if discriminant <= 0:
            return self.jump_strength / GRAVITY
        return (-b + math.sqrt(discriminant)) / (2 * a)

    def can_step(self, direction, platforms):
        probe_x = self.rect.right + 4 if direction > 0 else self.rect.left - 4
        probe_y = self.rect.bottom + 5
        for platform in platforms:
            if probe_x >= platform.rect.left and probe_x <= platform.rect.right:
                if probe_y >= platform.rect.top and probe_y <= platform.rect.top + 12:
                    return True
        return False

    def should_drop_toward_player(self, player):
        if not self.current_platform:
            return False
        return player.rect.centery > self.rect.centery + self.rect.height * 0.4

    def repath_path(self, player_platform, target_x):
        if not self.platform_graph or not self.current_platform or not player_platform:
            self.path = []
            self.current_path_index = 0
            self.last_goal_platform_id = None
            return

        start_node = self.platform_graph.get_nearest_node_on_platform(self.current_platform, self.rect.centerx)
        goal_node = self.platform_graph.get_nearest_node_on_platform(player_platform, target_x)
        self.path = self.platform_graph.astar(start_node, goal_node, self.agent_type)
        self.current_path_index = 1 if len(self.path) > 1 else 0
        self.repath_timer = 0.4
        self.last_goal_platform_id = player_platform.id if player_platform else None

    def check_stuck(self, dt):
        current_pos = (self.rect.x, self.rect.y)
        dx = abs(current_pos[0] - self.last_position[0])
        if self.vx != 0 and dx < 2 and self.on_ground:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0.0
        if self.stuck_timer >= 0.75:
            self.path = []
            self.current_path_index = 0
            self.repath_timer = 0.0
            if self.on_ground and self.emergency_jump_cooldown <= 0.0:
                self.vy = -self.jump_strength * 0.9
                self.emergency_jump_cooldown = 1.0
            self.stuck_timer = 0.0
        self.last_position = current_pos

    def collide_horizontal(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right
                self.pos_x = float(self.rect.x)

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
                    self.handle_head_bonk(platform)
                self.pos_y = float(self.rect.y)

    def handle_head_bonk(self, platform):
        if self.current_edge_action != "jump" and not self.jumping_toward_player:
            return

        self.path = []
        self.current_path_index = 0
        self.current_edge_action = None
        self.repath_timer = 0.2
        self.jump_retry_cooldown = 0.35
        self.jumping_toward_player = False

        if self.rect.centerx < platform.rect.centerx:
            self.vx = -self.speed
        else:
            self.vx = self.speed

    def resolve_player_target_platform(self, player, platforms):
        player_platform = self.find_platform(player.rect, platforms) if getattr(player, "on_ground", False) else None
        if player_platform:
            return player_platform

        candidates = []
        for platform in platforms:
            if player.rect.bottom <= platform.rect.top and player.rect.centerx >= platform.rect.left - 120 and player.rect.centerx <= platform.rect.right + 120:
                candidates.append(platform)

        if candidates:
            return min(candidates, key=lambda p: p.rect.top)

        return min(platforms, key=lambda p: abs(player.rect.centery - p.rect.top))

class WalkerZombie(GroundZombie):
    def __init__(self, x, y, image=None, animations=None):
        super().__init__(x, y, WALKER_WIDTH, WALKER_HEIGHT, WALKER_HP, WALKER_SPEED, WALKER_DAMAGE, WALKER_JUMP_INTERVAL, WALKER_JUMP_STRENGTH, image=image, animations=animations, color=COLOR_WALKER)
        self.agent_type = "walker"

class TankZombie(GroundZombie):
    def __init__(self, x, y, image=None, animations=None):
        super().__init__(x, y, TANK_WIDTH, TANK_HEIGHT, TANK_HP, TANK_SPEED, TANK_DAMAGE, TANK_JUMP_INTERVAL, TANK_JUMP_STRENGTH, image=image, animations=animations, color=COLOR_TANK)
        self.agent_type = "tank"
        self.attack_state = "heavy_attack"

class FlyingZombie(Enemy):
    def __init__(self, x, y, image=None, animations=None):
        super().__init__(x, y, FLYING_WIDTH, FLYING_HEIGHT, FLYING_HP, FLYING_SPEED, FLYING_DAMAGE, image=image, animations=animations, color=COLOR_FLYING)

    def update(self, player, platforms, dt):
        if self.dead:
            self.update_death_animation(dt)
            return

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance > 0:
            self.facing_right = dx >= 0
            self.move_x((dx / distance) * self.speed)
            self.move_y((dy / distance) * self.speed)
            self.update_animation(dt, "fly")
        else:
            self.update_animation(dt, "hover_idle")
