from nawminator.levels import Levels, AllianceType, HeroType, FightZone
import pytest
import numpy as np
import hypothesis as hp
import hypothesis.strategies as st

import nawminator as nm

from . import strategies as nm_st

@pytest.mark.parametrize(
    "levels,expected",
    [
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.GUERRIER),
            (0.9, 0.75),
        ),
        (Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE), (0.85, 0.8)),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.PACIFISTE),
            (0.8, 0.85),
        ),
        (
            Levels(mandibule=20, carapace=15, alliance=AllianceType.GUERRIER),
            (1.1, 0.75),
        ),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER),
            (0.9, 0.85),
        ),
    ],
)
def test_atk_bonus(levels: Levels, expected):
    assert np.isclose(levels.bonus_atk, expected).all()


@pytest.mark.parametrize(
    "levels,expected",
    [
        (Levels(mandibule=16, carapace=15, alliance=AllianceType.GUERRIER), (0.9, 0.8)),
        (Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE), (0.85, 0.85)),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.PACIFISTE),
            (0.8, 0.9),
        ),
        (Levels(mandibule=20, carapace=15, alliance=AllianceType.GUERRIER), (1.1, 0.8)),
        (Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER), (0.9, 0.9)),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER, dome=0),
            (0.9, 0.9),
        ),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER, dome=15),
            (0.9, 1.275),
        ),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER, dome=24),
            (0.9, 1.5),
        ),
    ],
)
def test_dome_bonus(levels: Levels, expected):
    assert np.isclose(levels.bonus_dome, expected).all()


@pytest.mark.parametrize(
    "levels,expected",
    [
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.GUERRIER),
            (0.9, 0.85),
        ),
        (Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE), (0.85, 0.9)),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.PACIFISTE),
            (0.8, 0.95),
        ),
        (
            Levels(mandibule=20, carapace=15, alliance=AllianceType.GUERRIER),
            (1.1, 0.85),
        ),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER),
            (0.9, 0.95),
        ),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE, loge=20),
            (0.85, 1.9),
        ),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE, loge=24),
            (0.85, 2.1),
        ),
        (
            Levels(mandibule=16, carapace=15, alliance=AllianceType.NEUTRE, loge=0),
            (0.85, 0.9),
        ),
    ],
)
def test_loge_bonus(levels: Levels, expected):
    assert np.isclose(levels.bonus_loge, expected).all()


@pytest.mark.parametrize(
    "levels,expected",
    [
        (
            Levels(
                mandibule=16,
                carapace=15,
                alliance=AllianceType.GUERRIER,
                hero_type=HeroType.VIE,
                hero_lvl=180,
            ),
            (0.9, 0.84),
        ),
        (
            Levels(
                mandibule=16,
                carapace=15,
                alliance=AllianceType.GUERRIER,
                hero_type=HeroType.ATTAQUE,
                hero_lvl=180,
            ),
            (0.90, 0.75),
        ),
        (
            Levels(
                mandibule=16,
                carapace=15,
                alliance=AllianceType.GUERRIER,
                hero_type=HeroType.DEFENSE,
                hero_lvl=180,
            ),
            (0.99, 0.75),
        ),
        (
            Levels(mandibule=20, carapace=15, alliance=AllianceType.GUERRIER),
            (1.1, 0.75),
        ),
        (
            Levels(mandibule=16, carapace=17, alliance=AllianceType.GUERRIER),
            (0.9, 0.85),
        ),
    ],
)
def test_tdc_bonus(levels: Levels, expected):
    assert np.isclose(levels.bonus_tdc, expected).all()


@pytest.mark.parametrize(
    "s,expected",
    [
        (
            "M1 C0 D5 L5 HV180 AG",
            Levels(1, 0, 180, HeroType.VIE, 0, 5, 5, AllianceType.GUERRIER),
        ),
        (
            "M1 C5 D5 AP",
            Levels(1, 5, 0, None, 0, 5, 0, AllianceType.PACIFISTE),
        ),
        (
            "M1 C5 S2 D5 L20",
            Levels(mandibule=1, carapace=5, dome=5, loge=20, special=2),
        )
    ],
)
def test_import(s, expected: Levels):
    assert Levels.from_str(s) == expected


@pytest.mark.parametrize(
    "hero_enabled,bonus_dmg,bonus_hp,lieu,alli_type,atk,expected",
    [
        (
            True,
            np.float64(1.14),
            np.float64(1.0),
            FightZone.TDC,
            AllianceType.GUERRIER,
            True,
            Levels(mandibule=19, carapace=20, hero_type=HeroType.ATTAQUE, hero_lvl=180, alliance=AllianceType.GUERRIER),
        ),
        (
            True,
            np.float64(1.05),
            np.float64(1.45),
            FightZone.DOME,
            AllianceType.NEUTRE,
            False,
            Levels(mandibule=20, carapace=20, hero_lvl=0, dome=14, alliance=AllianceType.NEUTRE),
        ),
        (
            True,
            np.float64(1.1),
            np.float64(2.1),
            FightZone.LOGE,
            AllianceType.PACIFISTE,
            False,
            Levels(mandibule=22, carapace=22, hero_lvl=0, loge=16, alliance=AllianceType.PACIFISTE),
        ),
        (
            False,
            np.float64(1.11),
            np.float64(2.11),
            FightZone.LOGE,
            AllianceType.NEUTRE,
            False,
            Levels(mandibule=20, carapace=20, hero_lvl=0, loge=18, alliance=AllianceType.NEUTRE, special=3)
        ),
        (
            False,
            np.float64(0.8),
            np.float64(0.75),
            FightZone.DOME,
            AllianceType.NEUTRE,
            False,
            Levels(mandibule=15, carapace=13, hero_lvl=0, dome=0, alliance=AllianceType.NEUTRE, special=0)
        ),
        (
            True,
            np.float64(1.14),
            None,
            FightZone.TDC,
            AllianceType.NEUTRE,
            True,
            Levels(mandibule=21, hero_type=None, alliance=AllianceType.NEUTRE, special=2)
        ),
        (
            False,
            np.float64(0.85),
            (np.float64(0.94), np.float64(0.96)),
            FightZone.LOGE,
            AllianceType.GUERRIER,
            False,
            Levels(mandibule=15, carapace=15, loge=2, alliance=AllianceType.GUERRIER)
        ),
        # (
        #     True,
        #     np.float64(1.21),
        #     np.float64(1.135),
        #     FightZone.TDC,
        #     AllianceType.PACIFISTE,
        #     False,
        #     Levels(mandibule=23, carapace=20, hero_lvl=0, hero_type=None, alliance=AllianceType.PACIFISTE, special=3)
        # ) # hero lvl is not a multiple of 10 so the granularity isn't good enough.
    ],
)
def test_from_bonuses(hero_enabled, bonus_dmg: np.float64, bonus_hp: np.float64, lieu, alli_type, atk, expected):
    assert Levels.from_bonuses(bonus_dmg, bonus_hp, lieu=lieu, alli_type=alli_type, atk=atk, hero_enabled=hero_enabled) == expected


@pytest.mark.property
@hp.example(levels=Levels(train=1), sep="\n").xfail(reason="Train is not used yet.")
@hp.example(levels=Levels(hero_type=HeroType.DEFENSE), sep="\n")
@hp.given(
    levels=nm_st.levels_strategy_factory(
        train=st.just(0), # train is not used yet
        hero_lvl=st.just(0),
        hero_type=st.just(HeroType.ATTAQUE) # Hero handling is temporarily disabled
    ),
    sep=st.characters(categories=["Zs"])
)
def test_import_export(levels: Levels, sep: str):
    s = levels.to_str(sep)
    l = Levels.from_str(s)
    assert levels == l, s
