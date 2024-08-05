import numpy as np
import pytest
import hypothesis as hp
import hypothesis.strategies as st

import nawminator as nm

army_strategy = st.builds(
    nm.army.Army,
    st.lists(st.integers(min_value=0, max_value=nm.army.MAX_UNIT_COUNT), min_size=15, max_size=15),
)
round_strategy = st.builds(
    nm.battle.Round,
    attacker_base_dmg=st.integers(min_value=0),
    attacker_bonus_dmg=st.integers(min_value=0),
    defender_base_dmg=st.integers(min_value=0),
    defender_bonus_dmg=st.integers(min_value=0),
    attacker_losses=army_strategy,
    defender_losses=army_strategy,
)
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
                nm.battle.Battle(
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
                nm.battle.Battle(
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
                nm.battle.Battle(
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
        assert nm.battle.Battle.from_rc(rc) == expected

    @pytest.mark.parametrize(
        "battle",
        [
            nm.battle.Battle(
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
    def test_export_import_rc(self, battle):
        assert battle == nm.battle.Battle.from_rc(battle.to_rc())

    @pytest.mark.skip("Must implement simulation first to generate coherent rounds")
    @hp.given(
        attacker=army_strategy,
        defender=army_strategy,
        rounds=st.lists(
            round_strategy,
            min_size=1,
            max_size=5,
        ),
    )
    def test_export_import_rc_property(self, attacker: nm.army.Army, defender: nm.army.Army, rounds):
        battle = nm.battle.Battle(
            attacker,
            defender,
            rounds,
        )
        assert battle == nm.battle.Battle.from_rc(battle.to_rc())

    @pytest.mark.parametrize(
        "battle,expected",
        [
            (
                nm.battle.Battle(
                    attacker=nm.army.Army(JS=100),
                    defender=nm.army.Army(JS=100),
                    rounds=[
                        nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                        nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                        nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                        nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                    ],
                ),
                RC_SIMU_NM,
            ),
        ],
    )
    @pytest.mark.skip
    def test_generate_rc(self, battle, expected):
        assert battle.to_rc() == expected

    @pytest.mark.parametrize(
        "battle,expected",
        [
            (
                nm.battle.Battle(
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
    def test_get_total_losses(self, battle, expected):
        assert battle.get_total_losses() == expected
