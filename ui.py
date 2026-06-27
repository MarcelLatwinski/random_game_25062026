import pygame
import settings
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_TEXT,
    COLOR_UI_BG,
    COLOR_HEALTH,
    COLOR_BACKGROUND,
    LEVELS,
)

FONTS = {}

def load_font(name="Segoe UI", size=24, bold=False):
    key = (name, size, bold)
    if key not in FONTS:
        FONTS[key] = pygame.font.SysFont(name, size, bold=bold)
    return FONTS[key]

class UI:
    def __init__(self):
        self.font = load_font()

    def draw_text(self, surface, text, x, y, color=COLOR_TEXT, size=24, bold=False):
        font = load_font("Segoe UI", size, bold=bold)
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
        self.draw_ammo(surface, player, x + bar_width + 34, y + 4)
        self.draw_upgrade_list(surface, player, x, y + bar_height + 24)

    def draw_ammo(self, surface, player, x, y):
        ammo_text = f"Ammo: {player.current_ammo_in_gun} / {player.reserve_ammo}"
        self.draw_text(surface, ammo_text, x, y, size=44, bold=True)
        now = pygame.time.get_ticks() / 1000
        if player.is_reloading(now):
            self.draw_text(surface, "Reloading", x, y + 48, size=32, bold=True)

    def draw_upgrade_list(self, surface, player, x, y):
        if not getattr(player, "picked_upgrades", None):
            return
        self.draw_text(surface, "Upgrades:", x, y, size=60, bold=True)
        for index, upgrade_name in enumerate(player.picked_upgrades[-5:], start=1):
            self.draw_text(surface, f"{index}. {upgrade_name}", x + 16, y + 60 * index, size=54)

    def draw_level(self, surface, level_number):
        self.draw_text(surface, f"Level {level_number}/{len(LEVELS)}", SCREEN_WIDTH - 360, 18, size=48, bold=True)

    def draw_fps_counter(self, surface, fps):
        font = load_font("Segoe UI", 30, bold=True)
        text_surface = font.render(f"FPS: {fps:.0f}", True, COLOR_TEXT)
        padding = 10
        x = SCREEN_WIDTH - text_surface.get_width() - 24
        y = 76
        background_rect = pygame.Rect(
            x - padding,
            y - 6,
            text_surface.get_width() + padding * 2,
            text_surface.get_height() + 12,
        )
        pygame.draw.rect(surface, COLOR_UI_BG, background_rect)
        pygame.draw.rect(surface, COLOR_TEXT, background_rect, 2)
        surface.blit(text_surface, (x, y))

    def draw_main_menu(self, surface):
        surface.fill(COLOR_BACKGROUND)
        title_font = load_font("Segoe UI Black", 104, bold=True)
        subtitle_font = load_font("Segoe UI", 54, bold=True)
        info_font = load_font("Segoe UI", 30, bold=True)

        title_surface = title_font.render("Zombie Platform Shooter", True, COLOR_TEXT)
        subtitle_surface = subtitle_font.render("Click to Start", True, COLOR_TEXT)
        info_surface = info_font.render("Travel right, reach the exit, upgrade between levels.", True, COLOR_TEXT)

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

    def draw_loading(self, surface, progress=0.0, status="Loading"):
        surface.fill(COLOR_BACKGROUND)
        self.draw_text(
            surface,
            "Loading...",
            SCREEN_WIDTH // 2 - 140,
            SCREEN_HEIGHT // 2 - 36,
            size=64,
            bold=True,
        )
        bar_width = 620
        bar_height = 28
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT // 2 + 52
        progress = max(0.0, min(1.0, progress))
        fill_width = int(bar_width * progress)
        pygame.draw.rect(surface, COLOR_UI_BG, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surface, COLOR_HEALTH, (bar_x, bar_y, fill_width, bar_height))
        pygame.draw.rect(surface, COLOR_TEXT, (bar_x, bar_y, bar_width, bar_height), 3)
        status_font = load_font("Segoe UI", 28, bold=True)
        status_surface = status_font.render(status, True, COLOR_TEXT)
        status_x = (SCREEN_WIDTH - status_surface.get_width()) // 2
        surface.blit(status_surface, (status_x, bar_y + 46))

    def draw_pause(self, surface, show_fps_counter=False):
        panel_width = 620
        panel_height = 290
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = 225
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(surface, COLOR_UI_BG, panel_rect)
        pygame.draw.rect(surface, COLOR_TEXT, panel_rect, 4)

        fps_status = "ON" if show_fps_counter else "OFF"
        debug_status = "ON" if settings.DEBUG_AIM_PIVOT else "OFF"
        self.draw_text(surface, "Paused", panel_x + 32, panel_y + 28, size=48, bold=True)
        self.draw_text(surface, "Esc: Resume", panel_x + 36, panel_y + 104, size=32, bold=True)
        self.draw_text(surface, f"F: FPS Counter {fps_status}", panel_x + 36, panel_y + 154, size=32, bold=True)
        self.draw_text(surface, f"D: Debug Pivot {debug_status}", panel_x + 36, panel_y + 204, size=32, bold=True)

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
