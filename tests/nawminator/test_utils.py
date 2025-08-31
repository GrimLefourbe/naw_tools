import nawminator as nm
import pytest
import datetime as dt

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
