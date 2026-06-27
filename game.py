import pygame
import random
from asset_manager import AssetManager
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    MAX_FRAME_DT,
    COLOR_BACKGROUND,
    COLOR_TEXT,
    SHOW_FPS_COUNTER,
    DRAW_PROCEDURAL_DECORATIONS,
    DRAW_PLATFORM_VISUALS,
    DRAW_GROUND_PLATFORM_VISUAL,
    DRAW_FLOOR_VISUAL,
    DRAW_MARGIN,
    COLLISION_QUERY_MARGIN,
    BULLET_COLLISION_QUERY_MARGIN,
    IMAGE_PATHS,
    ENVIRONMENT_IMAGE_PATHS,
    PLATFORM_KEYS,
    FLOOR_ASSET_KEY,
    FLOOR_SURFACE_OFFSET_Y,
    BACKGROUND_CUTOUT_KEYS,
    is_preprocessed_image_path,
    SPRITE_SHEETS,
    ENEMY_TYPE_CONFIGS,
    PICKUP_SPRITES,
    AMMO_PICKUP_AMOUNT,
    HEALTH_PICKUP_AMOUNT,
    AMMO_DROP_CHANCE,
    HEALTH_DROP_CHANCE,
)
from animation import flipped_surface
from player import Player
from level_manager import LevelManager
from upgrade_manager import UpgradeManager
from ui import UI
from platforms import Platform
from platform_nav import PlatformGraph, DEBUG_PATHS
from pickup import Pickup

GAME_STATES = [
    "MAIN_MENU",
    "LOADING",
    "PLAYING",
    "UPGRADE_SELECT",
    "PAUSED",
    "GAME_OVER",
    "VICTORY",
]

class Game:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.DOUBLEBUF,
        )
        pygame.display.set_caption("Zombie Platform Shooter")
        self.clock = pygame.time.Clock()
        self.state = "MAIN_MENU"
        self.assets = AssetManager()
        self.images = self.assets.images
        self.scaled_background = None
        self.parallax_cache = {}
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing level"
        self.loading_context = "new_game"
        self.level_manager = LevelManager()
        self.preloaded_sections = set()
        self.platforms = []
        self.floor_platform = None
        self.platform_graph = None
        self.load_level_layout()
        self.player = self.create_player()
        self.upgrade_manager = UpgradeManager()
        self.ui = UI()
        self.bullets = []
        self.pickups = []
        self.last_mouse = (0, 0)
        self.camera_x = 0
        self.show_fps_counter = SHOW_FPS_COUNTER
        self.debug_font = pygame.font.SysFont(None, 20)

    def load_level_layout(self):
        self.platforms = [
            Platform(rect, idx)
            for idx, rect in enumerate(self.level_manager.platforms)
        ]
        self.floor_platform = self.find_floor_platform()
        self.platform_graph = PlatformGraph(self.platforms)

    def find_floor_platform(self):
        for platform in self.platforms:
            is_level_floor = (
                platform.rect.width >= self.level_manager.level_width * 0.9
                and platform.rect.top >= SCREEN_HEIGHT * 0.75
            )
            if is_level_floor:
                return platform
        return None

    def create_player(self):
        x, y = self.level_manager.player_start
        return Player(
            x,
            y,
            animations=self.images.get("player"),
            arms_image=self.images.get("player_arms"),
            bullet_animations=self.images.get("bullet"),
        )

    def reset_player_for_level(self):
        self.player.rect.topleft = self.level_manager.player_start
        self.player.vx = 0
        self.player.vy = 0
        self.player.on_ground = False
        self.update_camera()

    def load_images(self):
        self.load_current_level_assets()
        return self.images

    def load_image(
        self,
        key,
        path,
        remove_light_pixels=False,
        remove_light_pixels_from_edges=False,
        trim_transparent=False,
        transparent_min_value=225,
        transparent_channel_spread=36,
    ):
        image = self.assets.load_image(
            key,
            path,
            remove_light_pixels=remove_light_pixels,
            remove_light_pixels_from_edges=remove_light_pixels_from_edges,
            trim_transparent=trim_transparent,
            transparent_min_value=transparent_min_value,
            transparent_channel_spread=transparent_channel_spread,
        )
        if key == "background" and image:
            self.scaled_background = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return image

    def load_environment_image(self, key):
        path = ENVIRONMENT_IMAGE_PATHS.get(key)
        is_preprocessed = is_preprocessed_image_path(path)
        is_platform_sprite = key in PLATFORM_KEYS
        is_floor_sprite = key == FLOOR_ASSET_KEY
        is_cutout_background = key in BACKGROUND_CUTOUT_KEYS
        min_value = 205 if is_cutout_background or is_floor_sprite else 225
        channel_spread = 46 if is_cutout_background or is_floor_sprite else 36
        return self.load_image(
            key,
            path,
            remove_light_pixels=(
                not is_preprocessed
                and (is_platform_sprite or is_cutout_background or is_floor_sprite)
            ),
            trim_transparent=is_platform_sprite,
            transparent_min_value=min_value,
            transparent_channel_spread=channel_spread,
        )

    def load_core_image(self, key, path):
        if key == "player_arms":
            needs_cleanup = not is_preprocessed_image_path(path)
            return self.load_image(
                key,
                path,
                remove_light_pixels=needs_cleanup,
                remove_light_pixels_from_edges=needs_cleanup,
                trim_transparent=False,
                transparent_min_value=185,
                transparent_channel_spread=52,
            )
        return self.load_image(key, path)

    def load_animation(self, key):
        sheet_config = SPRITE_SHEETS.get(key)
        return self.assets.load_animation(key, sheet_config)

    def load_core_gameplay_assets(self):
        for key, path in IMAGE_PATHS.items():
            self.load_core_image(key, path)
        self.load_pickup_sprites()
        for key in ("player", "bullet"):
            self.load_animation(key)

    def current_level_visual_asset_keys(self, section_names=None, section_limit=None):
        visual_keys = set()

        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            if image_key:
                visual_keys.add(image_key)

        if DRAW_FLOOR_VISUAL:
            visual_keys.add(FLOOR_ASSET_KEY)

        relevant_sections = self.level_manager.sections
        if section_names is not None:
            relevant_sections = [
                section for section in self.level_manager.sections
                if section.get("name") in section_names
            ]
        elif section_limit is not None:
            relevant_sections = self.level_manager.sections[:section_limit]

        if DRAW_PLATFORM_VISUALS:
            for section in relevant_sections:
                for platform_data in section.get("platforms", []):
                    if isinstance(platform_data, dict) and platform_data.get("sprite"):
                        visual_keys.add(platform_data["sprite"])

        for section in relevant_sections:
            for decoration in section.get("decorations", []):
                sprite_key = decoration.get("sprite")
                if sprite_key:
                    visual_keys.add(sprite_key)

        return sorted(visual_keys)

    def load_current_level_visual_assets(self):
        for key in self.current_level_visual_asset_keys():
            if key in ENVIRONMENT_IMAGE_PATHS:
                self.load_environment_image(key)

    def load_pickup_sprites(self):
        sheet = self.images.get("pickup_sheet")
        for pickup_type, config in PICKUP_SPRITES.items():
            key = f"{pickup_type}_pickup"
            if key in self.images:
                continue
            self.images[key] = self.create_pickup_sprite(sheet, config)

    def create_pickup_sprite(self, sheet, config):
        if sheet is None:
            return None

        source_rect = pygame.Rect(
            config["source_x"],
            config["source_y"],
            config["source_width"],
            config["source_height"],
        )
        sprite = pygame.Surface(source_rect.size, pygame.SRCALPHA)
        sprite.blit(sheet, (0, 0), source_rect)
        return pygame.transform.scale(
            sprite,
            (config["draw_width"], config["draw_height"]),
        )

    def current_level_enemy_asset_keys(self, section_names=None, section_limit=None):
        keys = set()

        relevant_spawn_points = self.level_manager.enemy_spawn_points
        if section_names is not None:
            relevant_spawn_points = [
                spawn_point for spawn_point in self.level_manager.enemy_spawn_points
                if spawn_point.get("section") in section_names
            ]
        elif section_limit is not None:
            relevant_spawn_points = self.level_manager.enemy_spawn_points[:section_limit]

        for spawn_point in relevant_spawn_points:
            type_config = ENEMY_TYPE_CONFIGS.get(spawn_point.get("type"), {})
            for key_name in ("animation_key", "spawn_sheet"):
                key = spawn_point.get(key_name, type_config.get(key_name))
                if key:
                    keys.add(key)

        return sorted(keys)

    def load_current_level_enemy_assets(self):
        for key in self.current_level_enemy_asset_keys():
            self.load_animation(key)

    def load_current_level_assets(self):
        self.load_core_gameplay_assets()
        self.load_current_level_visual_assets()
        self.load_current_level_enemy_assets()

    def add_loading_task(self, tasks, label, function, *args):
        tasks.append((label, lambda function=function, args=args: function(*args)))

    def current_level_section_names(self):
        return [
            section.get("name")
            for section in self.level_manager.sections
            if section.get("name")
        ]

    def prepare_start_loading_tasks(self):
        self.level_manager.start_level()
        self.load_level_layout()
        section_names = self.current_level_section_names()

        # Each task runs on a separate loading update. That lets the loading
        # screen repaint instead of freezing during one large asset load.
        tasks = []
        for key, path in IMAGE_PATHS.items():
            self.add_loading_task(tasks, f"Loading {key}", self.load_core_image, key, path)

        self.add_loading_task(tasks, "Preparing pickups", self.load_pickup_sprites)

        for key in self.current_level_visual_asset_keys(section_names=section_names):
            if key in ENVIRONMENT_IMAGE_PATHS:
                self.add_loading_task(tasks, f"Loading {key}", self.load_environment_image, key)

        animation_keys = ["player", "bullet"]
        for key in self.current_level_enemy_asset_keys(section_names=section_names):
            if key not in animation_keys:
                animation_keys.append(key)
        for key in animation_keys:
            self.add_loading_task(tasks, f"Loading {key}", self.load_animation, key)

        self.add_loading_task(tasks, "Preparing backgrounds", self.prepare_parallax_cache)
        self.add_loading_task(tasks, "Preparing platform sprites", self.prepare_platform_surfaces)
        self.add_loading_task(tasks, "Preparing flipped frames", self.prepare_flipped_animation_frames)

        self.loading_tasks = tasks
        self.loading_task_index = 0
        self.loading_task_total = len(tasks)

    def prepare_runtime_caches(self, section_names=None):
        self.prepare_parallax_cache()
        self.prepare_platform_surfaces(section_names=section_names)

    def prepare_flipped_animation_frames(self):
        for image_group in self.images.values():
            if not isinstance(image_group, dict):
                continue
            for animation in image_group.values():
                for frame in getattr(animation, "frames", []):
                    flipped_surface(frame)

    def prepare_parallax_cache(self):
        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            image = self.images.get(image_key)
            if image:
                self.scaled_parallax_layer(image_key, image)

    def prepare_platform_surfaces(self, section_names=None):
        if not DRAW_PLATFORM_VISUALS:
            return

        section_filter = set(section_names) if section_names is not None else None
        for platform in self.platforms:
            if section_filter is not None and platform.section not in section_filter:
                continue
            if not self.should_draw_platform_visual(platform):
                continue
            platform.prepare_surface(images=self.images)

    def should_draw_platform_visual(self, platform):
        if not DRAW_PLATFORM_VISUALS:
            return False
        if DRAW_GROUND_PLATFORM_VISUAL:
            return True

        # The first ground platform spans almost the whole level. Collision
        # remains active, but its old map-like art stays hidden so the new
        # backgrounds are the only large environment layer.
        return platform.rect.width < self.level_manager.level_width * 0.9

    def request_start_game(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.loading_context = "new_game"
        self.state = "LOADING"
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing level"

    def request_next_level_loading(self):
        self.loading_context = "next_level"
        self.state = "LOADING"
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing next level"

    def start_game(self):
        self.level_manager.reset()
        self.loading_context = "new_game"
        self.prepare_start_loading_tasks()
        for _, task in self.loading_tasks:
            task()
        self.loading_task_index = self.loading_task_total
        self.finish_loading()

    def finish_start_game(self):
        self.preloaded_sections = set()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.spawn_level_pickups()
        self.update_camera()
        self.mark_sections_preloaded(self.current_level_section_names())
        self.state = "PLAYING"
        self.clear_loading_state()

    def finish_next_level(self):
        self.preloaded_sections = set()
        self.reset_player_for_level()
        self.bullets = []
        self.pickups = []
        self.spawn_level_pickups()
        self.mark_sections_preloaded(self.current_level_section_names())
        self.state = "PLAYING"
        self.clear_loading_state()

    def finish_loading(self):
        if self.loading_context == "next_level":
            self.finish_next_level()
            return
        self.finish_start_game()

    def clear_loading_state(self):
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing level"

    def update_loading(self):
        if not self.loading_screen_drawn:
            return

        if not self.loading_tasks:
            self.prepare_start_loading_tasks()
            self.loading_status = "Loading 0 / {}".format(self.loading_task_total)
            return

        if self.loading_task_index < len(self.loading_tasks):
            label, task = self.loading_tasks[self.loading_task_index]
            self.loading_status = "{} ({} / {})".format(
                label,
                self.loading_task_index + 1,
                self.loading_task_total,
            )
            task()
            self.loading_task_index += 1
            return

        self.finish_loading()

    def loading_progress(self):
        if not self.loading_task_total:
            return 0.0
        return self.loading_task_index / self.loading_task_total

    def reset(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.preloaded_sections = set()
        self.update_camera()
        self.state = "MAIN_MENU"
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing level"

    def run(self):
        running = True
        while running:
            # If a frame hitches, cap dt so animations and physics do not try
            # to process a huge catch-up step all at once.
            dt = min(self.clock.tick(FPS) / 1000, MAX_FRAME_DT)
            now = pygame.time.get_ticks() / 1000
            self.handle_events(now)
            self.update(dt, now)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_events(self, now):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEMOTION:
                self.last_mouse = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "MAIN_MENU":
                    self.request_start_game()
                elif self.state == "PLAYING":
                    keys = pygame.key.get_pressed()
                    if self.player.run_input_active(keys):
                        continue
                    bullet = self.player.shoot(self.screen_to_world(self.last_mouse), now)
                    if bullet:
                        self.bullets.append(bullet)
                elif self.state == "UPGRADE_SELECT":
                    self.handle_upgrade_click(event.pos)
                elif self.state in ["GAME_OVER", "VICTORY"]:
                    pass
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.state = "PAUSED"
                    elif self.state == "PAUSED":
                        self.state = "PLAYING"
                if event.key == pygame.K_f and self.state == "PAUSED":
                    self.show_fps_counter = not self.show_fps_counter
                if event.key == pygame.K_d and self.state == "PAUSED":
                    import settings
                    settings.DEBUG_AIM_PIVOT = not settings.DEBUG_AIM_PIVOT
                if event.key == pygame.K_r:
                    if self.state == "PLAYING":
                        self.player.reload(now)
                    elif self.state in ["GAME_OVER", "VICTORY"]:
                        self.reset()
                if self.state == "UPGRADE_SELECT" and event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    choice_index = event.key - pygame.K_1
                    self.apply_upgrade_choice(choice_index)

    def handle_upgrade_click(self, mouse_pos):
        card_width = 440
        card_height = 260
        spacing = 60
        total_width = len(self.upgrade_manager.current_choices) * card_width + (len(self.upgrade_manager.current_choices) - 1) * spacing
        x_start = (SCREEN_WIDTH - total_width) // 2
        y = 220
        for index in range(len(self.upgrade_manager.current_choices)):
            x = x_start + index * (card_width + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            if card_rect.collidepoint(mouse_pos):
                self.apply_upgrade_choice(index)

    def apply_upgrade_choice(self, choice_index):
        if 0 <= choice_index < len(self.upgrade_manager.current_choices):
            picked = self.upgrade_manager.current_choices[choice_index]
            self.player.picked_upgrades.append(picked["name"])
        self.upgrade_manager.apply_upgrade(self.player, choice_index)
        if self.level_manager.next_level():
            self.request_next_level_loading()
        else:
            self.state = "VICTORY"

    def screen_to_world(self, screen_pos):
        return (screen_pos[0] + self.camera_x, screen_pos[1])

    def update_camera(self):
        max_camera_x = max(0, self.level_manager.level_width - SCREEN_WIDTH)
        target_x = self.player.rect.centerx - SCREEN_WIDTH // 2
        self.camera_x = max(0, min(target_x, max_camera_x))

    def is_world_rect_visible(self, rect, margin=DRAW_MARGIN):
        # Drawing off-screen objects wastes time. The margin prevents pop-in at
        # the screen edge while still skipping far-away objects.
        return (
            rect.right >= self.camera_x - margin
            and rect.left <= self.camera_x + SCREEN_WIDTH + margin
            and rect.bottom >= -margin
            and rect.top <= SCREEN_HEIGHT + margin
        )

    def platforms_near_rect(self, rect, padding=COLLISION_QUERY_MARGIN):
        # The player and bullets only need to collide with platforms close to
        # their current x position, not every platform in the whole level.
        left = rect.left - padding
        right = rect.right + padding
        nearby = [
            platform
            for platform in self.platforms
            if platform.rect.right >= left and platform.rect.left <= right
        ]
        return nearby or self.platforms

    def update(self, dt, now):
        if self.state == "LOADING":
            self.update_loading()
            return
        if self.state == "GAME_OVER":
            self.player.update_death_animation(dt)
            return

        if self.state == "PLAYING":
            keys = pygame.key.get_pressed()
            player_platforms = self.platforms_near_rect(self.player.rect)
            self.player.update(keys, player_platforms, now, dt, self.level_manager.level_width)
            self.update_camera()
            removed_enemies = self.level_manager.update(
                dt,
                self.platforms,
                self.player,
                self.images,
                self.platform_graph,
            )
            self.spawn_pickups_from_removed_enemies(removed_enemies)
            self.update_bullets(dt)
            self.check_collisions(now)
            self.update_pickups()
            if self.player.health <= 0:
                self.player.die()
                self.state = "GAME_OVER"
            elif self.level_manager.level_complete(self.player):
                if self.level_manager.is_final_level():
                    self.state = "VICTORY"
                else:
                    self.upgrade_manager.pick_upgrades()
                    self.state = "UPGRADE_SELECT"

    def mark_sections_preloaded(self, section_names):
        for section_name in section_names:
            if section_name:
                self.preloaded_sections.add(section_name)

    def update_bullets(self, dt):
        for index in range(len(self.bullets) - 1, -1, -1):
            bullet = self.bullets[index]
            if not self.is_world_rect_visible(bullet.rect, margin=BULLET_COLLISION_QUERY_MARGIN):
                del self.bullets[index]
                continue

            bullet_platforms = self.platforms_near_rect(
                bullet.rect,
                padding=BULLET_COLLISION_QUERY_MARGIN,
            )
            if not bullet.update(bullet_platforms, dt, self.level_manager.level_width):
                del self.bullets[index]

    def spawn_pickups_from_removed_enemies(self, enemies):
        for enemy in enemies:
            if getattr(enemy, "has_dropped_pickup", False):
                continue
            enemy.has_dropped_pickup = True
            pickup_type = self.roll_pickup_type()
            if not pickup_type:
                continue
            self.spawn_pickup(pickup_type, enemy.rect.centerx, enemy.rect.bottom)

    def roll_pickup_type(self):
        roll = random.random()
        if roll < AMMO_DROP_CHANCE:
            return "ammo"
        if roll < AMMO_DROP_CHANCE + HEALTH_DROP_CHANCE:
            return "health"
        return None

    def spawn_level_pickups(self):
        for pickup_point in self.level_manager.pickup_spawn_points:
            self.spawn_pickup(
                pickup_point["type"],
                pickup_point["x"],
                pickup_point["y"],
                amount=pickup_point.get("amount"),
            )

    def spawn_pickup(self, pickup_type, x, y, amount=None):
        if pickup_type not in PICKUP_SPRITES:
            return
        config = PICKUP_SPRITES[pickup_type]
        if amount is None:
            amount = AMMO_PICKUP_AMOUNT if pickup_type == "ammo" else HEALTH_PICKUP_AMOUNT
        image = self.images.get(f"{pickup_type}_pickup")
        self.pickups.append(
            Pickup(
                pickup_type,
                x,
                y,
                config["draw_width"],
                config["draw_height"],
                amount,
                image=image,
            )
        )

    def update_pickups(self):
        for index in range(len(self.pickups) - 1, -1, -1):
            pickup = self.pickups[index]
            if not self.is_world_rect_visible(pickup.rect, margin=DRAW_MARGIN):
                continue

            pickup.update()
            if (
                pickup.check_collision_with_player(self.player)
                and pickup.collect(self.player)
            ):
                del self.pickups[index]

    def check_collisions(self, now):
        for enemy in self.level_manager.active_enemies:
            if getattr(enemy, "dead", False) or not enemy.is_active():
                continue
            if enemy.rect.colliderect(self.player.rect):
                enemy.start_attack()
                self.player.apply_hurt(enemy.damage, now)
            for bullet in self.bullets:
                if getattr(bullet, "impacting", False) or getattr(bullet, "removable", False):
                    continue
                if not self.rects_near_for_collision(enemy.rect, bullet.rect):
                    continue
                if enemy.rect.colliderect(bullet.rect):
                    enemy.take_damage(bullet.damage)
                    bullet.start_impact()
                    break

    def rects_near_for_collision(self, rect_a, rect_b, padding=80):
        return (
            rect_a.right + padding >= rect_b.left
            and rect_a.left - padding <= rect_b.right
            and rect_a.bottom + padding >= rect_b.top
            and rect_a.top - padding <= rect_b.bottom
        )

    def draw(self):
        if self.state == "MAIN_MENU":
            self.ui.draw_main_menu(self.screen)
            return
        if self.state == "LOADING":
            self.ui.draw_loading(
                self.screen,
                progress=self.loading_progress(),
                status=self.loading_status,
            )
            self.loading_screen_drawn = True
            return
        if self.state == "PAUSED":
            self.draw_gameplay()
            self.ui.draw_pause(self.screen, self.show_fps_counter)
            return
        if self.state == "GAME_OVER":
            self.draw_gameplay()
            self.ui.draw_game_over(self.screen)
            return
        if self.state == "VICTORY":
            self.draw_gameplay()
            self.ui.draw_victory(self.screen)
            return
        if self.state == "UPGRADE_SELECT":
            self.ui.draw_upgrade_screen(self.screen, self.upgrade_manager.current_choices)
            return
        if self.state == "PLAYING":
            self.draw_gameplay()

    def draw_parallax_backgrounds(self):
        self.screen.fill((22, 27, 26))
        drew_layer = False

        # The old four-layer background setup is replaced by the three entries
        # in settings.BACKGROUND_LAYERS:
        # background_1 = far skyline, background_2 = ruined cutout structure,
        # background_3 = closest detail strip. They are drawn separately, not
        # flattened, so transparent openings in layers 2/3 reveal layer 1.
        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            image = self.images.get(image_key)
            if not image:
                continue

            scaled = self.scaled_parallax_layer(image_key, image)
            tile_width = scaled.get_width()
            # Camera x times layer speed creates parallax. Slow layers drift
            # gently in the distance; faster layers feel closer to the player.
            speed = layer.get("speed", 1.0)
            x = -int((self.camera_x * speed) % tile_width)
            # Only draw enough copies to cover the screen. The old loop always
            # drew one extra copy on the left when x was already 0.
            copy_count = (SCREEN_WIDTH - x + tile_width - 1) // tile_width

            for copy_index in range(copy_count):
                self.screen.blit(scaled, (x + copy_index * tile_width, 0))
            drew_layer = True

        if not drew_layer:
            self.screen.fill(COLOR_BACKGROUND)

    def scaled_parallax_layer(self, key, image):
        cache_key = (key, id(image), SCREEN_WIDTH, SCREEN_HEIGHT)
        if cache_key in self.parallax_cache:
            return self.parallax_cache[cache_key]

        scale = SCREEN_HEIGHT / image.get_height()
        target_width = max(SCREEN_WIDTH, int(round(image.get_width() * scale)))
        scaled = pygame.transform.scale(image, (target_width, SCREEN_HEIGHT))
        self.parallax_cache[cache_key] = scaled
        return scaled

    def draw_floor(self):
        if not DRAW_FLOOR_VISUAL or not self.floor_platform:
            return

        floor_image = self.images.get(FLOOR_ASSET_KEY)
        if not floor_image:
            return

        tile_width = floor_image.get_width()
        if tile_width <= 0:
            return

        floor_rect = self.floor_platform.rect
        # The ground collision line is floor_rect.top. The sprite is drawn above
        # that line so the concrete surface inside the PNG lines up with where
        # the player and zombies actually stand.
        floor_sprite_y = floor_rect.top - FLOOR_SURFACE_OFFSET_Y
        visible_world_left = max(floor_rect.left, self.camera_x - DRAW_MARGIN)
        visible_world_right = min(
            floor_rect.right,
            self.camera_x + SCREEN_WIDTH + DRAW_MARGIN,
        )
        if visible_world_left >= visible_world_right:
            return

        # The floor PNG is not stretched. We repeat the original tile across the
        # level, but only blit the copies close to the camera.
        first_tile = max(0, (visible_world_left - floor_rect.left) // tile_width)
        tile_world_x = floor_rect.left + first_tile * tile_width
        while tile_world_x < visible_world_right:
            self.screen.blit(
                floor_image,
                (round(tile_world_x - self.camera_x), floor_sprite_y),
            )
            tile_world_x += tile_width

    def draw_decorations(self, layer="back"):
        for decoration in self.level_manager.decorations:
            decoration_layer = decoration.get("layer", "back")
            if layer == "back" and decoration_layer == "front":
                continue
            if layer == "front" and decoration_layer != "front":
                continue

            parallax = decoration.get("parallax", 1.0)
            screen_x = round(decoration["x"] - self.camera_x * parallax)
            width = decoration["width"]
            if screen_x + width < -DRAW_MARGIN or screen_x > SCREEN_WIDTH + DRAW_MARGIN:
                continue

            rect = pygame.Rect(
                screen_x,
                decoration["y"],
                width,
                decoration["height"],
            )
            self.draw_decoration(decoration.get("type", "rubble"), rect)

    def draw_decoration(self, kind, rect):
        if kind == "rubble":
            self.draw_rubble(rect)
        elif kind == "broken_desk":
            self.draw_broken_desk(rect)
        elif kind == "hanging_cable":
            self.draw_hanging_cable(rect)
        elif kind == "cracked_wall":
            self.draw_cracked_wall(rect)
        elif kind == "broken_floor":
            self.draw_broken_floor(rect)
        elif kind == "exposed_beam":
            self.draw_exposed_beam(rect)
        elif kind == "vines":
            self.draw_vines(rect)
        elif kind == "overgrowth":
            self.draw_overgrowth(rect)
        elif kind == "collapsed_structure":
            self.draw_collapsed_structure(rect)
        elif kind == "elevator_door":
            self.draw_elevator_door(rect)
        elif kind == "warning_light":
            self.draw_warning_light(rect)
        elif kind == "shattered_window":
            self.draw_shattered_window(rect)
        elif kind == "rooftop_antenna":
            self.draw_rooftop_antenna(rect)
        else:
            pygame.draw.rect(self.screen, (68, 72, 62), rect)

    def draw_rubble(self, rect):
        colors = [(72, 70, 61), (94, 88, 73), (47, 45, 40), (93, 105, 58)]
        piece_count = 7
        for index in range(piece_count):
            width = max(14, rect.width // (piece_count + 1))
            height = 12 + (index % 3) * 7
            x = rect.left + 12 + index * max(18, rect.width // piece_count)
            y = rect.bottom - height - (index % 2) * 6
            pygame.draw.rect(self.screen, colors[index % len(colors)], (x, y, width, height))

    def draw_broken_desk(self, rect):
        top = pygame.Rect(rect.left, rect.top + rect.height // 3, rect.width, rect.height // 5)
        pygame.draw.rect(self.screen, (88, 62, 41), top)
        pygame.draw.rect(self.screen, (42, 32, 25), top, 3)
        pygame.draw.line(self.screen, (40, 28, 20), top.midleft, (top.centerx, top.bottom + 18), 5)
        pygame.draw.line(self.screen, (40, 28, 20), top.midright, (top.centerx + 22, top.bottom + 28), 5)
        pygame.draw.rect(self.screen, (55, 50, 46), (rect.left + rect.width // 3, top.bottom, rect.width // 5, rect.height // 3))

    def draw_hanging_cable(self, rect):
        color = (26, 24, 21)
        points = [
            (rect.centerx, rect.top),
            (rect.left + rect.width // 3, rect.top + rect.height // 3),
            (rect.right - rect.width // 4, rect.top + rect.height * 2 // 3),
            (rect.centerx, rect.bottom),
        ]
        pygame.draw.lines(self.screen, color, False, points, max(3, rect.width // 4))
        pygame.draw.circle(self.screen, (50, 43, 34), (rect.centerx, rect.bottom), max(4, rect.width // 3))

    def draw_cracked_wall(self, rect):
        pygame.draw.rect(self.screen, (54, 58, 54), rect, 3)
        start = (rect.left + rect.width // 2, rect.top + 12)
        cracks = [
            (start, (rect.left + rect.width // 2 - 35, rect.top + rect.height // 3)),
            ((rect.left + rect.width // 2 - 35, rect.top + rect.height // 3), (rect.left + 30, rect.bottom - 30)),
            ((rect.left + rect.width // 2 - 10, rect.top + rect.height // 2), (rect.right - 40, rect.bottom - 45)),
            ((rect.left + rect.width // 2 - 10, rect.top + rect.height // 2), (rect.right - 24, rect.top + 58)),
        ]
        for start_pos, end_pos in cracks:
            pygame.draw.line(self.screen, (26, 29, 27), start_pos, end_pos, 4)

    def draw_broken_floor(self, rect):
        pygame.draw.rect(self.screen, (45, 43, 38), rect)
        for index in range(4):
            x = rect.left + 28 + index * rect.width // 5
            pygame.draw.line(
                self.screen,
                (20, 21, 20),
                (x, rect.top + 5),
                (x + 38, rect.bottom - 4),
                3,
            )
        pygame.draw.rect(self.screen, (93, 105, 58), (rect.left, rect.top, rect.width, 6))

    def draw_exposed_beam(self, rect):
        pygame.draw.rect(self.screen, (72, 48, 34), rect)
        pygame.draw.rect(self.screen, (31, 28, 25), rect, 3)
        brace_step = max(40, rect.width // 6)
        for x in range(rect.left, rect.right, brace_step):
            pygame.draw.line(self.screen, (33, 28, 23), (x, rect.bottom), (x + brace_step, rect.top), 3)

    def draw_vines(self, rect):
        vine_color = (63, 91, 42)
        leaf_color = (86, 119, 54)
        strand_count = max(3, rect.width // 34)
        for index in range(strand_count):
            x = rect.left + 12 + index * rect.width // strand_count
            pygame.draw.line(self.screen, vine_color, (x, rect.top), (x + (index % 3 - 1) * 12, rect.bottom), 4)
            for leaf in range(3):
                y = rect.top + 34 + leaf * rect.height // 4
                pygame.draw.rect(self.screen, leaf_color, (x - 8, y, 16, 10))

    def draw_overgrowth(self, rect):
        colors = [(58, 85, 44), (79, 108, 54), (39, 65, 38)]
        clump_width = max(28, rect.width // 8)
        for index in range(9):
            x = rect.left + index * clump_width
            height = rect.height // 2 + (index % 4) * 8
            pygame.draw.rect(self.screen, colors[index % len(colors)], (x, rect.bottom - height, clump_width, height))

    def draw_collapsed_structure(self, rect):
        self.draw_rubble(rect)
        pygame.draw.line(self.screen, (64, 45, 32), rect.topleft, rect.bottomright, 9)
        pygame.draw.line(self.screen, (39, 33, 29), (rect.left + 40, rect.bottom), (rect.right, rect.top + 18), 6)

    def draw_elevator_door(self, rect):
        pygame.draw.rect(self.screen, (35, 38, 39), rect)
        pygame.draw.rect(self.screen, (83, 85, 79), rect, 5)
        pygame.draw.line(self.screen, (15, 17, 18), rect.midtop, rect.midbottom, 5)
        pygame.draw.rect(self.screen, (110, 82, 40), (rect.right - 34, rect.top + 42, 18, 42))

    def draw_warning_light(self, rect):
        pygame.draw.rect(self.screen, (46, 42, 34), rect)
        pygame.draw.circle(self.screen, (160, 36, 28), rect.center, min(rect.width, rect.height) // 3)
        pygame.draw.circle(self.screen, (230, 74, 48), rect.center, min(rect.width, rect.height) // 5)

    def draw_shattered_window(self, rect):
        pygame.draw.rect(self.screen, (22, 28, 30), rect, 5)
        pygame.draw.line(self.screen, (40, 49, 52), rect.midtop, rect.midbottom, 4)
        pygame.draw.line(self.screen, (40, 49, 52), rect.midleft, rect.midright, 4)
        for start, end in [
            (rect.topleft, rect.center),
            (rect.center, (rect.right, rect.top + rect.height // 4)),
            (rect.center, (rect.left + rect.width // 4, rect.bottom)),
            ((rect.left + 20, rect.top + rect.height // 2), (rect.right - 25, rect.bottom - 20)),
        ]:
            pygame.draw.line(self.screen, (137, 156, 160), start, end, 3)

    def draw_rooftop_antenna(self, rect):
        pygame.draw.line(self.screen, (58, 55, 49), rect.midbottom, rect.midtop, 6)
        pygame.draw.line(self.screen, (58, 55, 49), (rect.left, rect.top + rect.height // 3), (rect.right, rect.top + rect.height // 3), 5)
        pygame.draw.line(self.screen, (58, 55, 49), (rect.left + 10, rect.top + rect.height // 2), (rect.right - 10, rect.top + rect.height // 2), 4)
        pygame.draw.circle(self.screen, (145, 42, 32), rect.midtop, 7)

    def draw_gameplay(self):
        self.draw_parallax_backgrounds()

        # The bottom floor is only visual. Collision still comes from the simple
        # ground platform rectangle, so the transparent space in floor.png never
        # blocks the player, zombies, bullets, or pickups.
        self.draw_floor()

        # The new background art already contains the environmental detail.
        # Keeping old procedural decorations off prevents extra random-looking
        # rectangles/lines from being drawn over the supplied backgrounds.
        if DRAW_PROCEDURAL_DECORATIONS:
            self.draw_decorations(layer="back")

        if DRAW_PLATFORM_VISUALS:
            for platform in self.platforms:
                if not self.should_draw_platform_visual(platform):
                    continue
                if not self.is_world_rect_visible(platform.rect):
                    continue
                platform.draw(
                    self.screen,
                    images=self.images,
                    camera_x=self.camera_x,
                )

        self.draw_exit()
        if DRAW_PROCEDURAL_DECORATIONS:
            self.draw_decorations(layer="front")
        for pickup in self.pickups:
            if not self.is_world_rect_visible(pickup.rect):
                continue
            pickup.draw(self.screen, camera_x=self.camera_x)
        self.player.draw(self.screen, camera_x=self.camera_x)
        for enemy in self.level_manager.active_enemies:
            if not self.is_world_rect_visible(enemy.rect):
                continue
            enemy.draw(self.screen, camera_x=self.camera_x)
        for bullet in self.bullets:
            if not self.is_world_rect_visible(bullet.rect):
                continue
            bullet.draw(self.screen, camera_x=self.camera_x)

        if DEBUG_PATHS:
            self.platform_graph.draw(self.screen, self.debug_font, self.level_manager.active_enemies, self.camera_x)

        self.ui.draw_health_bar(self.screen, self.player)
        self.ui.draw_level(self.screen, self.level_manager.current_level_number())
        if self.show_fps_counter:
            self.ui.draw_fps_counter(self.screen, self.clock.get_fps())

    def draw_exit(self):
        exit_rect = self.level_manager.exit_rect()
        if not self.is_world_rect_visible(exit_rect):
            return

        exit_rect = exit_rect.move(-self.camera_x, 0)
        pygame.draw.rect(self.screen, (80, 220, 120), exit_rect)
        pygame.draw.rect(self.screen, COLOR_TEXT, exit_rect, 4)
