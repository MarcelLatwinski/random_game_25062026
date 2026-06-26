import os

import pygame


class Animation:
    def __init__(self, frames, fps=10, loop=True):
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.current_index = 0
        self.elapsed = 0.0
        self.finished = False

    def copy(self):
        return Animation(self.frames, self.fps, self.loop)

    def reset(self):
        self.current_index = 0
        self.elapsed = 0.0
        self.finished = False

    def update(self, dt):
        if not self.frames or self.finished:
            return

        frame_time = 1 / self.fps
        self.elapsed += dt

        while self.elapsed >= frame_time:
            self.elapsed -= frame_time
            if self.current_index < len(self.frames) - 1:
                self.current_index += 1
            elif self.loop:
                self.current_index = 0
            else:
                self.finished = True
                break

    def current_frame(self):
        if not self.frames:
            return None
        return self.frames[self.current_index]


class AnimatedSprite:
    def __init__(self, animations, initial_state=None):
        self.animations = {
            name: animation.copy()
            for name, animation in (animations or {}).items()
        }
        self.current_state = initial_state or next(iter(self.animations), None)

    def has_state(self, state):
        return state in self.animations

    def play(self, state, restart=False):
        if state not in self.animations:
            return
        if self.current_state != state:
            self.current_state = state
            self.animations[state].reset()
        elif restart:
            self.animations[state].reset()

    def play_once(self, state):
        if self.current_state == state and not self.is_finished():
            return
        self.play(state, restart=True)

    def update(self, dt):
        animation = self.current_animation()
        if animation:
            animation.update(dt)

    def current_animation(self):
        if self.current_state is None:
            return None
        return self.animations.get(self.current_state)

    def current_frame(self):
        animation = self.current_animation()
        if animation:
            return animation.current_frame()
        return None

    def is_finished(self):
        animation = self.current_animation()
        return bool(animation and animation.finished)

    def is_playing_once(self):
        animation = self.current_animation()
        return bool(animation and not animation.loop and not animation.finished)


def load_animation_set(sheet_config):
    path = sheet_config["path"]
    if not os.path.exists(path):
        return None

    sheet = pygame.image.load(path).convert_alpha()
    frames_by_row = slice_sheet(sheet, sheet_config)
    animations = {}

    # Add more animations by adding a row/frame entry in settings.SPRITE_SHEETS.
    for name, animation_config in sheet_config["animations"].items():
        row = animation_config["row"]
        frame_numbers = animation_config.get("frames")
        if frame_numbers is None:
            frame_numbers = range(sheet_config["columns"])

        frames = [frames_by_row[row][column] for column in frame_numbers]
        animations[name] = Animation(
            frames,
            fps=animation_config.get("fps", 10),
            loop=animation_config.get("loop", True),
        )

    return animations


def slice_sheet(sheet, sheet_config):
    columns = sheet_config["columns"]
    rows = sheet_config["rows"]
    margin = sheet_config.get("margin", 0)
    spacing = sheet_config.get("spacing", 0)
    scale = sheet_config.get("scale", 1)
    target_size = sheet_config.get("target_size")

    frame_width = sheet_config.get("frame_width")
    if frame_width is None:
        frame_width = (sheet.get_width() - margin * 2 - spacing * (columns - 1)) // columns

    frame_height = sheet_config.get("frame_height")
    if frame_height is None:
        frame_height = (sheet.get_height() - margin * 2 - spacing * (rows - 1)) // rows

    frames_by_row = []
    for row in range(rows):
        frames = []
        for column in range(columns):
            x = margin + column * (frame_width + spacing)
            y = margin + row * (frame_height + spacing)
            source_rect = pygame.Rect(x, y, frame_width, frame_height)
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), source_rect)

            if target_size:
                frame = pygame.transform.scale(frame, target_size)
            elif scale != 1:
                scaled_size = (
                    int(round(frame_width * scale)),
                    int(round(frame_height * scale)),
                )
                frame = pygame.transform.scale(frame, scaled_size)

            if sheet_config.get("remove_light_background", False):
                remove_light_background(frame, sheet_config)

            frames.append(frame)
        frames_by_row.append(frames)

    return frames_by_row


def remove_light_background(surface, sheet_config):
    min_value = sheet_config.get("background_min_value", 225)
    max_channel_spread = sheet_config.get("background_channel_spread", 28)
    width = surface.get_width()
    height = surface.get_height()

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
    surface.lock()
    for x, y in edge_pixels:
        if (x, y) not in visited and is_background(surface.get_at((x, y))):
            to_check.append((x, y))

    while to_check:
        x, y = to_check.pop()
        if (x, y) in visited:
            continue
        visited.add((x, y))

        color = surface.get_at((x, y))
        if not is_background(color):
            continue

        surface.set_at((x, y), (color.r, color.g, color.b, 0))
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            nx, ny = neighbor
            if 0 <= nx < width and 0 <= ny < height and neighbor not in visited:
                to_check.append(neighbor)

    surface.unlock()
