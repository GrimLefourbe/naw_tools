import functools
import itertools as it
from dataclasses import dataclass

import numpy as np
import regex as re

from nawminator.army import Army
from nawminator.utils import format_naw_int, NAW_INT_REGEX, parse_naw_int


@dataclass
class Round:
    attacker_base_dmg: np.int64
    attacker_bonus_dmg: np.float64
    defender_base_dmg: np.int64
    defender_bonus_dmg: np.float64
    defender_losses: Army
    attacker_losses: Army


@dataclass
class Battle:
    attacker: Army
    defender: Army
    rounds: list[Round]

    @classmethod
    def from_rc(cls, rc: str):
        attacker = Army.from_str(re.search(r"Troupe en attaque : (.*?)\n", rc).group(1))
        defender = Army.from_str(re.search(r"Troupe en défense : (.*?)\n", rc).group(1))

        res = re.findall(
            rf"^.*?inflige\w* ({NAW_INT_REGEX}) \(\+ ({NAW_INT_REGEX})\) dégâts .*? tu\w+ ({NAW_INT_REGEX}) (unités?|ennemis?)\W*$",
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
        return cls(
            attacker=attacker,
            defender=defender,
            rounds=rounds,
        )

    def to_rc(self) -> str:
        rapport = f"""Attaquant
Troupe en attaque : {self.attacker.to_str()}.
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

    def __hash__(self):
        return id(self)

    @functools.cache
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

    @functools.cache
    def get_left_armies(self) -> tuple[Army, Army]:
        atk_loss, def_loss = self.get_total_losses()
        return self.attacker - atk_loss, self.defender - def_loss
