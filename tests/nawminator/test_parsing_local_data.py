import pathlib

import nawminator as nm
import pytest

# Full-dataset regression against real (if slightly dated) scrapes of a live
# player list. Not committed to the repo — they contain other players'
# colony/alliance data and they're large (multiple MB combined). Drop them in
# tests/nawminator/local_data/ to run these tests locally; they're skipped
# automatically otherwise (including in CI). This is a dev sanity check
# ("did we miss any players") rather than a correctness assertion — see
# tests/nawminator/test_parsing.py for the curated correctness cases.
#
# players_copy_paste.txt (v1) is intentionally NOT used here anymore —
# parse_joueurs_text was rewritten for the page's dynamic/toggleable columns
# and backward compatibility with the old fixed-column format was dropped as
# not worth maintaining (see TODO.md "Parsing" section).

_LOCAL_DATA_DIR = pathlib.Path(__file__).parent / "local_data"
_FULL_COPY_PASTE = _LOCAL_DATA_DIR / "players_copy_paste_v2_all.txt"
_FULL_COPY_PASTE_MIN_COLUMNS = _LOCAL_DATA_DIR / "players_copy_paste_v2_min_columns.txt"
_FULL_COPY_PASTE_MISS_COLUMNS = _LOCAL_DATA_DIR / "players_copy_paste_v2_miss_columns.txt"
_FULL_SOURCE_CODE = _LOCAL_DATA_DIR / "players_source_code_v2.html"

_EXPECTED_ROW_COUNT = 1456


@pytest.mark.skipif(not _FULL_COPY_PASTE.exists(), reason="local-only fixture, see comment above")
def test_parse_text_full_dataset_row_count():
    df = nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE.read_text(encoding="utf-8"))
    assert len(df) == _EXPECTED_ROW_COUNT


@pytest.mark.skipif(not _FULL_COPY_PASTE_MIN_COLUMNS.exists(), reason="local-only fixture, see comment above")
def test_parse_text_min_columns_row_count():
    df = nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE_MIN_COLUMNS.read_text(encoding="utf-8"))
    assert len(df) == _EXPECTED_ROW_COUNT
    assert df["tdc"].notna().all()


@pytest.mark.skipif(not _FULL_COPY_PASTE_MISS_COLUMNS.exists(), reason="local-only fixture, see comment above")
def test_parse_text_miss_columns_rejected():
    # Terrain (tdc) isn't enabled in this dump — tdc is a required column
    # (not gracefully-optional), so the whole parse should be rejected
    # rather than silently coming back with tdc missing/wrong.
    with pytest.raises(nm.parsing.ParsingError):
        nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE_MISS_COLUMNS.read_text(encoding="utf-8"))


@pytest.mark.skipif(not _FULL_SOURCE_CODE.exists(), reason="local-only fixture, see comment above")
def test_parse_source_code_full_dataset_row_count():
    df = nm.parsing.parse_joueurs_sourcecode(_FULL_SOURCE_CODE.read_text(encoding="utf-8"))
    assert len(df) == _EXPECTED_ROW_COUNT


@pytest.mark.skipif(
    not (_FULL_COPY_PASTE.exists() and _FULL_SOURCE_CODE.exists()),
    reason="local-only fixtures, see comment above",
)
def test_parse_text_and_source_code_agree_on_full_dataset():
    # Both v2 dumps happen to have the same row count (1456) — close enough
    # in time to be worth cross-checking which colonies each parser found,
    # even though they're not guaranteed to be the exact same scrape.
    df_text = nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE.read_text(encoding="utf-8"))
    df_html = nm.parsing.parse_joueurs_sourcecode(_FULL_SOURCE_CODE.read_text(encoding="utf-8"))
    assert set(df_text["coord"]) == set(df_html["coord"])
