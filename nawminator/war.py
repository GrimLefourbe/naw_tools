from collections import namedtuple
from dataclasses import dataclass
from functools import reduce

import operator as op
import itertools as it
import numpy as np
import regex as re
import typing as t
from nawminator.army import Army, unit_names, last_units_hp
from nawminator.utils import format_naw_int, NAW_INT_REGEX, parse_naw_int


@dataclass
class Bonuses:
    dmg_bonus: np.float64
    hp_bonus: t.Optional[np.float64]
    min_hp_bonus: t.Optional[np.float64] = None


@dataclass
class WarParty:
    army: Army
    bonuses: Bonuses
    atk: bool

    @classmethod
    def from_str(cls):
        pass

    def to_str(self) -> str:
        pass

    @property
    def base_dmg(self):
        return self.army.base_atk if self.atk else self.army.base_def

    @property
    def bonus_dmg(self):
        return self.base_dmg * self.bonuses[0]

    @property
    def total_dmg(self) -> np.float64:
        return self.base_dmg + self.bonus_dmg

    @property
    def total_hp(self) -> np.float64:
        return self.army.base_hp * (1 + self.bonuses[1])

    def after_dmg(self, dmg: np.float64) -> tuple["WarParty", "WarParty"]:
        base_hp_lost = dmg / (1 + self.bonuses[1])
        lost, kept = self.army.split_by_hp(base_hp_lost)

        return WarParty(lost, self.bonuses, self.atk), WarParty(kept, self.bonuses, self.atk)


@dataclass
class Round:
    attacker_base_dmg: np.int64
    attacker_bonus_dmg: np.float64
    defender_base_dmg: np.int64
    defender_bonus_dmg: np.float64
    defender_losses: Army
    attacker_losses: Army

    def compute_bonuses(self):
        atk_dmg_bonus = self.attacker_bonus_dmg / self.attacker_base_dmg
        def_dmg_bonus = self.defender_bonus_dmg / self.defender_base_dmg
        atk_hp_bonus_max = (self.defender_bonus_dmg + self.defender_base_dmg) / (
            self.attacker_losses.base_hp - 0.5 * last_units_hp(self.attacker_losses)
        )
        atk_hp_bonus_min = (self.defender_bonus_dmg + self.defender_base_dmg) / (
            self.attacker_losses.base_hp + 0.49999 * last_units_hp(self.attacker_losses)
        )
        def_hp_bonus_max = (self.attacker_base_dmg + self.attacker_bonus_dmg) / (
            self.defender_losses.base_hp - 0.5 * last_units_hp(self.defender_losses)
        )
        def_hp_bonus_min = (self.attacker_base_dmg + self.attacker_bonus_dmg) / (
            self.defender_losses.base_hp + 0.49999 * last_units_hp(self.defender_losses)
        )
        return (atk_dmg_bonus, def_dmg_bonus), (
            (atk_hp_bonus_min, atk_hp_bonus_max),
            (def_hp_bonus_min, def_hp_bonus_max),
        )


@dataclass
class Battle:
    attacker: Army
    defender: Army
    rounds: list[Round]

    @classmethod
    def from_rounds(cls, attacker: Army, defender: Army, rounds: list[Round]) -> "Battle":
        return Battle(
            attacker=attacker,
            defender=defender,
            rounds=rounds,
        )

    @classmethod
    def from_bonuses(
        cls,
        attacker: Army,
        attacker_bonuses: Bonuses,
        defender: Army,
        defender_bonuses: Bonuses,
    ) -> "Battle":
        rounds = simulate_rounds(
            WarParty(attacker, attacker_bonuses, atk=True),
            WarParty(defender, defender_bonuses, atk=False),
        )
        return Battle(
            attacker=attacker,
            defender=defender,
            rounds=rounds,
        )

    def generate_rc(self):
        rapport = f"""Attaquant
Troupe en attaque : {self.attacker.to_str()}
Défenseur
Troupe en défense : {self.defender.to_str()}.

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
        total_atk_losses, total_def_losses = self.get_total_losses()
        final_atk = self.attacker - total_atk_losses
        final_def = self.defender - total_def_losses
        if final_atk.count != 0:
            rapport += f"Troupe restante à l'attaquant (avant xp): {final_atk.to_str()}\n"
        if final_def.count != 0:
            rapport += f"Troupe restante au défenseur (avant xp): {final_def.to_str()}\n"

        return rapport.strip()

    def get_total_losses(self) -> tuple[Army, Army]:
        total_atk_losses = sum(
            (r.attacker_losses for r in self.rounds),
            start=Army(),
        )
        total_def_losses = sum(
            (r.defender_losses for r in self.rounds),
            start=Army(),
        )
        return total_atk_losses, total_def_losses


def simulate_rounds(attacker: WarParty, defender: WarParty) -> list[Round]:
    current_atk = attacker
    current_def = defender

    rounds = []

    for round_no in range(100):
        defender_mult = (
            np.float64(0.1) if round_no == 0 and current_atk.total_dmg >= current_def.total_hp else np.float64(1)
        )
        atk_losses, new_atk_party = current_atk.after_dmg(current_def.total_dmg * defender_mult)
        def_losses, new_def_party = current_def.after_dmg(current_atk.total_dmg)
        rounds.append(
            Round(
                attacker_base_dmg=current_atk.base_dmg,
                attacker_bonus_dmg=current_atk.bonus_dmg,
                defender_base_dmg=current_def.base_dmg * defender_mult,
                defender_bonus_dmg=current_def.bonus_dmg * defender_mult,
                attacker_losses=atk_losses.army,
                defender_losses=def_losses.army,
            )
        )
        current_atk = new_atk_party
        current_def = new_def_party
        if current_atk.army.count == 0 or current_def.army.count == 0:
            break
    return rounds


def make_fight(
    attacker: WarParty, defender: WarParty
) -> tuple[str, tuple[WarParty, WarParty], tuple[WarParty, WarParty]]:
    battle = Battle.from_bonuses(
        attacker=attacker.army,
        attacker_bonuses=attacker.bonuses,
        defender=defender.army,
        defender_bonuses=defender.bonuses,
    )

    final_atk = WarParty(
        reduce(op.sub, (r.attacker_losses for r in battle.rounds), attacker.army),
        attacker.bonuses,
        atk=True,
    )
    final_def = WarParty(
        reduce(op.sub, (r.defender_losses for r in battle.rounds), defender.army),
        defender.bonuses,
        atk=False,
    )

    atk_losses, def_losses = battle.get_total_losses()
    atk_losses = WarParty(atk_losses, attacker.bonuses, atk=True)
    def_losses = WarParty(def_losses, defender.bonuses, atk=False)

    return battle.generate_rc(), (final_atk, final_def), (atk_losses, def_losses)


def parse_rc(rc: str) -> tuple[Army, Army, list[Round]]:
    attacker = Army.from_str(re.search(r"Troupe en attaque : (.*?)\n", rc).group(1))
    defender = Army.from_str(re.search(r"Troupe en défense : (.*?)\n", rc).group(1))

    res = re.findall(
        rf"^.*?inflige\w* ({NAW_INT_REGEX}) \(\+ ({NAW_INT_REGEX})\) dégâts .*? tu\w+ ({NAW_INT_REGEX}) (unités?|ennemis?)\W*$",
        rc,
        re.MULTILINE,
    )

    damage_lines = [(parse_naw_int(a), parse_naw_int(b), parse_naw_int(c)) for a, b, c, d in res]

    if len(damage_lines) % 2 != 0:
        raise ValueError(f"The number of rounds in the rapport is uneven. Parsed {len(damage_lines)} rounds from {rc}")

    cur_atk = attacker
    cur_def = defender
    rounds = []
    for atk, riposte in it.batched(damage_lines, n=2):
        atk_loss, cur_atk = cur_atk.split_by_count(riposte[2])
        def_loss, cur_def = cur_def.split_by_count(atk[2])
        rounds.append(
            Round(
                attacker_base_dmg=np.int64(atk[0]),
                attacker_bonus_dmg=np.float64(atk[1]),
                attacker_losses=atk_loss,
                defender_base_dmg=np.int64(riposte[0]),
                defender_bonus_dmg=np.float64(riposte[1]),
                defender_losses=def_loss,
            )
        )
    return attacker, defender, rounds


def analyse_rc(rc: str) -> tuple[Battle, tuple[WarParty, WarParty]]:
    battle = Battle.from_rounds(*parse_rc(rc))
    return battle, (
        WarParty(battle.attacker, Bonuses(*battle.max_atk_bonuses), atk=True),
        WarParty(battle.defender, Bonuses(*battle.max_def_bonuses), atk=False),
    )
