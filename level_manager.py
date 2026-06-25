import random
import pygame
from settings import LEVELS, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX, LEFT_SPAWN_RANGE, RIGHT_SPAWN_RANGE
from enemy import WalkerZombie, TankZombie, FlyingZombie

class LevelManager:
    def __init__(self):
        self.level_index = 0
        self.current_wave = LEVELS[self.level_index]
        self.spawn_timer = 0
        self.spawn_plan = self.build_spawn_queue(self.current_wave)
        self.active_enemies = []

    def build_spawn_queue(self, wave):
        queue = []
        queue.extend(["walker"] * wave["walkers"])
        queue.extend(["tank"] * wave["tanks"])
        queue.extend(["flying"] * wave["flyers"])
        random.shuffle(queue)
        return queue

    def reset(self):
        self.level_index = 0
        self.start_level()

    def start_level(self):
        self.current_wave = LEVELS[self.level_index]
        self.spawn_plan = self.build_spawn_queue(self.current_wave)
        self.spawn_timer = 0
        self.active_enemies = []

    def update(self, dt, platforms, player, images):
        self.spawn_timer -= dt
        if self.spawn_plan and self.spawn_timer <= 0:
            enemy_type = self.spawn_plan.pop(0)
            self.active_enemies.append(self.spawn_enemy(enemy_type, images))
            self.spawn_timer = random.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

        for enemy in list(self.active_enemies):
            enemy.update(player, platforms, dt)
            if enemy.hp <= 0:
                self.active_enemies.remove(enemy)

    def spawn_enemy(self, enemy_type, images):
        if enemy_type == "walker":
            x = random.randint(*LEFT_SPAWN_RANGE) if random.choice([True, False]) else random.randint(*RIGHT_SPAWN_RANGE)
            y = 0
            return WalkerZombie(x, y, image=images.get("walker_zombie"))
        if enemy_type == "tank":
            x = random.randint(*LEFT_SPAWN_RANGE) if random.choice([True, False]) else random.randint(*RIGHT_SPAWN_RANGE)
            y = 0
            return TankZombie(x, y, image=images.get("tank_zombie"))
        if enemy_type == "flying":
            spawn_side = random.choice(["top", "left", "right"])
            if spawn_side == "top":
                x = random.randint(0, 1280)
                y = -50
            elif spawn_side == "left":
                x = -50
                y = random.randint(0, 360)
            else:
                x = 1330
                y = random.randint(0, 360)
            return FlyingZombie(x, y, image=images.get("flying_zombie"))

    def level_complete(self):
        return not self.spawn_plan and not self.active_enemies

    def next_level(self):
        self.level_index += 1
        if self.level_index < len(LEVELS):
            self.start_level()
            return True
        return False

    def current_level_number(self):
        return self.level_index + 1
