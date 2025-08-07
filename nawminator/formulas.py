import math


def duree_attaque(
    x1,
    y1,
    x2,
    y2,
    va=0,
):
    d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    return round(0.4999 + 3000 * (1 + 100*(1-math.exp(-round(d)/1415)))/(1+va/10))