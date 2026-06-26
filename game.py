import pygame
import os
import random
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    COLOR_BACKGROUND,
    COLOR_TEXT,
    SHOW_FPS_COUNTER,
    IMAGE_PATHS,
    ENVIRONMENT_IMAGE_PATHS,
    SPRITE_SHEETS,
    ENEMY_TYPE_CONFIGS,
    PICKUP_SPRITES,
    AMMO_PICKUP_AMOUNT,
    HEALTH_PICKUP_AMOUNT,
    AMMO_DROP_CHANCE,
    HEALTH_DROP_CHANCE,
)
from animation import load_animation_set
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
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zombie Platform Shooter")
        self.clock = pygame.time.Clock()
        self.state = "MAIN_MENU"
        self.images = {}
        self.scaled_background = None
        self.parallax_cache = {}
        self.loading_screen_drawn = False
        self.level_manager = LevelManager()
        self.platforms = []
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
        self.platform_graph = PlatformGraph(self.platforms)

    def create_player(self):
        x, y = self.level_manager.player_start
        return Player(
            x,
            y,
            animations=self.images.get("player"),
            bullet_animations=self.images.get("bullet"),
        )

    def reset_player_for_level(self):
        self.player.rect.topleft = self.level_manager.player_start
        self.player.vx = 0
        self.player.vy = 0
        self.player.on_ground = False
        self.update_camera()

    def load_images(self):
        for key, path in IMAGE_PATHS.items():
            self.load_image(key, path)
        for key in ENVIRONMENT_IMAGE_PATHS:
            self.load_environment_image(key)
        self.load_pickup_sprites()

        for key in SPRITE_SHEETS:
            self.load_animation(key)
        return self.images

    def load_image(self, key, path, remove_light_pixels=False, trim_transparent=False):
        if key in self.images:
            return self.images[key]

        image = None
        if path and os.path.exists(path):
            try:
                image = pygame.image.load(path).convert_alpha()
                if remove_light_pixels:
                    self.remove_near_white_pixels(image)
                if trim_transparent:
                    image = self.trim_transparent_image(image)
            except pygame.error:
                image = None

        self.images[key] = image
        if key == "background" and image:
            self.scaled_background = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return image

    def load_environment_image(self, key):
        path = ENVIRONMENT_IMAGE_PATHS.get(key)
        return self.load_image(
            key,
            path,
            remove_light_pixels=True,
            trim_transparent=key.startswith("platform_"),
        )

    def remove_near_white_pixels(self, image):
        # The supplied environment PNGs are RGB files with a light checkerboard
        # baked in. Treat near-white, low-saturation pixels as transparent so
        # backgrounds and platform edges blend with the world.
        min_value = 235
        max_channel_spread = 32
        width = image.get_width()
        height = image.get_height()

        image.lock()
        for x in range(width):
            for y in range(height):
                color = image.get_at((x, y))
                brightest = max(color.r, color.g, color.b)
                darkest = min(color.r, color.g, color.b)
                if darkest >= min_value and brightest - darkest <= max_channel_spread:
                    image.set_at((x, y), (color.r, color.g, color.b, 0))
        image.unlock()

    def trim_transparent_image(self, image):
        bounds = image.get_bounding_rect(min_alpha=1)
        if bounds.width == 0 or bounds.height == 0:
            return image

        trimmed = pygame.Surface(bounds.size, pygame.SRCALPHA)
        trimmed.blit(image, (0, 0), bounds)
        return trimmed

    def load_animation(self, key):
        if key in self.images:
            return self.images[key]

        sheet_config = SPRITE_SHEETS.get(key)
        if not sheet_config:
            self.images[key] = None
            return None

        try:
            self.images[key] = load_animation_set(sheet_config)
        except pygame.error:
            self.images[key] = None
        return self.images[key]

    def load_core_gameplay_assets(self):
        for key, path in IMAGE_PATHS.items():
            self.load_image(key, path)
        self.load_pickup_sprites()
        for key in ("player", "bullet"):
            self.load_animation(key)

    def load_current_level_visual_assets(self):
        visual_keys = set()

        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            if image_key:
                visual_keys.add(image_key)

        for platform_data in self.level_manager.platforms:
            if isinstance(platform_data, dict) and platform_data.get("sprite"):
                visual_keys.add(platform_data["sprite"])

        for decoration in self.level_manager.decorations:
            sprite_key = decoration.get("sprite")
            if sprite_key:
                visual_keys.add(sprite_key)

        for key in sorted(visual_keys):
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

    def load_current_level_enemy_assets(self):
        keys = set()

        for config in ENEMY_TYPE_CONFIGS.values():
            for key_name in ("animation_key", "spawn_sheet"):
                key = config.get(key_name)
                if key:
                    keys.add(key)

        for spawn_point in self.level_manager.enemy_spawn_points:
            for key_name in ("animation_key", "spawn_sheet"):
                key = spawn_point.get(key_name)
                if key:
                    keys.add(key)

        for key in sorted(keys):
            self.load_animation(key)

    def load_current_level_assets(self):
        self.load_core_gameplay_assets()
        self.load_current_level_visual_assets()
        self.load_current_level_enemy_assets()

    def request_start_game(self):
        self.state = "LOADING"
        self.loading_screen_drawn = False

    def start_game(self):
        self.level_manager.start_level()
        self.load_level_layout()
        self.load_current_level_assets()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.spawn_level_pickups()
        self.update_camera()
        self.state = "PLAYING"
        self.loading_screen_drawn = False

    def reset(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.player = self.create_player()
        self.bullets = []
        self.pickups = []
        self.update_camera()
        self.state = "MAIN_MENU"
        self.loading_screen_drawn = False

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
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
            self.load_level_layout()
            self.load_current_level_assets()
            self.reset_player_for_level()
            self.bullets = []
            self.pickups = []
            self.spawn_level_pickups()
            self.state = "PLAYING"
        else:
            self.state = "VICTORY"

    def screen_to_world(self, screen_pos):
        return (screen_pos[0] + self.camera_x, screen_pos[1])

    def update_camera(self):
        max_camera_x = max(0, self.level_manager.level_width - SCREEN_WIDTH)
        target_x = self.player.rect.centerx - SCREEN_WIDTH // 2
        self.camera_x = max(0, min(target_x, max_camera_x))

    def update(self, dt, now):
        if self.state == "LOADING":
            if self.loading_screen_drawn:
                self.start_game()
            return

        if self.state == "PLAYING":
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.platforms, now, dt, self.level_manager.level_width)
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
                self.state = "GAME_OVER"
            elif self.level_manager.level_complete(self.player):
                if self.level_manager.is_final_level():
                    self.state = "VICTORY"
                else:
                    self.upgrade_manager.pick_upgrades()
                    self.state = "UPGRADE_SELECT"

    def update_bullets(self, dt):
        for bullet in list(self.bullets):
            if not bullet.update(self.platforms, dt, self.level_manager.level_width):
                self.bullets.remove(bullet)

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
        for pickup in list(self.pickups):
            pickup.update()
            if (
                pickup.check_collision_with_player(self.player)
                and pickup.collect(self.player)
            ):
                self.pickups.remove(pickup)

    def check_collisions(self, now):
        for enemy in list(self.level_manager.active_enemies):
            if getattr(enemy, "dead", False) or not enemy.is_active():
                continue
            if enemy.rect.colliderect(self.player.rect):
                enemy.start_attack()
                self.player.apply_hurt(enemy.damage, now)
            for bullet in list(self.bullets):
                if getattr(bullet, "impacting", False):
                    continue
                if enemy.rect.colliderect(bullet.rect):
                    enemy.take_damage(bullet.damage)
                    bullet.start_impact()
                    break

    def draw(self):
        if self.state == "MAIN_MENU":
            self.ui.draw_main_menu(self.screen)
            return
        if self.state == "LOADING":
            self.ui.draw_loading(self.screen)
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

        # Each layer repeats horizontally. The camera position multiplied by
        # the layer speed creates the parallax drift.
        for layer in self.level_manager.background_layers:
            image_key = layer.get("image")
            image = self.images.get(image_key)
            if not image:
                continue

            scaled = self.scaled_parallax_layer(image_key, image)
            tile_width = scaled.get_width()
            speed = layer.get("speed", 1.0)
            x = -(self.camera_x * speed) % tile_width
            x -= tile_width

            while x < SCREEN_WIDTH:
                self.screen.blit(scaled, (round(x), 0))
                x += tile_width
            drew_layer = True

        if not drew_layer:
            if self.scaled_background:
                self.screen.blit(self.scaled_background, (0, 0))
            else:
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

    def draw_decorations(self, layer="back"):
        for decoration in self.level_manager.decorations:
            decoration_layer = decoration.get("layer", "back")
            if layer == "back" and decoration_layer == "front":
                continue
            if layer == "front" and decoration_layer != "front":
                continue

            parallax = decoration.get("parallax", 1.0)
            rect = pygame.Rect(
                round(decoration["x"] - self.camera_x * parallax),
                decoration["y"],
                decoration["width"],
                decoration["height"],
            )
            if rect.right < -120 or rect.left > SCREEN_WIDTH + 120:
                continue
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
        self.draw_decorations(layer="back")

        for platform in self.platforms:
            platform.draw(
                self.screen,
                image=self.images.get("platform"),
                images=self.images,
                camera_x=self.camera_x,
            )

        self.draw_exit()
        self.draw_decorations(layer="front")
        for pickup in self.pickups:
            pickup.draw(self.screen, camera_x=self.camera_x)
        self.player.draw(self.screen, camera_x=self.camera_x)
        for enemy in self.level_manager.active_enemies:
            enemy.draw(self.screen, camera_x=self.camera_x)
        for bullet in self.bullets:
            bullet.draw(self.screen, camera_x=self.camera_x)

        if DEBUG_PATHS:
            self.platform_graph.draw(self.screen, self.debug_font, self.level_manager.active_enemies, self.camera_x)

        self.ui.draw_health_bar(self.screen, self.player)
        self.ui.draw_level(self.screen, self.level_manager.current_level_number())
        if self.show_fps_counter:
            self.ui.draw_fps_counter(self.screen, self.clock.get_fps())

    def draw_exit(self):
        exit_rect = self.level_manager.exit_rect().move(-self.camera_x, 0)
        pygame.draw.rect(self.screen, (80, 220, 120), exit_rect)
        pygame.draw.rect(self.screen, COLOR_TEXT, exit_rect, 4)
