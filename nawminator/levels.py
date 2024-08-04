import re
from dataclasses import dataclass

import numpy as np
from enum import Enum, StrEnum
import typing as t


class AllianceType(StrEnum):
    GUERRIER = "Guerrier"
    PACIFISTE = "Pacifiste"
    NEUTRE = "Neutre"


class HeroType(StrEnum):
    ATTAQUE = "Attaque"
    DEFENSE = "Défense"
    VIE = "Vie"


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

    @property
    def bonus_atk(self) -> (np.float64, np.float64):
        """(dmg, hp) bonuses when attacking"""
        dmg, hp = (self._mandi(), self._cara()) + self._alli()

        if self.hero_type == HeroType.ATTAQUE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_tdc(self) -> (np.float64, np.float64):
        """(dmg, hp) bonuses when defending in tdc"""
        dmg, hp = (self._mandi(), self._cara()) + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_dome(self) -> (np.float64, np.float64):
        """(dmg, hp) bonuses when defending in dome"""
        dmg, hp = (self._mandi(), self._cara() + self._dome()) + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @property
    def bonus_loge(self) -> (np.float64, np.float64):
        """(dmg, hp) bonuses when defending in loge"""
        dmg, hp = (self._mandi(), self._cara() + self._loge()) + self._alli()
        if self.hero_type == HeroType.DEFENSE:
            dmg += self.hero_lvl * 0.0005
        if self.hero_type == HeroType.VIE:
            hp += self.hero_lvl * 0.0005
        return dmg, hp

    @classmethod
    def from_str(cls, s: str):
        num_args = ["mandibule", "carapace", "dome", "loge"]
        pat = r"\s*".join(rf"(?:{i[0].upper()}(?P<{i}>\d+))?" for i in num_args)
        pat += r"(?:\s*H([ADV])(\d+))?"
        pat += r"(?:\s*A([PNGR]))?"
        pat = re.compile(pat)
        if not (match := pat.search(s)):
            raise ValueError(f"Can't interpret {s} as levels.")
        args = {k: int(v) for k, v in match.groupdict().items() if v is not None}
        match match.group(7):
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

        match match.group(5), match.group(6):
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

    def to_str(self) -> str:
        return f"""M{self.mandibule} C{self.carapace}
D{self.dome} L{self.loge}
H{self.hero_type[:1]}{self.hero_lvl}
A{self.alliance[:1] if self.alliance else "R"}"""
