import pytest
import hypothesis as hp
import hypothesis.strategies as st
import nawminator as nm
from nawminator.army import Army, MAX_UNIT_COUNT
from nmsite.army_list import ArmyList, split_army
from tests.nawminator.strategies import army_strategy_factory


# ── Unit tests ────────────────────────────────────────────────────────────────

def _al(*counts):
    """Build ArmyList from unit counts: _al(100, 200) → 2 armies with JS=100, JS=200."""
    return ArmyList([Army(JS=c) for c in counts])


def test_add_increases_length():
    al = _al(100, 200)
    result = al.add()
    assert len(result.armies) == 3
    assert result.armies[2] == Army()
    assert result.checks[2] is False


def test_remove_correct_row():
    al = _al(100, 200, 300)
    result = al.remove(1)
    assert len(result.armies) == 2
    assert result.armies[0] == Army(JS=100)
    assert result.armies[1] == Army(JS=300)


def test_remove_first_row():
    al = _al(100, 200, 300)
    result = al.remove(0)
    assert result.armies[0] == Army(JS=200)
    assert result.armies[1] == Army(JS=300)


def test_update_army():
    al = _al(100, 200)
    result = al.update_army(0, Army(JS=999))
    assert result.armies[0] == Army(JS=999)
    assert result.armies[1] == Army(JS=200)


def test_set_check():
    al = _al(100, 200)
    result = al.set_check(1, True)
    assert result.checks == [False, True]
    result2 = result.set_check(0, True)
    assert result2.checks == [True, True]


def test_fusionner_requires_two_selected():
    al = ArmyList([Army(JS=100), Army(JS=200)], [True, False])
    assert al.fusionner() is al  # no-op, returns same object


def test_fusionner_no_selection():
    al = _al(100, 200)
    assert al.fusionner() is al


def test_fusionner_merges_into_first_selected():
    al = ArmyList([Army(JS=100), Army(JS=200), Army(JS=300)], [True, False, True])
    result = al.fusionner()
    assert len(result.armies) == 2
    assert result.armies[0] == Army(JS=400)   # 100 + 300, at index 0
    assert result.armies[1] == Army(JS=200)   # untouched
    assert all(not c for c in result.checks)


def test_fusionner_all_selected():
    al = ArmyList([Army(JS=100), Army(JS=200), Army(JS=300)], [True, True, True])
    result = al.fusionner()
    assert len(result.armies) == 1
    assert result.armies[0] == Army(JS=600)


def test_repartir_noop_when_nothing_selected():
    al = _al(900, 600)
    assert al.repartir(3) is al


def test_repartir_merges_then_splits():
    al = ArmyList([Army(JS=100), Army(JS=900), Army(JS=600), Army(JS=50)], [False, True, True, False])
    result = al.repartir(3)
    assert len(result.armies) == 5          # 2 unselected + 3 parts
    assert result.armies[0] == Army(JS=100)
    assert result.armies[4] == Army(JS=50)
    assert result.armies[1] == Army(JS=500)  # 1500 // 3
    assert result.armies[2] == Army(JS=500)
    assert result.armies[3] == Army(JS=500)  # last part = remainder
    assert all(not c for c in result.checks)


def test_repartir_splits_evenly():
    al = ArmyList([Army(JS=900)], [True])
    result = al.repartir(3)
    assert len(result.armies) == 3
    assert all(a == Army(JS=300) for a in result.armies)
    assert all(not c for c in result.checks)


def test_repartir_preserves_surrounding_rows():
    al = ArmyList([Army(JS=100), Army(JS=600), Army(JS=50)], [False, True, False])
    result = al.repartir(2)
    assert len(result.armies) == 4
    assert result.armies[0] == Army(JS=100)
    assert result.armies[1] == Army(JS=300)
    assert result.armies[2] == Army(JS=300)
    assert result.armies[3] == Army(JS=50)


def test_total_sums_all():
    al = _al(100, 200, 300)
    assert al.total == Army(JS=600)


def test_total_empty_list():
    al = ArmyList([Army(), Army()])
    assert al.total == Army()


def test_immutability():
    al = _al(100, 200)
    al.add()
    assert len(al.armies) == 2  # original unchanged


# ── Property tests ────────────────────────────────────────────────────────────

_small_army = army_strategy_factory(min_value=0, max_value=MAX_UNIT_COUNT // 512)
_n_strategy = st.integers(min_value=2, max_value=10)


@pytest.mark.property
class TestProperties:

    @hp.given(armies=st.lists(_small_army, min_size=2, max_size=6))
    def test_total_is_sum_of_armies(self, armies: list[Army]):
        al = ArmyList(armies)
        expected = sum(armies, Army())
        assert al.total == expected

    @hp.given(armies=st.lists(_small_army, min_size=1, max_size=6),
              idx=st.integers(min_value=0))
    def test_remove_reduces_total(self, armies: list[Army], idx: int):
        idx = idx % len(armies)
        al = ArmyList(armies)
        result = al.remove(idx)
        assert result.total.count == al.total.count - armies[idx].count

    @hp.given(armies=st.lists(_small_army, min_size=2, max_size=6),
              sel=st.lists(st.booleans(), min_size=2, max_size=6))
    def test_fusionner_total_unchanged(self, armies: list[Army], sel: list[bool]):
        n = min(len(armies), len(sel))
        armies, sel = armies[:n], sel[:n]
        al = ArmyList(armies, sel)
        result = al.fusionner()
        assert result.total == al.total

    @hp.given(army=_small_army, n=_n_strategy)
    def test_repartir_exact_total(self, army: Army, n: int):
        al = ArmyList([army], [True])
        result = al.repartir(n)
        assert len(result.armies) == n
        assert result.total == al.total

    @hp.given(armies=st.lists(_small_army, min_size=1, max_size=6),
              idx=st.integers(min_value=0),
              checked=st.booleans())
    def test_set_check_only_affects_one_slot(self, armies: list[Army], idx: int, checked: bool):
        idx = idx % len(armies)
        al = ArmyList(armies)
        result = al.set_check(idx, checked)
        assert result.checks[idx] == checked
        for i, (old, new) in enumerate(zip(al.checks, result.checks)):
            if i != idx:
                assert old == new
