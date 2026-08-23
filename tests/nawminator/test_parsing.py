import nawminator as nm

import pandas as pd

# --- Curated edge cases, extracted by hand from real "joueurs" page dumps ---
#
# The copy-paste format ("Distance\tDurée\t...") and the HTML source-code
# format have each gone through their own NAW page redesign, at different
# times, so their fixtures below are unrelated snapshots — same underlying
# idea (a joueurs page dump) but not the same page revision or scrape.
#
# parse_joueurs_text/parse_joueurs_sourcecode are always called on a whole
# pasted page (many rows), never a single line, so the fixtures below are
# built as one realistic multi-row document per format rather than one
# document per case. Each row is kept as its own named constant so a failure
# is still easy to place — assert_frame_equal reports the row index/column
# that mismatched, and the row's own data (colo_name/player_name) identifies
# which case that was.

_COLUMNS = ["coord", "tdc", "colo_name", "player_name", "alliance"]

# --- Copy-paste format ---
#
#   - distance has one decimal, comma as decimal separator ("7,2")
#   - large numbers (Terrain) use space as thousands separator ("30 216 191")
#   - alliance is blank (not "-" or similar) for players without one — this is
#     the majority case, not an edge case: ~47% of rows in a real dump have it.

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

_EXPECTED_TEXT = pd.DataFrame(
    [
        ["[43:92]", 360_530, "Buzz le Clerc", "Grim", "SDS"],
        ["[49:88]", 30_216_191, "Burn in", "ChadoSantana", "SDS"],
        ["[36:97]", 35_905, "Lalaland", "Immalie", ""],
        ["[-34:25]", 13_780_767, "Bravo le veau", "Gizmorisa", "TJ"],
        ["[14:-19]", 3_625_043, "🪳🪳🪳", "Troglodyte", "RP"],
        ["[36:98]", 63_988, "Kröm'land", "Krömiz", ""],
        ["[46:46]", 1_791_688, "Synchro 59", "Jack Sparrow", "RDP"],
    ],
    columns=_COLUMNS,
)


def test_parse_text():
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_text(test_string_data_1), _EXPECTED_TEXT)


# --- HTML source-code format (current, as of the "state" widget redesign) ---
#
#   - every field-bearing <td> gained a data-player-column attribute, and most
#     values gained a wrapper tag (coord in <a>, tdc in <strong>)
#   - player_name/alliance lost their old <b>-wrapping and leading space —
#     plain text directly inside <a> now
#   - status is no longer visible text at all: it's icon widgets, with the
#     actual state living in the outer <span class="naw-player-state-list"
#     aria-label="...">, e.g. "Libre", "Vassal de X", or either of those plus
#     a ", Banni" / ", Débutant" / ", Vacances" modifier (vacations are no
#     longer their own status, just a modifier — "En vacances" as a standalone
#     status no longer exists in this format)

_TR_PLAIN_INTEGER_DISTANCE = """\
<tr class="naw-player-directory-row" style='color:green;'>
    <td data-player-column="distance" data-order="0.000000">0</td>
    <td data-player-column="duration">0s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-1-32" title="Voir cette colonie sur la carte">[1:32]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="10372233"><strong>10 372 233</strong></td>
    <td data-player-column="colony" data-search="✔️A FLOOD✔️" data-order="✔️A FLOOD✔️"><a style='color:green;' href='attaque-1-32' title='✔️A FLOOD✔️'>✔️A FLOOD✔️</a></td>
    <td data-player-column="player"><a style='color:green;' href="profil-337">Grim</a></td>
    <td data-player-column="alliance"><a style='color:green;' href="descriptionalliance-SDS">SDS</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Libre"><button type="button" class="naw-player-state-icon is-free naw-player-state-tooltip-trigger" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Libre&lt;/div&gt;" aria-label="Libre"><span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span></button></span></td>
</tr>"""

_TR_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="2.236068">2,2</td>
    <td data-player-column="duration">23m 15s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-0-30" title="Voir cette colonie sur la carte">[0:30]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="26515927"><strong>26 515 927</strong></td>
    <td data-player-column="colony" data-search="⛔ NO FLOOD ⛔" data-order="⛔ NO FLOOD ⛔"><a style='color:black;' href='attaque-0-30' title='⛔ NO FLOOD ⛔'>⛔ NO FLOOD ⛔</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-122">HarleyQueen</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-BORG">BORG</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de DAMsterdam"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-354" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de DAMsterdam&lt;/div&gt;" aria-label="Vassal de DAMsterdam"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">DAMsterdam</span></a></span></td>
</tr>"""

_TR_VASSAL_WITH_BLANK_ALLIANCE = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="73.824115">73,8</td>
    <td data-player-column="duration">05H 08m 23s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-36-97" title="Voir cette colonie sur la carte">[36:97]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="35905"><strong>35 905</strong></td>
    <td data-player-column="colony" data-search="Lalaland" data-order="Lalaland"><a style='color:black;' href='attaque-36-97' title='Lalaland'>Lalaland</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-814">Immalie</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-"></a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de Beru"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-367" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de Beru&lt;/div&gt;" aria-label="Vassal de Beru"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">Beru</span></a></span></td>
</tr>"""

# status is compound now: primary "Vassal de X" plus a ", Vacances" modifier
# (there's no standalone "vacances" status any more in this format).
_TR_VASSAL_PLUS_VACANCES_STATUS = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="35.693137">35,7</td>
    <td data-player-column="duration">02H 45m 16s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte--34-25" title="Voir cette colonie sur la carte">[-34:25]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="13780767"><strong>13 780 767</strong></td>
    <td data-player-column="colony" data-search="Bravo le veau" data-order="Bravo le veau"><a style='color:black;' href='attaque--34-25' title='Bravo le veau'>Bravo le veau</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-242">Gizmorisa</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-TJ">TJ</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de Barbe-Ôtage, Vacances"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-96" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de Barbe-Ôtage&lt;/div&gt;" aria-label="Vassal de Barbe-Ôtage"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">Barbe-Ôtage</span></a><button type="button" class="naw-player-state-icon is-vacation naw-player-state-tooltip-trigger" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;En vacances&lt;/div&gt;" aria-label="En vacances"><span class="glyphicon glyphicon-plane" aria-hidden="true"></span></button></span></td>
</tr>"""

# same modifier as above, but on top of "Libre" this time instead of "Vassal
# de X" — also covers emoji colo_name + negative coordinate.
_TR_EMOJI_COLO_NAME_NEGATIVE_COORD = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="52.630789">52,6</td>
    <td data-player-column="duration">03H 51m 10s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-14--19" title="Voir cette colonie sur la carte">[14:-19]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="3625043"><strong>3 625 043</strong></td>
    <td data-player-column="colony" data-search="🪳🪳🪳" data-order="🪳🪳🪳"><a style='color:black;' href='attaque-14--19' title='🪳🪳🪳'>🪳🪳🪳</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-541">Troglodyte</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-RP">RP</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Libre, Vacances"><button type="button" class="naw-player-state-icon is-free naw-player-state-tooltip-trigger" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Libre&lt;/div&gt;" aria-label="Libre"><span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span></button><button type="button" class="naw-player-state-icon is-vacation naw-player-state-tooltip-trigger" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;En vacances&lt;/div&gt;" aria-label="En vacances"><span class="glyphicon glyphicon-plane" aria-hidden="true"></span></button></span></td>
</tr>"""

# colo_name's apostrophe is still HTML-entity-encoded ("Kröm&#039;land"), but
# the accented "ö" is no longer entity-encoded like it used to be ("&ouml;")
# — raw UTF-8 now. Exercises the html.unescape() round-trip either way.
_TR_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="74.706091">74,7</td>
    <td data-player-column="duration">05H 11m 29s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-36-98" title="Voir cette colonie sur la carte">[36:98]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="63988"><strong>63 988</strong></td>
    <td data-player-column="colony" data-search="Kröm&#039;land" data-order="Kröm&#039;land"><a style='color:black;' href='attaque-36-98' title='Kröm&#039;land'>Kröm&#039;land</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-287">Krömiz</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-"></a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de Stil7"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-149" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de Stil7&lt;/div&gt;" aria-label="Vassal de Stil7"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">Stil7</span></a></span></td>
</tr>"""

_TR_MULTIWORD_NAMES_WITH_ALLIANCE = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="47.127487">47,1</td>
    <td data-player-column="duration">03H 30m 10s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-46-46" title="Voir cette colonie sur la carte">[46:46]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="917344"><strong>917 344</strong></td>
    <td data-player-column="colony" data-search="Synchro 59" data-order="Synchro 59"><a style='color:black;' href='attaque-46-46' title='Synchro 59'>Synchro 59</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-52">Jack Sparrow</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-RDP">RDP</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Libre"><button type="button" class="naw-player-state-icon is-free naw-player-state-tooltip-trigger" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Libre&lt;/div&gt;" aria-label="Libre"><span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span></button></span></td>
</tr>"""

# The colony name column truncates its *visible* link text once it's over
# ~14 chars ("Before i for.." for "Before i forget") but keeps the full name
# in the <a title='...'> attribute (also mirrored on the <td>'s data-search/
# data-order, unused here) — captured from real dump data, profil-139.
_TR_TRUNCATED_COLO_NAME = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="6.000000">6,0</td>
    <td data-player-column="duration">40m 03s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-1-38" title="Voir cette colonie sur la carte">[1:38]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="43651372"><strong>43 651 372</strong></td>
    <td data-player-column="colony" data-search="Before i forget" data-order="Before i forget"><a style='color:black;' href='attaque-1-38' title='Before i forget'>Before i for..</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-139">SlipKnot</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-S2">S2</a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de KingShark"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-6" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de KingShark&lt;/div&gt;" aria-label="Vassal de KingShark"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">KingShark</span></a></span></td>
</tr>"""

test_source_code_data_1 = "\n\n".join(
    [
        _TR_PLAIN_INTEGER_DISTANCE,
        _TR_DECIMAL_DISTANCE_VASSAL_WITH_ALLIANCE,
        _TR_VASSAL_WITH_BLANK_ALLIANCE,
        _TR_VASSAL_PLUS_VACANCES_STATUS,
        _TR_EMOJI_COLO_NAME_NEGATIVE_COORD,
        _TR_APOSTROPHE_ACCENTED_NAME_BLANK_ALLIANCE,
        _TR_MULTIWORD_NAMES_WITH_ALLIANCE,
        _TR_TRUNCATED_COLO_NAME,
    ]
)

_EXPECTED_SOURCE_CODE = pd.DataFrame(
    [
        ["[1:32]", 10_372_233, "✔️A FLOOD✔️", "Grim", "SDS"],
        ["[0:30]", 26_515_927, "⛔ NO FLOOD ⛔", "HarleyQueen", "BORG"],
        ["[36:97]", 35_905, "Lalaland", "Immalie", ""],
        ["[-34:25]", 13_780_767, "Bravo le veau", "Gizmorisa", "TJ"],
        ["[14:-19]", 3_625_043, "🪳🪳🪳", "Troglodyte", "RP"],
        ["[36:98]", 63_988, "Kröm'land", "Krömiz", ""],
        ["[46:46]", 917_344, "Synchro 59", "Jack Sparrow", "RDP"],
        ["[1:38]", 43_651_372, "Before i forget", "SlipKnot", "S2"],
    ],
    columns=_COLUMNS,
)


def test_parse_source_code():
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_sourcecode(test_source_code_data_1), _EXPECTED_SOURCE_CODE)


# --- Multi-word name + blank alliance, both parsers ---
#
# Used to be a documented known limitation for parse_joueurs_text: separating
# fields with generic whitespace instead of a fixed delimiter meant "Word1
# Word2" (multi-word player_name) + blank alliance was indistinguishable from
# "Word1" + alliance "Word2". Fixed by switching to tab-based field
# splitting (see TODO.md "Parsing" section for the tradeoff that came with
# that — tab reliability across platforms, mobile in particular, isn't
# verified yet). Kept as an isolated single-row case (unlike the two tests
# above) since it's specifically testing this one interaction, not meant to
# be read as "the realistic fixture."

test_string_data_multiword_name_blank_alliance = _HEADER + "70,2 \t04H 55m 37s \t[2:35] \t50 \tCitadelle \tLa mie \t\tVassal de Lolofourmizz"

test_source_code_data_multiword_name_blank_alliance = """\
<tr class="naw-player-directory-row" style='color:black;'>
    <td data-player-column="distance" data-order="3.162278">3,2</td>
    <td data-player-column="duration">27m 24s</td>
    <td data-player-column="map"><a class="naw-map-coordinate-text" href="/carte-2-35" title="Voir cette colonie sur la carte">[2:35]</a></td>
    <td data-player-column="terrain" class="naw-player-terrain" data-order="50"><strong>50</strong></td>
    <td data-player-column="colony" data-search="Citadelle" data-order="Citadelle"><a style='color:black;' href='attaque-2-35' title='Citadelle'>Citadelle</a></td>
    <td data-player-column="player"><a style='color:black;' href="profil-1015">La mie</a></td>
    <td data-player-column="alliance"><a style='color:black;' href="descriptionalliance-"></a></td>
    <td data-player-column="state"><span class="naw-player-state-list" aria-label="Vassal de Lolofourmizz"><a class="naw-player-state-icon is-vassal has-visible-label naw-player-state-tooltip-trigger naw-player-state-profile-link" href="profil-634" data-html="true" data-toggle="tooltip" data-trigger="manual" data-placement="top" data-container="body" title="&lt;div class=&#039;tooltip-zone-principale-general&#039;&gt;Vassal de Lolofourmizz&lt;/div&gt;" aria-label="Vassal de Lolofourmizz"><span class="glyphicon glyphicon-link" aria-hidden="true"></span><span class="naw-player-state-icon-label">Lolofourmizz</span></a></span></td>
</tr>"""


def test_parse_text_multiword_name_with_blank_alliance():
    df = nm.parsing.parse_joueurs_text(test_string_data_multiword_name_blank_alliance)
    row = df.iloc[0]
    assert row["player_name"] == "La mie"
    assert row["alliance"] == ""


def test_parse_source_code_multiword_name_with_blank_alliance():
    df = nm.parsing.parse_joueurs_sourcecode(test_source_code_data_multiword_name_blank_alliance)
    row = df.iloc[0]
    assert row["player_name"] == "La mie"
    assert row["alliance"] == ""
