#!/usr/bin/env python3
"""Check if shoulder needs per-frame calibration"""

import pygame
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set
from player import BODY_SHOULDER_OFFSET_RATIO

pygame.init()
screen = pygame.display.set_mode((100, 100))  # Needed for convert_alpha()

# Load animations
animations = load_animation_set(SPRITE_SHEETS["player"])

# Fixed calibration shoulder
calibration_shoulder_x = PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x
calibration_shoulder_y = PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y

print("Frame-by-Frame Shoulder Analysis:")
print("=" * 80)
print(f"Fixed calibration shoulder: ({calibration_shoulder_x:.1f}, {calibration_shoulder_y:.1f})")
print()

for anim_name in ["idle", "walk", "run", "jump", "fall"]:
    anim = animations.get(anim_name)
    if not anim or not hasattr(anim, 'frames'):
        continue
    
    print(f"\n{anim_name.upper()}:")
    for i, frame in enumerate(anim.frames):
        bounds = frame.get_bounding_rect(min_alpha=1)
        if bounds:
            # Check different parts of the body
            is_top = bounds.top == 0
            is_bottom = bounds.bottom == PLAYER_HEIGHT
            is_left = bounds.left == 0
            is_right = bounds.right == PLAYER_WIDTH
            
            # Calculate if shoulder is centered on body
            body_center_x = bounds.centerx
            body_center_y = bounds.centery
            
            dist_from_body_center_x = abs(calibration_shoulder_x - body_center_x)
            dist_from_body_center_y = abs(calibration_shoulder_y - body_center_y)
            
            print(f"  Frame {i}: bounds={bounds}")
            print(f"    Body center: ({body_center_x:.0f}, {body_center_y:.0f})")
            print(f"    Shoulder distance from body center: ({dist_from_body_center_x:.0f}, {dist_from_body_center_y:.0f})")
            
            if dist_from_body_center_x < 20 and dist_from_body_center_y < 20:
                print(f"    ✓ Shoulder is near body center (good)")
            else:
                print(f"    ⚠ Shoulder is FAR from body center (might be wrong for this pose)")

print("\n" + "=" * 80)
print("If shoulder is not centered on body for all frames,")
print("calibration won't work for all animations.")
print("You may need per-animation calibration or pose-relative shoulder tracking.")
