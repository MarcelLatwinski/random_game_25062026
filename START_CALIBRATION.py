#!/usr/bin/env python3
"""
QUICK START: Player Aiming Calibration

This is a step-by-step guide to calibrate your player's arm/gun aiming.

WHY? The arm was orbiting away from the shoulder instead of rotating around it.
This tool lets you visually position the shoulder joint precisely.

WHAT YOU NEED TO DO:

1. Run this file:
   cd /path/to/random_game_25062026
   python calibrate_aim.py

2. In the calibration tool window, you'll see:
   - LEFT: Body sprite with RED crosshair (shoulder position)
   - RIGHT: Arms image with BLUE crosshair (pivot inside arms)
   - CENTER: Real-time preview of arm rotation

3. Move the RED crosshair to the shoulder on the body:
   - Use arrow keys to move ±1px
   - Shift + arrow keys to move ±5px
   - Or left-click directly on the shoulder

4. Move the BLUE crosshair to the shoulder inside the arms image:
   - Use WASD to move ±1px
   - Shift + WASD to move ±5px
   - Or right-click directly on the shoulder position

5. Watch the CENTER preview:
   - Move your mouse over the center to see arm rotation
   - The red and blue dots should stay together
   - If they separate, adjust one of the crosshairs

6. When it looks correct, press S to SAVE

7. Close the tool (ESC) and run the game
   - The arm should now rotate smoothly around the shoulder
   - Test by moving the mouse in all directions

CONTROLS SUMMARY:
┌─────────────────────────────────────────┐
│ Red Crosshair (Body Shoulder)           │
│ • Arrow Keys → Move ±1px                │
│ • Shift + Arrow → Move ±5px             │
│ • Left Click → Set position directly    │
│                                         │
│ Blue Crosshair (Arm Pivot)              │
│ • WASD → Move ±1px                      │
│ • Shift + WASD → Move ±5px              │
│ • Right Click → Set position directly   │
│                                         │
│ Other                                   │
│ • [ and ] → Cycle animation frames      │
│ • Number Keys 0-9 → Jump to frame       │
│ • S → Save calibration                  │
│ • P → Generate debug PNG                │
│ • ESC → Exit                            │
└─────────────────────────────────────────┘

NEXT STEPS AFTER SAVING:

1. Run your game:
   python main.py

2. Test the aiming:
   - Move the mouse around
   - Arm should stay attached to shoulder
   - No orbiting at any angle

3. Test while moving:
   - Walk, run, jump
   - Aiming should still work

4. If something looks wrong:
   - Run calibrate_aim.py again
   - Re-position the crosshairs
   - Save and test again

TECHNICAL INFO:

The calibration tool creates:
  → assets/images/player_aim_config.json

The game automatically loads this when it starts.
If the config doesn't exist, it uses default values.

To see where the tool thinks the pivots are:
  Press P in the calibration tool
  Creates: debug/player_aim_calibration.png

For detailed information:
  Read: CALIBRATION_GUIDE.md
  Read: CALIBRATION_SYSTEM_SUMMARY.md

TROUBLESHOOTING:

Q: Arm still orbits away after calibration?
A: Make sure the crosshairs are exactly on the shoulder joints.
   Use the center preview to verify they stay together.
   Generate a debug PNG (P key) to visually confirm positions.

Q: Where's the shoulder on the body sprite?
A: It's where the arm connects to the body. Usually at the top-right
   area of the body sprite if the player is facing right.

Q: Where's the shoulder inside the arms image?
A: It's the base/origin point of the arm. Usually near the bottom-left
   of the arms image (where it would connect to the body).

Q: Can I calibrate just once?
A: Yes! Save the calibration with S, then it's used for all gameplay.
   Only re-run the tool if the arm behavior changes.

GOT THIS? LET'S GO!
Run: python calibrate_aim.py
"""

print(__doc__)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Check if calibrate_aim.py exists
    calibrate_path = Path(__file__).parent / "calibrate_aim.py"
    if not calibrate_path.exists():
        print("ERROR: calibrate_aim.py not found!")
        sys.exit(1)
    
    # Launch the calibration tool
    print("\n" + "="*60)
    print("Launching calibration tool...")
    print("="*60 + "\n")
    
    import subprocess
    result = subprocess.run([sys.executable, str(calibrate_path)])
    sys.exit(result.returncode)
