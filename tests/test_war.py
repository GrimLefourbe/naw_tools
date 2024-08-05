import pytest
import nawminator as nm
import numpy as np


class TestBonuses:
    @pytest.mark.parametrize(
        "battle_round,expected_bonuses",
        [
            (
                nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                (
                    nm.war.Bonuses(np.float64(0.95), np.float64(0.96), np.float64(0.92)),
                    nm.war.Bonuses(np.float64(0.95), np.float64(0.965), np.float64(0.935))
                )
            ),
            (
                nm.battle.Round(
                    161318462, 183903047, 64811476, 68052050,
                    nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=144322),
                    nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=276848)
                ),
                (
                    nm.war.Bonuses(np.float64(1.14), np.float64(1.0)),
                    nm.war.Bonuses(np.float64(1.05), np.float64(1.45))
                )
            )

        ]
    )
    def test_compute_bonuses(self, battle_round, expected_bonuses):
        assert nm.war.Bonuses.compute_bonuses(battle_round) == expected_bonuses

    @pytest.mark.parametrize(
        "attacker,defender,expected",
        [
            (
                nm.war.WarParty(
                    nm.army.Army(JS=100), bonuses=nm.war.Bonuses(0.95, 0.95), atk=True
                ),
                nm.war.WarParty(
                    nm.army.Army(JS=100), bonuses=nm.war.Bonuses(0.95, 0.95), atk=False
                ),
                [
                    nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                    nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                    nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                    nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
                ],
            ),
            (
                nm.war.WarParty(
                    nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=925779, JTK=291373, TK=203211, TKE=383906),
                    bonuses=nm.war.Bonuses(1.14, 1.0), atk=True,
                ),
                nm.war.WarParty(
                    nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=869999),
                    bonuses=nm.war.Bonuses(1.05, 1.45), atk=False
                ),
                [
                    nm.battle.Round(
                        161318462, 183903047, 64811476, 68052050,
                        nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=144322),
                        nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=276848)
                    ),
                    nm.battle.Round(124216167, 141606430, 725677, 761961, nm.army.Army(TKE=725677), nm.army.Army(SE=28608)),
                ]
            )
        ]
    )
    def test_simulate_rounds(self, attacker: nm.war.WarParty, defender: nm.war.WarParty, expected):
        assert nm.war.simulate_rounds(attacker, defender) == expected


@pytest.mark.skip
class TestWarParty:
    pass
