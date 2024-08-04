from nawminator.levels import Levels, AllianceType, HeroType
import pytest
import numpy as np


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
            Levels(1, 5, 0, HeroType.ATTAQUE, 0, 5, 0, AllianceType.PACIFISTE),
        ),
    ],
)
def test_import(s, expected: Levels):
    assert Levels.from_str(s) == expected
