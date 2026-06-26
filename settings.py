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
CHARACTER_ASSET_SCALE = 1.2


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

SPAWN_INTERVAL_MIN = 1.2
SPAWN_INTERVAL_MAX = 2.0
LEFT_SPAWN_RANGE = (60, 180)
RIGHT_SPAWN_RANGE = (1740, 1860)
GROUND_Y = 990

PLATFORMS = [
    (0, 990, 1920, 90),
    (240, 750, 405, 36),
    (758, 520, 405, 36),
    (1275, 750, 405, 36),
]

LEVELS = [
    {"walkers": 3, "tanks": 0, "flyers": 0},
    {"walkers": 5, "tanks": 0, "flyers": 0},
    {"walkers": 5, "tanks": 1, "flyers": 0},
    {"walkers": 6, "tanks": 1, "flyers": 0},
    {"walkers": 6, "tanks": 2, "flyers": 0},
    {"walkers": 5, "tanks": 1, "flyers": 2},
    {"walkers": 6, "tanks": 1, "flyers": 3},
    {"walkers": 7, "tanks": 2, "flyers": 3},
    {"walkers": 8, "tanks": 2, "flyers": 4},
    {"walkers": 7, "tanks": 2, "flyers": 5},
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
    "player": {
        "path": "assets/images/player_sheet.png",
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (PLAYER_WIDTH, PLAYER_HEIGHT),
        "remove_light_background": True,
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "run": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
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
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "walk": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
            "attack": {"row": 2, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
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
        "animations": {
            "idle": {"row": 0, "frames": [0, 1, 2, 3], "fps": 8, "loop": True},
            "walk": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": True},
            "heavy_attack": {"row": 2, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
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
