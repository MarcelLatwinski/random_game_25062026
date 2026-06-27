#!/usr/bin/env python3
"""Check character body position shifts across animation frames"""

import pygame
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set
from player import BODY_SHOULDER_OFFSET_RATIO

pygame.init()
screen = pygame.display.set_mode((800, 600))

# Load animations
animations = load_animation_set(SPRITE_SHEETS["player"])

print("Animation Frame Analysis (Opaque Bounds):")
print("=" * 70)

calibration_shoulder_x = PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x
calibration_shoulder_y = PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y

for anim_name, animation in sorted(animations.items()):
    if not hasattr(animation, 'frames'):
        continue
    
    print(f"\n{anim_name.upper()}:")
    print(f"  Calibration shoulder (fixed): ({calibration_shoulder_x:.1f}, {calibration_shoulder_y:.1f})")
    
    for i, frame in enumerate(animation.frames):
        bounds = frame.get_bounding_rect(min_alpha=1)
        if bounds:
            print(f"  Frame {i}: body at ({bounds.x}, {bounds.y}), size {bounds.width}x{bounds.height}")
            
            # Check if calibration shoulder is within bounds
            if bounds.collidepoint(calibration_shoulder_x, calibration_shoulder_y):
                print(f"    → Shoulder IS inside body bounds ✓")
            else:
                print(f"    → Shoulder is OUTSIDE body bounds ✗")
                # Calculate offset needed
                offset_x = bounds.left if calibration_shoulder_x < bounds.left else (bounds.right - PLAYER_WIDTH if calibration_shoulder_x > bounds.right else 0)
                offset_y = bounds.top if calibration_shoulder_y < bounds.top else (bounds.bottom - PLAYER_HEIGHT if calibration_shoulder_y > bounds.bottom else 0)
                if offset_x != 0 or offset_y != 0:
                    print(f"    → Needs offset: ({offset_x}, {offset_y})")

pygame.quit()
print("\n" + "=" * 70)
print("If shoulder is outside bounds for non-idle animations,")
print("each frame needs different shoulder calibration or consistent positioning.")
