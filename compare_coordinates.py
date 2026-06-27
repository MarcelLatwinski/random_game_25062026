#!/usr/bin/env python3
"""
Compare what calibration tool uses vs what game renders.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, '.')

import pygame
pygame.init()

from settings import PLAYER_WIDTH, PLAYER_HEIGHT
import player

# Load config
config_path = Path("assets/images/player_aim_config.json")

if not config_path.exists():
    print("No config file! Run calibrate_aim.py first.")
    sys.exit(1)

with open(config_path) as f:
    config = json.load(f)

print("=" * 70)
print("COORDINATE SPACE COMPARISON")
print("=" * 70)
print()

# What the calibration tool uses
calib_body_px = config["body_shoulder_offset"]
calib_frame_w = config.get("frame_width", 313)
calib_frame_h = config.get("frame_height", 313)
calib_zoom = 1.0  # Assume zoom=1.0 for comparison (no scaling)

print("CALIBRATION TOOL SPACE (what you see when positioning):")
print(f"  Shoulder pixel position: ({calib_body_px[0]}, {calib_body_px[1]})")
print(f"  Within frame size: {calib_frame_w}×{calib_frame_h}")
print(f"  Display zoom: {calib_zoom}×")
print(f"  Display position in tool: (100, 100) top-left")
print(f"  Dot screen position in tool: ({100 + calib_body_px[0]*calib_zoom}, {100 + calib_body_px[1]*calib_zoom})")
print()

# What the game uses
game_body_ratio = (player.BODY_SHOULDER_OFFSET_RATIO.x, player.BODY_SHOULDER_OFFSET_RATIO.y)
game_body_px = (PLAYER_WIDTH * game_body_ratio[0], PLAYER_HEIGHT * game_body_ratio[1])

print("GAME SPACE (what the game calculates):")
print(f"  PLAYER_WIDTH={PLAYER_WIDTH}, PLAYER_HEIGHT={PLAYER_HEIGHT}")
print(f"  Loaded ratio: {game_body_ratio}")
print(f"  Converted to pixels: ({game_body_px[0]:.2f}, {game_body_px[1]:.2f})")
print(f"  When player is at (140, 876), shoulder is at:")
print(f"    ({140 + game_body_px[0]:.1f}, {876 + game_body_px[1]:.1f})")
print()

# Check conversion
ratio_from_saved = (calib_body_px[0] / calib_frame_w, calib_body_px[1] / calib_frame_h)
print("CONVERSION CHECK:")
print(f"  Saved pixel coords: {calib_body_px}")
print(f"  Divided by frame ({calib_frame_w}, {calib_frame_h}): {ratio_from_saved}")
print(f"  Loaded ratio from config: {game_body_ratio}")
print(f"  Match? {abs(ratio_from_saved[0] - game_body_ratio[0]) < 0.001 and abs(ratio_from_saved[1] - game_body_ratio[1]) < 0.001}")
print()

# The key question
print("MISMATCH ANALYSIS:")
print(f"  In calibration tool with zoom=1.0, shoulder should be at screen pixel:")
print(f"    ({100 + calib_body_px[0]}, {100 + calib_body_px[1]})")
print()
print(f"  In game at player position (140, 876), shoulder is at screen pixel:")
print(f"    ({140 + game_body_px[0]:.1f}, {876 + game_body_px[1]:.1f})")
print()

# Check if the issue is the frame size
print(f"  Are frame dimensions saved in config? {config.get('frame_width')} x {config.get('frame_height')}")
if config.get('frame_width') != calib_frame_w or config.get('frame_height') != calib_frame_h:
    print(f"  ⚠️  MISMATCH! Config has {config.get('frame_width')}×{config.get('frame_height')}, expected {calib_frame_w}×{calib_frame_h}")
else:
    print(f"  ✓ Frame dimensions match")
