import pygame
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_TEXT,
    COLOR_UI_BG,
    COLOR_HEALTH,
    COLOR_BACKGROUND,
    LEVELS,
)

FONT = None

def load_font(name="Segoe UI", size=24, bold=False):
    global FONT
    if FONT is None or FONT.get_height() != size:
        FONT = pygame.font.SysFont(name, size, bold=bold)
    return FONT

class UI:
    def __init__(self):
        self.font = load_font()

    def draw_text(self, surface, text, x, y, color=COLOR_TEXT, size=24, bold=False):
        font = pygame.font.SysFont("Segoe UI", size, bold=bold)
        text_surface = font.render(text, True, color)
        surface.blit(text_surface, (x, y))

    def draw_health_bar(self, surface, player):
        bar_width = 1200
        bar_height = 66
        x = 20
        y = 20
        pygame.draw.rect(surface, COLOR_UI_BG, (x - 3, y - 3, bar_width + 6, bar_height + 6))
        fill_width = int(bar_width * player.health / player.max_health)
        pygame.draw.rect(surface, COLOR_HEALTH, (x, y, fill_width, bar_height))
        pygame.draw.rect(surface, COLOR_TEXT, (x, y, bar_width, bar_height), 4)
        self.draw_text(surface, f"HP: {player.health}/{player.max_health}", x + 12, y + 6, size=54, bold=True)
        self.draw_upgrade_list(surface, player, x, y + bar_height + 24)

    def draw_upgrade_list(self, surface, player, x, y):
        if not getattr(player, "picked_upgrades", None):
            return
        self.draw_text(surface, "Upgrades:", x, y, size=60, bold=True)
        for index, upgrade_name in enumerate(player.picked_upgrades[-5:], start=1):
            self.draw_text(surface, f"{index}. {upgrade_name}", x + 16, y + 60 * index, size=54)

    def draw_level(self, surface, level_number):
        self.draw_text(surface, f"Level {level_number}/{len(LEVELS)}", SCREEN_WIDTH - 360, 18, size=48, bold=True)

    def draw_main_menu(self, surface):
        surface.fill(COLOR_BACKGROUND)
        title_font = pygame.font.SysFont("Segoe UI Black", 104, bold=True)
        subtitle_font = pygame.font.SysFont("Segoe UI", 54, bold=True)
        info_font = pygame.font.SysFont("Segoe UI", 30, bold=True)

        title_surface = title_font.render("Zombie Platform Shooter", True, COLOR_TEXT)
        subtitle_surface = subtitle_font.render("Click to Start", True, COLOR_TEXT)
        info_surface = info_font.render("Survive waves, upgrade between levels, stay alive.", True, COLOR_TEXT)

        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        title_y = SCREEN_HEIGHT // 2 - 180
        subtitle_x = (SCREEN_WIDTH - subtitle_surface.get_width()) // 2
        subtitle_y = SCREEN_HEIGHT // 2 + 20
        info_x = (SCREEN_WIDTH - info_surface.get_width()) // 2
        info_y = subtitle_y + 80

        surface.blit(title_surface, (title_x, title_y))

        button_rect = pygame.Rect(subtitle_x - 24, subtitle_y - 16, subtitle_surface.get_width() + 48, subtitle_surface.get_height() + 24)
        pygame.draw.rect(surface, COLOR_UI_BG, button_rect)
        pygame.draw.rect(surface, COLOR_TEXT, button_rect, 3)
        surface.blit(subtitle_surface, (subtitle_x, subtitle_y))

        surface.blit(info_surface, (info_x, info_y))

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
        self.draw_text(surface, "Choose an Upgrade", SCREEN_WIDTH // 2 - 360, 80, size=72, bold=True)
        card_width = 440
        card_height = 260
        spacing = 60
        total_width = len(upgrades) * card_width + (len(upgrades) - 1) * spacing
        x_start = (SCREEN_WIDTH - total_width) // 2
        y = 220
        for index, upgrade in enumerate(upgrades):
            x = x_start + index * (card_width + spacing)
            rect = pygame.Rect(x, y, card_width, card_height)
            pygame.draw.rect(surface, COLOR_UI_BG, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 4)
            self.draw_text(surface, f"{index + 1}. {upgrade['name']}", x + 18, y + 18, size=38, bold=True)
            self.draw_text(surface, upgrade["description"], x + 18, y + 80, size=32)
