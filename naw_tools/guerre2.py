import functools
from datetime import datetime, timedelta, time
from typing import Optional, TypeVar

import numpy as np
import re

import pandas as pd
from loguru import logger
from naw_tools import formula

T = TypeVar("T", datetime, time)


def depart_to_arrival(
    depart: T,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    va: int = 0,
) -> T:
    d = timedelta(seconds=formula.duree_attaque(x1=x1, y1=y1, x2=x2, y2=y2, va=va))

    if isinstance(depart, time):
        return (datetime.combine(datetime.today(), depart) + d).time()
    else:
        return depart + d

def parse_naw_int(s: str) -> int:
    return int(s.replace(" ", ""))


def parse_fight(s: str) -> np.ndarray:
    res = re.findall(
        r"^.*?infli\w+ (\d[\d ]*) \(\+ (\d[\d ]*)\) dégâts et.*? tu\w+ (\d[\d ]*) (unités?|ennemis?)\W*$",
        s,
        re.MULTILINE,
    )
    return np.array([[parse_naw_int(a), parse_naw_int(b), parse_naw_int(c)] for a, b, c, d in res], dtype=np.int64)


unit_names = [
    r"Esclaves?",
    r"Maîtres? esclaves?",
    r"Jeunes? soldates?",
    r"Soldates?(?!s? d'élite)",
    r"Soldates? d'élite",
    r"Gardiennes?(?!s? d'élite)",
    r"Gardiennes? d'élite",
    r"Tirailleuses?(?!s? d'élite)",
    r"Tirailleuses? d'élite",
    r"Jeunes? légionnaires?",
    r"Légionnaires?(?!s? d'élite)",
    r"Légionnaires? d'élite",
    r"Jeunes? tanks?",
    r"Tanks?(?!s? d'élite)",
    r"Tanks? d'élite"
]

unit_stats = np.array([
    [4, 4, 3],
    [6, 6, 4],
    [16, 8, 7],
    [20, 11, 10],
    [26, 17, 14],
    [25, 1, 27],
    [32, 1, 35],
    [12, 32, 10],
    [15, 40, 12],
    [40, 45, 35],
    [55, 60, 45],
    [60, 65, 50],
    [40, 80, 1],
    [70, 140, 1],
    [80, 160, 1],
], dtype=np.int64)


class Armee:
    def __init__(self, units: np.ndarray, dmg_bonus: Optional[float] = None, hp_bonus: Optional[float] = None):
        self._data = units.astype(np.int64)
        self._bonuses = (dmg_bonus, hp_bonus)

    @property
    def data(self) -> np.ndarray:
        return self._data.copy()

    @property
    def bonuses(self) -> (float, float):
        return self._bonuses

    @classmethod
    def from_string(cls, s: str) -> "Armee":
        pattern = r"\W*".join([rf"(?:(\d[ \d]*) {i})?" for i in unit_names])

        match = re.search(pattern, s)
        if match is None:
            raise ValueError(f"Cannot parse army {s}")

        armee = np.array([parse_naw_int(i) if i is not None else 0 for i in match.groups()], dtype=np.int64)
        return cls(units=armee)

    def copy(self) -> "Armee":
        return Armee(self._data, self._bonuses[0], self._bonuses[1])

    def with_bonus(self, dmg_bonus: float = None, hp_bonus: float = None) -> "Armee":
        return Armee(self._data, dmg_bonus if dmg_bonus is not None else self._bonuses[0], hp_bonus if hp_bonus is not None else self._bonuses[1])

    def split(self, n) -> ("Armee", "Armee"):
        armee = self._data
        first = np.zeros_like(armee, dtype=np.int64)
        second = armee.copy()
        for i, cnt in enumerate(armee):
            amount = min(cnt, n)
            first[i] += amount
            second[i] -= amount
            n -= amount
        return Armee(
            first, dmg_bonus=self._bonuses[0], hp_bonus=self._bonuses[1]
        ), Armee(
            second, dmg_bonus=self._bonuses[0], hp_bonus=self._bonuses[1]
        )

    @property
    @functools.cache
    def stats_hb(self) -> np.ndarray:
        return (unit_stats * self._data[:, np.newaxis]).sum(axis=0, dtype=np.int64)

    @property
    @functools.cache
    def stats_ab(self) -> np.ndarray:
        return np.array([
            stat_hb * (1 + bonus) if bonus is not None else None for stat_hb, bonus in zip(self.stats_hb, [self.bonuses[1], self.bonuses[0], self.bonuses[0]])
        ])

    @functools.cache
    def count(self) -> np.ndarray:
        return self._data.sum()

    def __str__(self):
        return f"Armee(units={self._data}, bonuses={self._bonuses})"

    def to_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=[[*self._data, *map(lambda i: round(i) if i is not None else None, self.stats_ab)]],
            columns=[i.replace("s?", "").replace("(?! d'élite)", "") for i in unit_names] + ["Vie AB", "Attaque AB", "Riposte AB"],
            dtype=pd.Int64Dtype()
        )


def pipeline(rc: str):
    fight_data, army_attaque, army_defense = parse_rc(rc)

    (atk_before, def_before), (atk_after, def_after) = compute_bonuses(fight_data, army_attaque, army_defense)

    return format_results((atk_before, def_before), (atk_after, def_after))


def format_results(before: (Armee, Armee), after: (Armee, Armee)):
    return (
        pd.concat(map(lambda x: x.to_df(), before), axis=0, ignore_index=True).transpose().rename(columns={0: "Attaquant", 1: "Défenseur"}),
        pd.concat(map(lambda x: x.to_df(), after), axis=0, ignore_index=True).transpose().rename(columns={0: "Attaquant", 1: "Défenseur"}),
        pd.DataFrame(
            data=list(zip(before[0].bonuses, before[1].bonuses)),
            columns=["Attaquant", "Défenseur"],
            index=["Bonus Dégats (%)", "Bonus Vie (%)"]
        )
    )


def parse_rc(rc: str) -> (np.ndarray, Armee, Armee):
    attaque = re.search(r"Troupe en attaque : (.*?)\n", rc).group(1)
    defense = re.search(r"Troupe en défense : (.*?)\n", rc).group(1)
    fight = re.search(r"Combat\W+(.*)", rc, flags=re.S | re.MULTILINE | re.DOTALL).group(1)
    logger.debug("1st Parsing Step")
    logger.debug(attaque)
    logger.debug(defense)
    logger.debug(fight)

    fight_data = parse_fight(fight)
    army_attaque = Armee.from_string(attaque)
    army_defense = Armee.from_string(defense)

    logger.debug("2nd Parsing Step")
    logger.debug(fight_data)
    logger.debug(army_attaque)
    logger.debug(army_defense)

    return fight_data, army_attaque, army_defense


def compute_bonuses(fight_data, army_attaque: Armee, army_defense: Armee):
    army_attaque = army_attaque.with_bonus(dmg_bonus=fight_data[0, 1] / fight_data[0, 0])
    army_defense = army_defense.with_bonus(dmg_bonus=fight_data[1, 1] / fight_data[1, 0])

    logger.debug(f"Dmg bonuses: {army_attaque.bonuses[0]} {army_defense.bonuses[0]}")

    units_lost_attaque, _ = army_attaque.split(fight_data[1, 2])
    units_lost_defense, _ = army_defense.split(fight_data[0, 2])

    logger.debug("Units lost")
    logger.debug(units_lost_attaque.count())
    logger.debug(units_lost_defense.count())

    if army_attaque.count() != fight_data[1, 2]:
        army_attaque = army_attaque.with_bonus(hp_bonus=fight_data[1, :2].sum() / units_lost_attaque.stats_hb[0] - 1)
    if army_defense.count() != fight_data[0, 2]:
        army_defense = army_defense.with_bonus(hp_bonus=fight_data[0, :2].sum() / units_lost_defense.stats_hb[0] - 1)

    logger.debug("Armies before")

    logger.debug(army_attaque)
    logger.debug(army_attaque.stats_hb)
    logger.debug(army_attaque.stats_ab)
    logger.debug(army_defense)
    logger.debug(army_defense.stats_hb)
    logger.debug(army_defense.stats_ab)

    _, army_after_attaque = army_attaque.split(fight_data[1::2, 2].sum())
    _, army_after_defense = army_defense.split(fight_data[0::2, 2].sum())

    logger.debug(army_after_attaque)
    logger.debug(army_after_attaque.stats_ab)
    logger.debug(army_after_defense)
    logger.debug(army_after_defense.stats_ab)

    return (army_attaque, army_defense), (army_after_attaque, army_after_defense)


def format_stats(
    armies_avant, armies_apres, niveaux, mode="string", index=False, columns=None
):
    if mode == "html":
        formatter = lambda x: x.to_html(
            classes="data",
            index=True,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    elif mode == "string":
        formatter = lambda x: x.to_string(
            index=True,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    elif mode == "csv":
        formatter = lambda x: x.to_csv(
            index=index,
            columns=columns,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    else:
        raise NotImplementedError(f"{mode} is not supported")
    return formatter(armies_avant), formatter(armies_apres), formatter(niveaux)


if __name__ == "__main__":
    rc_string = """Yggdrasil
Rapport de combat en défense : Perdu
08/09 08:30

Rapport de combat en Dôme :
Votre colonie Nulle de Miel[335:370] a été attaqué par la colonie FK TEAM[-62:34] du joueur Yggdrasil en Dôme.

Avant combat
Troupe en attaque : 200 231 Esclaves, 22 373 Maîtres esclaves, 1 125 560 Jeunes soldates, 69 445 Soldates, 29 Soldates d'élite, 361 434 Jeunes légionnaires, 16 Légionnaires
Troupe en défense : 7 907 Esclaves, 196 Maîtres esclaves, 61 Jeunes soldates, 2 Soldates

Combat
L'assaillant vous a infligé 26 969 520 (+ 21 575 616) dégâts et vous a tué 8 166 unités.
Vous ripostez, infligeant 2 495 (+ 1 996) dégâts et tuant 636 ennemis

Après combat
Expérience gagnée : aucune.
Armée finale : Aucune.
Pillage : Vous avez été pillé de 1 613 568 cm² Terrain de chasse, 25 888 297 nourritures, 25 888 297 bois, 25 888 297 eaux."""

    pipeline(rc_string)
