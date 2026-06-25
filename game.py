import pygame
import os
import random
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    COLOR_BACKGROUND,
    PLATFORMS,
    IMAGE_PATHS,
    LEVELS,
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    WALKER_WIDTH,
    WALKER_HEIGHT,
    TANK_WIDTH,
    TANK_HEIGHT,
    FLYING_WIDTH,
    FLYING_HEIGHT,
    BULLET_WIDTH,
    BULLET_HEIGHT,
)
from player import Player
from level_manager import LevelManager
from upgrade_manager import UpgradeManager
from ui import UI
from platforms import Platform

GAME_STATES = [
    "MAIN_MENU",
    "PLAYING",
    "UPGRADE_SELECT",
    "PAUSED",
    "GAME_OVER",
    "VICTORY",
]

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zombie Platform Shooter")
        self.clock = pygame.time.Clock()
        self.state = "MAIN_MENU"
        self.images = self.load_images()
        self.platforms = [Platform(rect) for rect in PLATFORMS]
        self.player = Player(620, 580, image=self.images.get("player"), bullet_image=self.images.get("bullet"))
        self.level_manager = LevelManager()
        self.upgrade_manager = UpgradeManager()
        self.ui = UI()
        self.bullets = []
        self.last_mouse = (0, 0)

    def load_images(self):
        images = {}
        expected_sizes = {
            "player": (PLAYER_WIDTH, PLAYER_HEIGHT),
            "walker_zombie": (WALKER_WIDTH, WALKER_HEIGHT),
            "tank_zombie": (TANK_WIDTH, TANK_HEIGHT),
            "flying_zombie": (FLYING_WIDTH, FLYING_HEIGHT),
            "bullet": (BULLET_WIDTH, BULLET_HEIGHT),
        }
        for key, path in IMAGE_PATHS.items():
            if os.path.exists(path):
                try:
                    loaded = pygame.image.load(path).convert_alpha()
                    expected = expected_sizes.get(key)
                    if expected and loaded.get_size() != expected:
                        loaded = pygame.transform.smoothscale(loaded, expected)
                    images[key] = loaded
                except pygame.error:
                    images[key] = None
            else:
                images[key] = None
        return images

    def reset(self):
        self.player = Player(620, 580, image=self.images.get("player"), bullet_image=self.images.get("bullet"))
        self.level_manager.reset()
        self.bullets = []
        self.state = "MAIN_MENU"

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
                    self.state = "PLAYING"
                    self.level_manager.start_level()
                elif self.state == "PLAYING":
                    bullet = self.player.shoot(self.last_mouse, now)
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
        card_width = 320
        card_height = 180
        spacing = 40
        x_start = 120
        y = 180
        for index in range(len(self.upgrade_manager.current_choices)):
            x = x_start + index * (card_width + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            if card_rect.collidepoint(mouse_pos):
                self.apply_upgrade_choice(index)

    def apply_upgrade_choice(self, choice_index):
        self.upgrade_manager.apply_upgrade(self.player, choice_index)
        if self.level_manager.next_level():
            self.state = "PLAYING"
        else:
            self.state = "VICTORY"

    def update(self, dt, now):
        if self.state == "PLAYING":
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.platforms, now)
            self.level_manager.update(dt, self.platforms, self.player, self.images)
            self.update_bullets()
            self.check_collisions(now)
            if self.player.health <= 0:
                self.state = "GAME_OVER"
            elif self.level_manager.level_complete():
                if self.level_manager.level_index == len(LEVELS) - 1:
                    self.state = "VICTORY"
                else:
                    self.upgrade_manager.pick_upgrades()
                    self.state = "UPGRADE_SELECT"

    def update_bullets(self):
        for bullet in list(self.bullets):
            if not bullet.update():
                self.bullets.remove(bullet)

    def check_collisions(self, now):
        for enemy in list(self.level_manager.active_enemies):
            if enemy.rect.colliderect(self.player.rect):
                self.player.apply_hurt(enemy.damage, now)
            for bullet in list(self.bullets):
                if enemy.rect.colliderect(bullet.rect):
                    enemy.take_damage(bullet.damage)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

    def draw(self):
        if self.state == "MAIN_MENU":
            self.ui.draw_main_menu(self.screen)
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
        if self.images.get("background"):
            bg = pygame.transform.scale(self.images["background"], (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(COLOR_BACKGROUND)

        for platform in self.platforms:
            platform.draw(self.screen, image=self.images.get("platform"))

        self.player.draw(self.screen)
        for enemy in self.level_manager.active_enemies:
            enemy.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)

        self.ui.draw_health_bar(self.screen, self.player)
        self.ui.draw_level(self.screen, self.level_manager.current_level_number())
