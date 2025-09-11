import pytest
import nawminator as nm
import numpy as np

from nawminator.battle import Bonuses


class TestBonuses:
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
        ],
    )
    def test_compute_bonuses(self, battle_round, expected_bonuses: tuple[Bonuses, Bonuses]):
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
            (
                [
                    nm.battle.Round(8000,7752, 14335545, 15912455, nm.army.Army(JL=145), nm.army.Army(JS=1000))
                ],
                (
                    nm.battle.Bonuses(dmg=0.9690625, min_dmg=0.9689375, hp=None, min_hp=None),
                    nm.battle.Bonuses(dmg=1.11, min_dmg=1.11, hp=1.725259, min_hp=1.706529)
                )
            )
        ],
    )
    def test_from_rounds(self, rounds: list[nm.battle.Round], expected: tuple[Bonuses, Bonuses]):
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
def test_simulate_rounds(attacker: nm.battle.WarParty, defender: nm.battle.WarParty, expected):
    assert nm.battle.simulate_rounds(attacker, defender) == expected


@pytest.mark.skip
class TestWarParty:
    pass
