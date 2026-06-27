#!/usr/bin/env python3
"""Visual test: Show player body and arms together to check alignment"""

import pygame
import math
from settings import SPRITE_SHEETS, PLAYER_WIDTH, PLAYER_HEIGHT
from animation import load_animation_set
from player import (
    BODY_SHOULDER_OFFSET_RATIO, ARM_PIVOT_RATIO,
    rotate_around_pivot
)

pygame.init()
screen = pygame.display.set_mode((1200, 800))
pygame.display.set_caption("Body + Arms Alignment Test")
clock = pygame.time.Clock()

# Load body animation
body_animations = load_animation_set(SPRITE_SHEETS["player"])
idle_anim = body_animations.get("idle")
body_frame = idle_anim.frames[0] if idle_anim and hasattr(idle_anim, 'frames') else None

# Load arms
from animation import flipped_surface
arms_full = pygame.image.load("assets/images/player_arms.png")
arm_width = max(1, int(PLAYER_WIDTH * 0.56))
arm_scale = arm_width / arms_full.get_width()
arm_target_h = max(1, int(arms_full.get_height() * arm_scale))
arms_scaled = pygame.transform.smoothscale(arms_full, (arm_width, arm_target_h))

# Calculate positions
body_shoulder_x = PLAYER_WIDTH * BODY_SHOULDER_OFFSET_RATIO.x
body_shoulder_y = PLAYER_HEIGHT * BODY_SHOULDER_OFFSET_RATIO.y

arm_pivot_x = arms_scaled.get_width() * ARM_PIVOT_RATIO.x
arm_pivot_y = arms_scaled.get_height() * ARM_PIVOT_RATIO.y

print(f"Body frame size: {body_frame.get_size() if body_frame else 'N/A'}")
print(f"Body shoulder (calibrated): ({body_shoulder_x:.1f}, {body_shoulder_y:.1f})")
print(f"Arms scaled size: {arms_scaled.get_size()}")
print(f"Arm pivot (calibrated): ({arm_pivot_x:.1f}, {arm_pivot_y:.1f})")

# Display positions
body_screen_x = 150
body_screen_y = 200
arm_screen_x = 550
arm_screen_y = 200
comparison_x = 950
comparison_y = 200

running = True
angle = 0

while running:
    dt = clock.tick(60)
    angle = (angle + 1) % 360
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    
    screen.fill((20, 20, 30))
    
    # LEFT: Body sprite with shoulder marked
    if body_frame:
        screen.blit(body_frame, (body_screen_x, body_screen_y))
        
        # Draw shoulder marker on body
        shoulder_screen = (
            body_screen_x + body_shoulder_x,
            body_screen_y + body_shoulder_y
        )
        pygame.draw.circle(screen, (255, 50, 50), shoulder_screen, 10)
        pygame.draw.circle(screen, (100, 200, 100), shoulder_screen, 6)
    
    # MIDDLE: Arms sprite with pivot marked
    screen.blit(arms_scaled, (arm_screen_x, arm_screen_y))
    
    # Draw arm pivot
    arm_pivot_screen = (
        arm_screen_x + arm_pivot_x,
        arm_screen_y + arm_pivot_y
    )
    pygame.draw.circle(screen, (255, 50, 50), arm_pivot_screen, 10)
    pygame.draw.circle(screen, (100, 200, 100), arm_pivot_screen, 6)
    
    # RIGHT: Body + Arms combined with rotation
    if body_frame:
        screen.blit(body_frame, (comparison_x, comparison_y))
        
        # Draw shoulder on body
        body_shoulder_on_screen = (
            comparison_x + body_shoulder_x,
            comparison_y + body_shoulder_y
        )
        pygame.draw.circle(screen, (255, 50, 50), body_shoulder_on_screen, 10)
        
        # Rotate and position arms to attach at shoulder
        rotated_arms, rotated_rect = rotate_around_pivot(
            arms_scaled,
            angle,
            pygame.math.Vector2(arm_pivot_x, arm_pivot_y),
            pygame.math.Vector2(body_shoulder_on_screen),
        )
        screen.blit(rotated_arms, rotated_rect)
        
        # Mark where arm pivot ended up
        pygame.draw.circle(screen, (100, 200, 100), body_shoulder_on_screen, 6)
    
    # Labels
    font = pygame.font.SysFont("monospace", 16, bold=True)
    info_font = pygame.font.SysFont("monospace", 12)
    
    screen.blit(font.render("Body + Shoulder", True, (255, 255, 255)), (body_screen_x, body_screen_y - 40))
    screen.blit(font.render("Arms + Pivot", True, (255, 255, 255)), (arm_screen_x, arm_screen_y - 40))
    screen.blit(font.render("Combined (Rotating)", True, (255, 255, 255)), (comparison_x - 50, comparison_y - 40))
    
    screen.blit(info_font.render(f"Angle: {angle}°", True, (200, 200, 200)), (comparison_x, comparison_y + PLAYER_HEIGHT + 150))
    
    # Instructions
    info = [
        "RED circles = calibration points (should overlap)",
        "GREEN circles = inner markers",
        "",
        "If RED circles DON'T overlap on the combined view,",
        "calibration is wrong. Arms won't attach at shoulder.",
        "",
        "Check:",
        "- Left: Does shoulder look correct on character?",
        "- Middle: Is pivot at the arms' shoulder joint?",
        "- Right: Do the circles overlap as arms rotate?"
    ]
    
    for i, text in enumerate(info):
        screen.blit(info_font.render(text, True, (180, 180, 200)), (50, 550 + i * 18))
    
    pygame.display.flip()

pygame.quit()
