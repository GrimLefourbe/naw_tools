import numpy as np
import pytest
import hypothesis as hp
import hypothesis.strategies as st

import nawminator as nm
from nawminator.battle import BattleReport

from . import strategies as nm_st

RC_REEL = """Rapport de combat en Loge :

Vous attaquez la colonie Pandi[-220:-63] du joueur flomel avec votre colonie En vacances[47:235] en Loge.

Avant combat
Troupe en attaque : 100 Jeunes soldates
Troupe en défense : 1 118 Jeunes soldates

Combat
Vous infligez 800 (+ 840) dégâts et vous tuez 33 ennemis
La défense riposte, vous infligeant 7 826 (+ 6 965) dégâts et tuant 100 unités.

Après combat
Expérience gagnée : aucune.
Armée finale : Aucune."""

RC_SIMU_NAW = """Raid en Terrain de chasse

Avant combat
Troupe en attaque : 100 Jeunes soldates, 100 Soldates
Troupe en défense : 100 Soldates, 127 Tirailleuses

Vous infligez 1 900 (+ 0) dégâts et vous tuez 95 ennemis
La défense riposte, vous infligeant 2 270 (+ 0) dégâts et tuant 134 unités.
Vous infligez 726 (+ 0) dégâts et vous tuez 57 ennemis
La défense riposte, vous infligeant 1 320 (+ 0) dégâts et tuant 66 unités.

Vous venez d'être écrasé par votre rival !

Après combat
Troupes en attaque : aucune."""

RC_SIMU_NM = """Attaquant
Troupe en attaque : 100 Jeunes soldates
Défenseur
Troupe en défense : 100 Jeunes soldates

Combat
L'attaquant inflige 800 (+ 760) dégâts au défenseur et tue 50 unités.
Le défenseur inflige 700 (+ 665) dégâts à l'attaquant et tue 44 unités.
L'attaquant inflige 448 (+ 426) dégâts au défenseur et tue 28 unités.
Le défenseur inflige 350 (+ 333) dégâts à l'attaquant et tue 22 unités.
L'attaquant inflige 272 (+ 258) dégâts au défenseur et tue 17 unités.
Le défenseur inflige 154 (+ 146) dégâts à l'attaquant et tue 10 unités.
L'attaquant inflige 192 (+ 182) dégâts au défenseur et tue 5 unités.
Le défenseur inflige 35 (+ 33) dégâts à l'attaquant et tue 2 unités.

Après combat
Troupe restante à l'attaquant (avant xp): 22 Jeunes soldates
"""


class TestBattle:
    @pytest.mark.parametrize(
        "rc,expected",
        [
            (
                RC_REEL,
                nm.battle.BattleReport(
                    nm.army.Army(JS=100),
                    nm.army.Army(JS=1118),
                    [
                        nm.battle.Round(
                            attacker_base_dmg=np.int64(800),
                            attacker_bonus_dmg=np.float64(840),
                            defender_base_dmg=np.int64(7826),
                            defender_bonus_dmg=np.float64(6965),
                            attacker_losses=nm.army.Army(JS=100),
                            defender_losses=nm.army.Army(JS=33),
                        )
                    ],
                ),
            ),
            (
                RC_SIMU_NAW,
                nm.battle.BattleReport(
                    nm.army.Army(JS=100, S=100),
                    nm.army.Army(S=100, T=127),
                    [
                        nm.battle.Round(
                            attacker_base_dmg=np.int64(1900),
                            attacker_bonus_dmg=np.float64(0),
                            defender_base_dmg=np.int64(2270),
                            defender_bonus_dmg=np.float64(0),
                            attacker_losses=nm.army.Army(JS=100, S=34),
                            defender_losses=nm.army.Army(S=95),
                        ),
                        nm.battle.Round(
                            attacker_base_dmg=np.int64(726),
                            attacker_bonus_dmg=np.float64(0),
                            defender_base_dmg=np.int64(1320),
                            defender_bonus_dmg=np.float64(0),
                            attacker_losses=nm.army.Army(S=66),
                            defender_losses=nm.army.Army(S=5, T=52),
                        ),
                    ],
                ),
            ),
            (
                RC_SIMU_NM,
                nm.battle.BattleReport(
                    nm.army.Army(JS=100),
                    nm.army.Army(JS=100),
                    [
                        nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
            ),
        ],
    )
    def test_parse_rc(self, rc, expected):
        assert nm.battle.BattleReport.from_str(rc) == expected

    @pytest.mark.parametrize(
        "battle",
        [
            nm.battle.BattleReport(
                attacker=nm.army.Army(JS=100),
                defender=nm.army.Army(JS=100),
                rounds=[
                    nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                    nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                    nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                    nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                ],
            ),
        ],
    )
    def test_export_import_rc(self, battle: BattleReport):
        assert battle == nm.battle.BattleReport.from_str(battle.to_str())

    @pytest.mark.parametrize(
        "battle,expected",
        [
            (
                nm.battle.BattleReport(
                    attacker=nm.army.Army(JS=100),
                    defender=nm.army.Army(JS=100),
                    rounds=[
                        nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
                RC_SIMU_NM.strip(),
            ),
        ],
    )
    def test_generate_rc(self, battle, expected):
        assert battle.to_str() == expected

    @pytest.mark.parametrize(
        "battle,expected",
        [
            (
                nm.battle.BattleReport(
                    attacker=nm.army.Army(JS=100),
                    defender=nm.army.Army(JS=100),
                    rounds=[
                        nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
                (nm.army.Army(JS=78), nm.army.Army(JS=100)),
            ),
        ],
    )
    def test_get_total_losses(self, battle: BattleReport, expected):
        assert battle.total_losses() == expected

    @pytest.mark.xfail(reason="TODO")
    def test_analyze_battle(self):
        raise NotImplementedError # TODO

@pytest.mark.property
class TestProperties:
    @hp.given(attacker=nm_st.simple_warparty_strategy, defender=nm_st.simple_warparty_strategy)
    def test_simulation_export_import(self, attacker: nm.battle.WarParty, defender: nm.battle.WarParty):
        hp.assume((nm.army.MAX_UNIT_COUNT//64 > attacker.army._units).all())
        hp.assume((nm.army.MAX_UNIT_COUNT//64 > defender.army._units).all())
        defender.atk = False
        battle = nm.battle.BattleReport.simulate(attacker=attacker, defender=defender)
        rc = battle.to_str()
        parsed_battle = nm.battle.BattleReport.from_str(rc)
        assert battle == parsed_battle

    # @hp.reproduce_failure('6.130.4', b'AXicc2RwBEN3RinHtOmHsoEs5jYZ1XOPgoEshkWtedK3lzkyIKAGAxTAGciybj4Tb9TKXXFnenJ6a7SsNcjYCI230+UP4zMAAHK/Ggo=')
    @hp.given(attacker=nm_st.simple_warparty_strategy, defender=nm_st.simple_warparty_strategy)
    def test_simulation_one_dead(self, attacker: nm.battle.WarParty, defender: nm.battle.WarParty):
        hp.assume((nm.army.MAX_UNIT_COUNT//64 > attacker.army._units).all())
        hp.assume((nm.army.MAX_UNIT_COUNT//64 > defender.army._units).all())
        hp.assume(attacker.army.count > 0)
        hp.assume(defender.army.count > 0)
        hp.note(attacker.army.to_str())
        hp.note(defender.army.to_str())
        defender.atk = False
        battle = nm.battle.BattleReport.simulate(attacker=attacker, defender=defender)
        hp.note(battle.to_str())
        left_atk, left_def = battle.left_armies()
        assert (left_atk.count == 0) or (left_def.count == 0), battle

    attacker_bonuses_strategy = nm_st.levels_strategy.map(lambda x: nm.battle.Bonuses(*x.bonus_atk))
    defender_bonuses_strategy = nm_st.levels_strategy.map(lambda x: nm.battle.Bonuses(*x.bonus_dome))
    
    @pytest.mark.xfail(reason="Need better handling of uncertainty in computed bonuses")
    @hp.settings(suppress_health_check=[hp.HealthCheck.filter_too_much])
    @hp.given(
        attacker=st.builds(nm.battle.WarParty, army=nm_st.army_strategy, bonuses=attacker_bonuses_strategy, atk=st.just(True)),
        defender=st.builds(nm.battle.WarParty, army=nm_st.army_strategy, bonuses=defender_bonuses_strategy, atk=st.just(False))
    )
    def test_simulate_analyze_large_armies(self, attacker: nm.battle.WarParty, defender: nm.battle.WarParty):
        # hp.assume((nm.army.MAX_UNIT_COUNT//64 > attacker.army._units).all())
        # hp.assume((nm.army.MAX_UNIT_COUNT//64 > defender.army._units).all())
        hp.assume(attacker.army.count > 0 and defender.army.count > 0)
        hp.note(attacker.army.to_str())
        hp.note(defender.army.to_str())
        battle = nm.battle.BattleReport.simulate(attacker=attacker, defender=defender)
        hp.note(battle.to_str())
        analyzed_atk, analyzed_def = battle.analyze()
        assert attacker == analyzed_atk, defender == analyzed_def
