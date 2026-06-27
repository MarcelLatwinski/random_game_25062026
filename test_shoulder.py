#!/usr/bin/env python3
"""
Quick test to capture shoulder screen coordinates during first few frames.
"""
import sys
import os
sys.path.insert(0, '.')

# Enable debug mode
import settings
settings.DEBUG_AIM_PIVOT = True

# Now start the game and let it run for just 1 frame
import pygame
pygame.init()
from game import Game

print("\n[TEST] Starting game and capturing first frame output...\n")
print(f"[TEST] DEBUG_AIM_PIVOT BEFORE Game(): {settings.DEBUG_AIM_PIVOT}")
game = Game()
print(f"[TEST] DEBUG_AIM_PIVOT AFTER Game(): {settings.DEBUG_AIM_PIVOT}")
print(f"[TEST] game.player exists: {game.player is not None}")
print(f"[TEST] game.state: {game.state}")

# Set game state to PLAYING so draw_gameplay() will be called
game.state = "PLAYING"

# Manually call update and draw once with dt and now
import time
now = time.time() * 1000  # milliseconds
dt = 16  # milliseconds (16ms per frame ~60 FPS)
print(f"[TEST] Calling game.update({dt}, {now:.0f})")
game.update(dt, now)
print(f"[TEST] Calling game.draw()")
game.draw()

print("\n[TEST] Done with one frame.\n")
