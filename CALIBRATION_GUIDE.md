# Player Aim Calibration System

## Overview

The player aiming system requires precise calibration of two pivot points:

1. **BODY_SHOULDER_OFFSET**: Where the shoulder joint is located on the player body sprite
2. **ARM_PIVOT**: Where the shoulder joint is located inside the arms/gun overlay image

When these are properly calibrated, the arm will rotate smoothly around the shoulder at all aim angles without orbiting away from the player.

## Problem We're Solving

Pygame's default image rotation rotates around the image center, which causes the arm overlay to orbit away from the shoulder instead of rotating in place. Our solution uses a custom `rotate_around_pivot()` function that rotates around an arbitrary local point and positions the result so that pivot lands exactly where we want it on screen.

**Without calibration:** Arms orbit away from the shoulder
**With calibration:** Arms rotate cleanly around the shoulder joint

## Using the Calibration Tool

### Starting the Tool

```bash
cd /path/to/random_game_25062026
python calibrate_aim.py
```

The tool will:
1. Load the body sprite sheet (4×4 grid) from `assets/images/new_player_sheet_noarms.png`
2. Load the arms overlay from `assets/images/player_arms.png`
3. Display them at 4× zoom for easy visibility
4. Start with frame 0 (idle pose)

### What You'll See

The tool shows three sections:

**Left:** Body frame with a red crosshair marking where you place the shoulder
**Right:** Arms image with a blue crosshair marking the shoulder joint inside it
**Center:** Real-time preview showing arms rotating around the shoulder as you move your mouse

### Adjusting Body Shoulder

The red crosshair marks where the shoulder joint is on the body sprite:

- **Arrow Keys**: Move shoulder by 1 pixel
- **Shift + Arrow Keys**: Move shoulder by 5 pixels
- **Left Click**: Click directly on the body frame to set shoulder position

### Adjusting Arm Pivot

The blue crosshair marks where the shoulder joint is inside the arms image:

- **W/A/S/D**: Move arm pivot by 1 pixel
- **Shift + W/A/S/D**: Move arm pivot by 5 pixels
- **Right Click**: Click directly on the arms image to set pivot position

### Frame Navigation

The tool starts on frame 0 (idle). You can inspect other frames to ensure calibration works across animations:

- **[ and ]**: Cycle through frames 0-11
- **Number Keys (0-9)**: Jump to specific frame (0-9)

Frame layout (4×4 grid):
- **Row 1**: Frame 0 (idle), 1-3 (walking)
- **Row 2**: Frames 4-7 (running)
- **Row 3**: Frames 8-9 (jumping), 10-11 (falling)
- **Row 4**: Frames 12-15 (death)

*Note: You can calibrate using frame 0, then test frames 1-11 to ensure consistency.*

### Real-Time Preview

The center preview shows the arms rotating around the shoulder. As you move your mouse, the aim angle updates live. This helps you verify that:
- ✓ The arm pivot stays attached to the body shoulder
- ✓ The arm doesn't orbit away at any angle
- ✓ The shoulder joint alignment looks correct

### Saving the Calibration

When the crosshairs are positioned correctly, press **S** to save:

```
S: Save calibration to player_aim_config.json
```

This creates `assets/images/player_aim_config.json` with:

```json
{
  "body_shoulder_offset": [x, y],
  "arm_pivot": [x, y],
  "frame_width": 480,
  "frame_height": 480,
  "notes": "Coordinates are local pixel coordinates..."
}
```

### Generating Debug Images

Press **P** to output a visual proof PNG:

```
P: Output debug PNG to debug/player_aim_calibration.png
```

This creates an image showing:
- The body frame with shoulder marked in red
- The arms image with pivot marked in blue
- Text labels with exact coordinates

This helps you verify visually that positions are correct.

### Exiting

Press **ESC** to close the tool without saving.

## Integration with Game Code

Once you've saved the calibration:

1. The game automatically loads `player_aim_config.json` when it starts
2. The player aiming system uses the calibrated values
3. The arm should now rotate correctly around the shoulder

### What Happens If Config Doesn't Exist?

If `player_aim_config.json` is missing, the game falls back to default values:
- `BODY_SHOULDER_OFFSET_RATIO = (0.44, 0.40)`
- `ARM_PIVOT_RATIO = (0.08, 0.50)`

The calibration tool creates this file when you press S.

## Troubleshooting

### "Arm still orbits away at certain angles"

1. **Check alignment in center preview**
   - The red and blue dots should stay together at all angles
   - If they separate, one of the pivots is wrong

2. **Adjust body shoulder (red)**
   - Is the red dot actually on the shoulder joint?
   - Move it with arrow keys or click to adjust

3. **Adjust arm pivot (blue)**
   - Is the blue dot at the shoulder joint INSIDE the arms image?
   - Move it with WASD or right-click to adjust

4. **Test multiple frames**
   - Press [ or ] to cycle through animation frames
   - The shoulder position should work for all frames

### "The pivot looks correct but arm still seems off in game"

1. Check that `player_aim_config.json` exists
2. Verify the game loaded it (check console for `[AIM] Loaded calibration...`)
3. Make sure camera offset is handled correctly in-game (see below)

### "Coordinates in the config seem wrong"

The config stores absolute pixel coordinates, not ratios. For example:
- If frame is 480×480 pixels and shoulder is at 30% width, it saves as ~144 pixels
- The game converts these back to ratios when loading

This is intentional to make the config portable across different sprite sizes.

## Technical Details

### Why Two Pivot Points?

The body and arms are separate sprites with different coordinate systems:

1. **Body Shoulder (BODY_SHOULDER_OFFSET):** 
   - Local coordinates within the body sprite frame
   - Multiplied by player size to get screen position
   - Example: (0.44, 0.40) on a 114×114 player = (50, 45) pixels from top-left

2. **Arm Pivot (ARM_PIVOT):**
   - Local coordinates within the player_arms.png image
   - Changes when the image is scaled
   - Example: (0.08, 0.50) on a ~63×64 scaled arms image = (5, 32) pixels

### The Rotation Math

```python
def rotate_around_pivot(image, angle_degrees, image_pivot, target_pivot):
    # Step 1: Rotate image normally around its center
    rotated_image = pygame.transform.rotate(image, -angle_degrees)
    
    # Step 2: Calculate offset from image center to desired pivot
    image_center = Vector2(image.get_rect().center)
    pivot_offset = image_pivot - image_center
    
    # Step 3: Rotate that offset by the same angle
    rotated_pivot_offset = pivot_offset.rotate(angle_degrees)
    
    # Step 4: Position rotated image so pivot lands at target
    rotated_rect = rotated_image.get_rect(
        center = target_pivot - rotated_pivot_offset
    )
    
    return rotated_image, rotated_rect
```

This ensures the arm's shoulder joint (arm pivot) is positioned exactly at the body's shoulder (target pivot) at all rotation angles.

### In-Game Usage

In [player.py](player.py):

```python
# Calculate screen-space shoulder position
shoulder = self.aim_shoulder_screen(draw_rect)

# Calculate angle to mouse
angle = math.degrees(math.atan2(aim_vector.y, aim_vector.x))

# Rotate and position arm around shoulder
rotated_image, rotated_rect = rotate_around_pivot(
    arms_image,
    angle,
    self.arm_pivot,  # Calibrated pivot inside arms image
    shoulder,        # Calibrated shoulder on body sprite
)

surface.blit(rotated_image, rotated_rect)
```

## Testing After Calibration

1. **Run the game**
   - Verify the arm rotates smoothly around the shoulder
   - Move the mouse in all directions
   - The arm should never orbit away

2. **Test while moving**
   - Walk and run
   - Jump
   - Verify arm stays attached during all animations

3. **Test camera movement**
   - Scroll the camera
   - Arm should still track correctly (handled by screen-space conversion)

## Files Modified/Created

- **calibrate_aim.py** - Interactive calibration tool (new)
- **assets/images/player_aim_config.json** - Calibration data (created by tool)
- **debug/player_aim_calibration.png** - Visual proof (created by P key)
- **player.py** - Updated to load and use calibration
- **settings.py** - Updated with DEBUG_AIM_PIVOT flag

## Quick Reference

| Key | Action |
|-----|--------|
| **Arrow Keys** | Move shoulder ±1px |
| **Shift + Arrows** | Move shoulder ±5px |
| **WASD** | Move arm pivot ±1px |
| **Shift + WASD** | Move arm pivot ±5px |
| **Left Click** | Set shoulder at click position |
| **Right Click** | Set arm pivot at click position |
| **[ ]** | Previous/next frame |
| **0-9** | Jump to frame |
| **S** | Save calibration |
| **P** | Output debug PNG |
| **ESC** | Exit |

## Questions?

If the arm still doesn't rotate correctly after calibration:

1. Generate a debug PNG (press P) - visually inspect coordinates
2. Check console output for `[AIM]` log messages
3. Verify `player_aim_config.json` exists and contains reasonable numbers
4. Try re-calibrating - the shoulder joint alignment is critical
