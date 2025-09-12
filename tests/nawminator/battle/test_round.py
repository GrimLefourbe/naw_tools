import pytest

import nawminator as nm
import numpy as np



@pytest.mark.parametrize(
    "attacker,defender,expected",
    [
        (
            nm.battle.WarParty(nm.army.Army(JS=100), bonuses=nm.battle.Bonuses(0.95, 0.95), atk=True),
            nm.battle.WarParty(nm.army.Army(JS=100), bonuses=nm.battle.Bonuses(0.95, 0.95), atk=False),
            [
                nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
            ],
        ),
        (
            nm.battle.WarParty(
                nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=925779, JTK=291373, TK=203211, TKE=383906),
                bonuses=nm.battle.Bonuses(1.14, 1.0),
                atk=True,
            ),
            nm.battle.WarParty(
                nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=869999),
                bonuses=nm.battle.Bonuses(1.05, 1.45),
                atk=False,
            ),
            [
                nm.battle.Round(
                    np.int64(161318462),
                    np.float64(183903047),
                    np.int64(64811476),
                    np.float64(68052050),
                    nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=144322),
                    nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=276848),
                ),
                nm.battle.Round(
                    np.int64(124216167), 
                    np.float64(141606430), 
                    np.int64(725677), 
                    np.float64(761961), 
                    nm.army.Army(TKE=725677),
                    nm.army.Army(SE=28608)
                ),
            ],
        ),
    ],
)
def test_simulate_rounds(attacker: nm.battle.WarParty, defender: nm.battle.WarParty, expected: list[nm.battle.Round]):
    assert nm.battle.simulate_rounds(attacker, defender) == expected
