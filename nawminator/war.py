from dataclasses import dataclass

import numpy as np
import typing as t
import nawminator as nm


@dataclass
class Bonuses:
    dmg: np.float64
    hp: t.Optional[np.float64]
    min_hp: t.Optional[np.float64] = None

    @classmethod
    def compute_bonuses(cls, br: nm.battle.Round, step=5e-3) -> tuple["Bonuses", "Bonuses"]:
        istep = np.float64(1) / step
        atk_dmg_bonus = round(istep * br.attacker_bonus_dmg / br.attacker_base_dmg) / np.float64(istep)
        def_dmg_bonus = round(istep * br.defender_bonus_dmg / br.defender_base_dmg) / np.float64(istep)
        atk_hp_bonus_max = (br.defender_bonus_dmg + br.defender_base_dmg) / (
            br.attacker_losses.base_hp - 0.5 * nm.army.last_units_hp(br.attacker_losses)
        )
        atk_hp_bonus_min = (br.defender_bonus_dmg + br.defender_base_dmg) / (
            br.attacker_losses.base_hp + 0.49999 * nm.army.last_units_hp(br.attacker_losses)
        )
        def_hp_bonus_max = (br.attacker_base_dmg + br.attacker_bonus_dmg) / (
            br.defender_losses.base_hp - 0.5 * nm.army.last_units_hp(br.defender_losses)
        )
        def_hp_bonus_min = (br.attacker_base_dmg + br.attacker_bonus_dmg) / (
            br.defender_losses.base_hp + 0.49999 * nm.army.last_units_hp(br.defender_losses)
        )
        def_hp_bonus_max = np.floor(istep * (def_hp_bonus_max - 1)) / np.float64(istep)
        def_hp_bonus_min = np.ceil(istep * (def_hp_bonus_min - 1)) / np.float64(istep)

        atk_hp_bonus_max = np.floor(istep * (atk_hp_bonus_max - 1)) / np.float64(istep)
        atk_hp_bonus_min = np.ceil(istep * (atk_hp_bonus_min - 1)) / np.float64(istep)

        if def_hp_bonus_min == def_hp_bonus_max:
            def_bonuses = Bonuses(dmg=def_dmg_bonus, hp=def_hp_bonus_min)
        else:
            def_bonuses = Bonuses(dmg=def_dmg_bonus, hp=def_hp_bonus_max, min_hp=def_hp_bonus_min)
        if atk_hp_bonus_max == atk_hp_bonus_min:
            atk_bonuses = Bonuses(dmg=atk_dmg_bonus, hp=atk_hp_bonus_min)
        else:
            atk_bonuses = Bonuses(dmg=atk_dmg_bonus, hp=atk_hp_bonus_max, min_hp=atk_hp_bonus_min)
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


def simulate_battle(
    attacker: WarParty, defender: WarParty
) -> nm.battle.Battle:
    battle_rounds = simulate_rounds(attacker, defender)
    return nm.battle.Battle(attacker.army, defender.army, battle_rounds)


def analyze_battle(battle: nm.battle.Battle) -> tuple[WarParty, WarParty]:
    pass

