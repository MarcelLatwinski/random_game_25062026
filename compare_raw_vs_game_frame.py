#!/usr/bin/env python3
"""Compare raw sprite sheet frame with game-loaded frame"""

import pygame
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set

pygame.init()
screen = pygame.display.set_mode((800, 600))

# Load raw frame directly from sheet
body_sheet = pygame.image.load("assets/images/processed/new_player_sheet_noarms.png")
frame_w = body_sheet.get_width() // 4
frame_h = body_sheet.get_height() // 4

print(f"Sheet size: {body_sheet.get_size()}")
print(f"Frame size from sheet: {frame_w}x{frame_h}")

# Extract frame 0 (idle, row 0, col 0)
raw_frame = body_sheet.subsurface((0, 0, frame_w, frame_h)).copy()
print(f"Raw idle frame extracted: {raw_frame.get_size()}")

# Get a sample of pixels from raw frame (center area)
raw_center_pixel = raw_frame.get_at((frame_w // 2, frame_h // 2))
print(f"Raw frame pixel at center: {raw_center_pixel}")

# Load game idle frame
animations = load_animation_set(SPRITE_SHEETS["player"])
idle_anim = animations.get("idle")
game_frame = idle_anim.frames[0] if idle_anim and hasattr(idle_anim, 'frames') else None

if game_frame:
    print(f"Game idle frame: {game_frame.get_size()}")
    
    # Get pixel at center (accounting for scale)
    game_center_x = PLAYER_WIDTH // 2
    game_center_y = PLAYER_HEIGHT // 2
    game_center_pixel = game_frame.get_at((game_center_x, game_center_y))
    print(f"Game frame pixel at center: {game_center_pixel}")
    
    # Check a few pixels to see if they match
    for test_x in [10, 50, 100, 150]:
        test_y = 100
        if test_x < frame_w and test_y < frame_h:
            raw_px = raw_frame.get_at((test_x, test_y))
            # Scale coordinates to game frame
            game_x = int(test_x * PLAYER_WIDTH / frame_w)
            game_y = int(test_y * PLAYER_HEIGHT / frame_h)
            if game_x < PLAYER_WIDTH and game_y < PLAYER_HEIGHT:
                game_px = game_frame.get_at((game_x, game_y))
                match = "✓" if raw_px[:3] == game_px[:3] else "✗"
                print(f"  [{test_x},{test_y}] raw={raw_px[:3]} -> [{game_x},{game_y}] game={game_px[:3]} {match}")
    
    # Compare overall: Scale raw frame to 114x114 and blit to screen
    scale_factor = 3
    raw_scaled = pygame.transform.scale(raw_frame, (frame_w * scale_factor, frame_h * scale_factor))
    game_scaled = pygame.transform.scale(game_frame, (PLAYER_WIDTH * scale_factor, PLAYER_HEIGHT * scale_factor))
    
    screen.fill((30, 30, 30))
    screen.blit(raw_scaled, (10, 10))
    screen.blit(game_scaled, (450, 10))
    
    # Draw crosshairs and grid
    for i in range(0, frame_w * scale_factor, 50):
        pygame.draw.line(screen, (100, 100, 100), (10 + i, 10), (10 + i, 10 + frame_h * scale_factor), 1)
    for i in range(0, frame_h * scale_factor, 50):
        pygame.draw.line(screen, (100, 100, 100), (10, 10 + i), (10 + frame_w * scale_factor, 10 + i), 1)
    
    for i in range(0, PLAYER_WIDTH * scale_factor, 50):
        pygame.draw.line(screen, (100, 100, 100), (450 + i, 10), (450 + i, 10 + PLAYER_HEIGHT * scale_factor), 1)
    for i in range(0, PLAYER_HEIGHT * scale_factor, 50):
        pygame.draw.line(screen, (100, 100, 100), (450, 10 + i), (450 + PLAYER_WIDTH * scale_factor, 10 + i), 1)
    
    # Labels
    font = pygame.font.SysFont("monospace", 16, bold=True)
    screen.blit(font.render("Raw Sheet Frame (313x313)", True, (255, 255, 255)), (10, 630))
    screen.blit(font.render("Game Loaded Frame (114x114)", True, (255, 255, 255)), (450, 630))
    
    pygame.display.flip()
    pygame.time.wait(3000)

pygame.quit()
print("\nComparison complete. Check if frames look identical after scaling.")
