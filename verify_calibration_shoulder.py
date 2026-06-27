#!/usr/bin/env python3
"""Visualize the calibration shoulder position on the raw sprite sheet frame"""

import pygame
from player import BODY_SHOULDER_OFFSET_RATIO, ARM_PIVOT_RATIO

pygame.init()
screen = pygame.display.set_mode((1024, 800))
pygame.display.set_caption("Calibration Shoulder Verification")
clock = pygame.time.Clock()

# Load raw frame
body_sheet = pygame.image.load("assets/images/processed/new_player_sheet_noarms.png")
frame_w = body_sheet.get_width() // 4
frame_h = body_sheet.get_height() // 4
raw_frame = body_sheet.subsurface((0, 0, frame_w, frame_h)).copy()

# Load calibration
import json
from pathlib import Path
config_path = Path("assets/images/player_aim_config.json")
with open(config_path) as f:
    calib = json.load(f)

calib_shoulder_pixels = (calib["body_shoulder_offset"][0], calib["body_shoulder_offset"][1])
calib_frame_size = (calib["frame_width"], calib["frame_height"])

print(f"Raw frame size: ({frame_w}, {frame_h})")
print(f"Calibration expects frame size: {calib_frame_size}")
print(f"Calibration shoulder in pixels: {calib_shoulder_pixels}")
print(f"Actual shoulder from settings ratio: ({frame_w * BODY_SHOULDER_OFFSET_RATIO.x:.1f}, {frame_h * BODY_SHOULDER_OFFSET_RATIO.y:.1f})")

running = True
while running:
    dt = clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    
    screen.fill((20, 20, 30))
    
    # Scale and display the raw frame
    scale = 2
    scaled_frame = pygame.transform.scale(raw_frame, (frame_w * scale, frame_h * scale))
    screen.blit(scaled_frame, (20, 20))
    
    # Draw crosshair grid
    for x in range(0, frame_w * scale, 50):
        pygame.draw.line(screen, (60, 60, 60), (20 + x, 20), (20 + x, 20 + frame_h * scale), 1)
    for y in range(0, frame_h * scale, 50):
        pygame.draw.line(screen, (60, 60, 60), (20, 20 + y), (20 + frame_w * scale, 20 + y), 1)
    
    # Draw calibration shoulder marker
    shoulder_screen_x = 20 + int(calib_shoulder_pixels[0] * scale)
    shoulder_screen_y = 20 + int(calib_shoulder_pixels[1] * scale)
    pygame.draw.circle(screen, (255, 50, 50), (shoulder_screen_x, shoulder_screen_y), 12)
    pygame.draw.circle(screen, (100, 200, 100), (shoulder_screen_x, shoulder_screen_y), 8)
    
    # Info
    font = pygame.font.SysFont("monospace", 16)
    info_texts = [
        "CALIBRATION SHOULDER POSITION",
        f"Frame: {frame_w}×{frame_h} (expected: {calib_frame_size[0]}×{calib_frame_size[1]})",
        f"Shoulder: ({calib_shoulder_pixels[0]:.0f}, {calib_shoulder_pixels[1]:.0f}) pixels",
        f"Ratio: ({calib_shoulder_pixels[0]/calib_frame_size[0]:.4f}, {calib_shoulder_pixels[1]/calib_frame_size[1]:.4f})",
        "",
        "SCALED TO 114×114 GAME SPRITE:",
        f"Shoulder: ({114 * calib_shoulder_pixels[0]/calib_frame_size[0]:.1f}, {114 * calib_shoulder_pixels[1]/calib_frame_size[1]:.1f})",
        "",
        "RED circle = calibration shoulder position",
        "GREEN circle = inner marker"
    ]
    
    for i, text in enumerate(info_texts):
        surf = font.render(text, True, (200, 200, 200))
        screen.blit(surf, (20 + frame_w * scale + 40, 20 + i * 22))
    
    pygame.display.flip()

pygame.quit()
