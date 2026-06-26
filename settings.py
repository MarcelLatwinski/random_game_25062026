SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60

PLAYER_MAX_HEALTH = 100
PLAYER_START_HEALTH = 100
PLAYER_SPEED = 5
PLAYER_JUMP_STRENGTH = 24
GRAVITY = 0.8
MAX_FALL_SPEED = 20
PLAYER_BASE_DAMAGE = 10
PLAYER_FIRE_COOLDOWN = 0.35
PLAYER_BULLET_SPEED = 12
BULLET_WIDTH = 32
BULLET_HEIGHT = 12
HURT_INVINCIBILITY = 0.5
CHARACTER_ASSET_SCALE = 1.5


def scaled_character_size(size):
    return int(round(size * CHARACTER_ASSET_SCALE))


PLAYER_WIDTH = scaled_character_size(76)
PLAYER_HEIGHT = scaled_character_size(76)

WALKER_HP = 40
WALKER_SPEED = 3.2
WALKER_DAMAGE = 10
WALKER_JUMP_INTERVAL = (2.0, 3.0)
WALKER_JUMP_STRENGTH = 24
WALKER_WIDTH = scaled_character_size(76)
WALKER_HEIGHT = scaled_character_size(76)

TANK_HP = 100
TANK_SPEED = 1.6
TANK_DAMAGE = 25
TANK_JUMP_INTERVAL = (3.0, 4.0)
TANK_JUMP_STRENGTH = 24
TANK_WIDTH = scaled_character_size(92)
TANK_HEIGHT = scaled_character_size(92)

FLYING_HP = 30
FLYING_SPEED = 4.4
FLYING_DAMAGE = 8
FLYING_WIDTH = scaled_character_size(76)
FLYING_HEIGHT = scaled_character_size(76)

GROUND_Y = 990

# This is the shared side-scrolling map used by every level.
# Add more width here if you want a longer left-to-right level.
LEVEL_WIDTH = 7200
PLAYER_START = (140, GROUND_Y - PLAYER_HEIGHT)
EXIT_POSITION = (LEVEL_WIDTH - 180, GROUND_Y)
EXIT_WIDTH = 90
EXIT_HEIGHT = 170

# Spawn points wake up when they are this far ahead of the player.
# The points themselves are world positions, so they do not move with the camera.
SPAWN_ACTIVATION_DISTANCE = 800

# Later levels reuse the same map and spawn list, then scale enemies a little.
ENEMY_SPEED_SCALE_PER_LEVEL = 0.06
ENEMY_HEALTH_SCALE_PER_LEVEL = 0.10
GROUND_EMERGENCE_FPS = 8
GROUND_EMERGENCE_DRAW_OFFSET_Y = 12

# Enemy type config keeps asset names and optional spawn animation data together.
# To add future spawn animations, add a SPRITE_SHEETS entry for the new sheet,
# then set spawn_sheet/spawn_animation/spawn_state/starts_active here or on a
# specific ENEMY_SPAWN_POINTS entry.
ENEMY_TYPE_CONFIGS = {
    "walker": {
        "animation_key": "walker_zombie",
        "spawn_sheet": "walker_zombie_ground",
        "spawn_animation": "emerge",
        "spawn_state": "emerging",
        "starts_active": False,
    },
    "tank": {
        "animation_key": "tank_zombie",
        "spawn_sheet": "tank_zombie_ground",
        "spawn_animation": "emerge",
        "spawn_state": "emerging",
        "starts_active": False,
    },
    "flying": {
        "animation_key": "flying_zombie",
        "starts_active": True,
    },
}

# Platform layout for the shared level.
# Each rectangle is (x, y, width, height) in world coordinates.
# To add a platform, add another rectangle to this list.
PLATFORMS = [
    # Safe start and full ground path.
    (0, GROUND_Y, LEVEL_WIDTH, 90),

    # Platform/jumping section.
    (1150, 830, 360, 36),
    (1650, 690, 360, 36),
    (2150, 815, 420, 36),
    (2700, 720, 380, 36),

    # Flying zombie section.
    (3350, 610, 420, 36),
    (3900, 790, 380, 36),

    # Tank and mixed enemy sections.
    (4650, 760, 500, 36),
    (5350, 640, 400, 36),
    (5850, 800, 440, 36),

    # Final horde before the exit.
    (6350, 720, 340, 36),
]

# Zombie spawn points for the shared level.
# x/y are the zombie's bottom-center world position.
# For walkers and tanks, use GROUND_Y or the top y of a platform.
# For flying zombies, use an air y such as 580 or 620.
# To add a spawn point, add another {"x": ..., "y": ..., "type": "..."} entry.
# Optional "min_level" makes that spawn appear only from that level onward.
# Optional spawn_sheet/spawn_animation fields override ENEMY_TYPE_CONFIGS for
# one spawn point, so a future enemy can play a custom spawn animation there.
ENEMY_SPAWN_POINTS = [
    # Basic walker section.
    {"x": 1120, "y": GROUND_Y, "type": "walker"},
    {"x": 1420, "y": GROUND_Y, "type": "walker"},

    # Platform/jumping section.
    {"x": 1320, "y": 830, "type": "walker"},
    {"x": 1830, "y": 690, "type": "walker"},
    {"x": 2360, "y": 815, "type": "walker"},
    {"x": 2860, "y": 720, "type": "walker"},
    {"x": 1750, "y": GROUND_Y, "type": "tank", "min_level": 3},
    {"x": 2500, "y": 610, "type": "flying", "min_level": 2},

    # Flying zombie section.
    {"x": 3400, "y": 620, "type": "flying"},
    {"x": 3700, "y": 560, "type": "flying"},
    {"x": 4100, "y": GROUND_Y, "type": "walker"},

    # Tank zombie section.
    {"x": 4550, "y": GROUND_Y, "type": "tank"},
    {"x": 4900, "y": GROUND_Y, "type": "walker"},
    {"x": 5150, "y": GROUND_Y, "type": "tank"},
    {"x": 4720, "y": GROUND_Y, "type": "walker", "min_level": 2},

    # Mixed enemy section.
    {"x": 5450, "y": 640, "type": "walker"},
    {"x": 5650, "y": 590, "type": "flying"},
    {"x": 5900, "y": GROUND_Y, "type": "tank"},
    {"x": 6150, "y": GROUND_Y, "type": "walker"},
    {"x": 5750, "y": GROUND_Y, "type": "walker", "min_level": 3},

    # Final horde before the exit.
    {"x": 6350, "y": GROUND_Y, "type": "walker"},
    {"x": 6500, "y": GROUND_Y, "type": "walker"},
    {"x": 6650, "y": GROUND_Y, "type": "tank"},
    {"x": 6750, "y": 620, "type": "flying"},
    {"x": 6880, "y": GROUND_Y, "type": "walker"},
    {"x": 6600, "y": GROUND_Y, "type": "walker", "min_level": 2},
    {"x": 6820, "y": GROUND_Y, "type": "tank", "min_level": 4},
]

# These entries keep the game level-based and define how many times the shared
# map can be replayed before the final victory screen.
LEVELS = [
    {"number": 1},
    {"number": 2},
    {"number": 3},
    {"number": 4},
    {"number": 5},
    {"number": 6},
    {"number": 7},
    {"number": 8},
    {"number": 9},
    {"number": 10},
]

UPGRADES = [
    {
        "name": "Bigger Heart",
        "description": "+25 max HP and heal 25 HP",
        "effect_id": "bigger_heart",
    },
    {
        "name": "Stronger Bullets",
        "description": "Bullet damage x1.2",
        "effect_id": "stronger_bullets",
    },
    {
        "name": "Faster Trigger",
        "description": "Shoot faster",
        "effect_id": "faster_trigger",
    },
    {
        "name": "Runner's Boots",
        "description": "Move faster",
        "effect_id": "runners_boots",
    },
    {
        "name": "Spring Legs",
        "description": "Jump higher",
        "effect_id": "spring_legs",
    },
    {
        "name": "Quick Rounds",
        "description": "Bullets travel faster",
        "effect_id": "quick_rounds",
    },
    {
        "name": "Medkit",
        "description": "Heal 50 HP",
        "effect_id": "medkit",
    },
]

IMAGE_PATHS = {
    "platform": "assets/images/platform.png",
    "background": "assets/images/background.png",
}

# Sprite sheets are sliced by animation.load_animation_set.
# To add an animation later, add its frames to the sheet and add a named entry
# under "animations" with the row number, frame columns, fps, and loop setting.
SPRITE_SHEETS = {
    # Player sheet configuration.
    # This main sheet supplies idle, shoot, jump, and hurt. Individual
    # animations can override it with their own "sheet" config, as run does.
    "player": {
        "path": "assets/images/new_player_sheet.png",
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        # The source art is arranged as a 4x4 sheet, but the poses do not sit
        # inside perfectly even cells. These rectangles keep each source frame
        # from clipping into the row above/below it.
        "frame_rects": [
            [
                (121, 49, 148, 250),
                (394, 50, 149, 249),
                (678, 49, 150, 250),
                (967, 50, 151, 249),
            ],
            [
                (106, 363, 194, 230),
                (354, 363, 213, 230),
                (657, 363, 191, 232),
                (939, 363, 211, 227),
            ],
            [
                (86, 636, 197, 227),
                (368, 636, 237, 227),
                (668, 636, 240, 227),
                (951, 636, 193, 227),
            ],
            [
                (84, 886, 198, 260),
                (355, 901, 198, 225),
                (639, 918, 305, 261),
                (936, 922, 212, 257),
            ],
        ],
        "target_size": (PLAYER_WIDTH, PLAYER_HEIGHT),
        "remove_light_background": True,
        "trim_transparent": True,
        "align": "bottom",
        # Row mapping:
        # row 0 idle loops, row 2 shoot plays once,
        # row 3 frames 0-1 jump while airborne, row 3 frames 2-3 hurt once.
        # The run animation uses player_running_sheet.png below. To assign a
        # separate sheet to another animation, add a "sheet" block with its
        # path/columns/rows to that animation config.
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "run": {
                "sheet": {
                    "path": "assets/images/player_running_sheet.png",
                    "columns": 8,
                    "rows": 1,
                    "frame_width": None,
                    "frame_height": None,
                    "margin": 0,
                    "spacing": 0,
                },
                "row": 0,
                "frames": [0, 1, 2, 3, 4, 5, 6, 7],
                "fps": 12,
                "loop": True,
            },
            "shoot": {"row": 2, "frames": [0, 1, 2, 3], "fps": 12, "loop": False},
            "jump": {"row": 3, "frames": [0, 1], "fps": 10, "loop": True},
            "hurt": {"row": 3, "frames": [2, 3], "fps": 10, "loop": False},
        },
    },
    "walker_zombie": {
        "path": "assets/images/walker_zombie_sheet.png",
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (WALKER_WIDTH, WALKER_HEIGHT),
        "remove_light_background": True,
        "trim_transparent": True,
        "align": "bottom",
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "walk": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
            "attack": {"row": 2, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
        },
    },
    "walker_zombie_ground": {
        "path": "assets/images/walker_zombie_ground_sheet.png",
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (WALKER_WIDTH, WALKER_HEIGHT),
        "remove_light_background": True,
        "background_min_value": 220,
        "background_channel_spread": 32,
        "trim_transparent": True,
        "align": "bottom",
        "animations": {
            "emerge": {
                "rows": [0, 1],
                "fps": GROUND_EMERGENCE_FPS,
                "loop": False,
                "draw_offset": (0, GROUND_EMERGENCE_DRAW_OFFSET_Y),
            },
        },
    },
    "tank_zombie": {
        "path": "assets/images/tank_zombie_sheet.png",
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (TANK_WIDTH, TANK_HEIGHT),
        "remove_light_background": True,
        "trim_transparent": True,
        "align": "bottom",
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "walk": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
            "heavy_attack": {"row": 2, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
        },
    },
    "tank_zombie_ground": {
        "path": "assets/images/tank_zombie_ground_sheet.png",
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (TANK_WIDTH, TANK_HEIGHT),
        "remove_light_background": True,
        "background_min_value": 220,
        "background_channel_spread": 32,
        "trim_transparent": True,
        "align": "bottom",
        "animations": {
            "emerge": {
                "rows": [0, 1],
                "fps": GROUND_EMERGENCE_FPS,
                "loop": False,
                "draw_offset": (0, GROUND_EMERGENCE_DRAW_OFFSET_Y),
            },
        },
    },
    "flying_zombie": {
        "path": "assets/images/flying_zombie_sheet.png",
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (FLYING_WIDTH, FLYING_HEIGHT),
        "remove_light_background": True,
        "trim_transparent": True,
        "align": "bottom",
        "animations": {
            "hover_idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "fly": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
            "attack": {"row": 2, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
        },
    },
    "bullet": {
        "path": "assets/images/bullet_sheet.png",
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (BULLET_WIDTH, BULLET_HEIGHT),
        "remove_light_background": True,
        "trim_transparent": True,
        "align": "center",
        "animations": {
            "travel": {"row": 0, "frames": [0, 1, 2, 3], "fps": 14, "loop": True},
            "impact": {"row": 1, "frames": [0, 1, 2, 3], "fps": 16, "loop": False},
        },
    },
}

COLOR_BACKGROUND = (173, 216, 230)
COLOR_PLAYER = (50, 150, 230)
COLOR_WALKER = (100, 220, 120)
COLOR_TANK = (220, 100, 110)
COLOR_FLYING = (220, 220, 80)
COLOR_BULLET = (255, 215, 90)
COLOR_PLATFORM = (139, 69, 19)
COLOR_PLATFORM_OUTLINE = (50, 205, 50)
COLOR_TEXT = (235, 235, 235)
COLOR_UI_BG = (25, 25, 35)
COLOR_HEALTH = (220, 60, 60)
COLOR_HURT = (255, 80, 80)
