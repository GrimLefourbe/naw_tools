import numpy as np
import pytest
import hypothesis as hp
import hypothesis.strategies as st

import nawminator as nm

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
                (
                    nm.army.Army(JS=100),
                    nm.army.Army(JS=1118),
                    [
                        nm.war.Round(
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
                (
                    nm.army.Army(JS=100, S=100),
                    nm.army.Army(S=100, T=127),
                    [
                        nm.war.Round(
                            attacker_base_dmg=np.int64(1900),
                            attacker_bonus_dmg=np.float64(0),
                            defender_base_dmg=np.int64(2270),
                            defender_bonus_dmg=np.float64(0),
                            attacker_losses=nm.army.Army(JS=100, S=34),
                            defender_losses=nm.army.Army(S=95),
                        ),
                        nm.war.Round(
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
                (
                    nm.army.Army(JS=100),
                    nm.army.Army(JS=100),
                    [
                        nm.war.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.war.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.war.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.war.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
            ),
        ],
    )
    def test_parse_rc(self, rc, expected):
        assert nm.war.parse_rc(rc) == expected

    @pytest.mark.parametrize(
        "battle",
        [
            nm.war.Battle(
                attacker=nm.army.Army(JS=100),
                defender=nm.army.Army(JS=100),
                rounds=[
                    nm.war.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                    nm.war.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                    nm.war.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                    nm.war.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                ],
            ),
        ],
    )
    def test_export_import_rc(self, battle):
        assert battle == nm.war.Battle(*nm.war.parse_rc(battle.generate_rc()))

    @pytest.mark.skip
    @hp.given(
        attacker=st.lists(st.integers(min_value=0, max_value=2**56), min_size=15, max_size=15),
        defender=st.lists(st.integers(min_value=0, max_value=2**56), min_size=15, max_size=15),
        rounds=st.lists(
            st.tuples(
                st.lists(st.integers(min_value=0, max_value=2**56), min_size=4, max_size=4),
                st.lists(st.integers(min_value=0, max_value=2**56), min_size=15, max_size=15),
                st.lists(st.integers(min_value=0, max_value=2**56), min_size=15, max_size=15),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    def test_export_import_rc_property(self, attacker, defender, rounds):
        battle = nm.war.Battle(
            nm.army.Army(attacker),
            nm.army.Army(defender),
            [
                nm.war.Round(*round[0], attacker_losses=nm.army.Army(round[1]), defender_losses=nm.army.Army(round[2]))
                for round in rounds
            ],
        )
        assert battle == nm.war.Battle(*nm.war.parse_rc(battle.generate_rc()))

    @pytest.mark.parametrize(
        "battle,expected",
        [
            (
                nm.war.Battle(
                    attacker=nm.army.Army(JS=100),
                    defender=nm.army.Army(JS=100),
                    rounds=[
                        nm.war.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.war.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.war.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.war.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
                RC_SIMU_NM,
            ),
        ],
    )
    @pytest.mark.skip
    def test_generate_rc(self, battle, expected):
        assert battle.generate_rc() == expected

    @pytest.mark.skip
    def test_get_total_losses(self, battle, expected):
        pass
