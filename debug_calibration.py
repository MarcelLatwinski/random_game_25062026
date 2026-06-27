#!/usr/bin/env python3
"""
Debug script to verify calibration coordinate spaces match.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from settings import PLAYER_WIDTH, PLAYER_HEIGHT
import player

# Load the config
config_path = Path("assets/images/player_aim_config.json")

print("=== CALIBRATION DEBUG ===\n")
print(f"PLAYER_WIDTH: {PLAYER_WIDTH}")
print(f"PLAYER_HEIGHT: {PLAYER_HEIGHT}")
print(f"ARM_DRAW_WIDTH_RATIO: {player.ARM_DRAW_WIDTH_RATIO}")
print()

if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    
    print("Config file contents:")
    print(f"  body_shoulder_offset: {config['body_shoulder_offset']}")
    print(f"  arm_pivot: {config['arm_pivot']}")
    print(f"  frame_width: {config.get('frame_width', 313)}")
    print(f"  frame_height: {config.get('frame_height', 313)}")
    print(f"  arms_width: {config.get('arms_width', 1254)}")
    print(f"  arms_height: {config.get('arms_height', 1254)}")
    print()
    
    # Show what calibrate_aim.py is using
    body_px = config['body_shoulder_offset']
    arm_px = config['arm_pivot']
    frame_w = config.get('frame_width', 313)
    frame_h = config.get('frame_height', 313)
    arms_w = config.get('arms_width', 1254)
    arms_h = config.get('arms_height', 1254)
    
    print("Calibration tool space (what you set):")
    print(f"  Body shoulder in frame coords: ({body_px[0]}, {body_px[1]}) / ({frame_w}, {frame_h})")
    print(f"  Arm pivot in full image coords: ({arm_px[0]}, {arm_px[1]}) / ({arms_w}, {arms_h})")
    print()
    
    # Show what player.py calculates
    body_ratio_x = body_px[0] / frame_w
    body_ratio_y = body_px[1] / frame_h
    arm_ratio_x = arm_px[0] / arms_w
    arm_ratio_y = arm_px[1] / arms_h
    
    body_offset_x = PLAYER_WIDTH * body_ratio_x
    body_offset_y = PLAYER_HEIGHT * body_ratio_y
    
    # Load and scale the actual arms image like the game does
    import pygame
    pygame.init()
    try:
        arms_full = pygame.image.load("assets/images/player_arms.png")
        target_width = max(1, int(round(PLAYER_WIDTH * player.ARM_DRAW_WIDTH_RATIO)))
        scale = target_width / arms_full.get_width()
        target_height = max(1, int(round(arms_full.get_height() * scale)))
        
        scaled_arm_w = target_width
        scaled_arm_h = target_height
    except:
        # Fallback
        scaled_arm_w = int(PLAYER_WIDTH * player.ARM_DRAW_WIDTH_RATIO)
        scaled_arm_h = scaled_arm_w  # assume square
    
    arm_pivot_x = scaled_arm_w * arm_ratio_x
    arm_pivot_y = scaled_arm_h * arm_ratio_y
    
    print("Game rendering space (what the game will use):")
    print(f"  Body shoulder offset: ({body_offset_x:.1f}, {body_offset_y:.1f}) in player space (114x114)")
    print(f"    Ratio: ({body_ratio_x:.4f}, {body_ratio_y:.4f})")
    print()
    print(f"  Scaled arm image size: {scaled_arm_w}x{scaled_arm_h}")
    print(f"  Arm pivot in scaled image: ({arm_pivot_x:.1f}, {arm_pivot_y:.1f})")
    print(f"    Ratio: ({arm_ratio_x:.4f}, {arm_ratio_y:.4f})")
else:
    print(f"No config file found at {config_path}")
