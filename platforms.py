import pygame
from settings import (
    COLOR_PLATFORM,
    COLOR_PLATFORM_OUTLINE,
)

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
        else:
            rect = platform_data
            self.sprite_key = None
            self.visual_height = None
            self.section = None

        self.rect = pygame.Rect(rect)
        self.id = platform_id
        self.color = COLOR_PLATFORM
        self.outline_color = COLOR_PLATFORM_OUTLINE
        self._scaled_image = None
        self._scaled_source_id = None
        self._scaled_size = None

    def draw(self, surface, image=None, images=None, camera_x=0):
        draw_rect = self.rect.move(-camera_x, 0)
        platform_image = image
        if images and self.sprite_key:
            platform_image = images.get(self.sprite_key) or image

        if platform_image:
            visual_height = self.visual_height or max(self.rect.height, self.rect.height * 3)
            image_size = (self.rect.width, visual_height)
            scaled = self.scaled_platform_image(platform_image, image_size)
            image_rect = pygame.Rect(draw_rect.left, draw_rect.top, self.rect.width, visual_height)
            surface.blit(scaled, image_rect)

            # Collision stays rectangular and simple; this thin line only marks
            # the exact walkable top of the platform art.
            pygame.draw.line(
                surface,
                (34, 45, 32),
                (draw_rect.left, draw_rect.top),
                (draw_rect.right, draw_rect.top),
                2,
            )
        else:
            pygame.draw.rect(surface, self.color, draw_rect)
            pygame.draw.rect(surface, self.outline_color, draw_rect, 4)

    def scaled_platform_image(self, image, image_size):
        source_id = id(image)
        if self._scaled_source_id == source_id and self._scaled_size == image_size:
            return self._scaled_image

        self._scaled_image = pygame.transform.scale(image, image_size)
        self._scaled_source_id = source_id
        self._scaled_size = image_size
        return self._scaled_image
