#!/usr/bin/env python3
"""Visual comparison of calibration vs game rendering"""

import pygame
import sys
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_START
from animation import load_animation_set
from player import BODY_SHOULDER_OFFSET_RATIO, ARM_PIVOT_RATIO

pygame.init()
screen = pygame.display.set_mode((1600, 600))
pygame.display.set_caption("Calibration vs Game Comparison")
clock = pygame.time.Clock()

# Load sprite sheet for raw frame
body_sheet = pygame.image.load("assets/images/new_player_sheet_noarms.png")
frame_width = body_sheet.get_width() // 4
frame_height = body_sheet.get_height() // 4
raw_frame = body_sheet.subsurface((0, 0, frame_width, frame_height)).copy()

# Load game animations
animations = load_animation_set(SPRITE_SHEETS["player"])
idle_animation = animations.get("idle")

# Get the first idle frame (same as raw_frame but processed through game pipeline)
game_frame = idle_animation.frames[0] if idle_animation and hasattr(idle_animation, 'frames') else None

print(f"Raw frame from sheet: {raw_frame.get_size()}")
print(f"Game idle frame: {game_frame.get_size() if game_frame else 'N/A'}")
print(f"Body shoulder offset ratio: {BODY_SHOULDER_OFFSET_RATIO}")
print(f"Arm pivot ratio: {ARM_PIVOT_RATIO}")

# Calculate shoulder positions
# In raw 313×313 frame
raw_shoulder_x = frame_width * BODY_SHOULDER_OFFSET_RATIO.x
raw_shoulder_y = frame_height * BODY_SHOULDER_OFFSET_RATIO.y
print(f"Shoulder in raw frame: ({raw_shoulder_x:.1f}, {raw_shoulder_y:.1f})")

# In game 114×114 frame
game_shoulder_x = PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x
game_shoulder_y = PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y
print(f"Shoulder in game frame: ({game_shoulder_x:.1f}, {game_shoulder_y:.1f})")

running = True
while running:
    dt = clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    
    # Clear
    screen.fill((30, 30, 30))
    
    # Left: Raw frame from sheet (scaled to 3x for visibility)
    scale_raw = 3
    raw_scaled = pygame.transform.scale(raw_frame, 
                                       (frame_width * scale_raw, frame_height * scale_raw))
    screen.blit(raw_scaled, (10, 50))
    
    # Draw shoulder on raw frame
    raw_shoulder_screen = (
        10 + int(raw_shoulder_x * scale_raw),
        50 + int(raw_shoulder_y * scale_raw)
    )
    pygame.draw.circle(screen, (255, 0, 0), raw_shoulder_screen, 8)
    pygame.draw.circle(screen, (0, 255, 0), raw_shoulder_screen, 5)
    
    # Middle: Game frame (scaled to 3x for visibility)
    if game_frame:
        scale_game = 3
        game_scaled = pygame.transform.scale(game_frame,
                                           (PLAYER_WIDTH * scale_game, PLAYER_HEIGHT * scale_game))
        screen.blit(game_scaled, (100 + frame_width * scale_raw, 50))
        
        # Draw shoulder on game frame
        game_shoulder_screen = (
            100 + frame_width * scale_raw + int(game_shoulder_x * scale_game),
            50 + int(game_shoulder_y * scale_game)
        )
        pygame.draw.circle(screen, (255, 0, 0), game_shoulder_screen, 8)
        pygame.draw.circle(screen, (0, 255, 0), game_shoulder_screen, 5)
    
    # Draw labels
    font = pygame.font.SysFont("monospace", 20, bold=True)
    screen.blit(font.render("Raw Frame (313x313 scaled 3x)", True, (255, 255, 255)), (10, 20))
    screen.blit(font.render("Game Frame (114x114 scaled 3x)", True, (255, 255, 255)), 
                (100 + frame_width * scale_raw, 20))
    
    # Info text
    info_font = pygame.font.SysFont("monospace", 16)
    info = [
        f"Raw shoulder: ({raw_shoulder_x:.0f}, {raw_shoulder_y:.0f})",
        f"Game shoulder: ({game_shoulder_x:.0f}, {game_shoulder_y:.0f})",
        f"RED circle = shoulder joint (calibrated)",
        f"GREEN circle = inner marker",
    ]
    for i, text in enumerate(info):
        screen.blit(info_font.render(text, True, (200, 200, 200)), (10, 350 + i * 25))
    
    pygame.display.flip()

pygame.quit()
