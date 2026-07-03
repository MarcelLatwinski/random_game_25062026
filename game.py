import pygame
import random
from pathlib import Path
from asset_manager import AssetManager
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    MAX_FRAME_DT,
    COLOR_BACKGROUND,
    COLOR_TEXT,
    SHOW_FPS_COUNTER,
    DEBUG_HEADSHOTS,
    DRAW_PROCEDURAL_DECORATIONS,
    DRAW_PLATFORM_VISUALS,
    DRAW_GROUND_PLATFORM_VISUAL,
    DRAW_FLOOR_VISUAL,
    DRAW_MARGIN,
    CLOSE_FOREGROUND_NEAR_PARALLAX_BOOST,
    COLLISION_QUERY_MARGIN,
    BULLET_COLLISION_QUERY_MARGIN,
    IMAGE_PATHS,
    ENVIRONMENT_IMAGE_PATHS,
    PLATFORM_KEYS,
    FLOOR_ASSET_KEY,
    FLOOR_SURFACE_OFFSET_Y,
    BACKGROUND_CUTOUT_KEYS,
    CLOSE_FOREGROUND_ASSET_KEYS,
    RANDOM_GAMEPLAY_ASSET_KEYS,
    is_preprocessed_image_path,
    SPRITE_SHEETS,
    ENEMY_TYPE_CONFIGS,
    PICKUP_SPRITES,
    AMMO_PICKUP_AMOUNT,
    HEALTH_PICKUP_AMOUNT,
    AMMO_DROP_CHANCE,
    HEALTH_DROP_CHANCE,
    HEADSHOT_DAMAGE_MULTIPLIER,
    HEADSHOT_INDICATOR_MAX_SIZE,
    GROUND_Y,
    LEVELS,
)
from animation import flipped_surface
from player import Player
from level_manager import LevelManager
from upgrade_manager import UpgradeManager
from ui import UI, load_font
from platforms import Platform
from platform_nav import PlatformGraph, DEBUG_PATHS
from pickup import Pickup

GAME_STATES = [
    "LOADING",
    "TITLE",
    "MAIN_MENU",
    "PLAYING",
    "UPGRADE_TRANSITION_OUT",
    "UPGRADE_SELECT",
    "UPGRADE_TRANSITION_IN",
    "PAUSED",
    "GAME_OVER",
    "VICTORY",
]
UPGRADE_MENU_STATES = (
    "UPGRADE_TRANSITION_OUT",
    "UPGRADE_SELECT",
    "UPGRADE_TRANSITION_IN",
)

LOADING_FINISH_DELAY = 0.10
EXIT_ARROW_WIDTH = 170
EXIT_ARROW_HEIGHT = 82
EXIT_SIGN_WIDTH = 210
EXIT_SIGN_HEIGHT = 48
GAME_SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOWED_FLAGS = pygame.DOUBLEBUF
WINDOWED_FULLSCREEN_FLAGS = pygame.DOUBLEBUF | pygame.NOFRAME


class HeadshotIndicator:
    def __init__(self, x, y, image):
        self.image = image
        self.x = float(x)
        self.y = float(y)
        self.lifetime = 1.0
        self.age = 0.0
        self.float_speed = 45
        self.alive = True

    def update(self, dt):
        self.age += dt
        self.y -= self.float_speed * dt
        if self.age >= self.lifetime:
            self.alive = False

    def draw(self, surface, camera_x=0):
        if not self.image:
            return

        progress = min(self.age / self.lifetime, 1.0)
        alpha = int(255 * (1.0 - progress))
        image = self.image.copy()
        image.set_alpha(alpha)
        rect = image.get_rect(center=(round(self.x - camera_x), round(self.y)))
        surface.blit(image, rect)


class Game:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.windowed_fullscreen = False
        self.display_surface = None
        self.present_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.present_scale_surface = None
        self.fullscreen_renderer = None
        self.fullscreen_frame_texture = None
        self.uses_hardware_presenter = False
        self.apply_display_mode()
        self.clock = pygame.time.Clock()
        self.state = "LOADING"
        self.assets = AssetManager()
        self.images = self.assets.images
        self.scaled_background = None
        self.parallax_cache = {}
        self.world_sprite_cache = {}
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing game..."
        self.loading_context = "boot"
        self.loading_finished_at = None
        self.assets_ready = False
        self.level_manager = LevelManager()
        self.preloaded_sections = set()
        self.platforms = []
        self.floor_platform = None
        self.platform_graph = None
        self.load_level_layout()
        self.player = self.create_player()
        self.upgrade_manager = UpgradeManager()
        self.ui = UI()
        self.ui.load_loading_asset(self.assets)
        self.bullets = []
        self.pickups = []
        self.headshot_indicators = []
        self.last_mouse = self.current_mouse_game_pos()
        self.camera_x = 0
        self.show_fps_counter = SHOW_FPS_COUNTER
        self.debug_font = pygame.font.SysFont(None, 20)
        self.pause_menu_opened_at = 0.0
        self.hotbar_menu_pressed_until = 0.0
        self.pause_pressed_action = None
        self.pause_pressed_until = 0.0
        self.cursor_is_hand = False
        self.load_assets_with_progress()

    def desktop_size(self):
        try:
            desktop_sizes = pygame.display.get_desktop_sizes()
        except pygame.error:
            desktop_sizes = []

        if desktop_sizes and desktop_sizes[0][0] > 0 and desktop_sizes[0][1] > 0:
            return desktop_sizes[0]

        info = pygame.display.Info()
        return (
            info.current_w if info.current_w > 0 else SCREEN_WIDTH,
            info.current_h if info.current_h > 0 else SCREEN_HEIGHT,
        )

    def apply_display_mode(self):
        self.fullscreen_renderer = None
        self.fullscreen_frame_texture = None
        self.uses_hardware_presenter = False
        if self.windowed_fullscreen:
            self.apply_windowed_fullscreen_mode()
        else:
            self.display_surface = pygame.display.set_mode(GAME_SCREEN_SIZE, WINDOWED_FLAGS)
            self.screen = self.display_surface

        pygame.display.set_caption("Zombie Platform Shooter")
        self.update_present_rect()
        self.present_scale_surface = None

    def apply_windowed_fullscreen_mode(self):
        desktop_size = self.desktop_size()
        self.display_surface = pygame.display.set_mode(
            desktop_size,
            WINDOWED_FULLSCREEN_FLAGS,
        )
        self.screen = pygame.Surface(GAME_SCREEN_SIZE).convert()
        self.move_window_to_desktop()
        self.create_hardware_presenter()

    def move_window_to_desktop(self):
        try:
            from pygame._sdl2.video import Window
        except (ImportError, pygame.error):
            return

        try:
            window = Window.from_display_module()
            window.borderless = True
            window.position = (0, 0)
        except (AttributeError, pygame.error):
            pass

    def create_hardware_presenter(self):
        try:
            from pygame._sdl2.video import Renderer, Window

            window = Window.from_display_module()
            self.fullscreen_renderer = Renderer.from_window(window)
            self.uses_hardware_presenter = True
        except Exception as error:
            self.fullscreen_renderer = None
            self.uses_hardware_presenter = False
            print(f"[Display] Hardware fullscreen presenter unavailable; using software scaling. {error}")

    def update_present_rect(self):
        if self.windowed_fullscreen:
            self.present_rect = self.display_surface.get_rect()
            return

        window_rect = self.display_surface.get_rect()
        scale = min(window_rect.width / SCREEN_WIDTH, window_rect.height / SCREEN_HEIGHT)
        width = max(1, round(SCREEN_WIDTH * scale))
        height = max(1, round(SCREEN_HEIGHT * scale))
        self.present_rect = pygame.Rect(0, 0, width, height)
        self.present_rect.center = window_rect.center

    def toggle_windowed_fullscreen(self):
        self.windowed_fullscreen = not self.windowed_fullscreen
        self.apply_display_mode()
        self.last_mouse = self.current_mouse_game_pos()
        self.cursor_is_hand = None

    def window_to_game_pos(self, pos, clamp=False):
        x, y = pos
        if not self.present_rect.collidepoint(x, y):
            if not clamp:
                return None
            x = max(self.present_rect.left, min(x, self.present_rect.right - 1))
            y = max(self.present_rect.top, min(y, self.present_rect.bottom - 1))

        game_x = (x - self.present_rect.left) * SCREEN_WIDTH / self.present_rect.width
        game_y = (y - self.present_rect.top) * SCREEN_HEIGHT / self.present_rect.height
        return (
            max(0, min(SCREEN_WIDTH - 1, int(game_x))),
            max(0, min(SCREEN_HEIGHT - 1, int(game_y))),
        )

    def current_mouse_game_pos(self):
        return self.window_to_game_pos(pygame.mouse.get_pos(), clamp=True)

    def present(self):
        if self.uses_hardware_presenter:
            self.present_with_hardware()
            return

        if self.screen is self.display_surface:
            pygame.display.flip()
            return

        if (
            self.windowed_fullscreen
            and self.present_rect.topleft == (0, 0)
            and self.present_rect.size == self.display_surface.get_size()
        ):
            pygame.transform.scale(self.screen, self.present_rect.size, self.display_surface)
            pygame.display.flip()
            return

        if self.present_rect.size == GAME_SCREEN_SIZE:
            if self.present_rect.topleft != (0, 0):
                self.display_surface.fill((0, 0, 0))
            self.display_surface.blit(self.screen, self.present_rect)
        else:
            self.display_surface.fill((0, 0, 0))
            if (
                self.present_scale_surface is None
                or self.present_scale_surface.get_size() != self.present_rect.size
            ):
                self.present_scale_surface = pygame.Surface(self.present_rect.size).convert()
            pygame.transform.scale(self.screen, self.present_rect.size, self.present_scale_surface)
            self.display_surface.blit(self.present_scale_surface, self.present_rect)

        pygame.display.flip()

    def present_with_hardware(self):
        try:
            from pygame._sdl2.video import Texture

            self.fullscreen_frame_texture = Texture.from_surface(
                self.fullscreen_renderer,
                self.screen,
            )
            self.fullscreen_renderer.draw_color = (0, 0, 0, 255)
            self.fullscreen_renderer.clear()
            self.fullscreen_frame_texture.draw(dstrect=self.present_rect)
            self.fullscreen_renderer.present()
        except Exception as error:
            print(f"[Display] Hardware fullscreen present failed; using software scaling. {error}")
            self.fullscreen_renderer = None
            self.fullscreen_frame_texture = None
            self.uses_hardware_presenter = False
            self.present()

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
        remove_all_light_pixels=False,
        trim_transparent=False,
        transparent_min_value=225,
        transparent_channel_spread=36,
    ):
        image = self.assets.load_image(
            key,
            path,
            remove_light_pixels=remove_light_pixels,
            remove_light_pixels_from_edges=remove_light_pixels_from_edges,
            remove_all_light_pixels=remove_all_light_pixels,
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
        is_close_foreground = key in CLOSE_FOREGROUND_ASSET_KEYS
        is_random_gameplay_asset = key in RANDOM_GAMEPLAY_ASSET_KEYS

        needs_runtime_cleanup = not is_preprocessed

        needs_stronger_matte_cleanup = (
            is_cutout_background
            or is_floor_sprite
            or is_random_gameplay_asset
        )
        min_value = 205 if needs_stronger_matte_cleanup else 220
        channel_spread = 46 if needs_stronger_matte_cleanup else 44
        return self.load_image(
            key,
            path,
            remove_light_pixels=(
                needs_runtime_cleanup
                and (
                    is_platform_sprite
                    or is_cutout_background
                    or is_floor_sprite
                    or is_close_foreground
                    or is_random_gameplay_asset
                )
            ),
            remove_light_pixels_from_edges=(
                needs_runtime_cleanup
                and (
                    is_close_foreground
                    or is_random_gameplay_asset
                )
            ),
            remove_all_light_pixels=(
                needs_runtime_cleanup
                and (
                    is_close_foreground
                    or is_random_gameplay_asset
                )
            ),
            trim_transparent=(
                needs_runtime_cleanup
                and (
                    is_platform_sprite
                    or is_close_foreground
                    or is_random_gameplay_asset
                )
            ),
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
        if key == "headshot":
            needs_cleanup = not is_preprocessed_image_path(path)
            image = self.load_image(
                key,
                path,
                remove_light_pixels=needs_cleanup,
                trim_transparent=needs_cleanup,
                transparent_min_value=205,
                transparent_channel_spread=46,
            )
            return self.scale_headshot_image(image)
        return self.load_image(key, path)

    def scale_headshot_image(self, image):
        if not image:
            return None

        longest_side = max(image.get_width(), image.get_height())
        if longest_side <= HEADSHOT_INDICATOR_MAX_SIZE:
            return image

        scale = HEADSHOT_INDICATOR_MAX_SIZE / longest_side
        size = (
            max(1, int(round(image.get_width() * scale))),
            max(1, int(round(image.get_height() * scale))),
        )
        scaled = pygame.transform.smoothscale(image, size)
        self.images["headshot"] = scaled
        return scaled

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
        section_filter = set(section_names) if section_names is not None else None

        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            if image_key:
                visual_keys.add(image_key)

        # Generated props can change each time a level is reset, so preload the
        # full pools once instead of discovering a missing sprite during Start.
        for sprite_key in CLOSE_FOREGROUND_ASSET_KEYS + RANDOM_GAMEPLAY_ASSET_KEYS:
            if ENVIRONMENT_IMAGE_PATHS.get(sprite_key):
                visual_keys.add(sprite_key)

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

        # Runtime-generated collidable obstacles and close foreground assets are
        # not baked into section data, so include them explicitly.
        for platform_data in self.level_manager.platforms:
            if not isinstance(platform_data, dict):
                continue
            if section_filter is not None and platform_data.get("section") not in section_filter:
                continue
            sprite_key = platform_data.get("sprite")
            if sprite_key:
                visual_keys.add(sprite_key)

        for foreground in self.level_manager.close_foreground_assets:
            if section_filter is not None and foreground.get("section") not in section_filter:
                continue
            sprite_key = foreground.get("sprite")
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

    def image_loading_label(self, fallback_key, path):
        if path:
            return f"Loading {Path(path).name}"
        return f"Loading {fallback_key}"

    def animation_loading_label(self, key):
        sheet_config = SPRITE_SHEETS.get(key, {})
        return self.image_loading_label(key, sheet_config.get("path"))

    def current_level_section_names(self):
        return [
            section.get("name")
            for section in self.level_manager.sections
            if section.get("name")
        ]

    def load_assets_with_progress(self):
        self.prepare_start_loading_tasks(include_title_assets=True, load_all_animations=False)

    def prepare_start_loading_tasks(self, include_title_assets=False, load_all_animations=False):
        self.level_manager.start_level()
        self.load_level_layout()
        section_names = self.current_level_section_names()

        # Each task runs on a separate loading update. That lets the loading
        # screen repaint instead of freezing during one large asset load.
        tasks = []
        if include_title_assets:
            self.add_loading_task(tasks, "Preparing fonts", self.ui.prepare_fonts)
            self.add_loading_task(tasks, "Loading title_screen.png", self.ui.load_title_asset, self.assets)
            self.add_loading_task(tasks, "Loading hotbar2.png", self.ui.load_hotbar_asset, self.assets)
            self.add_loading_task(tasks, "Loading escape_menu.png", self.ui.load_escape_menu_asset, self.assets)
            self.add_loading_task(tasks, "Loading upgrade menu assets", self.ui.load_upgrade_menu_assets, self.assets)

        for key, path in IMAGE_PATHS.items():
            self.add_loading_task(tasks, self.image_loading_label(key, path), self.load_core_image, key, path)

        self.add_loading_task(tasks, "Preparing pickups", self.load_pickup_sprites)

        for key in self.current_level_visual_asset_keys(section_names=section_names):
            if key in ENVIRONMENT_IMAGE_PATHS:
                path = ENVIRONMENT_IMAGE_PATHS.get(key)
                self.add_loading_task(tasks, self.image_loading_label(key, path), self.load_environment_image, key)

        if load_all_animations:
            animation_keys = sorted(SPRITE_SHEETS)
        else:
            animation_keys = ["player", "bullet"]
            for key in self.current_level_enemy_asset_keys(section_names=section_names):
                if key not in animation_keys:
                    animation_keys.append(key)
        for key in animation_keys:
            self.add_loading_task(tasks, self.animation_loading_label(key), self.load_animation, key)

        # Only prepare flipped frames if loading all animations
        if load_all_animations:
            self.add_loading_task(tasks, "Preparing flipped frames", self.prepare_flipped_animation_frames)

        self.add_loading_task(tasks, "Preparing backgrounds", self.prepare_parallax_cache)
        self.add_loading_task(tasks, "Checking prop visuals", self.prune_invisible_random_asset_platforms)
        self.add_loading_task(tasks, "Preparing platform sprites", self.prepare_platform_surfaces)

        self.loading_tasks = tasks
        self.loading_task_index = 0
        self.loading_task_total = len(tasks)
        self.loading_finished_at = None

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
        if not platform.sprite_key:
            return False
        if DRAW_GROUND_PLATFORM_VISUAL:
            return True

        # The first ground platform spans almost the whole level. Collision
        # remains active, but its old map-like art stays hidden so the new
        # backgrounds are the only large environment layer.
        return platform.rect.width < self.level_manager.level_width * 0.9

    def prune_invisible_random_asset_platforms(self):
        kept_platform_data = []
        removed_count = 0
        for platform_data in self.level_manager.platforms:
            if (
                isinstance(platform_data, dict)
                and platform_data.get("sprite") in RANDOM_GAMEPLAY_ASSET_KEYS
                and not self.images.get(platform_data.get("sprite"))
            ):
                removed_count += 1
                continue
            kept_platform_data.append(platform_data)

        if removed_count == 0:
            return

        self.level_manager.platforms = kept_platform_data
        self.load_level_layout()
        print(f"[LevelManager] Removed {removed_count} invisible generated prop collider(s).")

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
        self.loading_finished_at = None

    def request_next_level_loading(self):
        self.loading_context = "next_level"
        self.state = "LOADING"
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing next level"
        self.loading_finished_at = None

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
        self.ui.reset_upgrade_menu()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.headshot_indicators = []
        self.spawn_level_pickups()
        self.update_camera()
        self.mark_sections_preloaded(self.current_level_section_names())
        self.state = "PLAYING"
        self.clear_loading_state()

    def finish_boot_loading(self):
        self.assets_ready = True
        self.state = "TITLE"
        self.clear_loading_state()

    def start_loaded_game(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.load_current_level_visual_assets()
        self.prune_invisible_random_asset_platforms()
        self.prepare_runtime_caches(section_names=self.current_level_section_names())
        self.preloaded_sections = set()
        self.ui.reset_upgrade_menu()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.headshot_indicators = []
        self.spawn_level_pickups()
        self.update_camera()
        self.mark_sections_preloaded(self.current_level_section_names())
        self.state = "PLAYING"

    def finish_next_level(self):
        self.preloaded_sections = set()
        self.reset_player_for_level()
        self.bullets = []
        self.pickups = []
        self.headshot_indicators = []
        self.spawn_level_pickups()
        self.mark_sections_preloaded(self.current_level_section_names())
        self.state = "PLAYING"
        self.clear_loading_state()

    def finish_loading(self):
        if self.loading_context == "boot":
            self.finish_boot_loading()
            return
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
        self.loading_finished_at = None

    def update_loading_screen(self, now):
        self.update_loading(now)

    def update_loading(self, now):
        if not self.loading_screen_drawn:
            return

        if not self.loading_tasks:
            self.prepare_start_loading_tasks(include_title_assets=self.loading_context == "boot")
            self.loading_status = "Preparing game..."
            return

        if self.loading_task_index < len(self.loading_tasks):
            label, task = self.loading_tasks[self.loading_task_index]
            self.loading_status = label
            task()
            self.loading_task_index += 1
            self.loading_finished_at = None
            return

        self.loading_status = "Preparing game..."
        if self.loading_finished_at is None:
            self.loading_finished_at = now
            return

        if now - self.loading_finished_at < LOADING_FINISH_DELAY:
            return

        self.finish_loading()

    def loading_progress(self):
        if not self.loading_task_total:
            return 0.0
        return self.loading_task_index / self.loading_task_total

    def reset(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.ui.reset_upgrade_menu()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.headshot_indicators = []
        self.preloaded_sections = set()
        self.update_camera()
        self.state = "TITLE"
        self.loading_screen_drawn = False
        self.loading_tasks = []
        self.loading_task_index = 0
        self.loading_task_total = 0
        self.loading_status = "Preparing level"
        self.pause_menu_opened_at = 0.0
        self.hotbar_menu_pressed_until = 0.0
        self.pause_pressed_action = None
        self.pause_pressed_until = 0.0

    def is_title_state(self):
        return self.state in ("TITLE", "MAIN_MENU")

    def open_pause_menu(self, now):
        self.state = "PAUSED"
        self.pause_menu_opened_at = now
        self.pause_pressed_action = None
        self.pause_pressed_until = 0.0

    def close_pause_menu(self):
        self.state = "PLAYING"
        self.pause_pressed_action = None
        self.pause_pressed_until = 0.0

    def handle_pause_action(self, action, now):
        if not action:
            return

        self.pause_pressed_action = action
        self.pause_pressed_until = now + 0.12
        if action == "resume":
            self.close_pause_menu()
        elif action == "fps":
            self.show_fps_counter = not self.show_fps_counter
        elif action == "windowed_fullscreen":
            self.toggle_windowed_fullscreen()
        elif action == "debug":
            import settings
            settings.DEBUG_AIM_PIVOT = not settings.DEBUG_AIM_PIVOT
        elif action == "main_menu":
            self.reset()
        elif action == "quit":
            pygame.quit()
            raise SystemExit

    def update_cursor(self):
        wants_hand = False
        if self.is_title_state():
            wants_hand = self.ui.start_button_rect(self.screen).collidepoint(self.last_mouse)
        elif self.state == "PLAYING":
            wants_hand = self.ui.hotbar_menu_button_rect(self.screen).collidepoint(self.last_mouse)
        elif self.state == "PAUSED":
            wants_hand = self.ui.pause_menu_action_at(self.screen, self.last_mouse) is not None
        elif self.state in UPGRADE_MENU_STATES:
            wants_hand = self.ui.upgrade_menu_wants_cursor(self.last_mouse)

        if wants_hand == self.cursor_is_hand:
            return

        self.cursor_is_hand = wants_hand
        hand_cursor = getattr(pygame, "SYSTEM_CURSOR_HAND", None)
        arrow_cursor = getattr(pygame, "SYSTEM_CURSOR_ARROW", None)
        if hand_cursor is None or arrow_cursor is None:
            return

        cursor = hand_cursor if wants_hand else arrow_cursor
        try:
            pygame.mouse.set_cursor(cursor)
        except pygame.error:
            pass

    def run(self):
        running = True
        while running:
            # If a frame hitches, cap dt so animations and physics do not try
            # to process a huge catch-up step all at once.
            dt = min(self.clock.tick(FPS) / 1000, MAX_FRAME_DT)
            now = pygame.time.get_ticks() / 1000
            self.handle_events(now)
            self.update_cursor()
            self.update(dt, now)
            self.draw()
            self.present()
        pygame.quit()

    def handle_events(self, now):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEMOTION:
                self.last_mouse = self.window_to_game_pos(event.pos, clamp=True)
            if event.type == pygame.MOUSEWHEEL:
                if self.state == "PLAYING":
                    self.player.cycle_weapon(event.y)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                if self.state == "PLAYING":
                    self.player.cycle_weapon(1 if event.button == 5 else -1)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self.window_to_game_pos(event.pos)
                if mouse_pos is None:
                    continue
                self.last_mouse = mouse_pos
                if self.is_title_state():
                    if self.ui.start_button_rect(self.screen).collidepoint(mouse_pos):
                        self.request_start_game()
                elif self.state == "PLAYING":
                    hotbar_action = self.ui.handle_hotbar_click(self.screen, mouse_pos)
                    if hotbar_action == "menu":
                        self.hotbar_menu_pressed_until = now + 0.12
                        self.open_pause_menu(now)
                        continue
                    if hotbar_action == "toggle_weapon":
                        self.player.cycle_weapon(1)
                        continue
                    if hotbar_action == "hud":
                        continue
                    if hotbar_action in ("melee", "pistol"):
                        self.player.select_weapon(hotbar_action)
                        continue
                    keys = pygame.key.get_pressed()
                    if self.player.run_input_active(keys):
                        continue
                    world_mouse = self.screen_to_world(self.last_mouse)
                    if self.player.is_melee_selected():
                        self.player.start_melee_attack(world_mouse)
                    else:
                        bullet = self.player.shoot(world_mouse, now)
                        if bullet:
                            self.bullets.append(bullet)
                elif self.state == "PAUSED":
                    action = self.ui.pause_menu_action_at(self.screen, mouse_pos)
                    self.handle_pause_action(action, now)
                elif self.state in UPGRADE_MENU_STATES:
                    self.handle_upgrade_click(mouse_pos)
                elif self.state in ["GAME_OVER", "VICTORY"]:
                    pass
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_windowed_fullscreen()
                    continue
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.open_pause_menu(now)
                    elif self.state == "PAUSED":
                        self.close_pause_menu()
                    continue
                if self.is_title_state() and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.request_start_game()
                    continue
                if event.key == pygame.K_f and self.state == "PAUSED":
                    self.show_fps_counter = not self.show_fps_counter
                if event.key == pygame.K_d and self.state == "PAUSED":
                    import settings
                    settings.DEBUG_AIM_PIVOT = not settings.DEBUG_AIM_PIVOT
                if event.key == pygame.K_r:
                    if self.state == "PLAYING":
                        if self.player.is_pistol_selected():
                            self.player.reload(now)
                    elif self.state in ["GAME_OVER", "VICTORY"]:
                        self.reset()
                if self.state == "PLAYING" and event.key == pygame.K_1:
                    self.player.select_weapon("melee")
                    continue
                if self.state == "PLAYING" and event.key == pygame.K_2:
                    self.player.select_weapon("pistol")
                    continue
                if self.state in UPGRADE_MENU_STATES and event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    choice_index = event.key - pygame.K_1
                    self.ui.select_upgrade_card(choice_index)

    def handle_upgrade_click(self, mouse_pos):
        self.ui.handle_upgrade_menu_click(mouse_pos)

    def begin_upgrade_menu(self):
        self.upgrade_manager.pick_upgrades()
        self.draw_gameplay()
        gameplay_snapshot = self.screen.copy()
        self.ui.open_upgrade_menu(self.upgrade_manager.current_choices, gameplay_snapshot)
        self.state = "UPGRADE_TRANSITION_OUT"

    def update_upgrade_menu(self, dt):
        result = self.ui.update_upgrade_menu(self.screen, dt, self.last_mouse)
        phase = self.ui.upgrade_menu.phase
        if phase == "fade_out":
            self.state = "UPGRADE_TRANSITION_OUT"
        elif phase == "closing":
            self.state = "UPGRADE_TRANSITION_IN"
        elif phase != "closed":
            self.state = "UPGRADE_SELECT"

        if result is not None:
            self.apply_upgrade_choice(result)

    def apply_upgrade_choice(self, choice_index):
        if not (0 <= choice_index < len(self.upgrade_manager.current_choices)):
            return

        picked = self.upgrade_manager.current_choices[choice_index]
        self.player.picked_upgrades.append(
            {
                "name": picked["name"],
                "description": picked.get("description", ""),
                "effect_id": picked.get("effect_id"),
            }
        )
        self.upgrade_manager.apply_upgrade(self.player, choice_index)
        self.ui.reset_upgrade_menu()
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
            self.update_loading_screen(now)
            return
        if self.state in UPGRADE_MENU_STATES:
            self.update_upgrade_menu(dt)
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
            self.update_melee_attack()
            self.update_bullets(dt)
            self.check_collisions(now)
            self.update_headshot_indicators(dt)
            self.update_pickups(dt)
            if self.player.health <= 0:
                self.player.die()
                self.state = "GAME_OVER"
            elif self.level_manager.level_complete(self.player):
                if self.level_manager.is_final_level():
                    self.state = "VICTORY"
                else:
                    self.begin_upgrade_menu()

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

    def update_melee_attack(self):
        if not self.player.melee_impact_ready():
            return

        enemy = self.closest_melee_target()
        if enemy:
            enemy.take_damage(self.player.melee_damage)
            self.spawn_headshot_indicator(enemy)
        self.player.mark_melee_hit()

    def closest_melee_target(self):
        hit_rect = self.player.melee_hit_rect()
        player_center_x = self.player.rect.centerx
        candidates = []
        for enemy in self.level_manager.active_enemies:
            if getattr(enemy, "dead", False) or not enemy.is_active():
                continue
            enemy_center_x = enemy.rect.centerx
            if self.player.facing_right and enemy_center_x <= player_center_x:
                continue
            if not self.player.facing_right and enemy_center_x >= player_center_x:
                continue
            if not hit_rect.colliderect(enemy.rect):
                continue
            distance = abs(enemy_center_x - player_center_x)
            candidates.append((distance, enemy))

        if not candidates:
            return None
        return min(candidates, key=lambda candidate: candidate[0])[1]

    def update_headshot_indicators(self, dt):
        for indicator in self.headshot_indicators[:]:
            indicator.update(dt)
            if not indicator.alive:
                self.headshot_indicators.remove(indicator)

    def spawn_headshot_indicator(self, enemy):
        image = self.images.get("headshot")
        if not image:
            return

        self.headshot_indicators.append(
            HeadshotIndicator(
                enemy.rect.centerx,
                enemy.rect.top - 20,
                image,
            )
        )

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
        y = self.surface_y_for_pickup(x, y)
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

    def surface_y_for_pickup(self, x, requested_y):
        if requested_y == GROUND_Y:
            return GROUND_Y

        platform_rects = [
            platform.rect
            for platform in self.platforms
            if getattr(platform, "drop_through", True)
            and platform.rect.left <= x <= platform.rect.right
        ]
        if not platform_rects:
            return GROUND_Y

        closest_platform = min(
            platform_rects,
            key=lambda rect: abs(rect.top - requested_y),
        )
        return closest_platform.top

    def update_pickups(self, dt):
        for index in range(len(self.pickups) - 1, -1, -1):
            pickup = self.pickups[index]
            if not self.is_world_rect_visible(pickup.rect, margin=DRAW_MARGIN):
                continue

            pickup.update(dt)
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
                    damage = getattr(bullet, "damage", 1)
                    if enemy.get_head_rect().colliderect(bullet.rect):
                        damage *= HEADSHOT_DAMAGE_MULTIPLIER
                        self.spawn_headshot_indicator(enemy)
                    enemy.take_damage(damage)
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
        now = pygame.time.get_ticks() / 1000
        if self.is_title_state():
            self.ui.draw_title_screen(self.screen, self.last_mouse, now)
            return
        if self.state == "LOADING":
            self.ui.draw_loading(
                self.screen,
                progress=self.loading_progress(),
                status=self.loading_status,
                now=now,
                loaded_count=self.loading_task_index,
                total_count=self.loading_task_total,
            )
            self.loading_screen_drawn = True
            return
        if self.state == "PAUSED":
            self.draw_gameplay()
            pressed_action = None
            if now < self.pause_pressed_until:
                pressed_action = self.pause_pressed_action
            self.ui.draw_pause(
                self.screen,
                self.player,
                show_fps_counter=self.show_fps_counter,
                windowed_fullscreen=self.windowed_fullscreen,
                mouse_pos=self.last_mouse,
                now=now,
                opened_at=self.pause_menu_opened_at,
                pressed_action=pressed_action,
            )
            return
        if self.state == "GAME_OVER":
            self.draw_gameplay()
            self.ui.draw_game_over(self.screen)
            return
        if self.state == "VICTORY":
            self.draw_gameplay()
            self.ui.draw_victory(self.screen)
            return
        if self.state in UPGRADE_MENU_STATES:
            self.ui.draw_upgrade_menu(self.screen)
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

    def draw_headshot_debug(self, enemy):
        head_rect = enemy.get_head_rect().move(-self.camera_x, 0)
        pygame.draw.rect(self.screen, (255, 220, 40), head_rect, 2)

    def draw_headshot_indicators(self):
        for indicator in self.headshot_indicators:
            indicator.draw(self.screen, camera_x=self.camera_x)

    def scaled_world_sprite(self, sprite_key, image, size):
        cache_key = (sprite_key, id(image), size[0], size[1])
        cached = self.world_sprite_cache.get(cache_key)
        if cached is not None:
            return cached

        scaled = pygame.transform.scale(image, size)
        self.world_sprite_cache[cache_key] = scaled
        return scaled

    def draw_close_foreground_assets(self):
        for item in self.level_manager.close_foreground_assets:
            image = self.images.get(item.get("sprite"))
            if not image:
                continue

            parallax = item.get("parallax", 1.12)
            camera_factor = 1.0 + max(0.0, parallax - 1.0) * CLOSE_FOREGROUND_NEAR_PARALLAX_BOOST
            screen_x = round(item["x"] - self.camera_x * camera_factor)
            draw_rect = pygame.Rect(
                screen_x,
                item["y"],
                item["width"],
                item["height"],
            )
            if draw_rect.right < -DRAW_MARGIN or draw_rect.left > SCREEN_WIDTH + DRAW_MARGIN:
                continue

            scaled = self.scaled_world_sprite(
                item["sprite"],
                image,
                (draw_rect.width, draw_rect.height),
            )
            self.screen.blit(scaled, draw_rect)

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
        self.player.draw(self.screen, camera_x=self.camera_x, mouse_pos=self.last_mouse)
        for enemy in self.level_manager.active_enemies:
            if not self.is_world_rect_visible(enemy.rect):
                continue
            enemy.draw(self.screen, camera_x=self.camera_x)
            if DEBUG_HEADSHOTS:
                self.draw_headshot_debug(enemy)
        for bullet in self.bullets:
            if not self.is_world_rect_visible(bullet.rect):
                continue
            bullet.draw(self.screen, camera_x=self.camera_x)
        self.draw_headshot_indicators()
        self.draw_close_foreground_assets()

        if DEBUG_PATHS:
            self.platform_graph.draw(self.screen, self.debug_font, self.level_manager.active_enemies, self.camera_x)

        now = pygame.time.get_ticks() / 1000
        self.ui.draw_hotbar(
            self.screen,
            self.player,
            self.level_manager.current_level_number(),
            len(LEVELS),
            mouse_pos=self.last_mouse,
            now=now,
            menu_pressed_until=self.hotbar_menu_pressed_until,
        )
        if self.show_fps_counter:
            self.ui.draw_fps_counter(self.screen, self.clock.get_fps())

    def draw_exit(self):
        exit_rect = self.level_manager.exit_rect()
        if not self.is_world_rect_visible(exit_rect):
            return

        exit_rect = exit_rect.move(-self.camera_x, 0)
        arrow_rect = pygame.Rect(0, 0, EXIT_ARROW_WIDTH, EXIT_ARROW_HEIGHT)
        arrow_rect.midbottom = (exit_rect.centerx, exit_rect.bottom - 18)

        sign_rect = pygame.Rect(0, 0, EXIT_SIGN_WIDTH, EXIT_SIGN_HEIGHT)
        sign_rect.midbottom = (arrow_rect.centerx, arrow_rect.top - 12)

        self.draw_exit_sign(sign_rect)
        self.draw_exit_arrow(arrow_rect)

    def draw_exit_sign(self, rect):
        shadow = rect.move(4, 5)
        pygame.draw.rect(self.screen, (5, 9, 8), shadow, border_radius=4)
        pygame.draw.rect(self.screen, (30, 43, 38), rect, border_radius=4)
        pygame.draw.rect(self.screen, (116, 133, 95), rect, 3, border_radius=4)
        pygame.draw.rect(self.screen, (173, 219, 91), rect.inflate(-18, -20), 2, border_radius=3)

        post_color = (24, 30, 27)
        for x in (rect.left + 36, rect.right - 40):
            pygame.draw.rect(self.screen, post_color, (x, rect.bottom - 2, 8, 24))
            pygame.draw.rect(self.screen, (97, 108, 82), (x, rect.bottom - 2, 8, 24), 1)

        font = load_font("ui", 24, bold=True)
        text = font.render("NEXT LEVEL", False, (226, 232, 186))
        outline = font.render("NEXT LEVEL", False, (7, 12, 10))
        text_rect = text.get_rect(center=rect.center)
        for offset in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            self.screen.blit(outline, text_rect.move(offset))
        self.screen.blit(text, text_rect)

    def draw_exit_arrow(self, rect):
        left = rect.left
        right = rect.right
        top = rect.top
        bottom = rect.bottom
        center_y = rect.centery
        head_left = rect.left + round(rect.width * 0.58)
        body_top = center_y - round(rect.height * 0.22)
        body_bottom = center_y + round(rect.height * 0.22)

        arrow_points = [
            (left, body_top),
            (head_left, body_top),
            (head_left, top),
            (right, center_y),
            (head_left, bottom),
            (head_left, body_bottom),
            (left, body_bottom),
        ]
        shadow_points = [(x + 5, y + 6) for x, y in arrow_points]
        pygame.draw.polygon(self.screen, (4, 8, 7), shadow_points)
        pygame.draw.polygon(self.screen, (33, 50, 44), arrow_points)
        pygame.draw.polygon(self.screen, (130, 148, 103), arrow_points, 4)

        stripe_area = pygame.Rect(
            left + 14,
            center_y - 13,
            max(1, head_left - left - 26),
            26,
        )
        pygame.draw.rect(self.screen, (25, 29, 26), stripe_area)
        stripe_x = stripe_area.left - 18
        while stripe_x < stripe_area.right:
            stripe = [
                (stripe_x, stripe_area.bottom),
                (stripe_x + 18, stripe_area.bottom),
                (stripe_x + 42, stripe_area.top),
                (stripe_x + 24, stripe_area.top),
            ]
            pygame.draw.polygon(self.screen, (166, 126, 41), stripe)
            stripe_x += 34
        pygame.draw.rect(self.screen, (91, 103, 77), stripe_area, 2)

        glow_points = [
            (head_left + 12, center_y - 17),
            (right - 24, center_y),
            (head_left + 12, center_y + 17),
        ]
        pygame.draw.lines(self.screen, (157, 239, 91), False, glow_points, 6)
        pygame.draw.lines(self.screen, (222, 244, 150), False, glow_points, 2)
