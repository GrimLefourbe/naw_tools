from nawminator.army import Army, MAX_UNIT_COUNT
import pytest
import numpy as np
import hypothesis as hp
import hypothesis.strategies as st
from . import strategies as nm_st


@pytest.mark.parametrize(
    ("army1", "army2"),
    [
        (Army(JS=1000), Army([0, 0, 1000, *[0] * 12])),
        (Army(E=123, TK=1234), Army([123, *[0] * 12, 1234, 0])),
        (Army(), Army(np.zeros(15))),
    ],
)
def test_init_and_compare(army1, army2):
    assert army1 == army2

@pytest.mark.parametrize(
    "string,expected",
    [
        (
            "1 000 Jeunes soldates, 1 000 Jeunes légionnaires, 1 000 Jeunes tanks",
            Army(JS=1000, JL=1000, JTK=1000),
        ),
        (
            "1000 Jeunes soldates, 1000 Jeunes légionnaires, 1000 Jeunes tanks",
            Army(JS=1000, JL=1000, JTK=1000),
        ),
        (
            "1 JS, 1 JL, 1 JTK, 1 TK, 1 TKE",
            Army(JS=1, JL=1, JTK=1, TK=1, TKE=1),
        ),
        (
            "Troupe en défense : 582 031 Jeunes soldates, 4 412 Soldates, 2 Soldates d'élite",
            Army(JS=582031, S=4412, SE=2),
        ),
        (
            "",
            Army(),
        )
    ],
)
def test_import(string, expected: Army):
    assert Army.from_str(string) == expected


@pytest.mark.parametrize(
    "army,expected",
    [
        (
            Army(JS=1000, JL=1000, JTK=1000),
            "1 000 Jeunes soldates, 1 000 Jeunes légionnaires, 1 000 Jeunes tanks",
        ),
    ],
)
def test_export(army: Army, expected):
    assert army.to_str() == expected

@pytest.mark.parametrize(
    "army,dmg,expected",
    [
        (Army(JS=1000), 8000, (Army(JS=500), Army(JS=500))),
        (Army(JS=1000), 8036, (Army(JS=502), Army(JS=498))),
        (Army(JS=1000), 8040, (Army(JS=503), Army(JS=497))),
        (Army(JS=500, S=500), 10000, (Army(JS=500, S=100), Army(S=400))),
    ],
)
def test_split_by_hp(army: Army, dmg, expected: tuple[Army, Army]):
    lost, left = army.split_by_hp(dmg)
    assert expected[0] == lost
    assert expected[1] == left
    assert lost + left == army


@pytest.mark.property
class TestProperties:
    @hp.example(Army(JS=MAX_UNIT_COUNT//128))
    @hp.example(Army(JS=MAX_UNIT_COUNT//16)).xfail(raises=OverflowError)
    @hp.example(Army(JS=MAX_UNIT_COUNT//64)).xfail(raises=OverflowError)
    @hp.example(Army(TKE=MAX_UNIT_COUNT//128))
    @hp.example(Army(TK=MAX_UNIT_COUNT//128, TKE=MAX_UNIT_COUNT//128)).xfail(raises=OverflowError)
    @hp.given(nm_st.army_strategy_factory(max_value=MAX_UNIT_COUNT//512))
    def test_recruit_time(self, army: Army):
        assert army.recruit_time()[1] >= army.non_xp_recruit_time()[1] >= 0

    @hp.given(army=nm_st.army_strategy, count=st.integers(min_value=0, max_value=2**63 - 1).map(np.int64))
    def test_split_by_count_property(self, army: Army, count: np.int64):
        hp.assume(count <= army.count)
        lost, left = army.split_by_count(count)
        assert lost.count == count
        assert lost + left == army

    @pytest.mark.filterwarnings("error::RuntimeWarning")
    @hp.given(army=nm_st.army_strategy, dmg=st.floats(min_value=0).map(np.float64))
    def test_split_by_hp_property(self, army: Army, dmg: np.float64):
        hp.assume(dmg <= army.base_hp)
        lost, left = army.split_by_hp(dmg)
        assert lost + left == army

    @hp.given(nm_st.army_strategy, st.characters(categories=["Zs"]))
    def test_import_export_compact(self, army: Army, sep: str):
        assert army == Army.from_str(army.to_str_compact(sep))

    @hp.given(nm_st.army_strategy)
    def test_import_export(self, army: Army):
        assert army == Army.from_str(army.to_str())
