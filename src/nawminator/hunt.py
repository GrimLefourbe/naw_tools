import typing as t
from dataclasses import dataclass

import numpy as np
import nawminator as nm
import re

def max_hunt_amount(start: np.int64, target_difficulty: np.int64) -> np.int64:
    h = np.int64(1)
    while d := nm.formulas.hunt_difficulty(start, h) < target_difficulty - 3:
        h *= 2
    upper = h
    lower = h//2
    n = 0
    while abs ((d := nm.formulas.hunt_difficulty(start, h)) - target_difficulty) > 3:
        if upper - lower == 1:
            if nm.formulas.hunt_difficulty(start, upper) >= target_difficulty - 3:
                h = lower
                break
            else:
                h = upper
                break
        if d > target_difficulty:
            upper = h
            h = (upper + lower) // 2
        else:
            lower = h
            h = (upper + lower) // 2
        n += 1
        if n > 100:
            raise ValueError(f"Can't get {target_difficulty} difficulty with {start=}: {lower=}, {upper=}")
    return h

danger_thresholds = {
    "low_danger": 1.0683751,
    "mid_danger": 1.2820501,
    "quite_danger": 1.4245000,
    "danger": 2.5641005,
}

hunt_pat = re.compile(
    r"""Avant combat\sTroupe en attaque : (.*?)\sTroupe en défense(.*?)Après combat\sExpérience gagnée : (.*?)\sArmée finale : (.*?)\..+Vous avez chassé ([\d ]+) cm².*?Terrain avant : ([\d ]+) cm² et Terrain après : ([\d ]+) cm²\.\s\sDifficulté de la chasse : ([\d ]+)\.""",
    flags=re.S,
)
@dataclass
class HuntingReport:
    start: int
    hunt: int
    attacker_before: nm.army.Army
    attacker_after: nm.army.Army

    @classmethod
    def from_rc(cls, rc: str):
        if match := hunt_pat.search(rc):
            start_army, defending_army, xp_army, final_army, hunt_amount, tdc_avant, tdc_apres, diff = match.groups()
            return cls(
                start=nm.utils.parse_naw_int(tdc_avant),
                hunt=nm.utils.parse_naw_int(hunt_amount),
                attacker_before=nm.army.Army.from_str(start_army),
                attacker_after=nm.army.Army.from_str(final_army),
            )
        else:
            raise ValueError(f"Could not find match within {rc=}")
    
    def diff(self, levels: nm.levels.Levels):
        dome_before = nm.battle.WarParty(self.attacker_before, nm.battle.Bonuses(*levels.bonus_dome), False)
        dome_after = nm.battle.WarParty(self.attacker_after, nm.battle.Bonuses(*levels.bonus_dome), False)
        loge_before = nm.battle.WarParty(self.attacker_before, nm.battle.Bonuses(*levels.bonus_loge), False)
        loge_after = nm.battle.WarParty(self.attacker_after, nm.battle.Bonuses(*levels.bonus_loge), False)
        atk_before = nm.battle.WarParty(self.attacker_before, nm.battle.Bonuses(*levels.bonus_atk), True)
        atk_after = nm.battle.WarParty(self.attacker_after, nm.battle.Bonuses(*levels.bonus_atk), True)
        return {
            "count": self.attacker_after.count - self.attacker_before.count,
            "fdf": atk_after.total_dmg - atk_before.total_dmg,
            "osd": dome_after.total_hp - dome_before.total_hp,
            "osl": loge_after.total_hp - loge_before.total_hp,
        }

