#!/usr/bin/env python3
"""Test script to visualize shoulder position rendering"""

import pygame
import sys
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_WIDTH, PLAYER_HEIGHT,
    PLAYER_START, FPS, SPRITE_SHEETS
)
from player import Player
from asset_manager import AssetManager
from animation import flipped_surface

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Shoulder Position Test")
clock = pygame.time.Clock()

# Load assets
assets = AssetManager()
player_animations = assets.load_animation("player", SPRITE_SHEETS["player"])
bullet_animations = assets.load_animation("bullet", SPRITE_SHEETS["bullet"])
arms_image = pygame.image.load("assets/images/player_arms.png")

# Create player at starting position
player = Player(
    PLAYER_START[0],
    PLAYER_START[1],
    animations=player_animations,
    arms_image=arms_image,
    bullet_animations=bullet_animations,
)

print(f"Player rect: {player.rect}")
print(f"Body shoulder offset: {player.body_shoulder_offset}")
print(f"Arm pivot: {player.arm_pivot}")

running = True
frame_count = 0
while running and frame_count < 60:  # Run for 1 second at 60 FPS
    dt = clock.tick(FPS) / 1000
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Draw
    screen.fill((50, 50, 50))
    
    # Draw player
    draw_rect = player.rect
    player.draw(screen, camera_x=0)
    
    # Calculate and display shoulder position
    shoulder = player.aim_shoulder_screen(draw_rect)
    shoulder_point = (round(shoulder.x), round(shoulder.y))
    
    # Draw guides
    pygame.draw.rect(screen, (200, 200, 200), draw_rect, 2)  # Player rect outline
    pygame.draw.circle(screen, (255, 100, 0), shoulder_point, 8)  # Large orange circle for shoulder
    pygame.draw.circle(screen, (0, 255, 0), (draw_rect.left, draw_rect.top), 5)  # Green circle for rect top-left
    
    # Draw crosshairs at center
    center_x, center_y = draw_rect.center
    pygame.draw.line(screen, (255, 0, 0), (center_x - 10, center_y), (center_x + 10, center_y), 1)
    pygame.draw.line(screen, (255, 0, 0), (center_x, center_y - 10), (center_x, center_y + 10), 1)
    
    # Display info
    font = pygame.font.SysFont("Segoe UI", 16)
    info_texts = [
        f"Player rect: {draw_rect}",
        f"Body shoulder offset: {player.body_shoulder_offset}",
        f"Shoulder screen: {shoulder_point}",
        f"Facing: {'RIGHT' if player.facing_right else 'LEFT'}",
    ]
    for i, text in enumerate(info_texts):
        surf = font.render(text, True, (255, 255, 255))
        screen.blit(surf, (10, 10 + i * 25))
    
    pygame.display.flip()
    frame_count += 1

pygame.quit()
print("Test completed")
