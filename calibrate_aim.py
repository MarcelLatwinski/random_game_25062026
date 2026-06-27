"""
Per-frame shoulder and arm-pivot calibration tool.

Controls:
- [ and ]: cycle body frames 0-11
- Arrow keys: move the selected frame's body shoulder point
- Shift + arrow keys: move body shoulder faster
- W/A/D/X: move the arm pivot inside player_arms.png
- Shift + W/A/D/X: move arm pivot faster
- Left click on the body panel: set the selected frame's body shoulder
- Right click on the arms panel: set the arm pivot
- S: save assets/images/player_aim_config.json
- P: export debug/player_aim_calibration.png
- Esc: quit
"""

import json
import math
from pathlib import Path
import sys

import pygame

sys.path.insert(0, str(Path(__file__).parent))
from settings import PLAYER_HEIGHT, PLAYER_WIDTH


pygame.init()

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 950
FPS = 60

CONFIG_PATH = Path("assets/images/player_aim_config.json")
BODY_SHEET_PATH = Path("assets/images/processed/new_player_sheet_noarms.png")
ARMS_PATH = Path("assets/images/processed/player_arms.png")
RAW_BODY_SHEET_PATH = Path("assets/images/new_player_sheet_noarms.png")
RAW_ARMS_PATH = Path("assets/images/player_arms.png")

if not BODY_SHEET_PATH.exists():
    BODY_SHEET_PATH = RAW_BODY_SHEET_PATH
if not ARMS_PATH.exists():
    ARMS_PATH = RAW_ARMS_PATH

AIM_BODY_FRAME_COUNT = 12
DEFAULT_BODY_SHOULDER_RATIO = pygame.math.Vector2(0.44, 0.40)
DEFAULT_ARM_PIVOT_RATIO = pygame.math.Vector2(0.08, 0.50)
ARM_DRAW_WIDTH_RATIO = 0.49

BODY_PANEL_POS = pygame.math.Vector2(50, 80)
ARMS_PANEL_POS = pygame.math.Vector2(1010, 80)
PREVIEW_BODY_POS = pygame.math.Vector2(970, 560)
BODY_ZOOM = 2.25
ARMS_ZOOM = 0.36
PREVIEW_SCALE = 3.0

RED = (255, 55, 55)
LIGHT_RED = (255, 160, 160)
BLUE = (70, 145, 255)
LIGHT_BLUE = (160, 210, 255)
GREEN = (80, 240, 145)
TEXT = (230, 230, 230)
MUTED = (160, 165, 170)
PANEL = (28, 31, 34)
BG = (18, 20, 22)


def vector_from_sequence(value, fallback):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return pygame.math.Vector2(fallback)
    try:
        return pygame.math.Vector2(float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return pygame.math.Vector2(fallback)


def load_body_frame(sheet, frame_index, frame_width, frame_height):
    row = frame_index // 4
    col = frame_index % 4
    frame_rect = pygame.Rect(
        col * frame_width,
        row * frame_height,
        frame_width,
        frame_height,
    )
    return sheet.subsurface(frame_rect).copy()


def default_body_offsets(frame_width, frame_height):
    fallback = pygame.math.Vector2(
        DEFAULT_BODY_SHOULDER_RATIO.x * frame_width,
        DEFAULT_BODY_SHOULDER_RATIO.y * frame_height,
    )
    return {
        frame_index: pygame.math.Vector2(fallback)
        for frame_index in range(AIM_BODY_FRAME_COUNT)
    }


def load_config(frame_width, frame_height, arms_width, arms_height):
    body_offsets = default_body_offsets(frame_width, frame_height)
    arm_pivot = pygame.math.Vector2(
        DEFAULT_ARM_PIVOT_RATIO.x * arms_width,
        DEFAULT_ARM_PIVOT_RATIO.y * arms_height,
    )

    if not CONFIG_PATH.exists():
        return body_offsets, arm_pivot

    try:
        with open(CONFIG_PATH) as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[CONFIG] Could not load {CONFIG_PATH}: {exc}")
        return body_offsets, arm_pivot

    saved_frame_width = float(config.get("frame_width", frame_width) or frame_width)
    saved_frame_height = float(config.get("frame_height", frame_height) or frame_height)
    saved_arms_width = float(config.get("arms_width", arms_width) or arms_width)
    saved_arms_height = float(config.get("arms_height", arms_height) or arms_height)

    single_shoulder = vector_from_sequence(
        config.get("body_shoulder_offset"),
        pygame.math.Vector2(
            DEFAULT_BODY_SHOULDER_RATIO.x * saved_frame_width,
            DEFAULT_BODY_SHOULDER_RATIO.y * saved_frame_height,
        ),
    )
    saved_offsets = config.get("body_shoulder_offsets")
    for frame_index in range(AIM_BODY_FRAME_COUNT):
        frame_key = str(frame_index)
        if isinstance(saved_offsets, dict) and frame_key in saved_offsets:
            saved_value = vector_from_sequence(saved_offsets[frame_key], single_shoulder)
        else:
            saved_value = pygame.math.Vector2(single_shoulder)
        body_offsets[frame_index] = pygame.math.Vector2(
            saved_value.x * frame_width / saved_frame_width if saved_frame_width else saved_value.x,
            saved_value.y * frame_height / saved_frame_height if saved_frame_height else saved_value.y,
        )

    saved_arm_pivot = vector_from_sequence(
        config.get("arm_pivot"),
        pygame.math.Vector2(
            DEFAULT_ARM_PIVOT_RATIO.x * saved_arms_width,
            DEFAULT_ARM_PIVOT_RATIO.y * saved_arms_height,
        ),
    )
    arm_pivot = pygame.math.Vector2(
        saved_arm_pivot.x * arms_width / saved_arms_width if saved_arms_width else saved_arm_pivot.x,
        saved_arm_pivot.y * arms_height / saved_arms_height if saved_arms_height else saved_arm_pivot.y,
    )

    print(f"[CONFIG] Loaded {CONFIG_PATH}")
    return body_offsets, arm_pivot


def save_config(body_offsets, arm_pivot, frame_width, frame_height, arms_width, arms_height):
    body_shoulder_offsets = {
        str(frame_index): [
            round(body_offsets[frame_index].x, 2),
            round(body_offsets[frame_index].y, 2),
        ]
        for frame_index in range(AIM_BODY_FRAME_COUNT)
    }
    config = {
        "arm_pivot": [round(arm_pivot.x, 2), round(arm_pivot.y, 2)],
        "body_shoulder_offsets": body_shoulder_offsets,
        "body_shoulder_offset": body_shoulder_offsets["0"],
        "frame_width": frame_width,
        "frame_height": frame_height,
        "arms_width": arms_width,
        "arms_height": arms_height,
        "notes": "Pixel coordinates: body offsets are per-frame in body sheet frame space; arm_pivot is local to the unrotated full player_arms image.",
    }
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")
    print(f"[SAVE] Calibration saved to {CONFIG_PATH}")


def draw_cross(surface, position, color, radius=14, width=3):
    x = round(position.x)
    y = round(position.y)
    pygame.draw.line(surface, color, (x - radius, y), (x + radius, y), width)
    pygame.draw.line(surface, color, (x, y - radius), (x, y + radius), width)
    pygame.draw.circle(surface, color, (x, y), max(3, width + 1))


def draw_checker(surface, rect, cell=24):
    light = (58, 61, 64)
    dark = (45, 48, 51)
    for y in range(rect.top, rect.bottom, cell):
        for x in range(rect.left, rect.right, cell):
            color = light if ((x - rect.left) // cell + (y - rect.top) // cell) % 2 == 0 else dark
            pygame.draw.rect(surface, color, (x, y, cell, cell))


def scale_point(point, source_size, target_size):
    source_width, source_height = source_size
    target_width, target_height = target_size
    return pygame.math.Vector2(
        point.x * target_width / source_width if source_width else point.x,
        point.y * target_height / source_height if source_height else point.y,
    )


def scaled_arms_size(arms_image, target_player_width):
    opaque_bounds = arms_image.get_bounding_rect(min_alpha=1)
    source_visible_width = opaque_bounds.width or arms_image.get_width()
    target_visible_width = max(1, target_player_width * ARM_DRAW_WIDTH_RATIO)
    scale = target_visible_width / source_visible_width
    return (
        max(1, round(arms_image.get_width() * scale)),
        max(1, round(arms_image.get_height() * scale)),
    )


def rotate_around_pivot(image, angle_degrees, image_pivot, target_pivot):
    rotated_image = pygame.transform.rotate(image, -angle_degrees)
    image_rect = image.get_rect()
    image_center = pygame.math.Vector2(image_rect.center)
    pivot_offset = image_pivot - image_center
    rotated_pivot_offset = pivot_offset.rotate(angle_degrees)
    rotated_rect = rotated_image.get_rect(center=target_pivot - rotated_pivot_offset)
    computed_pivot = pygame.math.Vector2(rotated_rect.center) + rotated_pivot_offset
    return rotated_image, rotated_rect, computed_pivot


def render_calibration_view(
    surface,
    fonts,
    body_sheet,
    arms_image,
    body_offsets,
    arm_pivot,
    frame_index,
    mouse_pos,
):
    font, font_small = fonts
    surface.fill(BG)

    sheet_width, sheet_height = body_sheet.get_size()
    frame_width = sheet_width // 4
    frame_height = sheet_height // 4
    body_frame = load_body_frame(body_sheet, frame_index, frame_width, frame_height)

    body_display_size = (
        round(frame_width * BODY_ZOOM),
        round(frame_height * BODY_ZOOM),
    )
    arms_display_size = (
        round(arms_image.get_width() * ARMS_ZOOM),
        round(arms_image.get_height() * ARMS_ZOOM),
    )
    preview_body_size = (
        round(PLAYER_WIDTH * PREVIEW_SCALE),
        round(PLAYER_HEIGHT * PREVIEW_SCALE),
    )
    preview_arms_size = scaled_arms_size(
        arms_image,
        PLAYER_WIDTH * PREVIEW_SCALE,
    )

    body_rect = pygame.Rect(BODY_PANEL_POS, body_display_size)
    arms_rect = pygame.Rect(ARMS_PANEL_POS, arms_display_size)
    preview_body_rect = pygame.Rect(PREVIEW_BODY_POS, preview_body_size)

    pygame.draw.rect(surface, PANEL, body_rect.inflate(24, 24), border_radius=6)
    pygame.draw.rect(surface, PANEL, arms_rect.inflate(24, 24), border_radius=6)
    pygame.draw.rect(surface, PANEL, preview_body_rect.inflate(260, 120), border_radius=6)

    scaled_body = pygame.transform.scale(body_frame, body_display_size)
    surface.blit(scaled_body, body_rect)
    shoulder = body_offsets[frame_index]
    body_shoulder_screen = BODY_PANEL_POS + scale_point(
        shoulder,
        (frame_width, frame_height),
        body_display_size,
    )
    draw_cross(surface, body_shoulder_screen, RED)

    scaled_arms = pygame.transform.smoothscale(arms_image, arms_display_size)
    draw_checker(surface, arms_rect, cell=18)
    surface.blit(scaled_arms, arms_rect)
    arm_pivot_screen = ARMS_PANEL_POS + scale_point(
        arm_pivot,
        arms_image.get_size(),
        arms_display_size,
    )
    draw_cross(surface, arm_pivot_screen, BLUE)

    preview_body = pygame.transform.scale(body_frame, preview_body_size)
    preview_arms = pygame.transform.smoothscale(arms_image, preview_arms_size)
    preview_shoulder = PREVIEW_BODY_POS + scale_point(
        shoulder,
        (frame_width, frame_height),
        preview_body_size,
    )
    preview_arm_pivot = scale_point(
        arm_pivot,
        arms_image.get_size(),
        preview_arms_size,
    )
    aim_vector = pygame.math.Vector2(mouse_pos) - preview_shoulder
    angle = 0
    if aim_vector.length_squared() > 0:
        angle = math.degrees(math.atan2(aim_vector.y, aim_vector.x))

    surface.blit(preview_body, preview_body_rect)
    rotated_arms, rotated_rect, computed_pivot = rotate_around_pivot(
        preview_arms,
        angle,
        preview_arm_pivot,
        preview_shoulder,
    )
    surface.blit(rotated_arms, rotated_rect)
    draw_cross(surface, preview_shoulder, RED, radius=15)
    draw_cross(surface, computed_pivot, GREEN, radius=8, width=2)

    labels = [
        ("Body frame", BODY_PANEL_POS.x, BODY_PANEL_POS.y - 34),
        ("Arms image", ARMS_PANEL_POS.x, ARMS_PANEL_POS.y - 34),
        ("Runtime preview", PREVIEW_BODY_POS.x - 120, PREVIEW_BODY_POS.y - 78),
    ]
    for text, x, y in labels:
        surface.blit(font.render(text, True, TEXT), (x, y))

    info_lines = [
        f"Frame {frame_index}: shoulder ({shoulder.x:.1f}, {shoulder.y:.1f})",
        f"Arm pivot: ({arm_pivot.x:.1f}, {arm_pivot.y:.1f})",
        f"Angle: {angle:.1f} deg",
        "[] frame  |  arrows shoulder  |  W/A/D/X arm pivot",
        "Shift moves 5 px  |  S save  |  P export PNG",
        "Left-click body sets shoulder. Right-click arms sets pivot.",
    ]
    info_x = 50
    info_y = SCREEN_HEIGHT - 165
    for index, line in enumerate(info_lines):
        color = TEXT if index < 3 else MUTED
        surface.blit(font_small.render(line, True, color), (info_x, info_y + index * 24))

    return {
        "body_rect": body_rect,
        "arms_rect": arms_rect,
        "frame_width": frame_width,
        "frame_height": frame_height,
    }


def export_debug_png(
    fonts,
    body_sheet,
    arms_image,
    body_offsets,
    arm_pivot,
    frame_index,
    mouse_pos,
):
    debug_dir = Path("debug")
    debug_dir.mkdir(exist_ok=True)
    output_path = debug_dir / "player_aim_calibration.png"
    debug_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    render_calibration_view(
        debug_surface,
        fonts,
        body_sheet,
        arms_image,
        body_offsets,
        arm_pivot,
        frame_index,
        mouse_pos,
    )
    pygame.image.save(debug_surface, output_path)
    print(f"[EXPORT] Debug PNG saved to {output_path}")


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Player Aim Calibration")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 24, bold=True)
    font_small = pygame.font.SysFont("Consolas", 18)
    fonts = (font, font_small)

    print("[LOAD] Loading calibration assets")
    print(f"[LOAD] Body sheet: {BODY_SHEET_PATH}")
    print(f"[LOAD] Arms image: {ARMS_PATH}")
    body_sheet = pygame.image.load(BODY_SHEET_PATH).convert_alpha()
    arms_image = pygame.image.load(ARMS_PATH).convert_alpha()

    sheet_width, sheet_height = body_sheet.get_size()
    frame_width = sheet_width // 4
    frame_height = sheet_height // 4
    body_offsets, arm_pivot = load_config(
        frame_width,
        frame_height,
        arms_image.get_width(),
        arms_image.get_height(),
    )

    frame_index = 0
    running = True
    layout = {}

    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()
        step = 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFTBRACKET:
                    frame_index = (frame_index - 1) % AIM_BODY_FRAME_COUNT
                    print(f"[FRAME] {frame_index}")
                elif event.key == pygame.K_RIGHTBRACKET:
                    frame_index = (frame_index + 1) % AIM_BODY_FRAME_COUNT
                    print(f"[FRAME] {frame_index}")
                elif event.key == pygame.K_LEFT:
                    body_offsets[frame_index].x -= step
                elif event.key == pygame.K_RIGHT:
                    body_offsets[frame_index].x += step
                elif event.key == pygame.K_UP:
                    body_offsets[frame_index].y -= step
                elif event.key == pygame.K_DOWN:
                    body_offsets[frame_index].y += step
                elif event.key == pygame.K_a:
                    arm_pivot.x -= step
                elif event.key == pygame.K_d:
                    arm_pivot.x += step
                elif event.key == pygame.K_w:
                    arm_pivot.y -= step
                elif event.key == pygame.K_x:
                    arm_pivot.y += step
                elif event.key == pygame.K_s:
                    save_config(
                        body_offsets,
                        arm_pivot,
                        frame_width,
                        frame_height,
                        arms_image.get_width(),
                        arms_image.get_height(),
                    )
                elif event.key == pygame.K_p:
                    export_debug_png(
                        fonts,
                        body_sheet,
                        arms_image,
                        body_offsets,
                        arm_pivot,
                        frame_index,
                        mouse_pos,
                    )
            elif event.type == pygame.KEYUP:
                pass
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and layout.get("body_rect") and layout["body_rect"].collidepoint(event.pos):
                    local = pygame.math.Vector2(event.pos) - BODY_PANEL_POS
                    body_offsets[frame_index] = scale_point(
                        local,
                        layout["body_rect"].size,
                        (frame_width, frame_height),
                    )
                elif event.button == 3 and layout.get("arms_rect") and layout["arms_rect"].collidepoint(event.pos):
                    local = pygame.math.Vector2(event.pos) - ARMS_PANEL_POS
                    arm_pivot = scale_point(
                        local,
                        layout["arms_rect"].size,
                        arms_image.get_size(),
                    )

        layout = render_calibration_view(
            screen,
            fonts,
            body_sheet,
            arms_image,
            body_offsets,
            arm_pivot,
            frame_index,
            mouse_pos,
        )
        pygame.display.flip()

    pygame.quit()
    print("[EXIT] Calibration tool closed")


if __name__ == "__main__":
    main()
