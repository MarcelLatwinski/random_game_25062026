from collections import deque
import argparse
from pathlib import Path
import sys

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from settings import (
    BACKGROUND_CUTOUT_KEYS,
    FLOOR_ASSET_KEY,
    IMAGE_PATHS,
    IMAGE_EXTENSIONS,
    PLATFORM_KEYS,
    SPRITE_SHEETS,
)


OUTPUT_DIR = Path("assets/images/processed")
SOURCE_ENVIRONMENT_DIRS = (
    Path("assets/images/background_platforms"),
    Path("assets/images"),
)

try:
    import numpy as np
except ImportError:
    np = None

try:
    import cv2
except ImportError:
    cv2 = None


def is_near_white(color, min_value, max_channel_spread):
    r, g, b = color[:3]
    brightest = max(r, g, b)
    darkest = min(r, g, b)
    return darkest >= min_value and brightest - darkest <= max_channel_spread


def process_global_transparency(source_path, min_value, max_channel_spread):
    image = Image.open(source_path).convert("RGBA")
    if np is not None:
        data = np.array(image)
        rgb = data[:, :, :3]
        alpha = data[:, :, 3]
        brightest = rgb.max(axis=2)
        darkest = rgb.min(axis=2)
        mask = (
            (alpha > 0)
            & (darkest >= min_value)
            & ((brightest - darkest) <= max_channel_spread)
        )
        data[mask, 3] = 0
        return Image.fromarray(data, "RGBA")

    pixels = image.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            color = pixels[x, y]
            if color[3] and is_near_white(color, min_value, max_channel_spread):
                pixels[x, y] = (color[0], color[1], color[2], 0)

    return image


def transparent_neighbor_mask(alpha):
    transparent = alpha == 0
    neighbor = np.zeros_like(transparent, dtype=bool)

    neighbor[1:, :] |= transparent[:-1, :]
    neighbor[:-1, :] |= transparent[1:, :]
    neighbor[:, 1:] |= transparent[:, :-1]
    neighbor[:, :-1] |= transparent[:, 1:]
    neighbor[1:, 1:] |= transparent[:-1, :-1]
    neighbor[:-1, :-1] |= transparent[1:, 1:]
    neighbor[1:, :-1] |= transparent[:-1, 1:]
    neighbor[:-1, 1:] |= transparent[1:, :-1]
    return neighbor


def is_halo_color(color, min_value, max_channel_spread):
    r, g, b = color[:3]
    brightest = max(r, g, b)
    darkest = min(r, g, b)
    spread = brightest - darkest
    return (
        (darkest >= min_value - 18 and spread <= max_channel_spread + 24)
        or (brightest >= min_value + 15 and darkest >= min_value - 55 and spread <= max_channel_spread + 55)
    )


def remove_light_halo_pixels(image, min_value, max_channel_spread, passes=1):
    """Remove the white matte fringe left after fake-background transparency.

    The source environment art is exported on a white/checkerboard background.
    Once those background pixels are made transparent, a one-pixel pale outline
    can remain where the artwork was anti-aliased against white. This pass only
    removes light pixels that directly touch transparency, so interior highlights
    and clouds in full background art are left alone.
    """
    if np is not None:
        data = np.array(image)
        rgb = data[:, :, :3].astype(np.int16)
        brightest = rgb.max(axis=2)
        darkest = rgb.min(axis=2)
        spread = brightest - darkest

        for _ in range(passes):
            alpha = data[:, :, 3]
            neighbor = transparent_neighbor_mask(alpha)
            halo = (
                (alpha > 0)
                & neighbor
                & (
                    ((darkest >= min_value - 18) & (spread <= max_channel_spread + 24))
                    | (
                        (brightest >= min_value + 15)
                        & (darkest >= min_value - 55)
                        & (spread <= max_channel_spread + 55)
                    )
                )
            )
            if not halo.any():
                break
            data[halo, 3] = 0

        return Image.fromarray(data, "RGBA")

    pixels = image.load()
    width, height = image.size

    for _ in range(passes):
        to_clear = []
        for y in range(height):
            for x in range(width):
                color = pixels[x, y]
                if not color[3] or not is_halo_color(color, min_value, max_channel_spread):
                    continue

                for nx in range(max(0, x - 1), min(width, x + 2)):
                    for ny in range(max(0, y - 1), min(height, y + 2)):
                        if nx == x and ny == y:
                            continue
                        if pixels[nx, ny][3] == 0:
                            to_clear.append((x, y, color))
                            break
                    else:
                        continue
                    break

        if not to_clear:
            break

        for x, y, color in to_clear:
            pixels[x, y] = (color[0], color[1], color[2], 0)

    return image


def clean_rect_from_edges(image, rect, min_value, max_channel_spread):
    left, top, width, height = rect
    if width <= 0 or height <= 0:
        return

    pixels = image.load()
    visited = bytearray(width * height)
    to_check = deque()

    def local_index(x, y):
        return (y - top) * width + (x - left)

    def queue_if_background(x, y):
        index = local_index(x, y)
        if visited[index]:
            return
        color = pixels[x, y]
        if color[3] and is_near_white(color, min_value, max_channel_spread):
            to_check.append((x, y))

    right = left + width - 1
    bottom = top + height - 1
    for x in range(left, right + 1):
        queue_if_background(x, top)
        queue_if_background(x, bottom)
    for y in range(top, bottom + 1):
        queue_if_background(left, y)
        queue_if_background(right, y)

    while to_check:
        x, y = to_check.pop()
        index = local_index(x, y)
        if visited[index]:
            continue
        visited[index] = 1

        color = pixels[x, y]
        if not color[3] or not is_near_white(color, min_value, max_channel_spread):
            continue

        pixels[x, y] = (color[0], color[1], color[2], 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if left <= nx <= right and top <= ny <= bottom:
                next_index = local_index(nx, ny)
                if not visited[next_index]:
                    to_check.append((nx, ny))


def build_frame_rects(image_size, sheet_config):
    columns = sheet_config["columns"]
    rows = sheet_config["rows"]
    configured_rects = sheet_config.get("frame_rects")

    if configured_rects:
        return [
            [
                tuple(configured_rects[row][column])
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
                (
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
        image_width, image_height = image_size
        available_width = image_width - margin * 2 - spacing * (columns - 1)
        available_height = image_height - margin * 2 - spacing * (rows - 1)
        frame_width = available_width // columns
        frame_height = available_height // rows
        return [
            [
                (
                    margin + column * (frame_width + spacing),
                    margin + row * (frame_height + spacing),
                    frame_width,
                    frame_height,
                )
                for column in range(columns)
            ]
            for row in range(rows)
        ]

    image_width, image_height = image_size
    available_width = image_width - margin * 2 - spacing * (columns - 1)
    available_height = image_height - margin * 2 - spacing * (rows - 1)
    x_edges = [round(index * available_width / columns) for index in range(columns + 1)]
    y_edges = [round(index * available_height / rows) for index in range(rows + 1)]

    return [
        [
            (
                margin + x_edges[column] + column * spacing,
                margin + y_edges[row] + row * spacing,
                x_edges[column + 1] - x_edges[column],
                y_edges[row + 1] - y_edges[row],
            )
            for column in range(columns)
        ]
        for row in range(rows)
    ]


def nested_animation_source_config(sheet_config, animation_config):
    animation_sheet = animation_config.get("sheet")
    if not animation_sheet:
        return None

    inherited_keys = (
        "remove_light_background",
        "background_min_value",
        "background_channel_spread",
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
        }
    )
    if "frame_rects" in animation_sheet:
        source_config["frame_rects"] = animation_sheet["frame_rects"]
    return source_config


def sprite_sheet_jobs():
    jobs = {}
    for sheet_config in SPRITE_SHEETS.values():
        jobs[sheet_config["path"]] = sheet_config

        for animation_config in sheet_config.get("animations", {}).values():
            source_config = nested_animation_source_config(sheet_config, animation_config)
            if source_config:
                jobs[source_config["path"]] = source_config

    return jobs.values()


def process_sprite_sheet(sheet_config):
    source_path = source_source_path(sheet_config["path"])
    image = Image.open(source_path).convert("RGBA")
    rects = build_frame_rects(image.size, sheet_config)
    min_value = sheet_config.get("background_min_value", 225)
    max_channel_spread = sheet_config.get("background_channel_spread", 28)

    if np is not None and cv2 is not None:
        data = np.array(image)
        for row in rects:
            for rect in row:
                clean_rect_from_edges_array(
                    data,
                    rect,
                    min_value,
                    max_channel_spread,
                )
        return Image.fromarray(data, "RGBA")

    for row in rects:
        for rect in row:
            clean_rect_from_edges(image, rect, min_value, max_channel_spread)

    return image


def source_source_path(path):
    source_path = Path(path)
    raw_path = source_environment_path(source_path.stem)
    if raw_path:
        return Path(raw_path)
    return source_path


def clean_rect_from_edges_array(data, rect, min_value, max_channel_spread):
    left, top, width, height = rect
    if width <= 0 or height <= 0:
        return

    region = data[top:top + height, left:left + width]
    rgb = region[:, :, :3]
    alpha = region[:, :, 3]
    brightest = rgb.max(axis=2)
    darkest = rgb.min(axis=2)
    background = (
        (alpha > 0)
        & (darkest >= min_value)
        & ((brightest - darkest) <= max_channel_spread)
    )
    if not background.any():
        return

    _, labels = cv2.connectedComponents(background.astype("uint8"), connectivity=4)
    edge_labels = np.unique(
        np.concatenate(
            (
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            )
        )
    )
    edge_labels = edge_labels[edge_labels != 0]
    if edge_labels.size == 0:
        return

    region[np.isin(labels, edge_labels), 3] = 0


def save_processed(image, source_path):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / Path(source_path).name
    image.save(output_path)
    print(f"{source_path} -> {output_path}")


def process_environment_assets():
    cleanup_keys = set(BACKGROUND_CUTOUT_KEYS)
    cleanup_keys.add(FLOOR_ASSET_KEY)
    cleanup_keys.update(PLATFORM_KEYS)

    for key in sorted(cleanup_keys):
        source_path = source_environment_path(key)
        if not source_path:
            continue

        is_cutout_or_floor = key in BACKGROUND_CUTOUT_KEYS or key == FLOOR_ASSET_KEY
        min_value = 205 if is_cutout_or_floor else 225
        max_channel_spread = 46 if is_cutout_or_floor else 36
        image = process_global_transparency(
            source_path,
            min_value=min_value,
            max_channel_spread=max_channel_spread,
        )
        image = remove_light_halo_pixels(
            image,
            min_value=min_value,
            max_channel_spread=max_channel_spread,
            passes=2 if is_cutout_or_floor else 1,
        )
        save_processed(image, source_path)


def process_core_image_assets():
    arms_path = IMAGE_PATHS.get("player_arms")
    if not arms_path:
        return

    source_path = source_source_path(arms_path)
    image = Image.open(source_path).convert("RGBA")
    clean_rect_from_edges(
        image,
        (0, 0, image.width, image.height),
        min_value=185,
        max_channel_spread=52,
    )
    save_processed(image, source_path)


def source_environment_path(key):
    for directory in SOURCE_ENVIRONMENT_DIRS:
        for extension in IMAGE_EXTENSIONS:
            path = directory / f"{key}{extension}"
            if path.exists():
                return str(path)
    return None


def process_animation_assets():
    for sheet_config in sprite_sheet_jobs():
        image = process_sprite_sheet(sheet_config)
        save_processed(image, sheet_config["path"])


def main():
    parser = argparse.ArgumentParser(
        description="Build preprocessed transparent copies of large image assets."
    )
    parser.add_argument(
        "--animations",
        action="store_true",
        help="Also preprocess animation sprite sheets. Environment art is the default fast path.",
    )
    args = parser.parse_args()

    process_environment_assets()
    process_core_image_assets()
    if args.animations:
        process_animation_assets()


if __name__ == "__main__":
    main()
