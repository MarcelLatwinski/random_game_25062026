import random
from settings import UPGRADES

class UpgradeManager:
    def __init__(self):
        self.available = UPGRADES
        self.current_choices = []

    def pick_upgrades(self):
        self.current_choices = random.sample(self.available, 3)
        return self.current_choices

    def apply_upgrade(self, player, choice_index):
        if 0 <= choice_index < len(self.current_choices):
            player.apply_upgrade(self.current_choices[choice_index]["effect_id"])
            self.current_choices = []
