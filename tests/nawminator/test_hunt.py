import hypothesis as hp
import hypothesis.strategies as st
import pytest

import nawminator as nm

@pytest.mark.filterwarnings("error::RuntimeWarning")
@pytest.mark.property
@hp.example(50, 107)
@hp.example(20000, 766730)
@hp.example(20000, 9446000)
@hp.example(100000, 248719)
@hp.given(
    start=st.integers(50, 2**48),
    target_difficulty=st.integers(1000, 2**54)
)
def test_max_hunt(start, target_difficulty):
    h = nm.hunt.max_hunt_amount(start, target_difficulty)
    dh = nm.formulas.hunt_difficulty(start, h+1)
    dl = nm.formulas.hunt_difficulty(start, h)
    hp.note(h)
    hp.note(dh)
    hp.note(dl)
    assert dh > target_difficulty + 3 and dl <= target_difficulty + 3

