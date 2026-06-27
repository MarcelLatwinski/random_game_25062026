import os

import pygame

from animation import load_animation_set


class AssetManager:
    """Simple cache for images, animations, and sounds.

    Assets are loaded once and then reused by the game objects and draw code.
    Missing files warn clearly instead of failing silently.
    """

    def __init__(self):
        self.images = {}
        self.animations = {}
        self.sounds = {}
        self._image_path_cache = {}
        self._sound_path_cache = {}

    def _warn(self, message):
        print(f"[AssetManager] Warning: {message}")

    def load_image(
        self,
        key,
        path,
        remove_light_pixels=False,
        remove_light_pixels_from_edges=False,
        trim_transparent=False,
        transparent_min_value=225,
        transparent_channel_spread=36,
    ):
        if key in self.images:
            return self.images[key]

        if not path:
            self._warn(f"No path provided for image '{key}'.")
            self.images[key] = None
            return None

        if not os.path.exists(path):
            self._warn(f"Missing image file for '{key}': {path}")
            self.images[key] = None
            return None

        cache_key = (
            path,
            remove_light_pixels,
            remove_light_pixels_from_edges,
            trim_transparent,
            transparent_min_value,
            transparent_channel_spread,
        )
        if cache_key in self._image_path_cache:
            self.images[key] = self._image_path_cache[cache_key]
            return self.images[key]

        try:
            image = pygame.image.load(path).convert_alpha()
        except (pygame.error, OSError) as exc:
            self._warn(f"Could not load image '{key}': {exc}")
            self.images[key] = None
            return None

        if remove_light_pixels:
            if remove_light_pixels_from_edges:
                image = self._remove_edge_connected_light_pixels(
                    image,
                    min_value=transparent_min_value,
                    max_channel_spread=transparent_channel_spread,
                )
            else:
                image = self._remove_near_white_pixels(
                    image,
                    min_value=transparent_min_value,
                    max_channel_spread=transparent_channel_spread,
                )
        if trim_transparent:
            image = self._trim_transparent_image(image)

        self.images[key] = image
        self._image_path_cache[cache_key] = image
        return image

    def load_animation(self, key, sheet_config):
        if key in self.images:
            return self.images[key]

        if not sheet_config:
            self._warn(f"No animation config provided for '{key}'.")
            self.images[key] = None
            self.animations[key] = None
            return None

        path = sheet_config.get("path")
        if not path:
            self._warn(f"No sprite sheet path provided for animation '{key}'.")
            self.images[key] = None
            self.animations[key] = None
            return None

        if not os.path.exists(path):
            self._warn(f"Missing sprite sheet for animation '{key}': {path}")
            self.images[key] = None
            self.animations[key] = None
            return None

        for nested_path in self._nested_animation_sheet_paths(sheet_config):
            if nested_path and not os.path.exists(nested_path):
                self._warn(f"Missing nested sprite sheet for animation '{key}': {nested_path}")

        try:
            animation_set = load_animation_set(sheet_config)
        except (pygame.error, OSError) as exc:
            self._warn(f"Could not load animation '{key}': {exc}")
            self.images[key] = None
            self.animations[key] = None
            return None

        if animation_set is None:
            self._warn(f"Animation '{key}' did not produce any frames.")

        self.images[key] = animation_set
        self.animations[key] = animation_set
        return animation_set

    def load_sound(self, key, path):
        if key in self.sounds:
            return self.sounds[key]

        if not path:
            self._warn(f"No path provided for sound '{key}'.")
            self.sounds[key] = None
            return None

        if not os.path.exists(path):
            self._warn(f"Missing sound file for '{key}': {path}")
            self.sounds[key] = None
            return None

        if path in self._sound_path_cache:
            self.sounds[key] = self._sound_path_cache[path]
            return self.sounds[key]

        try:
            sound = pygame.mixer.Sound(path)
        except (pygame.error, OSError) as exc:
            self._warn(f"Could not load sound '{key}': {exc}")
            self.sounds[key] = None
            return None

        self.sounds[key] = sound
        self._sound_path_cache[path] = sound
        return sound

    def get_image(self, key):
        return self.images.get(key)

    def get_animation(self, key):
        return self.animations.get(key, self.images.get(key))

    def required_assets_requested(self, image_keys=None, animation_keys=None, sound_keys=None):
        """True once required keys have been loaded or warned as missing."""
        image_keys = image_keys or ()
        animation_keys = animation_keys or ()
        sound_keys = sound_keys or ()
        return (
            all(key in self.images for key in image_keys)
            and all(key in self.animations for key in animation_keys)
            and all(key in self.sounds for key in sound_keys)
        )

    def _nested_animation_sheet_paths(self, sheet_config):
        for animation_config in sheet_config.get("animations", {}).values():
            nested_sheet = animation_config.get("sheet")
            if nested_sheet:
                yield nested_sheet.get("path")

    def _remove_near_white_pixels(self, image, min_value=225, max_channel_spread=36):
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
        return image

    def _remove_edge_connected_light_pixels(self, image, min_value=225, max_channel_spread=36):
        width = image.get_width()
        height = image.get_height()

        def is_background(color):
            brightest = max(color.r, color.g, color.b)
            darkest = min(color.r, color.g, color.b)
            return darkest >= min_value and brightest - darkest <= max_channel_spread

        edge_pixels = []
        for x in range(width):
            edge_pixels.append((x, 0))
            edge_pixels.append((x, height - 1))
        for y in range(height):
            edge_pixels.append((0, y))
            edge_pixels.append((width - 1, y))

        visited = set()
        to_check = []
        image.lock()
        for x, y in edge_pixels:
            if (x, y) not in visited and is_background(image.get_at((x, y))):
                to_check.append((x, y))

        while to_check:
            x, y = to_check.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))

            color = image.get_at((x, y))
            if not is_background(color):
                continue

            image.set_at((x, y), (color.r, color.g, color.b, 0))
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                nx, ny = neighbor
                if 0 <= nx < width and 0 <= ny < height and neighbor not in visited:
                    to_check.append(neighbor)

        image.unlock()
        return image

    def _trim_transparent_image(self, image):
        bounds = image.get_bounding_rect(min_alpha=1)
        if bounds.width == 0 or bounds.height == 0:
            return image

        trimmed = pygame.Surface(bounds.size, pygame.SRCALPHA)
        trimmed.blit(image, (0, 0), bounds)
        return trimmed
