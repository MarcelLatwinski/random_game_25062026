#!/usr/bin/env python3
"""
Complete coordinate audit: calibration values vs game rendering
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, '.')

import pygame
pygame.init()

from settings import PLAYER_WIDTH, PLAYER_HEIGHT
import player

print("\n" + "="*80)
print("COMPLETE CALIBRATION AUDIT")
print("="*80)

config_path = Path("assets/images/player_aim_config.json")

if not config_path.exists():
    print("No config file! Run calibrate_aim.py first.")
    sys.exit(1)

with open(config_path) as f:
    config = json.load(f)

print("\n1. RAW CONFIG FILE:")
print(f"   File: {config_path}")
print(f"   body_shoulder_offset: {config['body_shoulder_offset']}")
print(f"   frame_width: {config.get('frame_width', 'NOT SET')}")
print(f"   frame_height: {config.get('frame_height', 'NOT SET')}")

print("\n2. PLAYER MODULE CONSTANTS (loaded at import time):")
print(f"   BODY_SHOULDER_OFFSET_RATIO: {player.BODY_SHOULDER_OFFSET_RATIO}")
print(f"   ARM_PIVOT_RATIO: {player.ARM_PIVOT_RATIO}")

print("\n3. PLAYER OBJECT AFTER INITIALIZATION:")
from game import Game
game = Game()
print(f"   player.body_shoulder_offset: {game.player.body_shoulder_offset}")
print(f"   player.arm_pivot: {game.player.arm_pivot}")
print(f"   player.rect: {game.player.rect}")

print("\n4. EXPECTED GAME RENDERING:")
draw_rect = game.player.rect
shoulder = game.player.aim_shoulder_screen(draw_rect)
print(f"   Player rect position: ({draw_rect.left}, {draw_rect.top})")
print(f"   Shoulder screen position: ({shoulder.x:.1f}, {shoulder.y:.1f})")

print("\n5. WHAT THE CALIBRATION TOOL HAD:")
calib_body_px = config['body_shoulder_offset']
calib_frame = config.get('frame_width', 313)
print(f"   Saved shoulder pixels: {calib_body_px}")
print(f"   In frame of size: {calib_frame}x{calib_frame}")
print(f"   Ratio: ({calib_body_px[0]/calib_frame:.4f}, {calib_body_px[1]/calib_frame:.4f})")

print("\n6. CONVERSION PATH:")
print(f"   Pixel {calib_body_px} → Ratio {(calib_body_px[0]/calib_frame, calib_body_px[1]/calib_frame)}")
print(f"   Ratio × PLAYER_WIDTH(114) → ({calib_body_px[0]/calib_frame * 114:.2f}, {calib_body_px[1]/calib_frame * 114:.2f})")
print(f"   Which matches player.body_shoulder_offset? {abs(game.player.body_shoulder_offset.x - calib_body_px[0]/calib_frame * 114) < 0.1}")

print("\n" + "="*80)
print("If the shoulder position is wrong in the game:")
print("1. The position IN the calibration tool should match the game's calculation")
print("2. Enable DEBUG_AIM_PIVOT in settings.py and run the game to see debug dots")
print("="*80 + "\n")
