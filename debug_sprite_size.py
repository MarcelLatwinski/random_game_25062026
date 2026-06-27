#!/usr/bin/env python3
"""Debug script to check actual rendered sprite size vs expected"""

import pygame
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set

pygame.init()

# Set video mode
screen = pygame.display.set_mode((800, 600))

# Load player animations
animations = load_animation_set(SPRITE_SHEETS["player"])

if animations:
    print(f"Expected sprite size: {PLAYER_WIDTH}x{PLAYER_HEIGHT}")
    print(f"\nAnimation frames:")
    
    for anim_name, animation in animations.items():
        if hasattr(animation, 'frames'):
            for i, frame in enumerate(animation.frames[:1]):  # Just check first frame
                print(f"\n  {anim_name}[{i}]:")
                print(f"    Frame size: {frame.get_size()}")
                print(f"    Frame rect: {frame.get_rect()}")
                
                # Check if frame is smaller than expected
                w, h = frame.get_size()
                if w != PLAYER_WIDTH or h != PLAYER_HEIGHT:
                    print(f"    ⚠️  MISMATCH! Expected ({PLAYER_WIDTH}, {PLAYER_HEIGHT}), got ({w}, {h})")
                
                # Get bounding rect (non-transparent area)
                bounds = frame.get_bounding_rect(min_alpha=1)
                if bounds:
                    print(f"    Opaque bounds: {bounds}")
                    print(f"    Opaque size: {bounds.width}x{bounds.height}")
                    offset_x = bounds.left
                    offset_y = bounds.top
                    print(f"    Offset from top-left: ({offset_x}, {offset_y})")
