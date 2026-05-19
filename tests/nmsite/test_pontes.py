import pytest
import hypothesis as hp
import hypothesis.strategies as st
import nawminator as nm
from nawminator.army import MAX_UNIT_COUNT
from nmsite.tabs.pontes import _find_tdp_alli
from tests.nawminator.strategies import army_strategy_factory


def _army():
    return nm.army.Army(E=1000, JS=500, S=200, G=100, TK=50)


@pytest.mark.parametrize("tdp,alli", [
    (0, 0),
    (1, 0),
    (2, 0),
    (5, 0),
    (0, 1),
    (0, 3),
    (0, 5),
    (1, 1),
    (2, 3),
    (3, 5),
    (10, 0),
    (10, 5),
])
def test_find_tdp_alli_achieves_target(tdp, alli):
    army = _army()
    _, target_secs = army.recruit_time(tdp, alli)
    assert _find_tdp_alli(army, target_secs) == (tdp, alli)


def test_find_tdp_alli_no_bonus_needed():
    army = _army()
    _, base_secs = army.recruit_time()
    assert _find_tdp_alli(army, base_secs) == (0, 0)


def test_find_tdp_alli_empty_army():
    assert _find_tdp_alli(nm.army.Army(), 1000.0) == (0, 0)


def test_find_tdp_alli_impossible_target_returns_zero():
    army = _army()
    _, base_secs = army.recruit_time()
    assert _find_tdp_alli(army, base_secs * 2) == (0, 0)


_small_army_strategy = army_strategy_factory(min_value=0, max_value=MAX_UNIT_COUNT // 512)
_tdp_strategy = st.integers(min_value=0, max_value=150)
_alli_strategy = st.integers(min_value=0, max_value=5)


@pytest.mark.property
class TestProperties:
    @hp.given(army=_small_army_strategy, tdp=_tdp_strategy, alli=_alli_strategy)
    def test_find_tdp_alli_roundtrip(self, army: nm.army.Army, tdp: int, alli: int):
        _, base_secs = army.recruit_time()
        hp.assume(base_secs > 0)

        _, target_secs = army.recruit_time(tdp, alli)
        assert _find_tdp_alli(army, target_secs) == (tdp, alli)
