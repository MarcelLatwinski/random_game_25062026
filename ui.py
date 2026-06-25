import pygame
from settings import (
    SCREEN_WIDTH,
    COLOR_TEXT,
    COLOR_UI_BG,
    COLOR_HEALTH,
    COLOR_BACKGROUND,
    LEVELS,
)

FONT = None

def load_font():
    global FONT
    if FONT is None:
        FONT = pygame.font.SysFont("arial", 24)
    return FONT

class UI:
    def __init__(self):
        self.font = load_font()

    def draw_text(self, surface, text, x, y, color=COLOR_TEXT, size=24):
        font = pygame.font.SysFont("arial", size)
        text_surface = font.render(text, True, color)
        surface.blit(text_surface, (x, y))

    def draw_health_bar(self, surface, player):
        bar_width = 400
        bar_height = 22
        x = 20
        y = 20
        pygame.draw.rect(surface, COLOR_UI_BG, (x - 2, y - 2, bar_width + 4, bar_height + 4))
        fill_width = int(bar_width * player.health / player.max_health)
        pygame.draw.rect(surface, COLOR_HEALTH, (x, y, fill_width, bar_height))
        pygame.draw.rect(surface, COLOR_TEXT, (x, y, bar_width, bar_height), 2)
        self.draw_text(surface, f"HP: {player.health}/{player.max_health}", x + 8, y - 2)

    def draw_level(self, surface, level_number):
        self.draw_text(surface, f"Level {level_number}/{len(LEVELS)}", SCREEN_WIDTH - 220, 20)

    def draw_main_menu(self, surface):
        surface.fill(COLOR_BACKGROUND)
        self.draw_text(surface, "Zombie Platform Shooter", 420, 200, size=48)
        self.draw_text(surface, "Click to Start", 540, 320, size=32)

    def draw_pause(self, surface):
        self.draw_text(surface, "Paused", 560, 260, size=48)
        self.draw_text(surface, "Press Esc to resume", 510, 340, size=28)

    def draw_game_over(self, surface):
        self.draw_text(surface, "Game Over", 540, 260, size=48)
        self.draw_text(surface, "Press R to restart", 510, 340, size=28)

    def draw_victory(self, surface):
        self.draw_text(surface, "Victory!", 560, 260, size=48)
        self.draw_text(surface, "Press R to restart", 510, 340, size=28)

    def draw_upgrade_screen(self, surface, upgrades):
        surface.fill(COLOR_BACKGROUND)
        self.draw_text(surface, "Choose an Upgrade", 500, 80, size=40)
        card_width = 320
        card_height = 180
        spacing = 40
        x_start = 120
        y = 180
        for index, upgrade in enumerate(upgrades):
            x = x_start + index * (card_width + spacing)
            rect = pygame.Rect(x, y, card_width, card_height)
            pygame.draw.rect(surface, COLOR_UI_BG, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 2)
            self.draw_text(surface, f"{index + 1}. {upgrade['name']}", x + 12, y + 16, size=24)
            self.draw_text(surface, upgrade["description"], x + 12, y + 60, size=20)
