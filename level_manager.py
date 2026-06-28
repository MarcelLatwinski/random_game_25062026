import pygame
from settings import (
    LEVELS,
    LEVEL_WIDTH,
    LEVEL_HEIGHT,
    PLAYER_START,
    EXIT_POSITION,
    EXIT_WIDTH,
    EXIT_HEIGHT,
    PLATFORMS,
    ENEMY_SPAWN_POINTS,
    PICKUP_SPAWN_POINTS,
    DECORATIONS,
    ENEMY_TYPE_CONFIGS,
    SPAWN_ACTIVATION_DISTANCE,
    ENEMY_AI_ACTIVE_DISTANCE,
    ENEMY_PLATFORM_QUERY_MARGIN,
    ENEMY_SPEED_SCALE_PER_LEVEL,
    ENEMY_HEALTH_SCALE_PER_LEVEL,
    GROUND_Y,
)
from enemy import WalkerZombie, TankZombie, FlyingZombie


class LevelManager:
    def __init__(self):
        self.level_index = 0
        self.current_level = LEVELS[self.level_index]
        self.level_width = LEVEL_WIDTH
        self.level_height = LEVEL_HEIGHT
        self.player_start = PLAYER_START
        self.exit_position = EXIT_POSITION
        self.exit_width = EXIT_WIDTH
        self.exit_height = EXIT_HEIGHT
        self.sections = []
        self.background_layers = []
        self.platforms = []
        self.decorations = []
        self.pickup_spawn_points = []
        self.enemy_spawn_points = []
        self.next_spawn_index = 0
        self.active_enemies = []
        self.start_level()

    def reset(self):
        self.level_index = 0
        self.start_level()

    def start_level(self):
        self.current_level = LEVELS[self.level_index]
        self.level_width = self.current_level.get("width", LEVEL_WIDTH)
        self.level_height = self.current_level.get("height", LEVEL_HEIGHT)
        self.player_start = self.current_level.get("player_start", PLAYER_START)

        exit_data = self.current_level.get("exit", {})
        self.exit_position = (
            exit_data.get("x", EXIT_POSITION[0]),
            exit_data.get("y", EXIT_POSITION[1]),
        )
        self.exit_width = exit_data.get("width", EXIT_WIDTH)
        self.exit_height = exit_data.get("height", EXIT_HEIGHT)

        self.sections = self.current_level.get("sections", [])
        self.background_layers = list(self.current_level.get("backgrounds", []))

        # Platforms are defined in named level sections in settings.py.
        # Game turns these dictionaries into Platform objects after this resets.
        self.platforms = self.collect_section_items("platforms", fallback=PLATFORMS)
        self.platforms = [
            platform
            for platform in self.platforms
            if not isinstance(platform, dict) or platform.get("collidable", True)
        ]

        # Decorations are world-space visuals only. They never enter collision.
        self.decorations = self.collect_section_items("decorations", fallback=DECORATIONS)

        # Pickup positions are placed in level data, but use the same Pickup
        # class and collection behavior as enemy drops.
        self.pickup_spawn_points = self.build_pickup_spawn_points()

        # Spawn points reset every level, so each point can fire once again.
        self.enemy_spawn_points = self.build_spawn_points()
        self.next_spawn_index = 0
        self.active_enemies = []

    def collect_section_items(self, key, fallback=None):
        if not self.sections:
            return [self.copy_level_item(item) for item in (fallback or [])]

        items = []
        for section in self.sections:
            section_name = section.get("name", "")
            for item in section.get(key, []):
                copied = self.copy_level_item(item)
                if isinstance(copied, dict):
                    copied.setdefault("section", section_name)
                items.append(copied)
        return items

    def copy_level_item(self, item):
        if isinstance(item, dict):
            return dict(item)
        return item

    def platform_rect_from_data(self, platform_data):
        if isinstance(platform_data, dict):
            return pygame.Rect(
                platform_data["x"],
                platform_data["y"],
                platform_data["width"],
                platform_data["height"],
            )
        return pygame.Rect(platform_data)

    def is_floor_platform_data(self, platform_data):
        rect = self.platform_rect_from_data(platform_data)
        return (
            rect.width >= self.level_width * 0.9
            and rect.top >= GROUND_Y
        )

    def surface_y_for_x(self, x, requested_y):
        if requested_y == GROUND_Y:
            return GROUND_Y

        matching_platforms = []
        for platform_data in self.platforms:
            if self.is_floor_platform_data(platform_data):
                continue
            rect = self.platform_rect_from_data(platform_data)
            if rect.left <= x <= rect.right:
                matching_platforms.append(rect)

        if not matching_platforms:
            return GROUND_Y

        closest_platform = min(
            matching_platforms,
            key=lambda rect: abs(rect.top - requested_y),
        )
        return closest_platform.top

    def anchor_template_to_surface(self, template):
        anchored = dict(template)
        anchored["y"] = self.surface_y_for_x(anchored["x"], anchored.get("y", GROUND_Y))
        return anchored

    def build_spawn_points(self):
        spawn_points = []
        current_level_number = self.current_level_number()

        templates = self.collect_section_items("enemy_spawns", fallback=ENEMY_SPAWN_POINTS)
        for template in templates:
            min_level = template.get("min_level", 1)
            if current_level_number < min_level:
                continue

            spawn_points.append(self.build_spawn_point(template))

        return sorted(spawn_points, key=lambda point: point["trigger_x"])

    def build_spawn_point(self, template):
        template = self.anchor_template_to_surface(template)
        spawn_point = {
            key: value
            for key, value in template.items()
            if key != "min_level"
        }
        enemy_type = (
            spawn_point.get("type")
            or spawn_point.get("enemyType")
            or spawn_point.get("enemy_type")
        )
        spawn_point["type"] = enemy_type
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

        trigger_distance = spawn_point.get("trigger_distance")
        if trigger_distance is None:
            trigger_distance = SPAWN_ACTIVATION_DISTANCE
        spawn_point["trigger_distance"] = trigger_distance
        spawn_point["trigger_x"] = spawn_point["x"] - trigger_distance
        spawn_point["spawned"] = False
        return spawn_point

    def build_pickup_spawn_points(self):
        pickup_points = []
        current_level_number = self.current_level_number()

        for template in self.collect_section_items("pickups", fallback=PICKUP_SPAWN_POINTS):
            min_level = template.get("min_level", 1)
            if current_level_number < min_level:
                continue

            template = self.anchor_template_to_surface(template)
            pickup_point = {
                key: value
                for key, value in template.items()
                if key != "min_level"
            }
            pickup_points.append(pickup_point)

        return sorted(pickup_points, key=lambda point: point["x"])

    def update(self, dt, platforms, player, images, platform_graph):
        self.activate_spawn_points(player, images, platform_graph)
        removed_enemies = []
        active_section = self.current_section_name(player.rect.centerx)

        for index in range(len(self.active_enemies) - 1, -1, -1):
            enemy = self.active_enemies[index]
            if self.should_update_enemy(enemy, player, active_section):
                nearby_platforms = self.nearby_platforms_for_enemy(enemy, player, platforms)
                enemy.update(player, nearby_platforms, dt)
            else:
                self.pause_far_enemy(enemy)
            if enemy.removable:
                del self.active_enemies[index]
                removed_enemies.append(enemy)

        return removed_enemies

    def activate_spawn_points(self, player, images, platform_graph):
        # Spawn points are sorted by trigger_x, so the game only checks the next
        # unspawned point instead of scanning the whole level every frame.
        while self.next_spawn_index < len(self.enemy_spawn_points):
            spawn_point = self.enemy_spawn_points[self.next_spawn_index]
            if player.rect.centerx < spawn_point["trigger_x"]:
                break

            amount = max(1, int(spawn_point.get("amount", 1)))
            for spawn_index in range(amount):
                enemy = self.spawn_enemy(
                    spawn_point,
                    images,
                    platform_graph,
                    spawn_index,
                    amount,
                )
                if enemy:
                    self.active_enemies.append(enemy)
            spawn_point["spawned"] = True
            self.next_spawn_index += 1

    def spawn_enemy(self, spawn_point, images, platform_graph, spawn_index=0, spawn_count=1):
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

        spacing = spawn_point.get("spacing", 80)
        offset = (spawn_index - (spawn_count - 1) / 2) * spacing
        spawn_x = round(spawn_point["x"] + offset)
        spawn_y = self.surface_y_for_x(spawn_x, spawn_point["y"])
        enemy.rect.midbottom = (spawn_x, spawn_y)
        enemy.sync_position()
        enemy.section = spawn_point.get("section")
        self.apply_level_difficulty(enemy)
        self.start_enemy_spawn_animation(enemy, spawn_point)
        return enemy

    def current_section_name(self, player_x):
        for section in self.sections:
            if section.get("start_x", 0) <= player_x <= section.get("end_x", self.level_width):
                return section.get("name")
        return None

    def should_update_enemy(self, enemy, player, active_section):
        if enemy.dead or enemy.removable or enemy.is_emerging():
            return True

        horizontal_distance = abs(enemy.rect.centerx - player.rect.centerx)
        if horizontal_distance <= ENEMY_AI_ACTIVE_DISTANCE:
            return True

        if getattr(enemy, "section", None) == active_section:
            return True

        # Ground enemies still get physics while airborne so they do not freeze
        # mid-jump just because the player moved away.
        if hasattr(enemy, "current_platform") and not enemy.on_ground:
            return True

        return False

    def pause_far_enemy(self, enemy):
        enemy.vx = 0
        enemy.vy = 0
        if hasattr(enemy, "stuck_timer"):
            enemy.stuck_timer = 0.0

    def nearby_platforms_for_enemy(self, enemy, player, platforms):
        enemy_left = enemy.rect.left - ENEMY_PLATFORM_QUERY_MARGIN
        enemy_right = enemy.rect.right + ENEMY_PLATFORM_QUERY_MARGIN
        player_left = player.rect.left - ENEMY_PLATFORM_QUERY_MARGIN
        player_right = player.rect.right + ENEMY_PLATFORM_QUERY_MARGIN

        nearby = [
            platform
            for platform in platforms
            if (
                platform.rect.right >= enemy_left
                and platform.rect.left <= enemy_right
            )
            or (
                platform.rect.right >= player_left
                and platform.rect.left <= player_right
            )
        ]
        return nearby or platforms

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
        return pygame.Rect(
            x - self.exit_width // 2,
            y - self.exit_height,
            self.exit_width,
            self.exit_height,
        )

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
