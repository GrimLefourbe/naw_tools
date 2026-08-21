import nawminator as nm

import pandas as pd

# --- Curated edge cases, extracted by hand from real "joueurs" page dumps ---
#
# Current page format (since the NAW number-formatting change):
#   - distance has one decimal, comma as decimal separator ("7,2")
#   - large numbers (Terrain) use space as thousands separator ("30 216 191")
#   - alliance is blank (not "-" or similar) for players without one — this is
#     the majority case, not an edge case: ~47% of rows in a real dump have it.
#
# parse_joueurs_text/parse_joueurs_sourcecode are always called on a whole
# pasted page (many rows), never a single line, so the fixtures below are
# built as one realistic multi-row document per format rather than one
# document per case. Each row is kept as its own named constant so a failure
# is still easy to place — assert_frame_equal reports the row index/column
# that mismatched, and the row's own data (colo_name/player_name) identifies
# which case that was.

_HEADER = "Distance\tDurée\tCoordonnées\tTerrain\tColonie\tJoueur\tAlliance\tÉtat\n" * 2

_ROW_PLAIN_INTEGER_DISTANCE = "0 \t0s \t[43:92] \t360 530 \tBuzz le Clerc \tGrim \tSDS \tLibre"
_ROW_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE = "7,2 \t45m 25s \t[49:88] \t30 216 191 \tBurn in \tChadoSantana \tSDS \tVassal de Fuqit"
_ROW_VASSAL_WITH_BLANK_ALLIANCE = "8,6 \t51m 33s \t[36:97] \t35 905 \tLalaland \tImmalie \t\tVassal de Beru"
_ROW_EN_VACANCES_STATUS = "102,1 \t06H 42m 55s \t[-34:25] \t13 780 767 \tBravo le veau \tGizmorisa \tTJ \tEn vacances"
_ROW_EMOJI_COLO_NAME_NEGATIVE_COORD = "114,7 \t07H 22m 24s \t[14:-19] \t3 625 043 \t🪳🪳🪳 \tTroglodyte \tRP \tEn vacances"
_ROW_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE = "9,2 \t54m 15s \t[36:98] \t63 988 \tKröm'land \tKrömiz \t\tVassal de Stil7"
# multi-word colo_name AND multi-word player_name — works because alliance is
# non-blank here, which disambiguates the field split.
_ROW_MULTIWORD_NAMES_WITH_ALLIANCE = "46,1 \t03H 26m 12s \t[46:46] \t1 791 688 \tSynchro 59 \tJack Sparrow \tRDP \tLibre"

test_string_data_1 = _HEADER + "\n".join(
    [
        _ROW_PLAIN_INTEGER_DISTANCE,
        _ROW_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE,
        _ROW_VASSAL_WITH_BLANK_ALLIANCE,
        _ROW_EN_VACANCES_STATUS,
        _ROW_EMOJI_COLO_NAME_NEGATIVE_COORD,
        _ROW_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE,
        _ROW_MULTIWORD_NAMES_WITH_ALLIANCE,
    ]
)


def _tr(inner: str) -> str:
    return f"<tr style='color:green;font-weight:bold;'>\n{inner}\n</tr>"


_TR_PLAIN_INTEGER_DISTANCE = _tr("""\
    <td data-order="0.000000">0</td>
    <td>0s</td>
    <td>[43:92]</td>
    <td data-order="360530">360 530</td>
    <td><a style='color:green;font-weight:bold;' href='attaque-43-92'>Buzz le Clerc</a></td>
    <td><a style='color:green;font-weight:bold;' href="profil-337"> <b>Grim</b></a></td>
    <td><a style='color:green;font-weight:bold;' href="descriptionalliance-SDS"> <b>SDS</b></a></td>
    <td>Libre</td>""")

_TR_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE = _tr("""\
    <td data-order="7.211103">7,2</td>
    <td>45m 25s</td>
    <td>[49:88]</td>
    <td data-order="30216191">30 216 191</td>
    <td><a style='color:green;font-weight:bold;' href='attaque-49-88'>Burn in</a></td>
    <td><a style='color:green;font-weight:bold;' href="profil-119"> <b>ChadoSantana</b></a></td>
    <td><a style='color:green;font-weight:bold;' href="descriptionalliance-SDS"> <b>SDS</b></a></td>
    <td>Vassal de <a href='profil-65'> <b>Fuqit</b></a></td>""")

_TR_VASSAL_WITH_BLANK_ALLIANCE = _tr("""\
    <td data-order="8.602325">8,6</td>
    <td>51m 33s</td>
    <td>[36:97]</td>
    <td data-order="35905">35 905</td>
    <td><a style='color:black;font-weight:bold;' href='attaque-36-97'>Lalaland</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-814"> <b>Immalie</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-"> <b></b></a></td>
    <td>Vassal de <a href='profil-367'> <b>Beru</b></a></td>""")

_TR_EN_VACANCES_STATUS = _tr("""\
    <td data-order="102.068604">102,1</td>
    <td>06H 42m 55s</td>
    <td>[-34:25]</td>
    <td data-order="13780767">13 780 767</td>
    <td><a style='color:black;font-weight:bold;' href='attaque--34-25'>Bravo le veau</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-242"> <b>Gizmorisa</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-TJ"> <b>TJ</b></a></td>
    <td>En vacances</td>""")

_TR_EMOJI_COLO_NAME_NEGATIVE_COORD = _tr("""\
    <td data-order="114.725760">114,7</td>
    <td>07H 22m 24s</td>
    <td>[14:-19]</td>
    <td data-order="3625043">3 625 043</td>
    <td><a style='color:black;font-weight:bold;' href='attaque-14--19'>🪳🪳🪳</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-541"> <b>Troglodyte</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-RP"> <b>RP</b></a></td>
    <td>En vacances</td>""")

# colo_name is HTML-entity-encoded in the source ("Kr&ouml;m&#039;land"),
# exercising the html.unescape() round-trip.
_TR_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE = _tr("""\
    <td data-order="9.219544">9,2</td>
    <td>54m 15s</td>
    <td>[36:98]</td>
    <td data-order="63988">63 988</td>
    <td><a style='color:black;font-weight:bold;' href='attaque-36-98'>Kr&ouml;m&#039;land</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-287"> <b>Krömiz</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-"> <b></b></a></td>
    <td>Vassal de <a href='profil-149'> <b>Stil7</b></a></td>""")

_TR_MULTIWORD_NAMES_WITH_ALLIANCE = _tr("""\
    <td data-order="46.097722">46,1</td>
    <td>03H 26m 12s</td>
    <td>[46:46]</td>
    <td data-order="1791688">1 791 688</td>
    <td><a style='color:blue;font-weight:bold;' href='attaque-46-46'>Synchro 59</a></td>
    <td><a style='color:blue;font-weight:bold;' href="profil-52"> <b>Jack Sparrow</b></a></td>
    <td><a style='color:blue;font-weight:bold;' href="descriptionalliance-RDP"> <b>RDP</b></a></td>
    <td>Libre</td>""")

test_source_code_data_1 = "\n\n".join(
    [
        _TR_PLAIN_INTEGER_DISTANCE,
        _TR_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE,
        _TR_VASSAL_WITH_BLANK_ALLIANCE,
        _TR_EN_VACANCES_STATUS,
        _TR_EMOJI_COLO_NAME_NEGATIVE_COORD,
        _TR_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE,
        _TR_MULTIWORD_NAMES_WITH_ALLIANCE,
    ]
)

# Both fixtures describe the same 7 rows, in the same order, so one expected
# DataFrame covers both parsers.
_EXPECTED = pd.DataFrame(
    [
        ["[43:92]", 360_530, "Buzz le Clerc", "Grim", "SDS"],
        ["[49:88]", 30_216_191, "Burn in", "ChadoSantana", "SDS"],
        ["[36:97]", 35_905, "Lalaland", "Immalie", ""],
        ["[-34:25]", 13_780_767, "Bravo le veau", "Gizmorisa", "TJ"],
        ["[14:-19]", 3_625_043, "🪳🪳🪳", "Troglodyte", "RP"],
        ["[36:98]", 63_988, "Kröm'land", "Krömiz", ""],
        ["[46:46]", 1_791_688, "Synchro 59", "Jack Sparrow", "RDP"],
    ],
    columns=["coord", "tdc", "colo_name", "player_name", "alliance"],
)


def test_parse_text():
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_text(test_string_data_1), _EXPECTED)


def test_parse_source_code():
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_sourcecode(test_source_code_data_1), _EXPECTED)


# --- Known limitation, tracked in TODO.md ("Parsing" section) ---
#
# joueurs_copy_paste_pat separates fields with generic whitespace, not a fixed
# delimiter, so it has no way to represent "an empty field" unambiguously.
# When a multi-word player_name coincides with a blank alliance, "Word1 Word2"
# is indistinguishable from "Word1" + alliance "Word2" — this is a real
# pre-existing bug (confirmed on live data before this session), not
# something introduced by the NAW number-format adaptation, and not fixable
# without a reliable non-whitespace delimiter (needs cross-platform copy-paste
# investigation first — see TODO.md). This test documents current behavior so
# it doesn't get silently "fixed" by an unrelated regex tweak without noticing
# the tradeoff.
#
# The HTML source-code parser doesn't have this problem — <td> tags are an
# unambiguous delimiter — so it gets this same row right. Kept as an isolated
# single-row case (unlike the two tests above) since mixing a known-wrong
# result into the realistic multi-row fixture would muddy what that fixture
# is meant to prove.

test_string_data_known_limitation = _HEADER + "70,2 \t04H 55m 37s \t[2:35] \t50 \tCitadelle \tLa mie \t\tVassal de Lolofourmizz"

test_source_code_data_known_limitation = _tr("""\
    <td data-order="70.213959">70,2</td>
    <td>04H 55m 37s</td>
    <td>[2:35]</td>
    <td data-order="50">50</td>
    <td><a style='color:black;font-weight:bold;' href='attaque-2-35'>Citadelle</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-1015"> <b>La mie</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-"> <b></b></a></td>
    <td>Vassal de <a href='profil-634'> <b>Lolofourmizz</b></a></td>""")


def test_parse_text_known_limitation_multiword_name_with_blank_alliance():
    df = nm.parsing.parse_joueurs_text(test_string_data_known_limitation)
    row = df.iloc[0]
    # WRONG, but this is today's actual behavior — see comment above.
    assert row["player_name"] == "La"
    assert row["alliance"] == "mie"


def test_parse_source_code_gets_the_same_row_right():
    df = nm.parsing.parse_joueurs_sourcecode(test_source_code_data_known_limitation)
    row = df.iloc[0]
    assert row["player_name"] == "La mie"
    assert row["alliance"] == ""
