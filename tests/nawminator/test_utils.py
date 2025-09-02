import nawminator as nm
import pytest
import datetime as dt
import hypothesis as hp
import hypothesis.strategies as st

@pytest.mark.parametrize(
    "td,pad,expected",
    [
        (dt.timedelta(seconds=10), False, "10S"),
        (dt.timedelta(seconds=0), False, "0S"),
        (dt.timedelta(seconds=123456), False, "1J 10H 17M 36S"),
        (dt.timedelta(seconds=123456), True, "  1J 10H 17M 36S"),
        (dt.timedelta(seconds=123420), True, "  1J 10H 17M"),
        (dt.timedelta(seconds=86400), True, "  1J"),
        (dt.timedelta(seconds=86400 + 3600 + 60 + 1), "0", "001J 01H 01M 01S"),
        (dt.timedelta(seconds=86400 + 3600 + 60 + 1), True, "  1J  1H  1M  1S"),
        (dt.timedelta(seconds=86400 + 3600 + 60 + 1), False, "1J 1H 1M 1S"),
        (dt.timedelta(seconds=86400 + 60 + 1), True, "  1J  1M  1S"),
        (dt.timedelta(seconds=86400 + 60 + 1), "full", "0A 001J 00H 01M 01S"),
    ]
)
def test_timedelta_to_ajhms(td, pad, expected):
    assert nm.utils.timedelta_to_ajhms(td, pad) == expected


@pytest.mark.parametrize(
    "s,expected",
    [
        ('10S', dt.timedelta(seconds=10)),
        ('0S', dt.timedelta(0)),
        ('1J 10H 17M 36S', dt.timedelta(days=1, seconds=37056)),
        ('  1J 10H 17M 36S', dt.timedelta(days=1, seconds=37056)),
        ('  1J 10H 17M', dt.timedelta(days=1, seconds=37020)),
        ('  1J', dt.timedelta(days=1)),
        ('001J 01H 01M 01S', dt.timedelta(days=1, seconds=3661)),
        ('  1J  1H  1M  1S', dt.timedelta(days=1, seconds=3661)),
        ('1J 1H 1M 1S', dt.timedelta(days=1, seconds=3661)),
        ('  1J  1M  1S', dt.timedelta(days=1, seconds=61)),
        ('0A 001J 00H 01M 01S', dt.timedelta(days=1, seconds=61)),
    ]

)
def test_ajhms_to_timedelta(s, expected):
    assert nm.utils.parse_ajhms(s) == expected

@pytest.mark.property
@hp.given(td=st.timedeltas(min_value=dt.timedelta(seconds=0)))
def test_ajhms_export_import(td: dt.timedelta):
    hp.assume(td.microseconds==0)
    assert td == nm.utils.parse_ajhms(nm.utils.timedelta_to_ajhms(td))
