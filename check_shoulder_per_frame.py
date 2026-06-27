#!/usr/bin/env python3
"""Check shoulder position across different animation frames"""

import pygame
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set
from player import BODY_SHOULDER_OFFSET_RATIO

pygame.init()
screen = pygame.display.set_mode((1600, 900))
pygame.display.set_caption("Shoulder Position Across Animation Frames")
clock = pygame.time.Clock()

# Load animations
animations = load_animation_set(SPRITE_SHEETS["player"])

# Calculate expected shoulder from calibration
shoulder_x = PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x
shoulder_y = PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y

print(f"Calibration shoulder (fixed): ({shoulder_x:.1f}, {shoulder_y:.1f})")
print(f"\nChecking each animation state:")

running = True
current_anim = "idle"
frame_index = 0
anim_names = list(animations.keys())

while running:
    dt = clock.tick(30)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                anim_names_index = anim_names.index(current_anim)
                anim_names_index = (anim_names_index - 1) % len(anim_names)
                current_anim = anim_names[anim_names_index]
                frame_index = 0
            elif event.key == pygame.K_RIGHT:
                anim_names_index = anim_names.index(current_anim)
                anim_names_index = (anim_names_index + 1) % len(anim_names)
                current_anim = anim_names[anim_names_index]
                frame_index = 0
            elif event.key == pygame.K_ESCAPE:
                running = False
    
    # Get current animation and cycle frames
    anim = animations.get(current_anim)
    if anim and hasattr(anim, 'frames'):
        frame_index = (frame_index + 0.3) % len(anim.frames)
        current_frame = anim.frames[int(frame_index)]
    else:
        current_frame = None
    
    screen.fill((20, 20, 30))
    
    if current_frame:
        # Display frame
        scale = 3
        frame_scaled = pygame.transform.scale(current_frame, (PLAYER_WIDTH * scale, PLAYER_HEIGHT * scale))
        screen.blit(frame_scaled, (50, 100))
        
        # Get opaque bounds to see where character actually is
        bounds = current_frame.get_bounding_rect(min_alpha=1)
        
        # Draw grid
        for x in range(0, PLAYER_WIDTH * scale, 20):
            pygame.draw.line(screen, (60, 60, 80), (50 + x, 100), (50 + x, 100 + PLAYER_HEIGHT * scale), 1)
        for y in range(0, PLAYER_HEIGHT * scale, 20):
            pygame.draw.line(screen, (60, 60, 80), (50, 100 + y), (50 + PLAYER_WIDTH * scale, 100 + y), 1)
        
        # Draw calibration shoulder (fixed position)
        shoulder_screen_x = 50 + int(shoulder_x * scale)
        shoulder_screen_y = 100 + int(shoulder_y * scale)
        pygame.draw.circle(screen, (255, 50, 50), (shoulder_screen_x, shoulder_screen_y), 10)
        pygame.draw.circle(screen, (100, 200, 100), (shoulder_screen_x, shoulder_screen_y), 6)
        
        # Draw character bounds
        if bounds:
            bounds_scaled = pygame.Rect(
                50 + bounds.x * scale,
                100 + bounds.y * scale,
                bounds.width * scale,
                bounds.height * scale
            )
            pygame.draw.rect(screen, (200, 100, 100), bounds_scaled, 2)
        
        # Info
        font = pygame.font.SysFont("monospace", 18, bold=True)
        info_font = pygame.font.SysFont("monospace", 14)
        
        screen.blit(font.render(f"Animation: {current_anim}", True, (255, 255, 255)), (50, 20))
        screen.blit(info_font.render(f"Frame: {int(frame_index)}", True, (200, 200, 200)), (50, 45))
        
        info_texts = [
            f"Calibration shoulder (RED): ({shoulder_x:.1f}, {shoulder_y:.1f})",
            f"Character bounds (ORANGE): {bounds if bounds else 'N/A'}",
            "",
            "LEFT/RIGHT arrow = cycle animations",
            "ESC = exit",
            "",
            "Issue: Shoulder position is FIXED at calibration point,",
            "but character's pose changes per frame.",
            "Need per-frame shoulder tracking or pose-aware calibration."
        ]
        
        for i, text in enumerate(info_texts):
            screen.blit(info_font.render(text, True, (180, 180, 200)), (500, 100 + i * 20))
    
    pygame.display.flip()

pygame.quit()
print("\nDone. The shoulder is FIXED but the character MOVES within the sprite frame.")
print("This causes misalignment when animations play.")
