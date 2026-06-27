#!/usr/bin/env python3
"""
Find likely shoulder joint location on arms image by analyzing color transitions.
The shoulder should be where the arm connects to the body - typically a denser pixel area.
"""

import pygame
from PIL import Image

# Load arms image
arms_pil = Image.open("assets/images/player_arms.png")

print(f"Arms image size: {arms_pil.size}")

# Current calibration point
current_pivot = (288, 533)
current_ratio = (288/1254, 533/1254)

print(f"\nCurrent calibration:")
print(f"  Pixel coords: {current_pivot}")
print(f"  Ratio: ({current_ratio[0]:.4f}, {current_ratio[1]:.4f})")

# Analyze pixel density in 4x4 grid to find which quadrant has the shoulder
print("\nAnalyzing pixel density by quadrant...")
width, height = arms_pil.size

for i in range(4):
    for j in range(4):
        x1 = j * (width // 4)
        x2 = (j + 1) * (width // 4)
        y1 = i * (height // 4)
        y2 = (i + 1) * (height // 4)
        
        # Count non-transparent pixels
        region = arms_pil.crop((x1, y1, x2, y2))
        if region.mode == 'RGBA':
            pixels_data = list(region.getdata())
            non_transparent = sum(1 for p in pixels_data if p[3] > 100)  # Alpha > 100
        else:
            non_transparent = region.size[0] * region.size[1]
        
        marker = "█" if (j, i) == (current_pivot[0] // (width // 4), current_pivot[1] // (height // 4)) else " "
        print(f"  [{i},{j}]{marker} Non-transparent pixels: {non_transparent:6d}  (x:{x1:4d}-{x2:4d}, y:{y1:4d}-{y2:4d})")

print("\nThe shoulder joint should be in a high-density area.")

print("\nThe shoulder joint should be in a quadrant with moderate-to-high pixel density.")
print(f"Current pivot is in quadrant [{current_pivot[1]//(height//4)},{current_pivot[0]//(width//4)}]")

print(f"\nPixel analysis around current pivot {current_pivot}:")
sample_radius = 50
x, y = current_pivot

for dy in range(-sample_radius, sample_radius + 1, 20):
    for dx in range(-sample_radius, sample_radius + 1, 20):
        px = x + dx
        py = y + dy
        if 0 <= px < width and 0 <= py < height:
            pixel = arms_pil.getpixel((px, py))
            # Check if visible (has alpha if RGBA, or any color if RGB)
            is_visible = False
            if isinstance(pixel, tuple):
                if len(pixel) == 4:  # RGBA
                    is_visible = pixel[3] > 100
                else:  # RGB or grayscale
                    is_visible = any(c > 50 for c in pixel) if len(pixel) > 1 else pixel > 50
            
            if is_visible:
                print(f"  ({px:4d}, {py:4d}): VISIBLE - {pixel}")

print("\nTo recalibrate:")
print("  python3 calibrate_aim.py")
print("  Press 2 for arms mode")
print("  Use arrow keys to move pivot to actual shoulder joint")
print("  Press S to save")
