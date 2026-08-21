import pathlib

import nawminator as nm
import pytest

# Full-dataset regression against real (if slightly dated) scrapes of a live
# player list. Not committed to the repo — they contain other players'
# colony/alliance data and they're large (~1MB combined). Drop them in
# tests/nawminator/local_data/ to run these tests locally; they're skipped
# automatically otherwise (including in CI). This is a dev sanity check
# ("did we miss any players") rather than a correctness assertion — see
# tests/nawminator/test_parsing.py for the curated correctness cases.

_LOCAL_DATA_DIR = pathlib.Path(__file__).parent / "local_data"
_FULL_COPY_PASTE = _LOCAL_DATA_DIR / "players_copy_paste.txt"
_FULL_SOURCE_CODE = _LOCAL_DATA_DIR / "players_source_code.html"

_EXPECTED_ROW_COUNT = 1457


@pytest.mark.skipif(not _FULL_COPY_PASTE.exists(), reason="local-only fixture, see comment above")
def test_parse_text_full_dataset_row_count():
    df = nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE.read_text(encoding="utf-8"))
    assert len(df) == _EXPECTED_ROW_COUNT


@pytest.mark.skipif(not _FULL_SOURCE_CODE.exists(), reason="local-only fixture, see comment above")
def test_parse_source_code_full_dataset_row_count():
    df = nm.parsing.parse_joueurs_sourcecode(_FULL_SOURCE_CODE.read_text(encoding="utf-8"))
    assert len(df) == _EXPECTED_ROW_COUNT


@pytest.mark.skipif(
    not (_FULL_COPY_PASTE.exists() and _FULL_SOURCE_CODE.exists()),
    reason="local-only fixtures, see comment above",
)
def test_parse_text_and_source_code_agree_on_full_dataset():
    # The two formats are dumped separately (possibly seconds apart), so fast-moving
    # fields like tdc can legitimately drift — only check both parsers agree on which
    # colonies exist.
    df_text = nm.parsing.parse_joueurs_text(_FULL_COPY_PASTE.read_text(encoding="utf-8"))
    df_html = nm.parsing.parse_joueurs_sourcecode(_FULL_SOURCE_CODE.read_text(encoding="utf-8"))
    assert set(df_text["coord"]) == set(df_html["coord"])
