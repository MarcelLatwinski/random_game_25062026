import random
from pathlib import Path

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
SHOW_FPS_COUNTER = True
DEBUG_AIM_PIVOT = True
MAX_FRAME_DT = 1 / 20

PLAYER_MAX_HEALTH = 100
PLAYER_START_HEALTH = 100
PLAYER_SPEED = 8
PLAYER_RUN_SPEED_MULTIPLIER = 1.5
PLAYER_JUMP_STRENGTH = 30
GRAVITY = 1.2
MAX_FALL_SPEED = 30
PLAYER_BASE_DAMAGE = 10
PLAYER_FIRE_COOLDOWN = 0.35
PLAYER_BULLET_SPEED = 16
BULLET_WIDTH = 32
BULLET_HEIGHT = 12
HURT_INVINCIBILITY = 0.5
MAGAZINE_SIZE = 10
STARTING_TOTAL_AMMO = 50
STARTING_MAG_AMMO = 10
STARTING_RESERVE_AMMO = 40
MAX_RESERVE_AMMO = 60
RELOAD_DURATION = 0.5
RELOAD_PROMPT_DURATION = 1.0
RELOAD_PROMPT_RISE = 42
CHARACTER_ASSET_SCALE = 1.725
PLAYER_ASSET_SCALE = 1.92
TANK_ASSET_SCALE = 1.875


def scaled_character_size(size):
    return int(round(size * CHARACTER_ASSET_SCALE))


def scaled_player_size(size):
    return int(round(size * PLAYER_ASSET_SCALE))


def scaled_tank_size(size):
    return int(round(size * TANK_ASSET_SCALE))


PLAYER_WIDTH = scaled_player_size(76)
PLAYER_HEIGHT = scaled_player_size(76)

WALKER_HP = 40
WALKER_SPEED = 4.8
WALKER_DAMAGE = 10
WALKER_JUMP_INTERVAL = (1.4, 2.2)
WALKER_JUMP_STRENGTH = 30
WALKER_WIDTH = scaled_character_size(76)
WALKER_HEIGHT = scaled_character_size(76)

TANK_HP = 100
TANK_SPEED = 2.6
TANK_DAMAGE = 25
TANK_JUMP_INTERVAL = (2.0, 3.0)
TANK_JUMP_STRENGTH = 30
TANK_WIDTH = scaled_tank_size(92)
TANK_HEIGHT = scaled_tank_size(92)

FLYING_HP = 30
FLYING_SPEED = 6.4
FLYING_DAMAGE = 8
FLYING_WIDTH = scaled_character_size(56)
FLYING_HEIGHT = scaled_character_size(72)
FLYING_SPRITE_WIDTH = scaled_character_size(112)
FLYING_SPRITE_HEIGHT = scaled_character_size(112)
FLYING_SPRITE_DRAW_OFFSET = (
    (FLYING_WIDTH - FLYING_SPRITE_WIDTH) // 2,
    (FLYING_HEIGHT - FLYING_SPRITE_HEIGHT) // 2,
)

GROUND_Y = 990
GROUND_COLLISION_HEIGHT = SCREEN_HEIGHT - GROUND_Y

# This is the shared side-scrolling map used by every level.
# Add more width here if you want a longer left-to-right level.
LEVEL_WIDTH = 9800
LEVEL_HEIGHT = SCREEN_HEIGHT
PLAYER_START = (140, GROUND_Y - PLAYER_HEIGHT)
EXIT_POSITION = (LEVEL_WIDTH - 180, GROUND_Y)
EXIT_WIDTH = 90
EXIT_HEIGHT = 170

# The new environment art lives in a separate folder. These helpers find the
# actual file extension so level data can refer to "background_1" or
# "platform_3" instead of hard-coding ".png" everywhere.
ENVIRONMENT_ASSET_DIRS = (
    "assets/images/processed",
    "assets/images/background_platforms",
    "assets/images",
)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
PROCESSED_ASSET_DIR = Path("assets/images/processed")
BACKGROUND_ASSET_KEYS = (
    "background_1",
    "background_2",
    "background_3",
)
PLATFORM_KEYS = (
    "platform_1",
    "platform_2",
    "platform_3",
    "platform_4",
)
FLOOR_ASSET_KEY = "floor"
PLATFORM_COLLIDER_HEIGHT = 36


def find_image_asset(asset_name):
    for directory in ENVIRONMENT_ASSET_DIRS:
        for extension in IMAGE_EXTENSIONS:
            path = Path(directory) / f"{asset_name}{extension}"
            if path.exists():
                return str(path)
    return None


def is_preprocessed_image_path(path):
    if not path:
        return False
    try:
        return Path(path).resolve().parent == PROCESSED_ASSET_DIR.resolve()
    except OSError:
        return False


def image_asset_path(asset_name):
    path = find_image_asset(asset_name)
    if path:
        return path
    return str(Path("assets/images") / f"{asset_name}.png")


def needs_runtime_background_cleanup(path):
    return not is_preprocessed_image_path(path)


ENVIRONMENT_IMAGE_PATHS = {
    asset_name: find_image_asset(asset_name)
    for asset_name in BACKGROUND_ASSET_KEYS + PLATFORM_KEYS + (FLOOR_ASSET_KEY,)
}


def random_platform_key():
    return random.choice(PLATFORM_KEYS)

# These three images replace the old four-background setup.
# To use better art later, keep these same filenames or change the names here.
# To tweak parallax later, edit the speed values: smaller is farther away,
# larger is closer to the camera.
BACKGROUND_LAYERS = [
    {"image": "background_1", "speed": 0.15},  # far skyline, slowest
    {"image": "background_2", "speed": 0.40},  # ruined structure, middle speed
    {"image": "background_3", "speed": 0.70},  # close detail strip, fastest
]

# These RGB files were exported with a fake checkerboard background. The loader
# turns the near-white checkerboard pixels transparent while preserving any real
# alpha channel if future versions are saved with transparency.
BACKGROUND_CUTOUT_KEYS = ("background_2", "background_3")

# Keep this off when using full background artwork. The old procedural
# decorations draw extra rectangles and lines over the scene, which can look
# like random background artifacts.
DRAW_PROCEDURAL_DECORATIONS = False

# Draw the actual gameplay platform sprites. This is separate from the giant
# full-level ground visual below, which can look like an old map underlay.
DRAW_PLATFORM_VISUALS = True
DRAW_GROUND_PLATFORM_VISUAL = False
DRAW_PLATFORM_COLLISION_MARKERS = False
DRAW_FLOOR_VISUAL = True

# The bottom floor's collision still starts at GROUND_Y. The new floor PNG has
# transparent/fake-transparent space above the concrete, so it is drawn this
# many pixels above the collision line. If the player floats above the floor,
# increase this value. If the player sinks into the floor, decrease it.
FLOOR_SURFACE_OFFSET_Y = 204

# Spawn points wake up when they are this far ahead of the player.
# The points themselves are world positions, so they do not move with the camera.
SPAWN_ACTIVATION_DISTANCE = 800

# Small performance helpers. These keep drawing and collision checks focused on
# the part of the level the player can actually see or touch soon.
DRAW_MARGIN = 220
COLLISION_QUERY_MARGIN = 320
BULLET_COLLISION_QUERY_MARGIN = 140
ENEMY_PLATFORM_QUERY_MARGIN = 1100
ENEMY_AI_ACTIVE_DISTANCE = SCREEN_WIDTH + 900

# Later levels reuse the same map and spawn list, then scale enemies a little.
ENEMY_SPEED_SCALE_PER_LEVEL = 0.06
ENEMY_HEALTH_SCALE_PER_LEVEL = 0.10
GROUND_EMERGENCE_FPS = 8
GROUND_EMERGENCE_DRAW_OFFSET_Y = 12
AMMO_PICKUP_AMOUNT = 10
HEALTH_PICKUP_AMOUNT = 25
AMMO_DROP_CHANCE = 0.25
HEALTH_DROP_CHANCE = 0.15

# Pickup sprite source rectangles are adjustable because ammo_health_kit.png
# stores both pickup sprites in one image with padding around the art.
PICKUP_SPRITES = {
    "ammo": {
        "source_x": 60,
        "source_y": 295,
        "source_width": 430,
        "source_height": 360,
        "draw_width": 88,
        "draw_height": 74,
    },
    "health": {
        "source_x": 570,
        "source_y": 300,
        "source_width": 390,
        "source_height": 330,
        "draw_width": 84,
        "draw_height": 72,
    },
}

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

# Section-based level layout for the shared skyscraper level.
# Move platforms later by editing the x, y, width, and height values below.
# Add more chunks by appending another section dict with platforms,
# decorations, enemy_spawns, and pickups.
def platform(x, y, width, height, sprite, visual_height=None, drop_through=True):
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "sprite": sprite,
        "visual_height": visual_height,
        "collidable": True,
        "drop_through": drop_through,
    }


def jump_height_pixels():
    return int(round((PLAYER_JUMP_STRENGTH ** 2) / (2 * GRAVITY)))


def platform_from_layer(
    x,
    width,
    layer,
    sprite=None,
    visual_height=None,
    height=PLATFORM_COLLIDER_HEIGHT,
    variation=0,
):
    ratio = 0.8 if layer == 0 else 1.6
    base_y = GROUND_Y - height - int(round(jump_height_pixels() * ratio))
    return platform(
        x,
        base_y + variation,
        width,
        height,
        sprite or random_platform_key(),
        visual_height=visual_height,
    )


def decoration(kind, x, y, width, height, layer="back"):
    return {
        "type": kind,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "layer": layer,
        "collidable": False,
    }


def enemy_spawn(x, y, enemy_type, section, min_level=1, trigger_distance=None, amount=1, spacing=80):
    return {
        "x": x,
        "y": y,
        "type": enemy_type,
        "enemyType": enemy_type,
        "section": section,
        "min_level": min_level,
        "trigger_distance": trigger_distance or SPAWN_ACTIVATION_DISTANCE,
        "amount": amount,
        "spacing": spacing,
    }


def pickup_spawn(x, y, pickup_type, section, amount=None, min_level=1):
    return {
        "x": x,
        "y": y,
        "type": pickup_type,
        "section": section,
        "amount": amount,
        "min_level": min_level,
    }


LEVEL_SECTIONS = [
    {
        "name": "Ruined Lobby",
        "start_x": 0,
        "end_x": 1200,
        "platforms": [
            # This is the simple collision rectangle for the bottom floor. The
            # PNG art is drawn separately in game.py so the transparent area
            # above the concrete never becomes physical collision.
            platform(
                0,
                GROUND_Y,
                LEVEL_WIDTH,
                GROUND_COLLISION_HEIGHT,
                None,
                drop_through=False,
            ),
            platform_from_layer(430, 300, 0, visual_height=112, variation=10),
            platform_from_layer(800, 320, 1, visual_height=116, variation=-12),
        ],
        "decorations": [
            decoration("broken_floor", 260, 950, 250, 34),
            decoration("rubble", 560, 930, 210, 60, layer="front"),
            decoration("broken_desk", 810, 914, 160, 76),
            decoration("hanging_cable", 980, 620, 18, 250, layer="front"),
            decoration("cracked_wall", 160, 590, 190, 210),
        ],
        "enemy_spawns": [
            enemy_spawn(1030, GROUND_Y, "walker", "Ruined Lobby", min_level=2),
        ],
        "pickups": [
            pickup_spawn(380, GROUND_Y, "ammo", "Ruined Lobby", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(930, 835, "health", "Ruined Lobby", amount=HEALTH_PICKUP_AMOUNT, min_level=2),
        ],
    },
    {
        "name": "Open Office",
        "start_x": 1200,
        "end_x": 2500,
        "platforms": [
            platform_from_layer(1320, 320, 0, visual_height=120, variation=8),
            platform_from_layer(1800, 340, 1, visual_height=118, variation=-16),
            platform_from_layer(2200, 280, 0, visual_height=124, variation=14),
        ],
        "decorations": [
            decoration("broken_desk", 1340, 914, 180, 76),
            decoration("broken_desk", 1860, 914, 200, 76),
            decoration("exposed_beam", 1580, 650, 360, 34),
            decoration("hanging_cable", 2140, 600, 18, 260, layer="front"),
            decoration("cracked_wall", 2320, 560, 240, 240),
        ],
        "enemy_spawns": [
            enemy_spawn(1390, GROUND_Y, "walker", "Open Office"),
            enemy_spawn(1720, GROUND_Y, "walker", "Open Office", min_level=2),
            enemy_spawn(2100, GROUND_Y, "walker", "Open Office"),
            enemy_spawn(1510, 835, "walker", "Open Office", min_level=2),
            enemy_spawn(2360, GROUND_Y, "tank", "Open Office", min_level=4),
        ],
        "pickups": [
            pickup_spawn(1960, GROUND_Y, "ammo", "Open Office", amount=AMMO_PICKUP_AMOUNT),
        ],
    },
    {
        "name": "Broken Floor",
        "start_x": 2500,
        "end_x": 3850,
        "platforms": [
            platform_from_layer(2660, 300, 0, visual_height=118, variation=12),
            platform_from_layer(3080, 290, 1, visual_height=112, variation=-18),
            platform_from_layer(3460, 300, 0, visual_height=116, variation=10),
            platform_from_layer(3840, 260, 1, visual_height=120, variation=-14),
        ],
        "decorations": [
            decoration("broken_floor", 2580, 952, 280, 36),
            decoration("broken_floor", 3160, 952, 320, 36),
            decoration("rubble", 3490, 932, 260, 58, layer="front"),
            decoration("cracked_wall", 2820, 560, 260, 260),
            decoration("hanging_cable", 3610, 570, 16, 270, layer="front"),
        ],
        "enemy_spawns": [
            enemy_spawn(2760, GROUND_Y, "walker", "Broken Floor"),
            enemy_spawn(3180, 770, "walker", "Broken Floor"),
            enemy_spawn(3520, GROUND_Y, "walker", "Broken Floor", min_level=2),
            enemy_spawn(3680, 620, "flying", "Broken Floor", min_level=2),
        ],
        "pickups": [
            pickup_spawn(3140, 770, "ammo", "Broken Floor", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(3820, GROUND_Y, "health", "Broken Floor", amount=HEALTH_PICKUP_AMOUNT),
        ],
    },
    {
        "name": "Overgrown Interior",
        "start_x": 3850,
        "end_x": 5300,
        "platforms": [
            platform_from_layer(4020, 320, 0, visual_height=132, variation=8),
            platform_from_layer(4580, 300, 1, visual_height=130, variation=-20),
            platform_from_layer(5000, 280, 0, visual_height=132, variation=12),
        ],
        "decorations": [
            decoration("vines", 3960, 520, 120, 330, layer="front"),
            decoration("overgrowth", 4200, 920, 360, 70, layer="front"),
            decoration("collapsed_structure", 4680, 880, 300, 110),
            decoration("vines", 4920, 470, 170, 400, layer="front"),
            decoration("cracked_wall", 5140, 560, 250, 250),
        ],
        "enemy_spawns": [
            enemy_spawn(4160, GROUND_Y, "walker", "Overgrown Interior"),
            enemy_spawn(4360, 800, "walker", "Overgrown Interior", min_level=2),
            enemy_spawn(4720, GROUND_Y, "tank", "Overgrown Interior", min_level=3),
            enemy_spawn(5050, GROUND_Y, "walker", "Overgrown Interior"),
            enemy_spawn(5170, 590, "flying", "Overgrown Interior", min_level=2),
        ],
        "pickups": [
            pickup_spawn(4680, 690, "ammo", "Overgrown Interior", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(5200, GROUND_Y, "health", "Overgrown Interior", amount=HEALTH_PICKUP_AMOUNT),
        ],
    },
    {
        "name": "Elevator Shaft",
        "start_x": 5300,
        "end_x": 6600,
        "platforms": [
            platform_from_layer(5340, 220, 0, visual_height=116, variation=14),
            platform_from_layer(5680, 220, 1, visual_height=112, variation=-12),
            platform_from_layer(6020, 220, 0, visual_height=112, variation=10),
            platform_from_layer(6340, 220, 1, visual_height=120, variation=-16),
            platform_from_layer(6540, 220, 0, visual_height=120, variation=8),
        ],
        "decorations": [
            decoration("elevator_door", 5320, 700, 180, 290),
            decoration("hanging_cable", 5660, 350, 18, 520, layer="front"),
            decoration("hanging_cable", 6040, 300, 18, 560, layer="front"),
            decoration("exposed_beam", 5790, 450, 380, 34),
            decoration("warning_light", 6370, 610, 44, 44, layer="front"),
        ],
        "enemy_spawns": [
            enemy_spawn(5500, 870, "walker", "Elevator Shaft"),
            enemy_spawn(5870, 760, "walker", "Elevator Shaft", min_level=2),
            enemy_spawn(5960, 430, "flying", "Elevator Shaft"),
            enemy_spawn(6280, 590, "flying", "Elevator Shaft", min_level=2),
            enemy_spawn(6400, GROUND_Y, "tank", "Elevator Shaft", min_level=3),
        ],
        "pickups": [
            pickup_spawn(5560, 640, "ammo", "Elevator Shaft", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(6400, 700, "health", "Elevator Shaft", amount=HEALTH_PICKUP_AMOUNT),
        ],
    },
    {
        "name": "Exterior Ledge",
        "start_x": 6600,
        "end_x": 8100,
        "platforms": [
            platform_from_layer(6680, 300, 0, visual_height=118, variation=10),
            platform_from_layer(7160, 280, 1, visual_height=112, variation=-18),
            platform_from_layer(7560, 320, 0, visual_height=118, variation=8),
            platform_from_layer(7900, 300, 1, visual_height=130, variation=-14),
        ],
        "decorations": [
            decoration("shattered_window", 6660, 530, 280, 320),
            decoration("exposed_beam", 7040, 650, 420, 30),
            decoration("hanging_cable", 7380, 520, 18, 300, layer="front"),
            decoration("broken_floor", 7700, 952, 340, 36),
            decoration("rubble", 7930, 928, 280, 62, layer="front"),
        ],
        "enemy_spawns": [
            enemy_spawn(6780, 620, "flying", "Exterior Ledge"),
            enemy_spawn(7240, GROUND_Y, "walker", "Exterior Ledge"),
            enemy_spawn(7440, 600, "flying", "Exterior Ledge", min_level=2),
            enemy_spawn(7900, GROUND_Y, "tank", "Exterior Ledge", min_level=2),
            enemy_spawn(8120, GROUND_Y, "walker", "Exterior Ledge"),
        ],
        "pickups": [
            pickup_spawn(7260, 760, "ammo", "Exterior Ledge", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(8030, GROUND_Y, "health", "Exterior Ledge", amount=HEALTH_PICKUP_AMOUNT, min_level=2),
        ],
    },
    {
        "name": "Rooftop",
        "start_x": 8100,
        "end_x": LEVEL_WIDTH,
        "platforms": [
            platform_from_layer(8340, 320, 0, visual_height=122, variation=12),
            platform_from_layer(8840, 320, 1, visual_height=126, variation=-16),
            platform_from_layer(9340, 300, 0, visual_height=118, variation=10),
        ],
        "decorations": [
            decoration("rooftop_antenna", 8240, 700, 80, 290, layer="front"),
            decoration("rubble", 8520, 930, 300, 60, layer="front"),
            decoration("warning_light", 8940, 650, 44, 44, layer="front"),
            decoration("hanging_cable", 9180, 560, 18, 270, layer="front"),
            decoration("collapsed_structure", 9400, 890, 300, 100),
        ],
        "enemy_spawns": [
            enemy_spawn(8360, GROUND_Y, "walker", "Rooftop"),
            enemy_spawn(8560, GROUND_Y, "walker", "Rooftop", amount=2, spacing=95),
            enemy_spawn(8900, GROUND_Y, "tank", "Rooftop"),
            enemy_spawn(9100, 600, "flying", "Rooftop"),
            enemy_spawn(9300, GROUND_Y, "walker", "Rooftop", min_level=2, amount=2, spacing=90),
            enemy_spawn(9500, GROUND_Y, "tank", "Rooftop", min_level=2),
            enemy_spawn(9600, 620, "flying", "Rooftop", min_level=3),
        ],
        "pickups": [
            pickup_spawn(8260, GROUND_Y, "ammo", "Rooftop", amount=AMMO_PICKUP_AMOUNT),
            pickup_spawn(8840, GROUND_Y, "health", "Rooftop", amount=HEALTH_PICKUP_AMOUNT),
        ],
    },
]


def section_items(key):
    items = []
    for section in LEVEL_SECTIONS:
        for item in section.get(key, []):
            items.append(item)
    return items


SKYSCRAPER_LEVEL = {
    "name": "Abandoned Overgrown Skyscraper",
    "width": LEVEL_WIDTH,
    "height": LEVEL_HEIGHT,
    "player_start": PLAYER_START,
    "exit": {
        "x": EXIT_POSITION[0],
        "y": EXIT_POSITION[1],
        "width": EXIT_WIDTH,
        "height": EXIT_HEIGHT,
    },
    "backgrounds": BACKGROUND_LAYERS,
    "sections": LEVEL_SECTIONS,
}

# Compatibility exports for older code paths. LevelManager now reads the
# section data above, but these names remain useful for simple probes/tests.
PLATFORMS = section_items("platforms")
ENEMY_SPAWN_POINTS = section_items("enemy_spawns")
PICKUP_SPAWN_POINTS = section_items("pickups")
DECORATIONS = section_items("decorations")

# These entries keep the game level-based and define how many times the shared
# map can be replayed before the final victory screen. Each level reuses the
# same skyscraper layout for now, while enemy min_level values raise pressure.
LEVELS = [
    dict(SKYSCRAPER_LEVEL, number=number)
    for number in range(1, 11)
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
    "pickup_sheet": image_asset_path("ammo_health_kit"),
    "player_arms": image_asset_path("player_arms"),
}

PLAYER_BODY_SHEET_PATH = image_asset_path("new_player_sheet_noarms")
WALKER_ZOMBIE_SHEET_PATH = image_asset_path("walker_zombie_sheet")
WALKER_ZOMBIE_GROUND_SHEET_PATH = image_asset_path("walker_zombie_ground_sheet")
TANK_ZOMBIE_SHEET_PATH = image_asset_path("tank_zombie_sheet")
TANK_ZOMBIE_GROUND_SHEET_PATH = image_asset_path("tank_zombie_ground_sheet")
FLYING_ZOMBIE_SHEET_PATH = image_asset_path("flying_zombie_sheet")
BULLET_SHEET_PATH = image_asset_path("bullet_sheet")

# Sprite sheets are sliced by animation.load_animation_set.
# To add an animation later, add its frames to the sheet and add a named entry
# under "animations" with the row number, frame columns, fps, and loop setting.
SPRITE_SHEETS = {
    # Player body sheet configuration. The aiming arms are a separate cached
    # overlay image so idle/walk aiming can rotate without reslicing frames.
    "player": {
        "path": PLAYER_BODY_SHEET_PATH,
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "use_floor_grid": True,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (PLAYER_WIDTH, PLAYER_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(PLAYER_BODY_SHEET_PATH),
        "background_min_value": 185,
        "background_channel_spread": 52,
        "trim_transparent": False,
        "align": "bottom",
        "animations": {
            "idle": {"row": 0, "frames": [0], "fps": 2, "loop": True},
            "walk": {"row": 0, "frames": [1, 2, 3, 2], "fps": 8, "loop": True},
            "run": {"row": 1, "frames": [0, 1, 2, 3], "fps": 12, "loop": True},
            "jump": {"row": 2, "frames": [0, 1], "fps": 8, "loop": True},
            "fall": {"row": 2, "frames": [2, 3], "fps": 8, "loop": True},
            "death": {"row": 3, "frames": [0, 1, 2, 3], "fps": 8, "loop": False},
        },
    },
    "walker_zombie": {
        "path": WALKER_ZOMBIE_SHEET_PATH,
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (WALKER_WIDTH, WALKER_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(WALKER_ZOMBIE_SHEET_PATH),
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
        "path": WALKER_ZOMBIE_GROUND_SHEET_PATH,
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (WALKER_WIDTH, WALKER_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(WALKER_ZOMBIE_GROUND_SHEET_PATH),
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
        "path": TANK_ZOMBIE_SHEET_PATH,
        "columns": 4,
        "rows": 4,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (TANK_WIDTH, TANK_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(TANK_ZOMBIE_SHEET_PATH),
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
        "path": TANK_ZOMBIE_GROUND_SHEET_PATH,
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (TANK_WIDTH, TANK_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(TANK_ZOMBIE_GROUND_SHEET_PATH),
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
        "path": FLYING_ZOMBIE_SHEET_PATH,
        "columns": 4,
        "rows": 3,
        "frame_width": 362,
        "frame_height": 362,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (FLYING_SPRITE_WIDTH, FLYING_SPRITE_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(FLYING_ZOMBIE_SHEET_PATH),
        "trim_transparent": False,
        "align": "center",
        "draw_offset": FLYING_SPRITE_DRAW_OFFSET,
        "animations": {
            "idle": {"row": 0, "frames": [0], "fps": 6, "loop": True},
            "fly": {"row": 0, "frames": [0, 1, 2, 3, 2, 1], "fps": 8, "loop": True},
            "attack": {"row": 1, "frames": [0, 1, 2, 3], "fps": 10, "loop": False},
            "death": {"row": 2, "frames": [0, 1, 2, 3], "fps": 8, "loop": False},
        },
    },
    "bullet": {
        "path": BULLET_SHEET_PATH,
        "columns": 4,
        "rows": 2,
        "frame_width": None,
        "frame_height": None,
        "margin": 0,
        "spacing": 0,
        "scale": 1,
        "target_size": (BULLET_WIDTH, BULLET_HEIGHT),
        "remove_light_background": needs_runtime_background_cleanup(BULLET_SHEET_PATH),
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
