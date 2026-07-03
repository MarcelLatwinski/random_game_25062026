import pygame
import random
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
    CLOSE_FOREGROUND_ASSET_SPECS,
    MAX_CLOSE_FOREGROUND_OBJECTS,
    CLOSE_FOREGROUND_SPAWN_CHANCE,
    CLOSE_FOREGROUND_MIN_SPACING,
    CLOSE_FOREGROUND_VERTICAL_OVERSCAN,
    RANDOM_GAMEPLAY_ASSET_SPECS,
    MAX_RANDOM_GAMEPLAY_ASSETS_PER_LEVEL,
    RANDOM_GAMEPLAY_ASSET_TARGET_RANGE,
    MIN_FLOOR_RANDOM_ASSETS_PER_LEVEL,
    RANDOM_GAMEPLAY_ASSET_MIN_SPACING,
    RANDOM_GAMEPLAY_SURFACE_FILL_CHANCE,
    RANDOM_GAMEPLAY_ASSET_EDGE_MARGIN,
    RANDOM_GAMEPLAY_ASSET_SURFACE_SINK,
    ENVIRONMENT_IMAGE_PATHS,
    MIN_CLOSE_FOREGROUND_OBJECTS,
    SCREEN_HEIGHT,
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
        self.close_foreground_assets = []
        self.decorations = []
        self.pickup_spawn_points = []
        self.enemy_spawn_points = []
        self._asset_size_cache = {}
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

        # Add randomly placed collidable traversal obstacles after base map,
        # pickups, and spawns are defined so we can avoid important objects.
        self.platforms.extend(self.build_random_gameplay_platforms())

        # Very close decorative layer that renders above all world entities.
        self.close_foreground_assets = self.build_close_foreground_assets()

        self.next_spawn_index = 0
        self.active_enemies = []

    def section_name_for_x(self, world_x):
        for section in self.sections:
            if section.get("start_x", 0) <= world_x <= section.get("end_x", self.level_width):
                return section.get("name")
        return None

    def supports_random_asset(self, platform_data, allow_upper):
        rect = self.platform_rect_from_data(platform_data)
        if rect.width <= RANDOM_GAMEPLAY_ASSET_EDGE_MARGIN * 2:
            return False
        is_ground = self.is_floor_platform_data(platform_data)
        if is_ground:
            return True
        if not allow_upper:
            return False
        if isinstance(platform_data, dict) and not platform_data.get("drop_through", True):
            return False
        return True

    def random_asset_surfaces(self, allow_upper):
        surfaces = []
        for platform_data in self.platforms:
            if self.supports_random_asset(platform_data, allow_upper):
                surfaces.append(platform_data)
        return surfaces

    def reserved_world_points(self):
        points = [
            pygame.math.Vector2(self.player_start[0], self.player_start[1]),
            pygame.math.Vector2(self.exit_position[0], self.exit_position[1]),
        ]
        for pickup in self.pickup_spawn_points:
            points.append(pygame.math.Vector2(pickup.get("x", 0), pickup.get("y", GROUND_Y)))
        for spawn in self.enemy_spawn_points:
            points.append(pygame.math.Vector2(spawn.get("x", 0), spawn.get("y", GROUND_Y)))
        return points

    def is_random_asset_placement_valid(
        self,
        rect,
        occupied_rects,
        placed_rects,
        reserved_points,
    ):
        if rect.left < 0 or rect.right > self.level_width:
            return False

        for occupied in occupied_rects:
            if rect.colliderect(occupied):
                return False

        for placed in placed_rects:
            if rect.colliderect(placed):
                return False
            if abs(rect.centerx - placed.centerx) < RANDOM_GAMEPLAY_ASSET_MIN_SPACING:
                return False

        for point in reserved_points:
            if rect.collidepoint(round(point.x), round(point.y)):
                return False
            if abs(rect.centerx - point.x) < max(120, rect.width // 2 + 30):
                if abs(rect.bottom - point.y) < 120:
                    return False

        return True

    def build_random_gameplay_platforms(self):
        occupied_rects = [self.platform_rect_from_data(platform_data) for platform_data in self.platforms]
        reserved_points = self.reserved_world_points()
        placed_rects = []
        platforms = []
        placed_total = 0
        floor_placed = 0
        placed_by_type = {key: 0 for key in RANDOM_GAMEPLAY_ASSET_SPECS}

        def asset_source_size(sprite_key):
            if sprite_key in self._asset_size_cache:
                return self._asset_size_cache[sprite_key]

            path = ENVIRONMENT_IMAGE_PATHS.get(sprite_key)
            if not path:
                size = (96, 96)
            else:
                try:
                    image = pygame.image.load(path)
                    size = (max(1, image.get_width()), max(1, image.get_height()))
                except (pygame.error, OSError):
                    size = (96, 96)
            self._asset_size_cache[sprite_key] = size
            return size

        def try_place_asset(sprite_key, spec, use_spawn_chance=True, require_floor=False):
            nonlocal placed_total, floor_placed
            if placed_total >= MAX_RANDOM_GAMEPLAY_ASSETS_PER_LEVEL:
                return False
            if not ENVIRONMENT_IMAGE_PATHS.get(sprite_key):
                return False

            surfaces = self.random_asset_surfaces(spec.get("allow_upper", True))
            if require_floor:
                surfaces = [
                    surface_data for surface_data in surfaces
                    if self.is_floor_platform_data(surface_data)
                ]
            if not surfaces:
                return False

            spawn_chance = float(spec.get("spawn_chance", 0.0))
            source_w, source_h = asset_source_size(sprite_key)
            if "draw_width_range" in spec:
                draw_width = random.randint(*spec["draw_width_range"])
                draw_height = max(42, int(round(draw_width * (source_h / source_w))))
            else:
                scale_min, scale_max = spec.get("draw_scale_range", (1.0, 1.0))
                draw_scale = random.uniform(scale_min, scale_max)
                draw_width = max(70, int(round(source_w * draw_scale)))
                draw_height = max(54, int(round(source_h * draw_scale)))

            shuffled_surfaces = list(surfaces)
            random.shuffle(shuffled_surfaces)
            for surface_data in shuffled_surfaces:
                if use_spawn_chance and random.random() > RANDOM_GAMEPLAY_SURFACE_FILL_CHANCE:
                    continue
                if use_spawn_chance and random.random() > spawn_chance:
                    continue

                surface_rect = self.platform_rect_from_data(surface_data)
                surface_is_floor = self.is_floor_platform_data(surface_data)
                left = surface_rect.left + RANDOM_GAMEPLAY_ASSET_EDGE_MARGIN
                right = surface_rect.right - RANDOM_GAMEPLAY_ASSET_EDGE_MARGIN - draw_width
                if right <= left:
                    continue

                draw_left = random.randint(left, right)
                draw_top = surface_rect.top - draw_height
                collision_rects = self.random_asset_collision_rects(
                    spec,
                    draw_left,
                    draw_top,
                    draw_width,
                    draw_height,
                )
                rect = self.union_rects(collision_rects)
                if not self.is_random_asset_placement_valid(
                    rect,
                    occupied_rects,
                    placed_rects,
                    reserved_points,
                ):
                    continue

                platforms.append(
                    {
                        "x": rect.x,
                        "y": rect.y,
                        "width": rect.width,
                        "height": rect.height,
                        "collision_rects": self.relative_rects(collision_rects, rect),
                        "sprite": sprite_key,
                        "visual_width": draw_width,
                        "visual_height": draw_height,
                        "visual_x_offset": draw_left - rect.left,
                        "visual_bottom_offset": surface_rect.top - rect.bottom,
                        # Bottom-align to the surface, then sink the art a few
                        # pixels so it feels planted instead of hovering.
                        "visual_y_offset": RANDOM_GAMEPLAY_ASSET_SURFACE_SINK,
                        "align_visual_bottom": True,
                        "collidable": True,
                        "drop_through": False,
                        "surface": "floor" if surface_is_floor else "platform",
                        "section": self.section_name_for_x(rect.centerx),
                    }
                )
                placed_rects.append(rect)
                placed_total += 1
                if surface_is_floor:
                    floor_placed += 1
                placed_by_type[sprite_key] = placed_by_type.get(sprite_key, 0) + 1
                return True

            return False

        def try_place_random_asset(require_floor=False, allow_small_rubble=True):
            candidates = []
            for sprite_key, spec in RANDOM_GAMEPLAY_ASSET_SPECS.items():
                max_count = max(0, int(spec.get("max_count", 0)))
                if max_count == 0:
                    continue
                if placed_by_type.get(sprite_key, 0) >= max_count:
                    continue
                if not allow_small_rubble and sprite_key == "small_rubble":
                    continue
                candidates.append(sprite_key)

            random.shuffle(candidates)
            for sprite_key in candidates:
                spec = RANDOM_GAMEPLAY_ASSET_SPECS[sprite_key]
                if try_place_asset(sprite_key, spec, use_spawn_chance=False, require_floor=require_floor):
                    return True
            return False

        target_min, target_max = RANDOM_GAMEPLAY_ASSET_TARGET_RANGE
        target_total = random.randint(target_min, target_max)
        target_total = max(0, min(target_total, MAX_RANDOM_GAMEPLAY_ASSETS_PER_LEVEL))
        required_floor = min(MIN_FLOOR_RANDOM_ASSETS_PER_LEVEL, target_total)

        # Place a couple of props on the main floor first so the level variation
        # is not only on floating platforms.
        for _ in range(max(1, required_floor * 8)):
            if placed_total >= target_total or floor_placed >= required_floor:
                break
            try_place_random_asset(require_floor=True)

        # Fill the remaining sparse prop budget by choosing asset types in a
        # random order each attempt instead of always favoring the first spec.
        for _ in range(max(1, target_total * 12)):
            if placed_total >= target_total:
                break
            try_place_random_asset(require_floor=False)

        if placed_total > 1 and placed_by_type.get("small_rubble", 0) == placed_total:
            for _ in range(len(RANDOM_GAMEPLAY_ASSET_SPECS) * 4):
                if placed_total >= MAX_RANDOM_GAMEPLAY_ASSETS_PER_LEVEL:
                    break
                if try_place_random_asset(require_floor=False, allow_small_rubble=False):
                    break

        return platforms

    def random_asset_collision_rects(self, spec, draw_left, draw_top, draw_width, draw_height):
        image_bounds = pygame.Rect(draw_left, draw_top, draw_width, draw_height)
        collision_rects = []
        for rect_spec in spec.get("collision_rects", ()):
            if len(rect_spec) != 4:
                continue
            rx, ry, rw, rh = rect_spec
            rect = pygame.Rect(
                round(draw_left + draw_width * float(rx)),
                round(draw_top + draw_height * float(ry)),
                max(8, round(draw_width * float(rw))),
                max(8, round(draw_height * float(rh))),
            ).clip(image_bounds)
            if rect.width >= 8 and rect.height >= 8:
                collision_rects.append(rect)

        if collision_rects:
            return collision_rects

        collider_width_ratio = float(spec.get("collider_width_ratio", 0.8))
        collider_height_ratio = float(spec.get("collider_height_ratio", 0.7))
        collider_width = max(54, int(round(draw_width * collider_width_ratio)))
        collider_height = max(34, int(round(draw_height * collider_height_ratio)))
        return [
            pygame.Rect(
                draw_left + (draw_width - collider_width) // 2,
                draw_top + draw_height - collider_height,
                collider_width,
                collider_height,
            )
        ]

    def union_rects(self, rects):
        if not rects:
            return pygame.Rect(0, 0, 1, 1)

        union = rects[0].copy()
        for rect in rects[1:]:
            union.union_ip(rect)
        return union

    def relative_rects(self, rects, origin_rect):
        return [
            (
                rect.left - origin_rect.left,
                rect.top - origin_rect.top,
                rect.width,
                rect.height,
            )
            for rect in rects
        ]

    def can_place_close_foreground(self, x, used_x):
        if abs(x - self.player_start[0]) < 260:
            return False
        if abs(x - self.exit_position[0]) < 260:
            return False
        for previous_x in used_x:
            if abs(x - previous_x) < CLOSE_FOREGROUND_MIN_SPACING:
                return False
        return True

    def build_close_foreground_assets(self):
        if not self.sections:
            return []

        def asset_source_size(sprite_key):
            if sprite_key in self._asset_size_cache:
                return self._asset_size_cache[sprite_key]

            path = ENVIRONMENT_IMAGE_PATHS.get(sprite_key)
            if not path:
                size = (320, SCREEN_HEIGHT)
            else:
                try:
                    image = pygame.image.load(path)
                    size = (max(1, image.get_width()), max(1, image.get_height()))
                except (pygame.error, OSError):
                    size = (320, SCREEN_HEIGHT)
            self._asset_size_cache[sprite_key] = size
            return size

        placed = []
        used_x = []
        sprite_keys = [
            key for key in CLOSE_FOREGROUND_ASSET_SPECS
            if ENVIRONMENT_IMAGE_PATHS.get(key)
        ]
        if not sprite_keys:
            return []
        random.shuffle(sprite_keys)

        for section in self.sections:
            if len(placed) >= MAX_CLOSE_FOREGROUND_OBJECTS:
                break
            if random.random() > CLOSE_FOREGROUND_SPAWN_CHANCE:
                continue

            section_start = int(section.get("start_x", 0))
            section_end = int(section.get("end_x", self.level_width))
            if section_end - section_start < 200:
                continue

            sprite_key = sprite_keys[len(placed) % len(sprite_keys)]
            spec = CLOSE_FOREGROUND_ASSET_SPECS[sprite_key]
            source_w, source_h = asset_source_size(sprite_key)
            if spec.get("full_screen_height"):
                overscan = int(round(SCREEN_HEIGHT * CLOSE_FOREGROUND_VERTICAL_OVERSCAN))
                height = SCREEN_HEIGHT + overscan * 2
                width = int(round(source_w * (height / source_h)))
                width = max(spec["width_range"][0], min(width, spec["width_range"][1]))
            else:
                height = random.randint(*spec["height_range"])
                width = int(round(source_w * (height / source_h)))
                width = max(spec["width_range"][0], min(width, spec["width_range"][1]))
            left = section_start + 70
            right = section_end - width - 70
            if right <= left:
                continue

            x = random.randint(left, right)
            if not self.can_place_close_foreground(x, used_x):
                continue

            if spec.get("full_screen_height"):
                y = -int(round(SCREEN_HEIGHT * CLOSE_FOREGROUND_VERTICAL_OVERSCAN))
            elif spec.get("kind") == "vine":
                y = random.randint(-40, 120)
            else:
                y = GROUND_Y - height - random.randint(30, 90)

            placed.append(
                {
                    "sprite": sprite_key,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "parallax": random.uniform(*spec["parallax_range"]),
                    "section": section.get("name"),
                }
            )
            used_x.append(x)

        # If randomness produced too few occluders, add a couple guaranteed
        # placements near early/mid sections to keep depth visible.
        if len(placed) < MIN_CLOSE_FOREGROUND_OBJECTS:
            for section in self.sections[:3]:
                if len(placed) >= MIN_CLOSE_FOREGROUND_OBJECTS:
                    break

                section_start = int(section.get("start_x", 0))
                section_end = int(section.get("end_x", self.level_width))
                sprite_key = sprite_keys[len(placed) % len(sprite_keys)]
                spec = CLOSE_FOREGROUND_ASSET_SPECS[sprite_key]
                source_w, source_h = asset_source_size(sprite_key)
                if spec.get("full_screen_height"):
                    overscan = int(round(SCREEN_HEIGHT * CLOSE_FOREGROUND_VERTICAL_OVERSCAN))
                    height = SCREEN_HEIGHT + overscan * 2
                    width = int(round(source_w * (height / source_h)))
                    width = max(spec["width_range"][0], min(width, spec["width_range"][1]))
                else:
                    height = random.randint(*spec["height_range"])
                    width = int(round(source_w * (height / source_h)))
                    width = max(spec["width_range"][0], min(width, spec["width_range"][1]))
                section_width = max(1, section_end - section_start)
                x = section_start + int(section_width * 0.68)
                if not self.can_place_close_foreground(x, used_x):
                    continue

                if spec.get("full_screen_height"):
                    y = -int(round(SCREEN_HEIGHT * CLOSE_FOREGROUND_VERTICAL_OVERSCAN))
                else:
                    y = random.randint(-20, 90) if spec.get("kind") == "vine" else GROUND_Y - height - 52
                placed.append(
                    {
                        "sprite": sprite_key,
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height,
                        "parallax": random.uniform(*spec["parallax_range"]),
                        "section": section.get("name"),
                    }
                )
                used_x.append(x)

        return placed

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
        enemy_progression = self.current_level.get("enemy_progression", {})
        priority_section = self.current_level.get("priority_spawn_section")
        allowed_types = enemy_progression.get("allowed_types")
        if allowed_types is not None:
            allowed_types = set(allowed_types)

        max_total = enemy_progression.get("max_total")
        if max_total is not None:
            max_total = max(0, int(max_total))

        filtered_templates = []
        templates = self.collect_section_items("enemy_spawns", fallback=ENEMY_SPAWN_POINTS)
        for template in templates:
            min_level = template.get("min_level", 1)
            if current_level_number < min_level:
                continue

            enemy_type = (
                template.get("type")
                or template.get("enemyType")
                or template.get("enemy_type")
            )
            if allowed_types is not None and enemy_type not in allowed_types:
                continue

            filtered_templates.append(template)

        scheduled_total = 0
        reserved_template_index = None

        if priority_section and max_total and max_total > 0:
            for index, template in enumerate(filtered_templates):
                if template.get("section") != priority_section:
                    continue

                reserved_template_index = index
                reserved_template = dict(template)
                reserved_template["amount"] = 1
                spawn_points.append(self.build_spawn_point(reserved_template))
                scheduled_total += 1
                break

        for index, template in enumerate(filtered_templates):
            reserved_one = index == reserved_template_index

            amount = max(1, int(template.get("amount", 1)))
            if reserved_one:
                amount -= 1

            if amount <= 0:
                continue

            if max_total is not None:
                remaining = max_total - scheduled_total
                if remaining <= 0:
                    break
                if amount > remaining:
                    template = dict(template)
                    template["amount"] = remaining
                    amount = remaining

            scheduled_total += amount

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
