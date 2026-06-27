#!/usr/bin/env python3
"""Live gameplay diagnostic showing shoulder position vs actual character"""

import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_START, FPS, SPRITE_SHEETS,
    PLAYER_WIDTH, PLAYER_HEIGHT
)
from player import Player
from asset_manager import AssetManager

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Shoulder Position Diagnostic")
clock = pygame.time.Clock()

# Load assets
assets = AssetManager()
player_animations = assets.load_animation("player", SPRITE_SHEETS["player"])
bullet_animations = assets.load_animation("bullet", SPRITE_SHEETS["bullet"])
arms_image = pygame.image.load("assets/images/player_arms.png")

# Create player
player = Player(
    SCREEN_WIDTH // 2,
    400,
    animations=player_animations,
    arms_image=arms_image,
    bullet_animations=bullet_animations,
)

font = pygame.font.SysFont("monospace", 14)
running = True
frame_count = 0

print("Controls:")
print("  ARROW KEYS = Move player")
print("  W = Walk animation")
print("  R = Run animation")
print("  I = Idle animation")
print("  ESC = Exit")

while running and frame_count < 600:  # Run for 10 seconds
    dt = clock.tick(FPS) / 1000
    frame_count += 1
    
    keys = pygame.key.get_pressed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_w:
                # Force walk animation
                if player.animator:
                    player.animator.set_animation("walk")
            if event.key == pygame.K_r:
                # Force run animation  
                if player.animator:
                    player.animator.set_animation("run")
            if event.key == pygame.K_i:
                # Force idle animation
                if player.animator:
                    player.animator.set_animation("idle")
    
    # Simple movement
    if keys[pygame.K_LEFT]:
        player.rect.x -= 200 * dt
        player.facing_right = False
    if keys[pygame.K_RIGHT]:
        player.rect.x += 200 * dt
        player.facing_right = True
    if keys[pygame.K_UP]:
        player.rect.y -= 200 * dt
    if keys[pygame.K_DOWN]:
        player.rect.y += 200 * dt
    
    # Keep player on screen
    player.rect.left = max(0, min(player.rect.left, SCREEN_WIDTH - PLAYER_WIDTH))
    player.rect.top = max(0, min(player.rect.top, SCREEN_HEIGHT - PLAYER_HEIGHT))
    
    # Update animation
    if player.animator:
        player.animator.update(dt)
    
    # Draw
    screen.fill((40, 40, 50))
    
    # Draw player normally
    draw_rect = player.rect.copy()
    image = player.animator.current_frame() if player.animator else player.image
    if image:
        if not player.facing_right:
            from animation import flipped_surface
            image = flipped_surface(image)
        screen.blit(image, draw_rect)
    
    # Draw shoulder position
    shoulder = player.aim_shoulder_screen(draw_rect)
    shoulder_point = (round(shoulder.x), round(shoulder.y))
    
    # RED circle = calibration shoulder
    pygame.draw.circle(screen, (255, 50, 50), shoulder_point, 8)
    pygame.draw.circle(screen, (255, 150, 150), shoulder_point, 12, 2)
    
    # Draw frame outline
    pygame.draw.rect(screen, (100, 150, 100), draw_rect, 2)
    
    # Draw rect corners
    pygame.draw.circle(screen, (50, 200, 50), draw_rect.topleft, 4)
    pygame.draw.circle(screen, (200, 50, 50), draw_rect.topright, 4)
    pygame.draw.circle(screen, (50, 50, 200), draw_rect.bottomleft, 4)
    pygame.draw.circle(screen, (200, 200, 50), draw_rect.bottomright, 4)
    
    # Debug info
    anim_state = "?" 
    if player.animator:
        anim_state = player.animator.current_state
    
    info = [
        f"Pos: ({player.rect.x:.0f}, {player.rect.y:.0f})",
        f"Facing: {'→' if player.facing_right else '←'}",
        f"Animation: {anim_state}",
        f"Shoulder: ({shoulder_point[0]}, {shoulder_point[1]})",
        f"Shoulder offset: ({player.body_shoulder_offset.x:.1f}, {player.body_shoulder_offset.y:.1f})",
        "",
        "← → ↑ ↓ Move | W/R/I Animate | ESC Exit",
        "",
        "RED = Calibration shoulder (should be on actual joint)",
        "GREEN = Frame rect",
        "CORNERS = rect corners"
    ]
    
    for i, text in enumerate(info):
        surf = font.render(text, True, (200, 200, 200))
        screen.blit(surf, (10, 10 + i * 18))
    
    pygame.display.flip()

pygame.quit()
print("\nDone. Check if the RED shoulder circle stays on the character's actual shoulder.")
