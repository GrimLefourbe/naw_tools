import functools
import itertools as it
import typing as t
from dataclasses import dataclass

import numpy as np
import regex as re

import nawminator as nm
from nawminator.army import Army
from nawminator.utils import format_naw_int, NAW_INT_REGEX, parse_naw_int

__all__ = ["Bonuses", "WarParty", "Round", "BattleReport", "simulate_rounds"]

@dataclass
class Bonuses:
    max_dmg: float
    max_hp: t.Optional[float]
    min_dmg: float
    min_hp: t.Optional[float]

    def __init__(
        self,
        dmg: float,
        hp: t.Optional[float],
        min_dmg: t.Optional[float] = None,
        min_hp: t.Optional[float] = None,
    ):
        self.max_dmg = dmg
        self.min_dmg = dmg if min_dmg is None else min_dmg
        self.max_hp = hp
        self.min_hp = hp if min_hp is None or hp is None else min_hp

    @property
    def hp(self):
        return self.max_hp

    @property
    def dmg(self):
        return self.max_dmg

    def intersect(self, b: "Bonuses") -> "Bonuses":
        match (self.hp, b.hp):
            case (hp, None) | (None, hp):
                pass
            case ah, bh:
                hp = np.min((ah, bh))

        match (self.min_dmg, b.min_dmg):
            case (min_dmg, None) | (None, min_dmg):
                pass
            case amd, bmd:
                min_dmg = np.max([amd, bmd])

        match (self.min_hp, b.min_hp):
            case (min_hp, None) | (None, min_hp):
                pass
            case amh, bmh:
                min_hp = np.max([amh, bmh])

        return Bonuses(dmg=np.min([self.dmg, b.dmg]), hp=hp, min_dmg=min_dmg, min_hp=min_hp)

    @classmethod
    def from_rounds(cls, rounds: "list[nm.battle.Round] | nm.battle.Round") -> tuple["Bonuses", "Bonuses"]:
        if isinstance(rounds, nm.battle.Round):
            rounds = [rounds]

        atk_bonuses, def_bonuses = cls._from_round(rounds[0])
        for round in rounds[1:]:
            new_atk_bonuses, new_def_bonuses = cls._from_round(round)

            atk_bonuses = atk_bonuses.intersect(new_atk_bonuses)
            def_bonuses = def_bonuses.intersect(new_def_bonuses)

        return atk_bonuses, def_bonuses

    @classmethod
    def _from_round(cls, br: "nm.battle.Round") -> tuple["Bonuses", "Bonuses"]:
        EPS = 1e-7
        ### COMPUTE DMG BONUSES
        atk_dmg_bonus_max = (br.attacker_bonus_dmg + 0.5 - EPS) / br.attacker_base_dmg
        atk_dmg_bonus_min = (br.attacker_bonus_dmg - 1 + EPS) / br.attacker_base_dmg
        def_dmg_bonus_max = (br.defender_bonus_dmg + 0.5 - EPS) / br.defender_base_dmg
        def_dmg_bonus_min = (br.defender_bonus_dmg - 1 + EPS) / br.defender_base_dmg

        assert atk_dmg_bonus_max >= atk_dmg_bonus_min
        assert def_dmg_bonus_max >= def_dmg_bonus_min

        ### COMPUTE HP BONUSES
        if br.defender_base_dmg + br.defender_bonus_dmg > 4 * br.attacker_losses.base_hp:
            atk_hp_bonus_max, atk_hp_bonus_min = None, None
        else:
            atk_hp_bonus_max, atk_hp_bonus_min = _compute_hp_bonus_range(br.defender_bonus_dmg + br.defender_base_dmg, br.attacker_losses)

        if br.attacker_base_dmg + br.attacker_bonus_dmg > 4 * br.defender_losses.base_hp:
            def_hp_bonus_max, def_hp_bonus_min = None, None
        else:
            def_hp_bonus_max, def_hp_bonus_min = _compute_hp_bonus_range(br.attacker_base_dmg + br.attacker_bonus_dmg, br.defender_losses)

        def_bonuses = Bonuses(
            dmg=def_dmg_bonus_max, hp=def_hp_bonus_max, min_dmg=def_dmg_bonus_min, min_hp=def_hp_bonus_min
        )
        atk_bonuses = Bonuses(
            dmg=atk_dmg_bonus_max, hp=atk_hp_bonus_max, min_dmg=atk_dmg_bonus_min, min_hp=atk_hp_bonus_min
        )

        return atk_bonuses, def_bonuses

@dataclass
class WarParty:
    army: nm.army.Army
    bonuses: Bonuses
    atk: bool

    @classmethod
    def from_str(cls):
        pass

    def to_str(self) -> str:
        raise NotImplementedError

    @property
    def base_dmg(self):
        return self.army.base_atk if self.atk else self.army.base_def

    @property
    def bonus_dmg(self) -> float:
        return nm.formulas.naw_round(self.base_dmg * self.bonuses.dmg)

    @property
    def total_dmg(self) -> float:
        return nm.formulas.naw_round(self.base_dmg + self.bonus_dmg)

    @property
    def total_hp(self) -> float:
        return float("nan") if self.bonuses.hp is None else nm.formulas.naw_round(self.army.base_hp * (1 + self.bonuses.hp))

    def after_dmg(self, dmg: float) -> tuple["WarParty", "WarParty"]:
        if self.bonuses.hp is None:
            raise ValueError("Can't compute after damage without knowing hp bonus")
        base_hp_lost = dmg / (1 + self.bonuses.hp)
        lost, kept = self.army.split_by_hp(np.float64(base_hp_lost))

        return WarParty(lost, self.bonuses, self.atk), WarParty(kept, self.bonuses, self.atk)


@dataclass
class Round:
    attacker_base_dmg: np.int64
    attacker_bonus_dmg: np.float64
    defender_base_dmg: np.int64
    defender_bonus_dmg: np.float64
    defender_losses: Army
    attacker_losses: Army

    @classmethod
    def simulate(cls, attacker: WarParty, defender: WarParty, first_round: bool) -> tuple[t.Self, WarParty, WarParty]:
        defender_mult = (
            np.float64(0.1) if first_round and attacker.total_dmg >= defender.total_hp else np.float64(1)
        )
        atk_losses, new_atk_party = attacker.after_dmg(defender.total_dmg * defender_mult)
        def_losses, new_def_party = defender.after_dmg(attacker.total_dmg)

        round = cls(
            attacker_base_dmg=attacker.base_dmg,
            attacker_bonus_dmg=np.round(attacker.bonus_dmg),
            defender_base_dmg=np.int64(np.round(defender.base_dmg * defender_mult)),
            defender_bonus_dmg=np.round(defender.bonus_dmg * defender_mult),
            attacker_losses=atk_losses.army,
            defender_losses=def_losses.army,
        )
        return round, new_atk_party, new_def_party


def _compute_hp_bonus_range(dmg: np.float64, losses: nm.army.Army):
    EPS = 1e-7
    ### COMPUTE HP BONUSES
    upper_limit = dmg / (losses.base_hp - 0.5 * nm.army.last_units_hp(losses))
    lower_limit = dmg / (losses.base_hp + (0.5 - EPS) * nm.army.last_units_hp(losses))

    return upper_limit - 1, lower_limit - 1


@dataclass
class BattleReport:
    attacker: Army
    defender: Army
    rounds: list[Round]

    @classmethod
    def from_str(cls, rc: str):
        if res := re.search(r"Troupe en attaque : (.*?)\n", rc):
            attacker = Army.from_str(res.group(1))
        else:
            raise ValueError(f"Could not parse attacker in {rc}")
        
        if res := re.search(r"Troupe en défense : (.*?)\n", rc):
            defender = Army.from_str(res.group(1))

        res = re.findall(
            rf"^.*?inflig[eé]\w* ({NAW_INT_REGEX}) \(\+ ({NAW_INT_REGEX})\) dégâts .*? tu\w+ ({NAW_INT_REGEX}) (unités?|ennemis?)\W*$",
            rc,
            re.MULTILINE,
        )

        damage_lines = [(parse_naw_int(a), parse_naw_int(b), parse_naw_int(c)) for a, b, c, d in res]

        if len(damage_lines) % 2 != 0:
            raise ValueError(
                f"The number of rounds in the rapport is uneven. Parsed {len(damage_lines)} rounds from {rc}"
            )

        cur_atk = attacker
        cur_def = defender
        rounds: list[Round] = []
        for atk, riposte in it.batched(damage_lines, n=2):
            atk_loss, cur_atk = cur_atk.split_by_count(np.int64(riposte[2]))
            def_loss, cur_def = cur_def.split_by_count(np.int64(atk[2]))
            rounds.append(
                Round(
                    attacker_base_dmg=np.int64(atk[0]),
                    attacker_bonus_dmg=np.round(np.float64(atk[1])),
                    attacker_losses=atk_loss,
                    defender_base_dmg=np.int64(riposte[0]),
                    defender_bonus_dmg=np.round(np.float64(riposte[1])),
                    defender_losses=def_loss,
                )
            )
        return cls(
            attacker=attacker,
            defender=defender,
            rounds=rounds,
        )

    def to_str(self) -> str:
        rapport = f"""Attaquant
Troupe en attaque : {self.attacker.to_str()}
Défenseur
Troupe en défense : {self.defender.to_str()}

Combat
"""

        for r in self.rounds:
            rapport += "L'attaquant inflige {} (+ {}) dégâts au défenseur et tue {} unités.\n".format(
                format_naw_int(round(r.attacker_base_dmg)),
                format_naw_int(round(r.attacker_bonus_dmg)),
                format_naw_int(r.defender_losses.count),
            )
            rapport += "Le défenseur inflige {} (+ {}) dégâts à l'attaquant et tue {} unités.\n".format(
                format_naw_int(round(r.defender_base_dmg)),
                format_naw_int(round(r.defender_bonus_dmg)),
                format_naw_int(r.attacker_losses.count),
            )

        rapport += "\nAprès combat\n"
        total_atk_losses, total_def_losses = self.total_losses()
        final_atk = self.attacker - total_atk_losses
        final_def = self.defender - total_def_losses
        if final_atk.count != 0:
            rapport += f"Troupe restante à l'attaquant (avant xp): {final_atk.to_str()}\n"
        if final_def.count != 0:
            rapport += f"Troupe restante au défenseur (avant xp): {final_def.to_str()}\n"

        return rapport.strip()

    def __hash__(self):
        return id(self)

    @functools.cache
    def total_losses(self) -> tuple[Army, Army]:
        total_atk_losses = sum(
            (r.attacker_losses for r in self.rounds),
            start=Army(),
        )
        total_def_losses = sum(
            (r.defender_losses for r in self.rounds),
            start=Army(),
        )
        return total_atk_losses, total_def_losses

    @functools.cache
    def left_armies(self) -> tuple[Army, Army]:
        atk_loss, def_loss = self.total_losses()
        return self.attacker - atk_loss, self.defender - def_loss
    
    def analyze(self) -> tuple[WarParty, WarParty]:
        atk_bonuses, def_bonuses = Bonuses.from_rounds(self.rounds)
        if self.rounds[0].defender_losses == self.defender:
            def_bonuses = Bonuses(dmg=def_bonuses.max_dmg, min_dmg=def_bonuses.min_dmg, hp=None)
        return (
            WarParty(self.attacker, bonuses=atk_bonuses, atk=True),
            WarParty(self.defender, bonuses=def_bonuses, atk=False),
        )
    
    @classmethod
    def simulate(cls, attacker: WarParty, defender: WarParty) -> t.Self:
        battle_rounds = simulate_rounds(attacker, defender)
        return cls(attacker.army, defender.army, battle_rounds)        


def simulate_rounds(attacker: WarParty, defender: WarParty) -> list[Round]:
    current_atk = attacker
    current_def = defender

    rounds = []
    for round_no in range(500):
        round, current_atk, current_def = Round.simulate(current_atk, current_def, round_no==0)
        rounds.append(round)
        if current_atk.army.count == 0 or current_def.army.count == 0:
            break
    return rounds
