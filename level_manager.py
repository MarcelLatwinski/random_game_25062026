import pygame
from settings import (
    LEVELS,
    LEVEL_WIDTH,
    PLAYER_START,
    EXIT_POSITION,
    EXIT_WIDTH,
    EXIT_HEIGHT,
    PLATFORMS,
    ENEMY_SPAWN_POINTS,
    ENEMY_TYPE_CONFIGS,
    SPAWN_ACTIVATION_DISTANCE,
    ENEMY_SPEED_SCALE_PER_LEVEL,
    ENEMY_HEALTH_SCALE_PER_LEVEL,
)
from enemy import WalkerZombie, TankZombie, FlyingZombie


class LevelManager:
    def __init__(self):
        self.level_index = 0
        self.current_level = LEVELS[self.level_index]
        self.level_width = LEVEL_WIDTH
        self.player_start = PLAYER_START
        self.exit_position = EXIT_POSITION
        self.platforms = []
        self.enemy_spawn_points = []
        self.active_enemies = []
        self.start_level()

    def reset(self):
        self.level_index = 0
        self.start_level()

    def start_level(self):
        self.current_level = LEVELS[self.level_index]
        self.level_width = LEVEL_WIDTH
        self.player_start = PLAYER_START
        self.exit_position = EXIT_POSITION

        # Every level uses the same platform rectangles for now.
        # Game turns these rectangles into Platform objects after this resets.
        self.platforms = list(PLATFORMS)

        # Spawn points reset every level, so each point can fire once again.
        self.enemy_spawn_points = self.build_spawn_points()
        self.active_enemies = []

    def build_spawn_points(self):
        spawn_points = []
        current_level_number = self.current_level_number()

        for template in ENEMY_SPAWN_POINTS:
            min_level = template.get("min_level", 1)
            if current_level_number < min_level:
                continue

            spawn_points.append(self.build_spawn_point(template))

        return sorted(spawn_points, key=lambda point: point["x"])

    def build_spawn_point(self, template):
        spawn_point = {
            key: value
            for key, value in template.items()
            if key != "min_level"
        }
        type_config = ENEMY_TYPE_CONFIGS.get(spawn_point["type"], {})

        # Optional spawn animation fields can live on the enemy type config or
        # on a single spawn point for one-off future spawn effects.
        for key in (
            "animation_key",
            "spawn_sheet",
            "spawn_animation",
            "spawn_state",
            "starts_active",
        ):
            if key in type_config and key not in spawn_point:
                spawn_point[key] = type_config[key]

        spawn_point["spawned"] = False
        return spawn_point

    def update(self, dt, platforms, player, images, platform_graph):
        self.activate_spawn_points(player, images, platform_graph)

        for enemy in list(self.active_enemies):
            enemy.update(player, platforms, dt)
            if enemy.removable:
                self.active_enemies.remove(enemy)

    def activate_spawn_points(self, player, images, platform_graph):
        activation_x = player.rect.centerx + SPAWN_ACTIVATION_DISTANCE

        for spawn_point in self.enemy_spawn_points:
            if spawn_point["spawned"]:
                continue
            if spawn_point["x"] > activation_x:
                continue

            enemy = self.spawn_enemy(spawn_point, images, platform_graph)
            if enemy:
                self.active_enemies.append(enemy)
            spawn_point["spawned"] = True

    def spawn_enemy(self, spawn_point, images, platform_graph):
        enemy_type = spawn_point["type"]
        animations = self.build_enemy_animations(enemy_type, spawn_point, images)

        if enemy_type == "walker":
            enemy = WalkerZombie(0, 0, animations=animations)
            enemy.platform_graph = platform_graph
        elif enemy_type == "tank":
            enemy = TankZombie(0, 0, animations=animations)
            enemy.platform_graph = platform_graph
        elif enemy_type == "flying":
            enemy = FlyingZombie(0, 0, animations=animations)
        else:
            return None

        enemy.rect.midbottom = (spawn_point["x"], spawn_point["y"])
        enemy.sync_position()
        self.apply_level_difficulty(enemy)
        self.start_enemy_spawn_animation(enemy, spawn_point)
        return enemy

    def build_enemy_animations(self, enemy_type, spawn_point, images):
        type_config = ENEMY_TYPE_CONFIGS.get(enemy_type, {})
        animation_key = spawn_point.get("animation_key", type_config.get("animation_key"))
        animation_sets = {}

        if animation_key and images.get(animation_key):
            animation_sets.update(images[animation_key])

        spawn_sheet = spawn_point.get("spawn_sheet")
        if spawn_sheet and images.get(spawn_sheet):
            animation_sets.update(images[spawn_sheet])

        return animation_sets or None

    def start_enemy_spawn_animation(self, enemy, spawn_point):
        spawn_animation = spawn_point.get("spawn_animation")
        starts_active = spawn_point.get("starts_active", not bool(spawn_animation))
        if not spawn_animation or starts_active:
            return

        enemy.start_spawn_animation(
            spawn_animation,
            state=spawn_point.get("spawn_state", "emerging"),
            post_spawn_state="idle",
        )

    def apply_level_difficulty(self, enemy):
        # Later levels are harder without changing the map:
        # each level slightly increases enemy speed and health.
        speed_factor = 1 + self.level_index * ENEMY_SPEED_SCALE_PER_LEVEL
        health_factor = 1 + self.level_index * ENEMY_HEALTH_SCALE_PER_LEVEL
        enemy.speed *= speed_factor
        enemy.hp = max(1, int(round(enemy.hp * health_factor)))

    def level_complete(self, player):
        return player.rect.centerx >= self.exit_position[0]

    def exit_rect(self):
        x, y = self.exit_position
        return pygame.Rect(x - EXIT_WIDTH // 2, y - EXIT_HEIGHT, EXIT_WIDTH, EXIT_HEIGHT)

    def next_level(self):
        self.level_index += 1
        if self.level_index < len(LEVELS):
            self.start_level()
            return True
        return False

    def is_final_level(self):
        return self.level_index == len(LEVELS) - 1

    def current_level_number(self):
        return self.level_index + 1
