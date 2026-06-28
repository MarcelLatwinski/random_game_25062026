import math

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


DEBUG_UI_RECTS = False

UI_IMAGE_PATHS = {
    "loading_screen": "assets/images/loading_screen.png",
    "title_screen": "assets/images/title_screen.png",
    "hotbar": "assets/images/new_hotbar.png",
    "escape_menu": "assets/images/escape_menu.png",
}

# All rectangle constants are percentages of the image/screen they belong to.
LOADING_TEXT_RECT = (0.274, 0.435, 0.452, 0.185)
LOADING_BAR_RECT = (0.233, 0.703, 0.534, 0.026)
LOADING_STATUS_RECT = (0.284, 0.778, 0.431, 0.080)
LOADING_ELLIPSIS_INTERVAL = 0.40
LOADING_ELLIPSIS_STEPS = (".", "..", "...", "..")
START_BUTTON_RECT = (0.326, 0.565, 0.363, 0.142)

# The hotbar art is authored against this 1728 x 576 design canvas. The file
# may be exported larger, but every HUD coordinate below is in this base space.
HOTBAR_DESIGN_WIDTH = 1728
HOTBAR_DESIGN_HEIGHT = 576
HOTBAR_VISIBLE_HEIGHT = 178
HEALTH_BAR_X = 136
HEALTH_BAR_Y = 58
HEALTH_BAR_WIDTH = 574
HEALTH_BAR_HEIGHT = 38
HEALTH_TEXT_X = HEALTH_BAR_X + HEALTH_BAR_WIDTH // 2
HEALTH_TEXT_Y = HEALTH_BAR_Y + HEALTH_BAR_HEIGHT // 2
AMMO_TEXT_X = 1224
AMMO_TEXT_Y = 75
ROUND_TEXT_X = 1525
ROUND_TEXT_Y = 75
AMMO_TEXT_WIDTH = 280
AMMO_TEXT_HEIGHT = 48
ROUND_TEXT_WIDTH = 270
ROUND_TEXT_HEIGHT = 48
MENU_BUTTON_X = 806
MENU_BUTTON_Y = 32
MENU_BUTTON_WIDTH = 116
MENU_BUTTON_HEIGHT = 112

PAUSE_MENU_HEIGHT_RATIO = 0.84
PAUSE_MENU_ANIMATION_SECONDS = 0.18
PAUSE_BUTTON_WIDTH_RATIO = 0.66
PAUSE_BUTTON_HEIGHT_RATIO = 0.075
PAUSE_BUTTON_LAYOUT = (
    ("resume", 0.315),
    ("fps", 0.425),
    ("debug", 0.535),
    ("main_menu", 0.645),
    ("quit", 0.755),
)

FONTS = {}
_UI_FONT_NAME = None
UI_FONT_CANDIDATES = (
    "Bahnschrift Condensed",
    "Arial Black",
    "Segoe UI Black",
    "DejaVu Sans Condensed",
    "Liberation Sans",
)


def preferred_ui_font_name():
    global _UI_FONT_NAME
    if _UI_FONT_NAME is not None:
        return _UI_FONT_NAME

    for name in UI_FONT_CANDIDATES:
        if pygame.font.match_font(name):
            _UI_FONT_NAME = name
            return _UI_FONT_NAME

    _UI_FONT_NAME = ""
    return None


def load_font(name="Segoe UI", size=24, bold=False):
    if name == "ui":
        name = preferred_ui_font_name()

    key = (name, size, bold)
    if key not in FONTS:
        FONTS[key] = pygame.font.SysFont(name, size, bold=bold)
    return FONTS[key]


def rect_from_percent(container_rect, spec):
    x_ratio, y_ratio, width_ratio, height_ratio = spec
    return pygame.Rect(
        round(container_rect.left + container_rect.width * x_ratio),
        round(container_rect.top + container_rect.height * y_ratio),
        round(container_rect.width * width_ratio),
        round(container_rect.height * height_ratio),
    )


def clamp(value, low, high):
    return max(low, min(value, high))


def smooth_progress(value):
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def fitted_font_size(text, max_width, max_size, min_size=18):
    size = max_size
    while size > min_size:
        font = load_font("ui", size, bold=True)
        if font.size(text)[0] <= max_width:
            return size
        size -= 2
    return min_size


class UI:
    def __init__(self):
        self.font = load_font()
        self.loading_screen_image = None
        self.title_image = None
        self.hotbar_image = None
        self.escape_menu_image = None
        self.scaled_images = {}

    def load_loading_asset(self, asset_manager):
        self.loading_screen_image = asset_manager.load_image(
            "ui_loading_screen",
            UI_IMAGE_PATHS["loading_screen"],
        )

    def load_title_asset(self, asset_manager):
        self.title_image = asset_manager.load_image(
            "ui_title_screen",
            UI_IMAGE_PATHS["title_screen"],
        )

    def load_game_ui_assets(self, asset_manager):
        self.load_hotbar_asset(asset_manager)
        self.load_escape_menu_asset(asset_manager)

    def load_hotbar_asset(self, asset_manager):
        self.hotbar_image = asset_manager.load_image(
            "ui_hotbar",
            UI_IMAGE_PATHS["hotbar"],
            remove_light_pixels=True,
            remove_light_pixels_from_edges=True,
            trim_transparent=False,
            transparent_min_value=215,
            transparent_channel_spread=24,
        )

    def load_escape_menu_asset(self, asset_manager):
        self.escape_menu_image = asset_manager.load_image(
            "ui_escape_menu",
            UI_IMAGE_PATHS["escape_menu"],
            remove_light_pixels=True,
            remove_light_pixels_from_edges=True,
            trim_transparent=True,
            transparent_min_value=215,
            transparent_channel_spread=24,
        )

    def load_ui_assets(self, asset_manager):
        self.load_loading_asset(asset_manager)
        self.load_title_asset(asset_manager)
        self.load_game_ui_assets(asset_manager)

    def prepare_fonts(self):
        for size in (24, 28, 30, 34, 48, 54, 64, 72, 82, 104):
            load_font("ui", size, bold=True)
        load_font("ui", 24, bold=False)

    def scaled_image(self, cache_name, image, target_size):
        if image is None:
            return None

        target_size = (max(1, target_size[0]), max(1, target_size[1]))
        cache_key = (cache_name, id(image), target_size)
        if cache_key not in self.scaled_images:
            self.scaled_images[cache_key] = pygame.transform.smoothscale(image, target_size)
        return self.scaled_images[cache_key]

    def pixel_scaled_image(self, cache_name, image, target_size):
        if image is None:
            return None

        target_size = (max(1, target_size[0]), max(1, target_size[1]))
        cache_key = (cache_name, "pixel", id(image), target_size)
        if cache_key not in self.scaled_images:
            # Pygame's nearest-neighbor scale is the canvas equivalent of
            # imageSmoothingEnabled = false; it keeps the pixel-art edges crisp.
            self.scaled_images[cache_key] = pygame.transform.scale(image, target_size)
        return self.scaled_images[cache_key]

    def draw_text(self, surface, text, x, y, color=COLOR_TEXT, size=24, bold=False):
        font = load_font("ui", size, bold=bold)
        text_surface = font.render(text, True, color)
        surface.blit(text_surface, (x, y))

    def draw_outlined_text(
        self,
        surface,
        text,
        rect,
        size,
        color=(238, 232, 195),
        outline=(20, 25, 22),
        bold=True,
        center=True,
        alpha=255,
        antialias=True,
    ):
        font = load_font("ui", size, bold=bold)
        text_surface = font.render(text, antialias, color)
        outline_surface = font.render(text, antialias, outline)
        if alpha < 255:
            text_surface.set_alpha(alpha)
            outline_surface.set_alpha(alpha)
        if center:
            text_rect = text_surface.get_rect(center=rect.center)
        else:
            text_rect = text_surface.get_rect(midleft=(rect.left, rect.centery))

        for offset in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surface.blit(outline_surface, text_rect.move(offset))
        surface.blit(text_surface, text_rect)

    def title_surface(self, surface):
        return self.scaled_image(
            "title_screen",
            self.title_image,
            surface.get_size(),
        )

    def start_button_rect(self, surface):
        return rect_from_percent(surface.get_rect(), START_BUTTON_RECT)

    def draw_title_screen(self, surface, mouse_pos=(0, 0), now=0.0):
        title = self.title_surface(surface)
        if title:
            surface.blit(title, (0, 0))
        else:
            self.draw_title_fallback(surface)

        button_rect = self.start_button_rect(surface)
        if button_rect.collidepoint(mouse_pos):
            pulse = 1.0 + 0.035 * math.sin(now * 9.0)
            hover_rect = button_rect.inflate(
                round(button_rect.width * 0.025 * pulse),
                round(button_rect.height * 0.16 * pulse),
            )
            glow = pygame.Surface(hover_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (190, 220, 115, 58),
                glow.get_rect(),
                width=5,
                border_radius=10,
            )
            surface.blit(glow, hover_rect)

        if DEBUG_UI_RECTS:
            pygame.draw.rect(surface, (255, 60, 60), button_rect, 3)

    def draw_title_fallback(self, surface):
        surface.fill(COLOR_BACKGROUND)
        title_font = load_font("ui", 104, bold=True)
        subtitle_font = load_font("ui", 54, bold=True)
        info_font = load_font("ui", 30, bold=True)

        title_surface = title_font.render("Zombie Platform Shooter", True, COLOR_TEXT)
        subtitle_surface = subtitle_font.render("Click to Start", True, COLOR_TEXT)
        info_surface = info_font.render(
            "Travel right, reach the exit, upgrade between levels.",
            True,
            COLOR_TEXT,
        )

        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        title_y = SCREEN_HEIGHT // 2 - 180
        subtitle_x = (SCREEN_WIDTH - subtitle_surface.get_width()) // 2
        subtitle_y = SCREEN_HEIGHT // 2 + 20
        info_x = (SCREEN_WIDTH - info_surface.get_width()) // 2
        info_y = subtitle_y + 80

        surface.blit(title_surface, (title_x, title_y))
        button_rect = pygame.Rect(
            subtitle_x - 24,
            subtitle_y - 16,
            subtitle_surface.get_width() + 48,
            subtitle_surface.get_height() + 24,
        )
        pygame.draw.rect(surface, COLOR_UI_BG, button_rect)
        pygame.draw.rect(surface, COLOR_TEXT, button_rect, 3)
        surface.blit(subtitle_surface, (subtitle_x, subtitle_y))
        surface.blit(info_surface, (info_x, info_y))

    def draw_main_menu(self, surface):
        self.draw_title_screen(surface, pygame.mouse.get_pos(), pygame.time.get_ticks() / 1000)

    def loading_screen_surface(self, surface):
        return self.pixel_scaled_image(
            "loading_screen",
            self.loading_screen_image,
            surface.get_size(),
        )

    def loading_text_rect(self, surface):
        return rect_from_percent(surface.get_rect(), LOADING_TEXT_RECT)

    def loading_bar_rect(self, surface):
        return rect_from_percent(surface.get_rect(), LOADING_BAR_RECT)

    def loading_status_rect(self, surface):
        return rect_from_percent(surface.get_rect(), LOADING_STATUS_RECT)

    def loading_ellipsis(self, now):
        # The ellipsis is timer-based, so it keeps animating at the same pace
        # even if one loading task takes longer than a normal frame.
        step = int(now / LOADING_ELLIPSIS_INTERVAL) % len(LOADING_ELLIPSIS_STEPS)
        return LOADING_ELLIPSIS_STEPS[step]

    def hotbar_scale(self, surface):
        return surface.get_width() / HOTBAR_DESIGN_WIDTH

    def hotbar_design_rect(self, surface, x, y, width, height):
        scale = self.hotbar_scale(surface)
        return pygame.Rect(
            round(x * scale),
            round(y * scale),
            round(width * scale),
            round(height * scale),
        )

    def hotbar_rect(self, surface):
        scale = self.hotbar_scale(surface)
        return pygame.Rect(
            0,
            0,
            surface.get_width(),
            round(HOTBAR_DESIGN_HEIGHT * scale),
        )

    def hotbar_visible_rect(self, surface):
        scale = self.hotbar_scale(surface)
        return pygame.Rect(
            0,
            0,
            surface.get_width(),
            round(HOTBAR_VISIBLE_HEIGHT * scale),
        )

    def hotbar_menu_button_rect(self, surface):
        return self.hotbar_design_rect(
            surface,
            MENU_BUTTON_X,
            MENU_BUTTON_Y,
            MENU_BUTTON_WIDTH,
            MENU_BUTTON_HEIGHT,
        )

    def hotbar_health_rect(self, surface):
        return self.hotbar_design_rect(
            surface,
            HEALTH_BAR_X,
            HEALTH_BAR_Y,
            HEALTH_BAR_WIDTH,
            HEALTH_BAR_HEIGHT,
        )

    def hotbar_ammo_rect(self, surface):
        return self.hotbar_design_rect(
            surface,
            AMMO_TEXT_X - AMMO_TEXT_WIDTH // 2,
            AMMO_TEXT_Y - AMMO_TEXT_HEIGHT // 2,
            AMMO_TEXT_WIDTH,
            AMMO_TEXT_HEIGHT,
        )

    def hotbar_round_rect(self, surface):
        return self.hotbar_design_rect(
            surface,
            ROUND_TEXT_X - ROUND_TEXT_WIDTH // 2,
            ROUND_TEXT_Y - ROUND_TEXT_HEIGHT // 2,
            ROUND_TEXT_WIDTH,
            ROUND_TEXT_HEIGHT,
        )

    def handle_hotbar_click(self, surface, mouse_pos):
        if self.hotbar_menu_button_rect(surface).collidepoint(mouse_pos):
            return "menu"
        if self.hotbar_visible_rect(surface).collidepoint(mouse_pos):
            return "hud"
        return None

    def draw_health_bar(self, surface, player):
        self.draw_hotbar(
            surface,
            player,
            level_number=1,
            level_total=len(LEVELS),
            mouse_pos=pygame.mouse.get_pos(),
            now=pygame.time.get_ticks() / 1000,
        )

    def draw_hotbar(
        self,
        surface,
        player,
        level_number,
        level_total,
        mouse_pos=(0, 0),
        now=0.0,
        menu_pressed_until=0.0,
    ):
        hotbar_rect = self.hotbar_rect(surface)
        hotbar = self.pixel_scaled_image(
            "hotbar",
            self.hotbar_image,
            hotbar_rect.size,
        )
        if hotbar:
            surface.blit(hotbar, hotbar_rect)
        else:
            fallback_rect = self.hotbar_visible_rect(surface)
            fallback = pygame.Surface(fallback_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(fallback, (18, 22, 20, 210), fallback.get_rect(), border_radius=8)
            pygame.draw.rect(fallback, (238, 232, 195), fallback.get_rect(), 3, border_radius=8)
            surface.blit(fallback, fallback_rect)

        self.draw_hotbar_health(surface, player)
        self.draw_hotbar_ammo(surface, player, now)
        self.draw_hotbar_round(surface, level_number, level_total)
        self.draw_hotbar_menu_icon(surface, mouse_pos, now, menu_pressed_until)
        upgrade_y = self.hotbar_visible_rect(surface).bottom + 12
        self.draw_upgrade_list(surface, player, 24, upgrade_y)

        if DEBUG_UI_RECTS:
            for rect, color in (
                (self.hotbar_visible_rect(surface), (200, 200, 200)),
                (self.hotbar_health_rect(surface), (255, 70, 70)),
                (self.hotbar_ammo_rect(surface), (255, 210, 70)),
                (self.hotbar_round_rect(surface), (70, 180, 255)),
                (self.hotbar_menu_button_rect(surface), (120, 255, 120)),
            ):
                pygame.draw.rect(surface, color, rect, 2)

    def draw_hotbar_health(self, surface, player):
        health_rect = self.hotbar_health_rect(surface).inflate(-6, -6)
        health_ratio = 0.0
        if getattr(player, "max_health", 0) > 0:
            health_ratio = clamp(player.health / player.max_health, 0.0, 1.0)

        fill_rect = health_rect.copy()
        fill_rect.width = round(health_rect.width * health_ratio)
        pygame.draw.rect(surface, (45, 12, 12), health_rect)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, (151, 30, 28), fill_rect)
            shine_rect = pygame.Rect(fill_rect.left, fill_rect.top, fill_rect.width, max(4, fill_rect.height // 5))
            pygame.draw.rect(surface, (219, 70, 55), shine_rect)
        pygame.draw.rect(surface, (22, 28, 23), health_rect, max(2, round(self.hotbar_scale(surface) * 2)))
        self.draw_outlined_text(
            surface,
            f"HP {player.health}/{player.max_health}",
            health_rect,
            size=round(29 * self.hotbar_scale(surface)),
            antialias=False,
        )

    def draw_hotbar_ammo(self, surface, player, now):
        ammo_rect = self.hotbar_ammo_rect(surface).inflate(-8, -6)
        ammo_text = f"{player.current_ammo_in_gun} / {player.reserve_ammo}"
        if player.is_reloading(now):
            ammo_text = "Reloading"
        self.draw_outlined_text(
            surface,
            ammo_text,
            ammo_rect,
            size=round(31 * self.hotbar_scale(surface)),
            antialias=False,
        )

    def draw_hotbar_round(self, surface, level_number, level_total):
        round_rect = self.hotbar_round_rect(surface).inflate(-8, -6)
        self.draw_outlined_text(
            surface,
            f"ROUND {level_number}",
            round_rect,
            size=round(29 * self.hotbar_scale(surface)),
            antialias=False,
        )

    def draw_hotbar_menu_icon(self, surface, mouse_pos, now, menu_pressed_until):
        button_rect = self.hotbar_menu_button_rect(surface)
        hover = button_rect.collidepoint(mouse_pos)
        pressed = now < menu_pressed_until
        pulse = 1.0 + (0.035 * math.sin(now * 12.0) if hover else 0.0)
        if pressed:
            pulse = 0.92

        center = button_rect.center
        radius = round(min(button_rect.width, button_rect.height) * 0.28 * pulse)
        if hover or pressed:
            glow = pygame.Surface((radius * 2 + 18, radius * 2 + 18), pygame.SRCALPHA)
            pygame.draw.circle(
                glow,
                (183, 213, 105, 70 if hover else 95),
                glow.get_rect().center,
                radius + 6,
                width=4,
            )
            surface.blit(glow, glow.get_rect(center=center))

        line_length = round(button_rect.width * (0.38 if not hover else 0.43) * pulse)
        line_width = max(3, round(button_rect.height * 0.050))
        spacing = round(button_rect.height * (0.145 if not pressed else 0.115))
        line_color = (213, 202, 156) if not hover else (232, 228, 184)
        shadow_color = (22, 25, 21)

        for index in (-1, 0, 1):
            y = center[1] + index * spacing
            start = (center[0] - line_length // 2, y)
            end = (center[0] + line_length // 2, y)
            pygame.draw.line(surface, shadow_color, (start[0] + 2, start[1] + 2), (end[0] + 2, end[1] + 2), line_width)
            pygame.draw.line(surface, line_color, start, end, line_width)

    def draw_ammo(self, surface, player, x, y):
        ammo_text = f"Ammo: {player.current_ammo_in_gun} / {player.reserve_ammo}"
        self.draw_text(surface, ammo_text, x, y, size=44, bold=True)
        now = pygame.time.get_ticks() / 1000
        if player.is_reloading(now):
            self.draw_text(surface, "Reloading", x, y + 48, size=32, bold=True)

    def draw_upgrade_list(self, surface, player, x, y):
        if not getattr(player, "picked_upgrades", None):
            return

        upgrades = player.picked_upgrades[-5:]
        title_font = load_font("ui", 24, bold=True)
        item_font = load_font("ui", 21, bold=True)
        width = 340
        height = 42 + len(upgrades) * 30
        panel = pygame.Rect(x, y, width, height)
        panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (15, 19, 17, 172), panel_surface.get_rect(), border_radius=6)
        pygame.draw.rect(panel_surface, (155, 177, 95, 120), panel_surface.get_rect(), 2, border_radius=6)
        surface.blit(panel_surface, panel)
        surface.blit(title_font.render("Upgrades", True, (238, 232, 195)), (panel.x + 12, panel.y + 9))
        for index, upgrade_name in enumerate(upgrades):
            text = item_font.render(upgrade_name, True, (218, 220, 188))
            surface.blit(text, (panel.x + 14, panel.y + 42 + index * 30))

    def draw_level(self, surface, level_number):
        self.draw_text(surface, f"Level {level_number}/{len(LEVELS)}", SCREEN_WIDTH - 360, 18, size=48, bold=True)

    def draw_fps_counter(self, surface, fps):
        font = load_font("ui", 30, bold=True)
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

    def draw_loading(
        self,
        surface,
        progress=0.0,
        status="Preparing game...",
        now=0.0,
        loaded_count=0,
        total_count=0,
    ):
        self.draw_loading_screen(
            surface,
            progress=progress,
            status=status,
            now=now,
            loaded_count=loaded_count,
            total_count=total_count,
        )

    def draw_loading_screen(
        self,
        surface,
        progress=0.0,
        status="Preparing game...",
        now=0.0,
        loaded_count=0,
        total_count=0,
    ):
        background = self.loading_screen_surface(surface)
        if background:
            surface.blit(background, (0, 0))
        else:
            surface.fill((42, 64, 41))

        text_rect = self.loading_text_rect(surface)
        bar_rect = self.loading_bar_rect(surface)
        status_rect = self.loading_status_rect(surface)
        progress = clamp(progress, 0.0, 1.0)

        loading_text = f"LOADING{self.loading_ellipsis(now)}"
        self.draw_outlined_text(
            surface,
            loading_text,
            text_rect,
            size=82,
            color=(238, 232, 195),
            outline=(18, 32, 20),
        )

        # Progress is based on completed loading tasks divided by the total
        # number of required tasks. The fill stays clipped inside the asset bar.
        fill_rect = bar_rect.copy()
        fill_rect.width = round(bar_rect.width * progress)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, (133, 158, 75), fill_rect, border_radius=2)
            shine_rect = pygame.Rect(
                fill_rect.left,
                fill_rect.top,
                fill_rect.width,
                max(3, fill_rect.height // 3),
            )
            pygame.draw.rect(surface, (205, 222, 119), shine_rect, border_radius=2)

        count_text = ""
        if total_count:
            count_text = f"  {loaded_count} / {total_count}"
        status_text = f"{status}{count_text}"
        status_size = fitted_font_size(status_text, status_rect.width - 24, 30)
        self.draw_outlined_text(
            surface,
            status_text,
            status_rect,
            size=status_size,
            color=(220, 224, 187),
            outline=(12, 24, 16),
        )

        if DEBUG_UI_RECTS:
            for rect, color in (
                (text_rect, (255, 80, 80)),
                (bar_rect, (255, 220, 80)),
                (status_rect, (100, 200, 255)),
            ):
                pygame.draw.rect(surface, color, rect, 2)

    def pause_menu_rect(self, surface):
        if not self.escape_menu_image:
            width = 620
            height = 740
        else:
            height = round(surface.get_height() * PAUSE_MENU_HEIGHT_RATIO)
            scale = height / self.escape_menu_image.get_height()
            width = round(self.escape_menu_image.get_width() * scale)

        width = min(width, surface.get_width() - 120)
        height = min(height, surface.get_height() - 80)
        return pygame.Rect(
            (surface.get_width() - width) // 2,
            (surface.get_height() - height) // 2,
            width,
            height,
        )

    def pause_button_rects(self, surface, menu_rect=None):
        menu_rect = menu_rect or self.pause_menu_rect(surface)
        rects = []
        width = round(menu_rect.width * PAUSE_BUTTON_WIDTH_RATIO)
        height = round(menu_rect.height * PAUSE_BUTTON_HEIGHT_RATIO)
        x = menu_rect.centerx - width // 2
        for action, y_ratio in PAUSE_BUTTON_LAYOUT:
            y = round(menu_rect.top + menu_rect.height * y_ratio)
            rects.append((action, pygame.Rect(x, y, width, height)))
        return rects

    def pause_menu_action_at(self, surface, mouse_pos):
        for action, rect in self.pause_button_rects(surface):
            if rect.collidepoint(mouse_pos):
                return action
        return None

    def pause_button_label(self, action, show_fps_counter=False):
        if action == "resume":
            return "Resume"
        if action == "fps":
            return f"FPS Counter: {'ON' if show_fps_counter else 'OFF'}"
        if action == "debug":
            return f"Debug Pivot: {'ON' if settings.DEBUG_AIM_PIVOT else 'OFF'}"
        if action == "main_menu":
            return "Main Menu"
        if action == "quit":
            return "Quit Game"
        return action.replace("_", " ").title()

    def draw_pause(
        self,
        surface,
        show_fps_counter=False,
        mouse_pos=(0, 0),
        now=0.0,
        opened_at=0.0,
        pressed_action=None,
    ):
        self.draw_pause_menu(
            surface,
            mouse_pos=mouse_pos,
            now=now,
            opened_at=opened_at,
            show_fps_counter=show_fps_counter,
            pressed_action=pressed_action,
        )

    def draw_pause_menu(
        self,
        surface,
        mouse_pos=(0, 0),
        now=0.0,
        opened_at=0.0,
        show_fps_counter=False,
        pressed_action=None,
    ):
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 128))
        surface.blit(dim, (0, 0))

        final_rect = self.pause_menu_rect(surface)
        progress = smooth_progress((now - opened_at) / PAUSE_MENU_ANIMATION_SECONDS)
        scale = 0.90 + 0.10 * progress
        alpha = round(255 * progress)
        draw_size = (
            max(1, round(final_rect.width * scale)),
            max(1, round(final_rect.height * scale)),
        )
        draw_rect = pygame.Rect(0, 0, *draw_size)
        draw_rect.center = final_rect.center

        menu = self.scaled_image("escape_menu", self.escape_menu_image, final_rect.size)
        if menu:
            if draw_size != final_rect.size:
                menu_to_draw = pygame.transform.smoothscale(menu, draw_size)
            else:
                menu_to_draw = menu.copy()
            menu_to_draw.set_alpha(alpha)
            surface.blit(menu_to_draw, draw_rect)
        else:
            fallback = pygame.Surface(draw_rect.size, pygame.SRCALPHA)
            fallback.fill((92, 96, 77, alpha))
            pygame.draw.rect(fallback, (23, 29, 24, alpha), fallback.get_rect(), 4)
            surface.blit(fallback, draw_rect)

        text_alpha = alpha
        for action, rect in self.pause_button_rects(surface, draw_rect):
            hover = rect.collidepoint(mouse_pos)
            pressed = action == pressed_action
            if hover or pressed:
                button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
                fill_alpha = 75 if hover else 52
                if pressed:
                    fill_alpha = 105
                pygame.draw.rect(
                    button_surface,
                    (28, 36, 29, fill_alpha),
                    button_surface.get_rect(),
                    border_radius=6,
                )
                pygame.draw.rect(
                    button_surface,
                    (185, 211, 108, min(210, text_alpha)),
                    button_surface.get_rect(),
                    3,
                    border_radius=6,
                )
                surface.blit(button_surface, rect)

            label = self.pause_button_label(action, show_fps_counter)
            text_color = (238, 232, 195)
            if action == "quit":
                text_color = (232, 168, 142)
            self.draw_outlined_text(
                surface,
                label,
                rect,
                size=34,
                color=text_color,
                outline=(18, 23, 19),
                alpha=text_alpha,
            )

        if DEBUG_UI_RECTS:
            pygame.draw.rect(surface, (255, 70, 70), final_rect, 2)
            for _, rect in self.pause_button_rects(surface, final_rect):
                pygame.draw.rect(surface, (120, 255, 120), rect, 2)

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
