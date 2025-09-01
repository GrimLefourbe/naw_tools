import typing as t
from dataclasses import dataclass


import numpy as np
import nawminator as nm

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

@dataclass
class HuntingReport:
    start: int
    hunt: int
    attacker_before: nm.army.Army
    attacker_after: nm.army.Army

    @classmethod
    def from_rc(cls, rc: str):
        raise NotImplementedError


