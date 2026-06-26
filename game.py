import pygame
import os
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    COLOR_BACKGROUND,
    COLOR_TEXT,
    IMAGE_PATHS,
    SPRITE_SHEETS,
    ENEMY_TYPE_CONFIGS,
)
from animation import load_animation_set
from player import Player
from level_manager import LevelManager
from upgrade_manager import UpgradeManager
from ui import UI
from platforms import Platform
from platform_nav import PlatformGraph, DEBUG_PATHS

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
        self.loading_screen_drawn = False
        self.level_manager = LevelManager()
        self.platforms = []
        self.platform_graph = None
        self.load_level_layout()
        self.player = self.create_player()
        self.upgrade_manager = UpgradeManager()
        self.ui = UI()
        self.bullets = []
        self.last_mouse = (0, 0)
        self.camera_x = 0
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

        for key in SPRITE_SHEETS:
            self.load_animation(key)
        return self.images

    def load_image(self, key, path):
        if key in self.images:
            return self.images[key]

        image = None
        if os.path.exists(path):
            try:
                image = pygame.image.load(path).convert_alpha()
            except pygame.error:
                image = None

        self.images[key] = image
        if key == "background" and image:
            self.scaled_background = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return image

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
        for key in ("player", "bullet"):
            self.load_animation(key)

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
        self.update_camera()
        self.state = "PLAYING"
        self.loading_screen_drawn = False

    def reset(self):
        self.level_manager.reset()
        self.load_level_layout()
        self.player = self.create_player()
        self.bullets = []
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
                if event.key == pygame.K_r and self.state in ["GAME_OVER", "VICTORY"]:
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
            self.load_current_level_enemy_assets()
            self.reset_player_for_level()
            self.bullets = []
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
            self.level_manager.update(dt, self.platforms, self.player, self.images, self.platform_graph)
            self.update_bullets(dt)
            self.check_collisions(now)
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
            self.ui.draw_pause(self.screen)
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

    def draw_gameplay(self):
        if self.scaled_background:
            self.screen.blit(self.scaled_background, (0, 0))
        else:
            self.screen.fill(COLOR_BACKGROUND)

        pygame.draw.circle(self.screen, (255, 255, 100), (SCREEN_WIDTH - 90, 90), 40)

        for platform in self.platforms:
            platform.draw(self.screen, image=self.images.get("platform"), camera_x=self.camera_x)

        self.draw_exit()
        self.player.draw(self.screen, camera_x=self.camera_x)
        for enemy in self.level_manager.active_enemies:
            enemy.draw(self.screen, camera_x=self.camera_x)
        for bullet in self.bullets:
            bullet.draw(self.screen, camera_x=self.camera_x)

        if DEBUG_PATHS:
            self.platform_graph.draw(self.screen, self.debug_font, self.level_manager.active_enemies, self.camera_x)

        self.ui.draw_health_bar(self.screen, self.player)
        self.ui.draw_level(self.screen, self.level_manager.current_level_number())

    def draw_exit(self):
        exit_rect = self.level_manager.exit_rect().move(-self.camera_x, 0)
        pygame.draw.rect(self.screen, (80, 220, 120), exit_rect)
        pygame.draw.rect(self.screen, COLOR_TEXT, exit_rect, 4)
