#!/usr/bin/env python3
"""Visualize the arms image with calibration pivot"""

import pygame
import json
from pathlib import Path

pygame.init()
screen = pygame.display.set_mode((1400, 800))
pygame.display.set_caption("Arms Image Calibration Pivot Verification")
clock = pygame.time.Clock()

# Load arms image
arms_img = pygame.image.load("assets/images/player_arms.png")

# Load calibration
config_path = Path("assets/images/player_aim_config.json")
with open(config_path) as f:
    calib = json.load(f)

arm_pivot_pixels = (calib['arm_pivot'][0], calib['arm_pivot'][1])
print(f"Arms image size: {arms_img.get_size()}")
print(f"Calibration arm pivot: {arm_pivot_pixels}")

running = True
zoom = 0.3  # Start zoomed out to see full image

while running:
    dt = clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_UP:
                zoom = min(2.0, zoom + 0.1)
            if event.key == pygame.K_DOWN:
                zoom = max(0.1, zoom - 0.1)
    
    screen.fill((20, 20, 30))
    
    # Display full arms image scaled
    w, h = arms_img.get_size()
    scaled_size = (int(w * zoom), int(h * zoom))
    if scaled_size[0] > 0 and scaled_size[1] > 0:
        arms_scaled = pygame.transform.scale(arms_img, scaled_size)
        screen.blit(arms_scaled, (50, 50))
        
        # Draw calibration pivot
        pivot_screen_x = 50 + int(arm_pivot_pixels[0] * zoom)
        pivot_screen_y = 50 + int(arm_pivot_pixels[1] * zoom)
        
        # Large circle for visibility
        pygame.draw.circle(screen, (255, 50, 50), (pivot_screen_x, pivot_screen_y), 15)
        pygame.draw.circle(screen, (100, 200, 100), (pivot_screen_x, pivot_screen_y), 10)
        pygame.draw.circle(screen, (255, 200, 100), (pivot_screen_x, pivot_screen_y), 5)
        
        # Draw crosshairs from pivot
        pygame.draw.line(screen, (255, 100, 100), (pivot_screen_x - 30, pivot_screen_y), (pivot_screen_x + 30, pivot_screen_y), 2)
        pygame.draw.line(screen, (255, 100, 100), (pivot_screen_x, pivot_screen_y - 30), (pivot_screen_x, pivot_screen_y + 30), 2)
        
        # Grid overlay
        for x in range(0, scaled_size[0], int(100 * zoom)):
            pygame.draw.line(screen, (60, 60, 80), (50 + x, 50), (50 + x, 50 + scaled_size[1]), 1)
        for y in range(0, scaled_size[1], int(100 * zoom)):
            pygame.draw.line(screen, (60, 60, 80), (50, 50 + y), (50 + scaled_size[0], 50 + y), 1)
    
    # Info
    font = pygame.font.SysFont("monospace", 16, bold=True)
    info_font = pygame.font.SysFont("monospace", 14)
    
    screen.blit(font.render("ARMS IMAGE CALIBRATION", True, (255, 255, 255)), (50, 10))
    
    info = [
        f"Zoom: {zoom:.1f}x (↑/↓ to adjust)",
        f"Pivot (RED): ({arm_pivot_pixels[0]:.0f}, {arm_pivot_pixels[1]:.0f})",
        f"Image size: {w}×{h}",
        "",
        "The RED/GREEN circle marks where the arms' shoulder joint",
        "is located. This should align with the body's shoulder when",
        "the arms are rotated to attach.",
        "",
        "Visual check:",
        "- Does the pivot look like it's AT the shoulder joint?",
        "- Is it in the upper-middle part of the arms?",
        "",
        "If not, the calibration tool needs to re-calibrate the arms."
    ]
    
    for i, text in enumerate(info):
        screen.blit(info_font.render(text, True, (180, 180, 200)), (50 + scaled_size[0] + 50 if scaled_size[0] > 0 else 500, 50 + i * 20))
    
    pygame.display.flip()

pygame.quit()
