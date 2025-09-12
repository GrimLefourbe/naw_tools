import pytest

import nawminator as nm
import numpy as np

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (
            nm.battle.Bonuses(dmg=1.0, hp=None),
            nm.battle.Bonuses(dmg=1.0, hp=1.2),
            nm.battle.Bonuses(dmg=1.0, hp=1.2),
        ),
        (
            nm.battle.Bonuses(dmg=1.0, min_dmg=0.95, hp=None),
            nm.battle.Bonuses(dmg=1.05, min_dmg=1, hp=None),
            nm.battle.Bonuses(dmg=1, hp=None)
        ),
        (
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=1, min_hp=0.95),
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=1.05, min_hp=1),
            nm.battle.Bonuses(dmg=1, hp=1)
        ),
        (
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=1, min_hp=0.95),
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=1.05, min_hp=0.97),
            nm.battle.Bonuses(dmg=1, hp=1.0, min_hp=0.97)
        ),
        (
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=1, min_hp=0.95),
            nm.battle.Bonuses(dmg=1, min_dmg=1, hp=None, min_hp=None),
            nm.battle.Bonuses(dmg=1, hp=1.0, min_hp=0.95)
        ),
    ]
)
def test_intersect(a: nm.battle.Bonuses, b: nm.battle.Bonuses, expected: nm.battle.Bonuses):
    assert a.intersect(b) == b.intersect(a) == expected

@pytest.mark.parametrize(
    "battle_round,expected_bonuses",
    [
        (
            nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
            (
                nm.battle.Bonuses(dmg=np.float64(0.95), min_dmg=np.float64(0.95), hp=np.float64(0.96), min_hp=np.float64(0.92)),
                nm.battle.Bonuses(dmg=np.float64(0.95), min_dmg=np.float64(0.95), hp=np.float64(0.965), min_hp=np.float64(0.935)),
            ),
        ),
        (
            nm.battle.Round(80, 84, 70, 74, nm.army.Army(JS=5), nm.army.Army(JS=4)),
            (
                nm.battle.Bonuses(
                    dmg=np.float64(1.055), min_dmg=np.float64(1.045), hp=np.float64(1.57), min_hp=np.float64(1.005)
                ),
                nm.battle.Bonuses(
                    np.float64(1.06), min_dmg=np.float64(1.05), hp=np.float64(1.275), min_hp=np.float64(0.865)
                ),
            ),
        ),
        (
            nm.battle.Round(
                161318462,
                183903047,
                64811476,
                68052050,
                nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=144322),
                nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=276848),
            ),
            (
                nm.battle.Bonuses(dmg=np.float64(1.14), min_dmg=np.float64(1.14), hp=np.float64(1.0), min_hp=np.float64(1.0)), 
                nm.battle.Bonuses(dmg=np.float64(1.05), min_dmg=np.float64(1.05), hp=np.float64(1.45), min_hp=np.float64(1.45))
            ),
        ),
        (
            nm.battle.Round(
                attacker_base_dmg=np.int64(800),
                attacker_bonus_dmg=np.float64(840),
                defender_base_dmg=np.int64(7826),
                defender_bonus_dmg=np.float64(6965),
                attacker_losses=nm.army.Army(JS=100),
                defender_losses=nm.army.Army(JS=33),
            ),
            (
                nm.battle.Bonuses(dmg=np.float64(1.05), min_dmg=np.float64(1.05), hp=None),
                nm.battle.Bonuses(dmg=np.float64(0.89), min_dmg=np.float64(0.89), hp=np.float64(2.15), min_hp=np.float64(2.06)),
            ),
        ),
        (
            nm.battle.Round(8000,7752, 14335545, 15912455, nm.army.Army(JL=145), nm.army.Army(JS=1000)),
            (
                nm.battle.Bonuses(dmg=0.9690625, min_dmg=0.9689375, hp=None, min_hp=None),
                nm.battle.Bonuses(dmg=1.11, min_dmg=1.11, hp=1.725259, min_hp=1.706529)
            )
        ),
    ],
)
def test_from_round(battle_round: nm.battle.Round, expected_bonuses: tuple[nm.battle.Bonuses, nm.battle.Bonuses]):
    obs_atk, obs_def = nm.battle.Bonuses._from_round(battle_round)
    exp_atk, exp_def = expected_bonuses
    atol = 1/200
    assert obs_atk.max_dmg >= obs_atk.min_dmg and \
        obs_def.max_dmg >= obs_def.min_dmg and \
        np.isclose(obs_atk.max_dmg, exp_atk.max_dmg, atol=atol) and \
        np.isclose(obs_atk.min_dmg, exp_atk.min_dmg, atol=atol)
    
    if exp_atk.max_hp is not None:
        assert np.isclose(obs_atk.max_hp, exp_atk.max_hp, atol=atol) and np.isclose(obs_atk.min_hp, exp_atk.min_hp, atol=atol)
    else:
        assert obs_atk.min_hp == exp_atk.min_hp and obs_atk.max_hp == exp_atk.max_hp

    assert np.isclose(obs_def.max_dmg, exp_def.max_dmg, atol=atol) and \
        np.isclose(obs_def.max_dmg, exp_def.max_dmg, atol=atol)
    if exp_def.max_hp is not None:
        assert np.isclose(obs_def.max_hp, exp_def.max_hp, atol=atol) and np.isclose(obs_def.min_hp, exp_def.min_hp, atol=atol)
    else:
        assert obs_def.max_hp == exp_def.max_hp and obs_def.min_hp == exp_def.min_hp
    # assert nm.battle.Bonuses._from_round(battle_round) == expected_bonuses

@pytest.mark.parametrize(
    "rounds,expected",
    [
        (
            [
                nm.battle.Round(800, 760, 700, 665, nm.army.Army(JS=50), nm.army.Army(JS=44)),
                nm.battle.Round(448, 426, 350, 333, nm.army.Army(JS=28), nm.army.Army(JS=22)),
                nm.battle.Round(272, 258, 154, 146, nm.army.Army(JS=17), nm.army.Army(JS=10)),
                nm.battle.Round(192, 182, 35, 33, nm.army.Army(JS=5), nm.army.Army(JS=2)),
            ],
            (
                nm.battle.Bonuses(dmg=np.float64(0.950625), min_dmg=np.float64(0.949375), hp=np.float64(0.96), min_hp=np.float64(0.92)),
                nm.battle.Bonuses(dmg=np.float64(0.95071428), min_dmg=np.float64(0.949285), hp=np.float64(0.965), min_hp=np.float64(0.935)),
            ),
        ),
        (
            [
                nm.battle.Round(
                    161318462,
                    183903047,
                    64811476,
                    68052050,
                    nm.army.Army(JS=99989, S=909880, SE=3856893, JTK=31776, TK=114476, TKE=144322),
                    nm.army.Army(E=999990, ME=502, JS=2480000, S=777537, SE=276848),
                )
            ],
            (
                nm.battle.Bonuses(dmg=np.float64(1.14), min_dmg=np.float64(1.14), hp=np.float64(1.0), min_hp=np.float64(1.0)),
                nm.battle.Bonuses(dmg=np.float64(1.05), min_dmg=np.float64(1.05), hp=np.float64(1.45), min_hp=np.float64(1.45)),
            ),
        ),

    ],
)
def test_from_rounds(rounds: list[nm.battle.Round], expected: tuple[nm.battle.Bonuses, nm.battle.Bonuses]):
    obs_atk, obs_def = nm.battle.Bonuses.from_rounds(rounds)
    exp_atk, exp_def = expected
    atol = 1/200
    assert obs_atk.max_dmg >= obs_atk.min_dmg and \
        obs_def.max_dmg >= obs_def.min_dmg and \
        np.isclose(obs_atk.max_dmg, exp_atk.max_dmg, atol=atol) and \
        np.isclose(obs_atk.min_dmg, exp_atk.min_dmg, atol=atol)
    
    if exp_atk.max_hp is not None:
        assert np.isclose(obs_atk.max_hp, exp_atk.max_hp, atol=atol) and np.isclose(obs_atk.min_hp, exp_atk.min_hp, atol=atol)
    else:
        assert obs_atk.min_hp == exp_atk.min_hp and obs_atk.max_hp == exp_atk.max_hp

    assert np.isclose(obs_def.max_dmg, exp_def.max_dmg, atol=atol) and \
        np.isclose(obs_def.max_dmg, exp_def.max_dmg, atol=atol)
    if exp_def.max_hp is not None:
        assert np.isclose(obs_def.max_hp, exp_def.max_hp, atol=atol) and np.isclose(obs_def.min_hp, exp_def.min_hp, atol=atol)
    else:
        assert obs_def.max_hp == exp_def.max_hp and obs_def.min_hp == exp_def.min_hp
    # assert nm.battle.Bonuses.from_rounds(rounds) == expected
