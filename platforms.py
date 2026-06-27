import pygame
from settings import (
    SCREEN_WIDTH,
    DRAW_MARGIN,
    DRAW_PLATFORM_COLLISION_MARKERS,
    COLOR_PLATFORM,
    COLOR_PLATFORM_OUTLINE,
)

MAX_REPEATING_PLATFORM_TILE_WIDTH = 640


class Platform:
    def __init__(self, platform_data, platform_id):
        if isinstance(platform_data, dict):
            rect = (
                platform_data["x"],
                platform_data["y"],
                platform_data["width"],
                platform_data["height"],
            )
            self.sprite_key = platform_data.get("sprite")
            self.visual_height = platform_data.get("visual_height")
            self.section = platform_data.get("section")
            self.drop_through = bool(platform_data.get("drop_through", True))
        else:
            rect = platform_data
            self.sprite_key = None
            self.visual_height = None
            self.section = None
            self.drop_through = True

        self.rect = pygame.Rect(rect)
        self.id = platform_id
        self.color = COLOR_PLATFORM
        self.outline_color = COLOR_PLATFORM_OUTLINE
        self._scaled_image = None
        self._scaled_source_id = None
        self._scaled_size = None

    def is_near_camera(self, camera_x, screen_width, margin=DRAW_MARGIN):
        return (
            self.rect.right >= camera_x - margin
            and self.rect.left <= camera_x + screen_width + margin
        )

    def resolve_image(self, image=None, images=None):
        if images and self.sprite_key:
            return images.get(self.sprite_key)
        return image

    def visual_draw_height(self):
        return self.visual_height or max(self.rect.height, self.rect.height * 3)

    def scaled_image_size(self, visual_height):
        if self.rect.width > SCREEN_WIDTH * 2:
            return (min(MAX_REPEATING_PLATFORM_TILE_WIDTH, self.rect.width), visual_height)
        return (self.rect.width, visual_height)

    def prepare_surface(self, image=None, images=None):
        platform_image = self.resolve_image(image=image, images=images)
        if not platform_image:
            return

        # Build the scaled sprite during loading so gameplay draw calls only blit.
        visual_height = self.visual_draw_height()
        self.scaled_platform_image(platform_image, self.scaled_image_size(visual_height))

    def draw(self, surface, image=None, images=None, camera_x=0):
        if not self.is_near_camera(camera_x, surface.get_width()):
            return

        draw_rect = self.rect.move(-camera_x, 0)
        platform_image = self.resolve_image(image=image, images=images)

        if platform_image:
            visual_height = self.visual_draw_height()
            image_size = self.scaled_image_size(visual_height)
            scaled = self.scaled_platform_image(platform_image, image_size)
            image_rect = pygame.Rect(draw_rect.left, draw_rect.top, self.rect.width, visual_height)
            if self.rect.width > scaled.get_width():
                self.blit_repeated(surface, scaled, image_rect)
            else:
                self.blit_clipped(surface, scaled, image_rect)

            if DRAW_PLATFORM_COLLISION_MARKERS:
                self.draw_visible_top_line(surface, draw_rect)
        else:
            self.draw_fallback_rect(surface, draw_rect)

    def blit_clipped(self, surface, image, image_rect, clip_rect=None):
        visible = image_rect.clip(surface.get_rect())
        if clip_rect:
            visible = visible.clip(clip_rect)
        if visible.width <= 0 or visible.height <= 0:
            return

        source_area = pygame.Rect(
            visible.left - image_rect.left,
            visible.top - image_rect.top,
            visible.width,
            visible.height,
        )
        surface.blit(image, visible, source_area)

    def blit_repeated(self, surface, image, image_rect):
        tile_width = image.get_width()
        if tile_width <= 0:
            return

        screen_left = -DRAW_MARGIN
        screen_right = surface.get_width() + DRAW_MARGIN
        visible_left = max(image_rect.left, screen_left)
        visible_right = min(image_rect.right, screen_right)
        if visible_left >= visible_right:
            return

        # Very wide platforms, especially the ground, use repeated visible tiles
        # instead of one huge scaled image.
        first_tile = max(0, (visible_left - image_rect.left) // tile_width)
        tile_x = image_rect.left + first_tile * tile_width
        while tile_x < visible_right:
            tile_rect = pygame.Rect(tile_x, image_rect.top, tile_width, image_rect.height)
            self.blit_clipped(surface, image, tile_rect, clip_rect=image_rect)
            tile_x += tile_width

    def draw_visible_top_line(self, surface, draw_rect):
        line_left = max(draw_rect.left, -DRAW_MARGIN)
        line_right = min(draw_rect.right, surface.get_width() + DRAW_MARGIN)
        if line_right <= line_left:
            return

        pygame.draw.line(
            surface,
            (34, 45, 32),
            (line_left, draw_rect.top),
            (line_right, draw_rect.top),
            2,
        )

    def draw_fallback_rect(self, surface, draw_rect):
        visible = draw_rect.clip(surface.get_rect())
        if visible.width <= 0 or visible.height <= 0:
            return

        pygame.draw.rect(surface, self.color, visible)
        pygame.draw.rect(surface, self.outline_color, visible, 4)

    def scaled_platform_image(self, image, image_size):
        source_id = id(image)
        if self._scaled_source_id == source_id and self._scaled_size == image_size:
            return self._scaled_image

        self._scaled_image = pygame.transform.scale(image, image_size)
        self._scaled_source_id = source_id
        self._scaled_size = image_size
        return self._scaled_image
