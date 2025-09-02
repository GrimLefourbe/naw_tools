import re
from dataclasses import dataclass

import numpy as np
from enum import Enum, StrEnum
import typing as t

from loguru import logger

__all__ = ["AllianceType", "HeroType", "FightZone", "Levels"]


class AllianceType(StrEnum):
    GUERRIER = "Guerrier"
    PACIFISTE = "Pacifiste"
    NEUTRE = "Neutre"


class HeroType(StrEnum):
    ATTAQUE = "Attaque"
    DEFENSE = "Défense"
    VIE = "Vie"


class FightZone(StrEnum):
    TDC = "TDC"
    DOME = "Dôme"
    LOGE = "Loge"

HERO_ENABLED = False

@dataclass
class Levels:
    mandibule: int = 0
    carapace: int = 0
    hero_lvl: int = 0
    hero_type: HeroType = HeroType.ATTAQUE
    train: int = 0
    dome: int = 0
    loge: int = 0
    alliance: t.Optional[AllianceType] = AllianceType.NEUTRE
    special: int = 0

    def _mandi(self):
        return 0.05 * self.mandibule

    def _cara(self):
        return 0.05 * self.carapace

    def _dome(self):
        return 0.05 + 0.025 * self.dome

    def _loge(self):
        return 0.1 + 0.05 * self.loge

    def _alli(self):
        match self.alliance:
            case AllianceType.GUERRIER:
                return np.array((0.1, 0))
            case AllianceType.NEUTRE:
                return np.array((0.05, 0.05))
            case AllianceType.PACIFISTE:
                return np.array((0, 0.1))
            case None:
                return np.array((0, 0))
    def _special(self):
        return np.array((self.special * 0.02, self.special * 0.02))

    @property
    def bonus_atk(self) -> tuple[np.float64, np.float64]:
        """(dmg, hp) bonuses when attacking"""
        dmg, hp = (self._mandi(), self._cara()) + self._special() + self._alli()

        if self.hero_type == HeroType.ATTAQUE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_tdc(self) -> tuple[np.float64, np.float64]:
        """(dmg, hp) bonuses when defending in tdc"""
        dmg, hp = (self._mandi(), self._cara()) + self._special() + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_dome(self) -> tuple[np.float64, np.float64]:
        """(dmg, hp) bonuses when defending in dome"""
        dmg, hp = (self._mandi(), self._cara() + self._dome()) + self._special() + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_loge(self) -> tuple[np.float64, np.float64]:
        """(dmg, hp) bonuses when defending in loge"""
        dmg, hp = (self._mandi(), self._cara() + self._loge()) + self._special() + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @classmethod
    def from_str(cls, s: str):
        num_args = ["mandibule", "carapace", "special", "dome", "loge"]
        pat = r"\s*".join(rf"(?:{i[0].upper()}(?P<{i}>\d+))?" for i in num_args)
        pat += r"(?:\s*H([ADV])(\d+))?"
        pat += r"(?:\s*A([PNGR]))?"
        pat = re.compile(pat)
        if not (match := pat.search(s)):
            raise ValueError(f"Can't interpret {s} as levels.")
        args: dict[str, t.Any] = {k: int(v) for k, v in match.groupdict().items() if v is not None}
        match match.group(8):
            case "P":
                args["alliance"] = AllianceType.PACIFISTE
            case "N":
                args["alliance"] = AllianceType.NEUTRE
            case "G":
                args["alliance"] = AllianceType.GUERRIER
            case "R":
                args["alliance"] = None
            case None:
                pass

        match match.group(6), match.group(7):
            case "A", level:
                args["hero_type"] = HeroType.ATTAQUE
            case "D", level:
                args["hero_type"] = HeroType.DEFENSE
            case "V", level:
                args["hero_type"] = HeroType.VIE
            case _:
                args["hero_type"] = HeroType.ATTAQUE
                level = 0
        args["hero_lvl"] = int(level)
        return cls(**args)

    def to_str(self, sep="\n") -> str:
        s = []
        s.append(f"M{self.mandibule} C{self.carapace} S{self.special}")
        s.append(f"D{self.dome} L{self.loge}")
        if HERO_ENABLED:
            s.append(f"H{self.hero_type[:1]}{self.hero_lvl}")
        s.append(f"A{self.alliance[:1] if self.alliance else "R"}")
        return sep.join(s)

    @classmethod
    def from_bonuses(cls, bonus_dmg, bonus_hp, lieu: FightZone, alli_type: t.Optional[AllianceType] = None, atk=True, step=1/100, hero_enabled=None):
        args: dict[str, t.Any] = {"alliance": alli_type}
        if hero_enabled is None:
            hero_enabled = HERO_ENABLED

        explained_dmg_bonus = 0
        unexplained_dmg_bonus = round(bonus_dmg / step)

        ## finding atk bonus
        mandi = 0
        if alli_type == AllianceType.GUERRIER:
            explained_dmg_bonus += 10
            unexplained_dmg_bonus -= 10
        elif alli_type == AllianceType.NEUTRE:
            explained_dmg_bonus += 5
            unexplained_dmg_bonus -= 5

        if unexplained_dmg_bonus % 5 != 0: # mandi is not enough to explain
            if hero_enabled:
                # hero must explain diff
                args["hero_type"] = HeroType.ATTAQUE if atk else HeroType.DEFENSE
                args["hero_lvl"] = hero_lvl = 100 + 20 * (unexplained_dmg_bonus % 5)
                explained_dmg_bonus += hero_lvl / 20
                unexplained_dmg_bonus -= hero_lvl / 20  ## TODO: check if that makes it subzero
                # TODO: Enable both hero and specialisation together
            else:
                # specialisation must explain diff
                if unexplained_dmg_bonus % 2: # mandi is odd
                    mandi += 1
                    unexplained_dmg_bonus -= 5
                    explained_dmg_bonus += 5
                args["special"] = special = unexplained_dmg_bonus % 10 / 2
                unexplained_dmg_bonus -= special * 2
                explained_dmg_bonus += special * 2

        # no hero needed to explain leftover
        mandi += unexplained_dmg_bonus // 5
        args ["mandibule"] = mandi
        if bonus_hp is None:
            unexplained_hp_bonus = None
        else:
            explained_hp_bonus = 0
            unexplained_hp_bonus = round(bonus_hp / step)
            if "special" in args:
                explained_hp_bonus += special * 2
                unexplained_hp_bonus -= special * 2

            if alli_type == AllianceType.NEUTRE:
                explained_hp_bonus += 5
                unexplained_hp_bonus -= 5
            elif alli_type == AllianceType.PACIFISTE:
                explained_hp_bonus += 10
                unexplained_hp_bonus -= 10

            if atk or lieu == FightZone.TDC:
                if HERO_ENABLED:
                    if unexplained_hp_bonus % 5 != 0:
                        args["hero_type"] = HeroType.VIE
                        args["hero_lvl"] = hero_lvl = 100 + 20 * (unexplained_hp_bonus % 5)
                        explained_hp_bonus += hero_lvl / 20
                        unexplained_hp_bonus -= hero_lvl / 20

                cara = unexplained_hp_bonus // 5

            elif lieu == FightZone.DOME:
                explained_hp_bonus += 5
                unexplained_hp_bonus -= 5

                # change step to 0.05
                explained_hp_bonus *= 2
                unexplained_hp_bonus *= 2

                if unexplained_hp_bonus % 5 != 0:
                    if HERO_ENABLED:
                        if hero_enabled:
                            args["hero_type"] = HeroType.VIE
                            args["hero_lvl"] = hero_lvl = 150 + 10 * (unexplained_hp_bonus % 5)
                            explained_hp_bonus += hero_lvl / 10
                            unexplained_hp_bonus -= hero_lvl / 10  # TODO: check if subzero

                cara = min(mandi, unexplained_hp_bonus // 10)
                explained_hp_bonus += cara * 10
                unexplained_hp_bonus -= cara * 10

                args["dome"] = unexplained_hp_bonus // 5

            elif lieu == FightZone.LOGE:
                explained_hp_bonus += 10
                unexplained_hp_bonus -= 10
                
                if HERO_ENABLED:
                    if unexplained_hp_bonus % 5 != 0:
                        args["hero_type"] = HeroType.VIE
                        args["hero_lvl"] = hero_lvl = 100 + 20 * (unexplained_hp_bonus % 5)
                        explained_hp_bonus += hero_lvl / 20
                        unexplained_hp_bonus -= hero_lvl / 20

                cara = min(mandi, unexplained_hp_bonus // 5)
                explained_hp_bonus += cara * 5
                unexplained_hp_bonus -= cara * 5
                args["loge"] = unexplained_hp_bonus // 5
            else:
                raise ValueError(f"Unknown FightZone: {lieu}")
            args["carapace"] = cara
        logger.debug(f"Unexplained bonuses left: {unexplained_dmg_bonus}/{unexplained_hp_bonus}")
        return cls(
            **args
        )
