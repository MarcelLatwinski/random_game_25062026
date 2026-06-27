#!/usr/bin/env python3
"""Check arms image and pivot calibration"""

import pygame
import json
from pathlib import Path
from player import ARM_PIVOT_RATIO

pygame.init()

# Load arms image
arms_img = pygame.image.load("assets/images/player_arms.png")
print(f"Arms image size: {arms_img.get_size()}")

# Load calibration
config_path = Path("assets/images/player_aim_config.json")
with open(config_path) as f:
    calib = json.load(f)

print(f"\nCalibration config:")
print(f"  arm_pivot (pixels): ({calib['arm_pivot'][0]}, {calib['arm_pivot'][1]})")
print(f"  arms_width: {calib['arms_width']}")
print(f"  arms_height: {calib['arms_height']}")

arm_pivot_pixels_x = ARM_PIVOT_RATIO.x * arms_img.get_width()
arm_pivot_pixels_y = ARM_PIVOT_RATIO.y * arms_img.get_height()

print(f"\nArm pivot from ratio:")
print(f"  ({arm_pivot_pixels_x:.1f}, {arm_pivot_pixels_y:.1f}) on {arms_img.get_size()}")

# Check if pivot is correct
actual_pivot_x = calib['arm_pivot'][0]
actual_pivot_y = calib['arm_pivot'][1]
actual_size_x = calib['arms_width']
actual_size_y = calib['arms_height']

print(f"\nIs calibration correct?")
print(f"  Calibration expects: {actual_size_x}x{actual_size_y} image")
print(f"  Actual image size: {arms_img.get_width()}x{arms_img.get_height()}")

if actual_size_x == arms_img.get_width() and actual_size_y == arms_img.get_height():
    print(f"  ✓ Sizes match!")
else:
    print(f"  ✗ MISMATCH! Calibration might be wrong.")

# Check bounds
bounds = arms_img.get_bounding_rect(min_alpha=1)
print(f"\nArm sprite opaque bounds: {bounds}")
print(f"Arm pivot is at: ({arm_pivot_pixels_x:.0f}, {arm_pivot_pixels_y:.0f})")
print(f"Is pivot inside bounds? {bounds.collidepoint(arm_pivot_pixels_x, arm_pivot_pixels_y) if bounds else 'N/A'}")
