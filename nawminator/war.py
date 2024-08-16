from dataclasses import dataclass

import numpy as np
import typing as t
import nawminator as nm


def compute_hp_bonus_range(dmg: np.float64, losses: nm.army.Army):
    ### COMPUTE HP BONUSES
    upper_limit = dmg / (losses.base_hp - 0.5 * nm.army.last_units_hp(losses))
    lower_limit = dmg / (losses.base_hp + 0.49999 * nm.army.last_units_hp(losses))

    return upper_limit, lower_limit


@dataclass
class Bonuses:
    dmg: np.float64
    hp: t.Optional[np.float64]
    min_dmg: t.Optional[np.float64] = None
    min_hp: t.Optional[np.float64] = None

    def __init__(
        self,
        dmg: np.float64,
        hp: t.Optional[np.float64],
        min_dmg: t.Optional[np.float64] = None,
        min_hp: t.Optional[np.float64] = None,
    ):
        if dmg == min_dmg:
            min_dmg = None
        if hp == min_hp:
            min_hp = None
        self.dmg = dmg
        self.min_dmg = min_dmg
        self.hp = hp
        self.min_hp = min_hp

    @classmethod
    def from_rounds(cls, rounds: list[nm.battle.Round] | nm.battle.Round) -> tuple["Bonuses", "Bonuses"]:
        if isinstance(rounds, nm.battle.Round):
            rounds = [rounds]

        atk_bonuses, def_bonuses = cls.compute_bonuses(rounds[0])
        atk_dmg, atk_hp = (atk_bonuses.dmg, atk_bonuses.min_dmg), (atk_bonuses.hp, atk_bonuses.min_hp)
        def_dmg, def_hp = (def_bonuses.dmg, def_bonuses.min_dmg), (def_bonuses.hp, def_bonuses.min_hp)

        for br in rounds[1:]:
            new_atk_bonuses, new_def_bonuses = cls.compute_bonuses(br)

            if atk_dmg[1] is not None:
                atk_dmg = (min(atk_dmg[0], new_atk_bonuses.dmg), max(atk_dmg[1], new_atk_bonuses.min_dmg))
            if def_dmg[1] is not None:
                def_dmg = (min(def_dmg[0], new_def_bonuses.dmg), max(def_dmg[1], new_def_bonuses.min_dmg))

            if new_atk_bonuses.min_hp is not None:
                atk_hp = (
                    min(atk_hp[0], new_atk_bonuses.hp),
                    max(atk_hp[1], new_atk_bonuses.min_hp),
                )
            if new_def_bonuses.min_hp is not None:
                def_hp = (
                    min(def_hp[0], new_def_bonuses.hp),
                    max(def_hp[1], new_def_bonuses.min_hp),
                )

        return Bonuses(dmg=atk_dmg[0], min_dmg=atk_dmg[1], hp=atk_hp[0], min_hp=atk_hp[1]), Bonuses(
            dmg=def_dmg[0], min_dmg=def_dmg[1], hp=def_hp[0], min_hp=def_hp[1]
        )

    @classmethod
    def compute_bonuses(cls, br: nm.battle.Round, step=5e-3) -> tuple["Bonuses", "Bonuses"]:
        istep = np.float64(1) / step

        ### COMPUTE DMG BONUSES
        atk_dmg_bonus_max = np.floor(istep * (br.attacker_bonus_dmg + 0.4999) / br.attacker_base_dmg) / np.float64(
            istep
        )
        atk_dmg_bonus_min = np.ceil(istep * (br.attacker_bonus_dmg - 0.5) / br.attacker_base_dmg) / np.float64(istep)
        def_dmg_bonus_max = np.floor(istep * (br.defender_bonus_dmg + 0.4999) / br.defender_base_dmg) / np.float64(
            istep
        )
        def_dmg_bonus_min = np.ceil(istep * (br.defender_bonus_dmg - 0.5) / br.defender_base_dmg) / np.float64(istep)

        ### COMPUTE HP BONUSES
        if br.defender_base_dmg + br.defender_bonus_dmg > 4 * br.attacker_losses.base_hp:
            atk_hp_bonus_max, atk_hp_bonus_min = None, None
        else:
            atk_hp_bonus = compute_hp_bonus_range(br.defender_bonus_dmg + br.defender_base_dmg, br.attacker_losses)
            atk_hp_bonus_max = np.floor(istep * (atk_hp_bonus[0] - 1)) / np.float64(istep)
            atk_hp_bonus_min = np.ceil(istep * (atk_hp_bonus[1] - 1)) / np.float64(istep)
        if br.attacker_base_dmg + br.attacker_bonus_dmg > 4 * br.defender_losses.base_hp:
            def_hp_bonus_max, def_hp_bonus_min = None, None
        else:
            def_hp_bonus = compute_hp_bonus_range(br.attacker_base_dmg + br.attacker_bonus_dmg, br.defender_losses)
            def_hp_bonus_max = np.floor(istep * (def_hp_bonus[0] - 1)) / np.float64(istep)
            def_hp_bonus_min = np.ceil(istep * (def_hp_bonus[1] - 1)) / np.float64(istep)

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
        pass

    @property
    def base_dmg(self):
        return self.army.base_atk if self.atk else self.army.base_def

    @property
    def bonus_dmg(self):
        return np.floor(0.5 + self.base_dmg * self.bonuses.dmg)

    @property
    def total_dmg(self) -> np.float64:
        return np.floor(0.5 + self.base_dmg + self.bonus_dmg)

    @property
    def total_hp(self) -> np.float64:
        return np.floor(0.5 + self.army.base_hp * (1 + self.bonuses.hp))

    def after_dmg(self, dmg: np.float64) -> tuple["WarParty", "WarParty"]:
        base_hp_lost = dmg / (1 + self.bonuses.hp)
        lost, kept = self.army.split_by_hp(base_hp_lost)

        return WarParty(lost, self.bonuses, self.atk), WarParty(kept, self.bonuses, self.atk)


def simulate_rounds(attacker: WarParty, defender: WarParty) -> list[nm.battle.Round]:
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
            nm.battle.Round(
                attacker_base_dmg=current_atk.base_dmg,
                attacker_bonus_dmg=current_atk.bonus_dmg,
                defender_base_dmg=np.int64(current_def.base_dmg * defender_mult),
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


def simulate_battle(attacker: WarParty, defender: WarParty) -> nm.battle.Battle:
    battle_rounds = simulate_rounds(attacker, defender)
    return nm.battle.Battle(attacker.army, defender.army, battle_rounds)


def analyze_battle(battle: nm.battle.Battle) -> tuple[WarParty, WarParty]:
    atk_bonuses, def_bonuses = Bonuses.from_rounds(battle.rounds)

    return (
        WarParty(battle.attacker, bonuses=atk_bonuses, atk=True),
        WarParty(battle.defender, bonuses=def_bonuses, atk=False),
    )
