import re
from dataclasses import dataclass

import numpy as np
from enum import Enum, StrEnum
import typing as t

import pulp as pl

from loguru import logger

__all__ = ["AllianceType", "HeroType", "FightZone", "Levels"]


class AllianceType(StrEnum):
    GUERRIER = "Guerrier"
    PACIFISTE = "Pacifiste"
    NEUTRE = "Neutre"
    NONE = "None"

    @property
    def bonus(self):
        match self:
            case AllianceType.GUERRIER:
                return 0.1, 0.0
            case AllianceType.NEUTRE:
                return 0.05, 0.05
            case AllianceType.PACIFISTE:
                return 0.0, 0.1
            case AllianceType.NONE:
                return 0.0, 0.0


class HeroType(StrEnum):
    ATTAQUE = "Attaque"
    DEFENSE = "Défense"
    VIE = "Vie"


class FightZone(StrEnum):
    TDC = "TDC"
    DOME = "Dome"
    LOGE = "Loge"

@dataclass
class Levels:
    mandibule: int = 0
    carapace: int = 0
    hero_lvl: int = 0
    hero_type: t.Optional[HeroType] = None
    train: int = 0
    dome: int = 0
    loge: int = 0
    alliance: AllianceType = AllianceType.NONE
    special: int = 0

    def __post_init__(self):
        if isinstance(self.alliance, str):
            self.alliance = AllianceType(self.alliance)

    def _mandi(self):
        return 0.05 * self.mandibule

    def _cara(self):
        return 0.05 * self.carapace

    def _dome(self):
        return 0.05 + 0.025 * self.dome

    def _loge(self):
        return 0.1 + 0.05 * self.loge

    def _alli(self):
        return np.array((self.alliance.bonus))

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

    def bonus(self, lieu: FightZone, atk: bool):
        match atk, lieu:
            case True, _:
                return self.bonus_atk
            case False, FightZone.DOME:
                return self.bonus_dome
            case False, FightZone.LOGE:
                return self.bonus_loge
            case False, FightZone.TDC:
                return self.bonus_tdc

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
                args["alliance"] = AllianceType.NONE
            case None:
                args["alliance"] = AllianceType.NONE

        match match.group(6), match.group(7):
            case "A", level:
                args["hero_type"] = HeroType.ATTAQUE
            case "D", level:
                args["hero_type"] = HeroType.DEFENSE
            case "V", level:
                args["hero_type"] = HeroType.VIE
            case _:
                args["hero_type"] = None
                level = 0
        args["hero_lvl"] = int(level)
        return cls(**args)

    def to_str(self, sep="\n", hero_enabled: bool = True) -> str:
        s = []
        s.append(f"M{self.mandibule} C{self.carapace} S{self.special}")
        s.append(f"D{self.dome} L{self.loge}")
        alli_string = f"A{self.alliance[:1] if self.alliance != AllianceType.NONE else "R"}"
        if hero_enabled and self.hero_type is not None:
            s.append(f"H{self.hero_type[:1]}{self.hero_lvl} {alli_string}")
        else:
            s.append(alli_string)
        return sep.join(s)

    @classmethod
    def from_bonuses(
        cls, 
        bonus_dmg: float | tuple[float, float], 
        bonus_hp: None | float | tuple[float | None, float | None], 
        lieu: FightZone, 
        alli_type: AllianceType = AllianceType.NONE, 
        atk=True, 
        hero_enabled=None,
        opt: t.Literal["max"] | t.Literal["min"] = "max"
    ):
        logger.debug(f"Computing bonuses from {bonus_dmg=}, {bonus_hp=} in {lieu=} with {alli_type=}, {atk=}, {hero_enabled=}")
        step=1/20000
        to_step = lambda x: round(x/step)
        args: dict[str, t.Any] = {
            "alliance": alli_type
        }

        if not isinstance(bonus_dmg, tuple):
            bonus_dmg = bonus_dmg, bonus_dmg
        if not isinstance(bonus_hp, tuple):
            bonus_hp = bonus_hp, bonus_hp

        HP_ENABLED = bonus_hp[0] is not None and bonus_hp[1] is not None

        dmg_base, hp_base = alli_type.bonus
 
        match atk, lieu:
            case False, FightZone.DOME:
                base_lieu, base_step = 0.05, 0.025
            case False, FightZone.LOGE:
                base_lieu, base_step = 0.1, 0.05
            case _:
                base_lieu, base_step = 0, 0
        hp_base += base_lieu
 
        hero_types: list[t.Optional[HeroType]] = [None]
        if hero_enabled:
            if bonus_hp is not None:
                hero_types.append(HeroType.VIE)
            if atk:
                hero_types.append(HeroType.ATTAQUE)
            else:
                hero_types.append(HeroType.DEFENSE)
                
        solutions: list[tuple[int, dict[str, pl.LpVariable], HeroType | None]] = []
        for hero_type in hero_types:
            possible_vars = {
                "M": (to_step(0.05), pl.LpVariable("mandibule", lowBound=0, upBound=40, cat="Integer")),
                "C": (to_step(0.05), pl.LpVariable("carapace", lowBound=0, upBound=40, cat="Integer")),
                "S": (to_step(0.02), pl.LpVariable("special", lowBound=0, upBound=5, cat="Integer")),
                "D": (to_step(base_step), pl.LpVariable("dome", lowBound=0, upBound=40, cat="Integer")),
                "L": (to_step(base_step), pl.LpVariable("loge", lowBound=0, upBound=40, cat="Integer")),
                "H": (to_step(0.0005), pl.LpVariable("hero_lvl", lowBound=0, upBound=180, cat="Integer")),
            }

            off_vars = ["M", "S"]
            def_vars = ["S"]
            if HP_ENABLED:
                def_vars += ["C"]

                match atk, lieu:
                    case False, FightZone.DOME:
                        def_vars += ["D"]
                    case False, FightZone.LOGE:
                        def_vars += ["L"]
                    case _:
                        pass
            match hero_type:
                case HeroType.ATTAQUE | HeroType.DEFENSE:
                    off_vars += ["H"]
                case HeroType.VIE if bonus_hp is not None:
                    def_vars += ["H"]
                case _:
                    pass
            off_sum = pl.lpSum(possible_vars[k][0] * possible_vars[k][1] for k in off_vars)
            def_sum = pl.lpSum(possible_vars[k][0] * possible_vars[k][1] for k in def_vars)

            used_vars = {k: v for k, (_, v) in possible_vars.items() if k in off_vars or k in def_vars}

            balancing_weights = {
                "main_error_atk": 1_000_000,
                "main_error_def": 1_000_000,
                "h_ismid": 20_000,
                "H=0": 5_000,
                "S_H": 1_250,
                "M~C": 1_000,
                "DL~C": 1_000,
                "Final": 1,
            }
            m = pl.LpProblem("find_levels", pl.LpMinimize)
            
            main_error_atk = pl.LpVariable("main_error_atk", lowBound=0, cat="Integer")
            main_error_def = pl.LpVariable("main_error_def", lowBound=0, cat="Integer")
            hmid_penalty = pl.LpVariable("h_ismid", lowBound=0, cat="Integer")
            h_nonzero_penalty = pl.LpVariable("H=0", lowBound=0, upBound=1, cat="Integer")
            sh_error = pl.LpVariable("S_H", lowBound=0, cat="Integer")
            mc_error = pl.LpVariable("M~C", lowBound=0, cat="Integer")
            dlc_error = pl.LpVariable("DL~C", lowBound=0, cat="Integer")
            final_error = pl.LpVariable("Final", lowBound=0, cat="Integer")

            errors = []

            m += to_step(dmg_base) + off_sum >= to_step(bonus_dmg[0])
            m += to_step(dmg_base) + off_sum <= to_step(bonus_dmg[1])
            if HP_ENABLED:
                m += to_step(hp_base) + def_sum >= to_step(bonus_hp[0])
                m += to_step(hp_base) + def_sum <= to_step(bonus_hp[1])
            if opt == "max":
                m += to_step(dmg_base) + off_sum + main_error_atk == to_step(bonus_dmg[1])
                errors += [main_error_atk]
                if HP_ENABLED:
                    m += to_step(hp_base) + def_sum + main_error_def == to_step(bonus_hp[1])
                    errors += [main_error_def]
            elif opt == "min":
                m += to_step(dmg_base) + off_sum == to_step(bonus_dmg[0]) + main_error_atk
                errors += [main_error_atk]
                if HP_ENABLED:
                    m += to_step(hp_base) + def_sum == to_step(bonus_hp[0]) + main_error_def 
                    errors += [main_error_def]
                
            # target_bonus_dmg = base
            # m += off_sum - target_bonus_dmg <= main_error
            # m += target_bonus_dmg - off_sum <= main_error

            # if variable_hp_bonus is not None:
            #     target_bonus_hp = round(variable_hp_bonus/step)
            #     m += def_sum - target_bonus_hp <= main_error
            #     m += target_bonus_hp - def_sum <= main_error

            if {"C", "M"} < used_vars.keys():
                m += used_vars["M"] - used_vars["C"] <= mc_error
                m += used_vars["C"] - used_vars["M"] <= mc_error
                errors += [mc_error]
                if "D" in used_vars:
                    m += used_vars["D"] - used_vars["C"] <= dlc_error
                    m += used_vars["C"] - used_vars["D"] <= dlc_error
                if "L" in used_vars:
                    m += used_vars["L"] - used_vars["C"] <= dlc_error
                    m += used_vars["C"] - used_vars["L"] <= dlc_error

            if {"H"} <= used_vars.keys():
                h_used   = pl.LpVariable("h_used",   lowBound=0, upBound=1, cat="Binary")
                h_is18   = pl.LpVariable("h_is18",   lowBound=0, upBound=1, cat="Binary")
                h_nonext = pl.LpVariable("h_nonext", lowBound=0, upBound=1, cat="Binary")
                H = used_vars["H"]
                m += H >= 1 * h_used; m += H <= 180 * h_used
                m += H >= 180 * h_is18; m += H <= 179 + 1 * h_is18

                m += h_nonext == h_used - h_is18
                m += h_nonext <= h_used
                m += h_nonext <= 1 - h_is18

                m += hmid_penalty == h_nonext
                m += h_nonzero_penalty == h_used

                errors += [hmid_penalty, h_nonzero_penalty]
            
            if {"S"} <= used_vars.keys():
                m += sh_error == used_vars["S"]
                errors += [sh_error]

            tot_error = pl.lpSum(err*balancing_weights[err.name] for err in errors)
            m += tot_error
            m.solve(pl.PULP_CBC_CMD(msg=False))
            if pl.LpStatus[m.status] not in ("Optimal", "Feasible"):
                continue
            err_value = int(tot_error.value())
            solutions.append((err_value, used_vars, hero_type))
            print(solutions[-1])

        if len(solutions) == 0:
            raise ValueError(f"Failed to find levels for {bonus_dmg=}, {bonus_hp=}, {lieu=}, {alli_type=}, {atk=}, {hero_enabled=}")

        solutions = sorted(solutions, key=lambda x: x[0])
        # if solutions[0][0] >= 3000000000:
        #     raise ValueError(f"Found no solutions with errors less than 3000000 for {bonus_dmg=}, {bonus_hp=}, {lieu=}, {alli_type=}, {atk=}, {hero_enabled=}")
        
        error_value, used_vars, hero_type = solutions[0]

        args = {
            var.name: int(var.value()) for var in used_vars.values()
        }
        args["alliance"] = alli_type

        if hero_type is not None:
            args["hero_type"] = hero_type
            args["hero_lvl"] = args["hero_lvl"]
            print(f"Added hero {args["hero_type"]=} {args["hero_lvl"]=}")
        levels = cls(**args)
        match atk, lieu:
            case True, _:
                guessed_bonuses = levels.bonus_atk
            case False, FightZone.DOME:
                guessed_bonuses = levels.bonus_dome
            case False, FightZone.LOGE:
                guessed_bonuses = levels.bonus_loge
            case False, FightZone.TDC:
                guessed_bonuses = levels.bonus_tdc

        guessed_bonuses = levels.bonus(lieu, atk)
        epsilon = 1e-7
        if HP_ENABLED:
            assert (bonus_dmg[0] - epsilon <= guessed_bonuses[0] <= bonus_dmg[1] + epsilon) and (bonus_hp[0] - epsilon <= guessed_bonuses[1] <= bonus_hp[1] + epsilon), f"Got {guessed_bonuses} expected to be within {bonus_dmg} for dmg and {bonus_hp} for hp."
        else:
            assert bonus_dmg[0] - epsilon <= guessed_bonuses[0] <= bonus_dmg[1] + epsilon, f"Got {guessed_bonuses[0]} expected to be within {bonus_dmg}"

        return cls(**args)
