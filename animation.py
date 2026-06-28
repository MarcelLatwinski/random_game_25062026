import os

import pygame


_FLIPPED_SURFACE_CACHE = {}
_SHEET_FRAME_CACHE = {}


def flipped_surface(image):
    """Return a cached left-facing copy instead of flipping every frame."""
    if image is None:
        return None

    cache_key = id(image)
    flipped = _FLIPPED_SURFACE_CACHE.get(cache_key)
    if flipped is None:
        flipped = pygame.transform.flip(image, True, False)
        _FLIPPED_SURFACE_CACHE[cache_key] = flipped
    return flipped


class Animation:
    def __init__(self, frames, fps=10, loop=True, draw_offset=(0, 0)):
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.draw_offset = draw_offset
        self.current_index = 0
        self.elapsed = 0.0
        self.finished = False

    def copy(self):
        return Animation(self.frames, self.fps, self.loop, self.draw_offset)

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

    def current_draw_offset(self):
        return self.draw_offset


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

    def current_draw_offset(self):
        animation = self.current_animation()
        if animation:
            return animation.current_draw_offset()
        return (0, 0)

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

    frames_by_row = load_sheet_frames(sheet_config)
    animations = {}

    # Add more animations by adding row/frame entries in settings.SPRITE_SHEETS.
    # Animations can span rows, use frame_sequence, or provide their own
    # per-animation "sheet" config while inheriting shared visual settings.
    for name, animation_config in sheet_config["animations"].items():
        source_config = get_animation_source_config(sheet_config, animation_config)
        source_frames = frames_by_row
        if source_config is not sheet_config:
            source_frames = load_sheet_frames(source_config)
            if source_frames is None:
                continue

        frames = collect_animation_frames(source_frames, source_config, animation_config)
        animations[name] = Animation(
            frames,
            fps=animation_config.get("fps", 10),
            loop=animation_config.get("loop", True),
            draw_offset=animation_config.get(
                "draw_offset",
                sheet_config.get("draw_offset", (0, 0)),
            ),
        )

    return animations


def load_sheet_frames(sheet_config):
    path = sheet_config["path"]
    if not os.path.exists(path):
        return None

    cache_key = (
        path,
        sheet_config.get("columns"),
        sheet_config.get("rows"),
        sheet_config.get("frame_width"),
        sheet_config.get("frame_height"),
        sheet_config.get("target_size"),
        sheet_config.get("margin", 0),
        sheet_config.get("spacing", 0),
        sheet_config.get("scale", 1),
        sheet_config.get("background_min_value"),
        sheet_config.get("background_channel_spread"),
        sheet_config.get("remove_light_background", False),
        sheet_config.get("trim_transparent", False),
        sheet_config.get("align"),
        sheet_config.get("use_floor_grid", False),
        repr(sheet_config.get("keep_largest_component_rows")),
        repr(sheet_config.get("frame_rects")),
    )
    if cache_key in _SHEET_FRAME_CACHE:
        return _SHEET_FRAME_CACHE[cache_key]

    sheet = pygame.image.load(path).convert_alpha()
    frames_by_row = slice_sheet(sheet, sheet_config)
    _SHEET_FRAME_CACHE[cache_key] = frames_by_row
    return frames_by_row


def get_animation_source_config(sheet_config, animation_config):
    animation_sheet = animation_config.get("sheet")
    if not animation_sheet:
        return sheet_config

    inherited_keys = (
        "target_size",
        "remove_light_background",
        "background_min_value",
        "background_channel_spread",
        "trim_transparent",
        "align",
        "draw_offset",
        "use_floor_grid",
    )
    source_config = {
        key: sheet_config[key]
        for key in inherited_keys
        if key in sheet_config
    }
    source_config.update(
        {
            "path": animation_sheet["path"],
            "columns": animation_sheet["columns"],
            "rows": animation_sheet.get("rows", 1),
            "frame_width": animation_sheet.get("frame_width"),
            "frame_height": animation_sheet.get("frame_height"),
            "margin": animation_sheet.get("margin", 0),
            "spacing": animation_sheet.get("spacing", 0),
            "scale": animation_sheet.get("scale", sheet_config.get("scale", 1)),
        }
    )
    if "frame_rects" in animation_sheet:
        source_config["frame_rects"] = animation_sheet["frame_rects"]
    return source_config


def collect_animation_frames(frames_by_row, sheet_config, animation_config):
    frame_sequence = animation_config.get("frame_sequence")
    if frame_sequence is not None:
        return [
            frames_by_row[row][column]
            for row, column in frame_sequence
        ]

    frame_numbers = animation_config.get("frames")
    if frame_numbers is None:
        frame_numbers = range(sheet_config["columns"])

    rows = animation_config.get("rows")
    if rows is not None:
        return [
            frames_by_row[row][column]
            for row in rows
            for column in frame_numbers
        ]

    row = animation_config["row"]
    return [frames_by_row[row][column] for column in frame_numbers]


def slice_sheet(sheet, sheet_config):
    columns = sheet_config["columns"]
    rows = sheet_config["rows"]
    frame_rects = build_frame_rects(sheet, sheet_config)

    frames_by_row = []
    for row in range(rows):
        frames = []
        for column in range(columns):
            source_rect = frame_rects[row][column]
            frame = pygame.Surface(source_rect.size, pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), source_rect)

            if sheet_config.get("remove_light_background", False):
                remove_light_background(frame, sheet_config)

            if should_keep_largest_component(sheet_config, row):
                keep_largest_opaque_component(frame)

            if sheet_config.get("trim_transparent", False):
                frame = trim_and_scale_frame(frame, sheet_config)
            else:
                frame = scale_frame(frame, sheet_config)

            frames.append(frame)
        frames_by_row.append(frames)

    return frames_by_row


def build_frame_rects(sheet, sheet_config):
    columns = sheet_config["columns"]
    rows = sheet_config["rows"]
    configured_rects = sheet_config.get("frame_rects")

    if configured_rects:
        return [
            [
                pygame.Rect(configured_rects[row][column])
                for column in range(columns)
            ]
            for row in range(rows)
        ]

    margin = sheet_config.get("margin", 0)
    spacing = sheet_config.get("spacing", 0)
    explicit_width = sheet_config.get("frame_width")
    explicit_height = sheet_config.get("frame_height")

    if explicit_width and explicit_height:
        return [
            [
                pygame.Rect(
                    margin + column * (explicit_width + spacing),
                    margin + row * (explicit_height + spacing),
                    explicit_width,
                    explicit_height,
                )
                for column in range(columns)
            ]
            for row in range(rows)
        ]

    if sheet_config.get("use_floor_grid", False):
        available_width = sheet.get_width() - margin * 2 - spacing * (columns - 1)
        available_height = sheet.get_height() - margin * 2 - spacing * (rows - 1)
        frame_width = available_width // columns
        frame_height = available_height // rows
        return [
            [
                pygame.Rect(
                    margin + column * (frame_width + spacing),
                    margin + row * (frame_height + spacing),
                    frame_width,
                    frame_height,
                )
                for column in range(columns)
            ]
            for row in range(rows)
        ]

    available_width = sheet.get_width() - margin * 2 - spacing * (columns - 1)
    available_height = sheet.get_height() - margin * 2 - spacing * (rows - 1)
    x_edges = [round(index * available_width / columns) for index in range(columns + 1)]
    y_edges = [round(index * available_height / rows) for index in range(rows + 1)]

    return [
        [
            pygame.Rect(
                margin + x_edges[column] + column * spacing,
                margin + y_edges[row] + row * spacing,
                x_edges[column + 1] - x_edges[column],
                y_edges[row + 1] - y_edges[row],
            )
            for column in range(columns)
        ]
        for row in range(rows)
    ]


def scale_frame(frame, sheet_config):
    target_size = sheet_config.get("target_size")
    scale = sheet_config.get("scale", 1)

    if target_size:
        return pygame.transform.scale(frame, target_size)
    if scale != 1:
        scaled_size = (
            int(round(frame.get_width() * scale)),
            int(round(frame.get_height() * scale)),
        )
        return pygame.transform.scale(frame, scaled_size)
    return frame


def should_keep_largest_component(sheet_config, row):
    rows = sheet_config.get("keep_largest_component_rows")
    return rows is not None and row in rows


def keep_largest_opaque_component(surface):
    width = surface.get_width()
    height = surface.get_height()
    visited = set()
    largest_component = []
    opaque_pixels = []

    surface.lock()
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            if surface.get_at((x, y)).a <= 0:
                continue

            component = []
            to_check = [(x, y)]
            visited.add((x, y))
            while to_check:
                px, py = to_check.pop()
                component.append((px, py))
                for neighbor in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    nx, ny = neighbor
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    if neighbor in visited:
                        continue
                    if surface.get_at((nx, ny)).a <= 0:
                        continue
                    visited.add(neighbor)
                    to_check.append(neighbor)

            opaque_pixels.extend(component)
            if len(component) > len(largest_component):
                largest_component = component

    keep_pixels = set(largest_component)
    for pixel in opaque_pixels:
        if pixel in keep_pixels:
            continue
        x, y = pixel
        color = surface.get_at((x, y))
        surface.set_at((x, y), (color.r, color.g, color.b, 0))
    surface.unlock()


def trim_and_scale_frame(frame, sheet_config):
    bounds = get_opaque_bounds(frame)
    if bounds is None:
        return scale_frame(frame, sheet_config)

    trimmed = pygame.Surface(bounds.size, pygame.SRCALPHA)
    trimmed.blit(frame, (0, 0), bounds)

    target_size = sheet_config.get("target_size")
    if not target_size:
        return trimmed

    target_width, target_height = target_size
    scale = min(target_width / trimmed.get_width(), target_height / trimmed.get_height())
    scaled_size = (
        max(1, int(round(trimmed.get_width() * scale))),
        max(1, int(round(trimmed.get_height() * scale))),
    )
    trimmed = pygame.transform.scale(trimmed, scaled_size)

    canvas = pygame.Surface(target_size, pygame.SRCALPHA)
    align = sheet_config.get("align", "bottom")
    x = (target_width - trimmed.get_width()) // 2
    y = target_height - trimmed.get_height() if align == "bottom" else (target_height - trimmed.get_height()) // 2
    canvas.blit(trimmed, (x, y))
    return canvas


def get_opaque_bounds(surface):
    bounds = surface.get_bounding_rect(min_alpha=1)
    if bounds.width == 0 or bounds.height == 0:
        return None
    return bounds


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
