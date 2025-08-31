import math
import numpy as np

def duree_attaque(
    x1,
    y1,
    x2,
    y2,
    va=0,
):
    d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    return round(0.4999 + 3000 * (1 + 100*(1-math.exp(-round(d)/1415)))*va_ratio(va))

def va_ratio(va: int):
    return 1/(1+va/10)

def from_va(ratio: float) -> float:
    return 10*(1/ratio - 1)

hunt_params = {
    "base": np.float64(78.78), # + 78 for s1
    "power": np.float64(0.10594649535008978),
    "coef": np.float64(4.685486475),
}

def vt_ratio(vt: int):
    return 1/(1+vt/10)

def hunt_duration(
    start: np.int64,
    hunt: np.int64,
    vt: int = 0,
):
    return np.int64((60 + hunt/2 + start/10)*(1/(1+vt/10)))

def hunt_difficulty(
    start: np.int64,
    hunt: np.int64, 
    base: np.float64 = hunt_params["base"], 
    power: np.float64 = hunt_params["power"], 
    coef: np.float64 = hunt_params["coef"],
) -> np.int64:
    b = base
    terrain_weight = hunt + start/10
    mult = coef * terrain_weight
    p = hunt ** power
    v = p * mult
    return np.int64(np.ceil(b + 2.5 * np.round(v / 2.5)))
    return np.ceil(base + 2.5 * (((hunt ** power) * (coef * (hunt + start/10)))//2.5))
    return base + coef * (hunt ** (power+1)) + (coef/10) * (hunt ** power) * start 
    return base + coef * (hunt ** (power+1)) + coef * hunt ** power * start/10
    return base + coef * (hunt ** (power)) * hunt + coef * hunt ** power * start/10

def max_hunt_per_hour(
    vt: int,
) -> np.int64:
    return np.ceil(3600 * 2/vt_ratio(vt))
