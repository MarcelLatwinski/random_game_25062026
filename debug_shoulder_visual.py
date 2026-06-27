#!/usr/bin/env python3
"""
Visual diagnostic to show where the shoulder is actually positioned on the sprite.
Displays the sprite with grid overlay and current shoulder position marked.
"""

import pygame
import json
from pathlib import Path

pygame.init()

# Load config
config_path = Path("assets/images/player_aim_config.json")
with open(config_path) as f:
    config = json.load(f)

body_shoulder_pixels = config.get("body_shoulder_offset", [0, 0])
frame_width = config.get("frame_width", 313)
frame_height = config.get("frame_height", 313)

# Load sprite
sheet = pygame.image.load("assets/images/new_player_sheet_noarms.png")
frame = sheet.subsurface((0, 0, 313, 313))

# Create display: show frame scaled up with grid and shoulder marker
scale = 4
display_size = (313 * scale, 313 * scale + 100)
screen = pygame.display.set_mode(display_size)
pygame.display.set_caption("Shoulder Position Diagnostic")

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    screen.fill((40, 40, 50))
    
    # Draw scaled frame
    scaled_frame = pygame.transform.scale(frame, (313 * scale, 313 * scale))
    screen.blit(scaled_frame, (0, 0))
    
    # Draw grid
    for x in range(0, 313 * scale + 1, 50 * scale):
        pygame.draw.line(screen, (80, 80, 100), (x, 0), (x, 313 * scale), 1)
    for y in range(0, 313 * scale + 1, 50 * scale):
        pygame.draw.line(screen, (80, 80, 100), (0, y), (313 * scale, y), 1)
    
    # Draw center crosshair
    cx, cy = int(156.5 * scale), int(156.5 * scale)
    pygame.draw.line(screen, (100, 200, 100), (cx - 30, cy), (cx + 30, cy), 2)
    pygame.draw.line(screen, (100, 200, 100), (cx, cy - 30), (cx, cy + 30), 2)
    pygame.draw.circle(screen, (100, 200, 100), (cx, cy), 5)
    
    # Draw current shoulder position
    sx = int(body_shoulder_pixels[0] * scale)
    sy = int(body_shoulder_pixels[1] * scale)
    pygame.draw.circle(screen, (255, 100, 100), (sx, sy), 12)
    pygame.draw.circle(screen, (200, 50, 50), (sx, sy), 8)
    
    # Draw labels
    font = pygame.font.SysFont("monospace", 18)
    text_y = 313 * scale + 10
    
    ratio_x = body_shoulder_pixels[0] / frame_width
    ratio_y = body_shoulder_pixels[1] / frame_height
    
    label1 = font.render(f"Frame space: ({body_shoulder_pixels[0]:.1f}, {body_shoulder_pixels[1]:.1f})", True, (255, 255, 255))
    label2 = font.render(f"Ratio: ({ratio_x:.4f}, {ratio_y:.4f})", True, (255, 255, 255))
    label3 = font.render(f"Center at (156.5, 156.5). Shoulder offset from center: ({body_shoulder_pixels[0]-156.5:.1f}, {body_shoulder_pixels[1]-156.5:.1f})", True, (200, 200, 50))
    
    screen.blit(label1, (10, text_y))
    screen.blit(label2, (10, text_y + 25))
    screen.blit(label3, (10, text_y + 50))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
