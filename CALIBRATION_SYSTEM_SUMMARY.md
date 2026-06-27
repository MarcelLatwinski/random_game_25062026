# Player Aiming System - Complete Calibration Implementation

## What Was Built

A complete interactive calibration system for the player arm/gun overlay aiming mechanics. The system allows you to precisely position two critical pivot points visually, then saves and loads them for use in the game.

### Key Components

#### 1. **calibrate_aim.py** (Interactive Tool)
A standalone Pygame application that lets you:
- View the body sprite frame and arms image at 4× zoom
- Visually position the shoulder joint on the body (red crosshair)
- Visually position the shoulder pivot inside the arms image (blue crosshair)
- See real-time arm rotation preview as you move the mouse
- Cycle through animation frames to test calibration consistency
- Save calibration to `player_aim_config.json`
- Generate debug PNG images for visual verification

**How to run:**
```bash
python calibrate_aim.py
```

#### 2. **player_aim_config.json** (Calibration Data)
Stores the calibrated pivot coordinates:
```json
{
  "body_shoulder_offset": [50, 45],
  "arm_pivot": [5, 32],
  "frame_width": 480,
  "frame_height": 480,
  "notes": "..."
}
```

This file is created automatically when you press **S** in the calibration tool.

#### 3. **player.py** (Updated Game Code)
Modified to:
- Load calibration from `player_aim_config.json` on startup
- Convert pixel coordinates back to ratios
- Use loaded values for all aiming calculations
- Fall back to sensible defaults if config doesn't exist
- Include comprehensive documentation of the pivot system

#### 4. **CALIBRATION_GUIDE.md** (User Documentation)
Complete guide covering:
- What the calibration tool does and why it's needed
- Step-by-step instructions for using it
- Troubleshooting common issues
- Technical explanations of the math
- Testing procedures

---

## How the System Works

### The Problem
When you rotate an image in Pygame around its center and position it, the image orbits away instead of rotating in place. This is especially problematic for the arm overlay, which should rotate around the shoulder joint without moving away from the player.

### The Solution
The system uses a **pivot-based rotation** approach:

1. **Two calibrated points** are defined:
   - **Body Shoulder:** Where the shoulder joint is on the player body sprite
   - **Arm Pivot:** Where the shoulder joint is inside the player_arms.png image

2. **Rotation math** properly handles the offset:
   ```python
   def rotate_around_pivot(image, angle_degrees, image_pivot, target_pivot):
       # Rotate image normally
       rotated = pygame.transform.rotate(image, -angle_degrees)
       
       # Calculate offset from image center to pivot point
       offset = image_pivot - image_center
       
       # Rotate that offset
       rotated_offset = offset.rotate(angle_degrees)
       
       # Position so rotated pivot lands at target
       rect = rotated.get_rect(center = target_pivot - rotated_offset)
       
       return rotated, rect
   ```

3. **At game time:**
   - Calculate screen-space shoulder position from player body position
   - Rotate arm image around its internal pivot point
   - Position it so the arm's pivot lands on the body's shoulder
   - Result: Arm rotates cleanly around shoulder at all angles

---

## Workflow

### Step 1: Run the Calibration Tool
```bash
python calibrate_aim.py
```

### Step 2: Position the Body Shoulder (Red Crosshair)
- Look at the left panel showing the body frame (frame 0, idle pose)
- Move your cursor to find the shoulder joint on the body sprite
- Use arrow keys (1px) or Shift+Arrow (5px) to adjust
- Or left-click directly on the shoulder position

**Correct position:** The red dot should be centered on the shoulder joint.

### Step 3: Position the Arm Pivot (Blue Crosshair)
- Look at the right panel showing the arms image
- Use WASD (1px) or Shift+WASD (5px) to adjust
- Or right-click directly on the shoulder position inside the arms

**Correct position:** The blue dot should be at the shoulder joint inside the arms image.

### Step 4: Verify in the Center Preview
- Move your mouse over the center preview area
- The arm should rotate smoothly around the shoulder
- The red and blue dots should stay together at all angles
- If they separate, one of the positions is wrong

### Step 5: Test Other Frames (Optional)
- Press `[` or `]` to cycle through animation frames
- Or press number keys 0-9 to jump to specific frames
- The shoulder position should work consistently across frames
- If not, you may need per-frame offsets (advanced)

### Step 6: Save the Calibration
- Press **S** to save to `player_aim_config.json`
- Console will show:
  ```
  Calibration saved to assets/images/player_aim_config.json
  ```

### Step 7: Exit and Test
- Press **ESC** to close the tool
- Run the game - it will automatically load the calibration
- The arm should now rotate correctly around the shoulder

---

## File Structure

```
random_game_25062026/
├── calibrate_aim.py                    # ← New: Interactive calibration tool
├── player.py                           # ← Modified: Loads and uses calibration
├── settings.py                         # (No changes needed)
├── CALIBRATION_GUIDE.md                # ← New: Detailed user guide
├── assets/
│   └── images/
│       ├── new_player_sheet_noarms.png # (Existing body sprites)
│       ├── player_arms.png             # (Existing arms/gun overlay)
│       └── player_aim_config.json      # ← Created by calibration tool
└── debug/
    └── player_aim_calibration.png      # ← Created by pressing P
```

---

## Key Improvements Over Manual Guessing

### Before
- Hardcoded ratio constants that required trial-and-error
- Invisible coordinate system
- No visual feedback
- Arm orbited away from shoulder

### After
- Interactive visual tool shows exact positions
- Real-time rotation preview
- Pixel-perfect alignment
- Saved configuration for consistency
- Debug PNG output for verification
- Automatic loading in game

---

## Technical Highlights

### Config Loading Logic (player.py)
```python
def _load_aim_config():
    """Load shoulder/pivot calibration from player_aim_config.json"""
    config_path = Path("assets/images/player_aim_config.json")
    
    if not config_path.exists():
        return default_body_shoulder, default_arm_pivot
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Convert pixels to ratios
    body_shoulder_ratio = pygame.math.Vector2(
        config["body_shoulder_offset"][0] / frame_width,
        config["body_shoulder_offset"][1] / frame_height,
    )
    
    return body_shoulder_ratio, arm_pivot_ratio
```

### Rotation Usage (player.py)
```python
def draw_aim_arms(self, surface, draw_rect, target_pos):
    # Get calibrated pivot points
    shoulder_screen = self.aim_shoulder_screen(draw_rect)
    arm_pivot = self.arm_pivot  # From calibration
    
    # Calculate angle to mouse
    angle = math.degrees(math.atan2(dy, dx))
    
    # Rotate and position
    rotated_image, rotated_rect = rotate_around_pivot(
        arms_image,
        angle,
        arm_pivot,        # ← Calibrated
        shoulder_screen,  # ← Calibrated
    )
    
    surface.blit(rotated_image, rotated_rect)
```

---

## Troubleshooting Checklist

### ✓ Arms rotate but orbit away from shoulder
- Run calibration tool
- Verify red crosshair is on actual shoulder (left panel)
- Verify blue crosshair is on actual shoulder in arms image (right panel)
- Check center preview - red and blue dots should stay together
- Re-save calibration

### ✓ Config not loading in game
- Check console for `[AIM] Loaded calibration...` message
- Verify `player_aim_config.json` exists in `assets/images/`
- Verify JSON file contains valid coordinates
- Press P in calibration tool to see debug PNG

### ✓ Different calibration for left vs right facing
- The system automatically handles flipped arms
- `flipped_arm_pivot` is calculated from `arm_pivot`
- If left-facing looks wrong, verify `shoulder_offset()` method

### ✓ Calibration works but seems off at high camera zoom
- Camera offset is handled in screen-space conversion
- Verify `aim_shoulder_screen()` applies camera offset correctly
- Check game.py for camera handling in draw calls

---

## Next Steps After Calibration

1. **Test in gameplay:**
   - Walk, run, jump with aiming active
   - Verify arm stays attached during all animations

2. **Test camera movement:**
   - Move camera horizontally and vertically
   - Arm should track correctly (screen-space math handles this)

3. **Test edge angles:**
   - Aim directly right, left, up, down
   - Aim diagonals
   - Rapid angle changes

4. **Optional improvements:**
   - Per-frame body offsets if needed (see CALIBRATION_GUIDE.md)
   - Muzzle position calibration (where bullets spawn)
   - Different body sprites (if you have multiple character types)

5. **Clean up temporary files:**
   - Delete `temp_pivot_location/` folder when done
   - Keep `player_aim_config.json` for production
   - Keep `debug/player_aim_calibration.png` as reference

---

## Code Integration Summary

### What Changed in player.py
1. Added `_load_aim_config()` function
2. Modified imports (added `json`, `Path`)
3. Enhanced `rotate_around_pivot()` with detailed comments
4. Enhanced `draw_aim_arms()` with system documentation
5. Enhanced `__init__` with calibration explanations
6. Fallback to sensible defaults if config missing

### What Remained Unchanged
- All movement, collision, animation logic
- Enemy, bullet, level systems
- UI and settings
- Game state machine

### Backward Compatibility
- Game runs fine without `player_aim_config.json` (uses defaults)
- Existing game saves not affected
- Can be gradually improved through calibration

---

## Summary

You now have a complete, professional calibration system that:

✅ **Solves the orbiting arm problem** - Clean pivot-based rotation
✅ **Provides visual feedback** - See exact positions in real-time
✅ **Automates configuration** - Save/load coordinates precisely
✅ **Includes fallbacks** - Defaults if config doesn't exist
✅ **Documents thoroughly** - Comments explain all the math
✅ **Enables debugging** - PNG output for verification
✅ **Preserves existing code** - Minimal changes to game logic
✅ **Works at any resolution** - Ratio-based approach scales

To get started: **`python calibrate_aim.py`**

For detailed instructions: **See CALIBRATION_GUIDE.md**
