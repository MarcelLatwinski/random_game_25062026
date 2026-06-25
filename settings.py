SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

PLAYER_MAX_HEALTH = 100
PLAYER_START_HEALTH = 100
PLAYER_SPEED = 5
PLAYER_JUMP_STRENGTH = 15
GRAVITY = 0.8
MAX_FALL_SPEED = 20
PLAYER_BASE_DAMAGE = 10
PLAYER_FIRE_COOLDOWN = 0.35
PLAYER_BULLET_SPEED = 12
BULLET_WIDTH = 12
BULLET_HEIGHT = 6
HURT_INVINCIBILITY = 0.5
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 60

WALKER_HP = 40
WALKER_SPEED = 2.0
WALKER_DAMAGE = 10
WALKER_JUMP_INTERVAL = (2.0, 3.0)
WALKER_JUMP_STRENGTH = 13
WALKER_WIDTH = 40
WALKER_HEIGHT = 60

TANK_HP = 100
TANK_SPEED = 1.0
TANK_DAMAGE = 25
TANK_JUMP_INTERVAL = (3.0, 4.0)
TANK_JUMP_STRENGTH = 11
TANK_WIDTH = 60
TANK_HEIGHT = 80

FLYING_HP = 30
FLYING_SPEED = 2.6
FLYING_DAMAGE = 8
FLYING_WIDTH = 40
FLYING_HEIGHT = 40

SPAWN_INTERVAL_MIN = 1.2
SPAWN_INTERVAL_MAX = 2.0
LEFT_SPAWN_RANGE = (40, 120)
RIGHT_SPAWN_RANGE = (1160, 1240)
GROUND_Y = 660

PLATFORMS = [
    (0, 660, 1280, 60),
    (160, 500, 270, 24),
    (505, 380, 270, 24),
    (850, 500, 270, 24),
    (490, 250, 300, 24),
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
    "player": "assets/images/player.png",
    "walker_zombie": "assets/images/walker_zombie.png",
    "tank_zombie": "assets/images/tank_zombie.png",
    "flying_zombie": "assets/images/flying_zombie.png",
    "bullet": "assets/images/bullet.png",
    "platform": "assets/images/platform.png",
    "background": "assets/images/background.png",
}

COLOR_BACKGROUND = (15, 15, 20)
COLOR_PLAYER = (50, 150, 230)
COLOR_WALKER = (100, 220, 120)
COLOR_TANK = (220, 100, 110)
COLOR_FLYING = (220, 220, 80)
COLOR_BULLET = (255, 215, 90)
COLOR_PLATFORM = (100, 100, 100)
COLOR_TEXT = (235, 235, 235)
COLOR_UI_BG = (25, 25, 35)
COLOR_HEALTH = (220, 60, 60)
COLOR_HURT = (255, 80, 80)
