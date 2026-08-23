import pandas as pd
import datetime as dt

from nmsite.synchro_copy import (
    format_copy_data_text,
    format_copy_data_discord,
    format_copy_data_table,
    _format_colonie_link,
)

_BASE_URL = "https://s2.natureatwar.fr"


def _targets():
    return pd.DataFrame(
        [
            {
                "Horaire": "14:32:10",
                "Durée": "2j 3h 10m 5s",
                "Joueur": "Bob",
                "Colonie": "ColoB",
                "Alli": "XYZ",
                "Pos": "1:2",
                "TDC": "5 000",
            },
            {
                "Horaire": "15:00:00",
                "Durée": "3j 0h 0m 0s",
                "Joueur": "Ann",
                "Colonie": "ColoA",
                "Alli": "ABC",
                "Pos": "3:4",
                "TDC": "10 000",
            },
        ]
    )


def _player(**overrides):
    values = {"player_name": "Alice", "colo_name": "Home", "alliance": "PQR", "tdc": 20000, "x": 5, "y": 6}
    values.update(overrides)
    return pd.Series(values)


def _depart():
    return dt.datetime(2026, 8, 22, 12, 0, 0)


def test_format_copy_data_text_is_fully_plain():
    # Universal/safe fallback, no markdown at all - readable pasted anywhere
    # (Discord, plain text editors, the forum, etc), not just Discord specifically.
    # format_copy_data_discord is the ANSI-colored, Discord-specific alternative;
    # format_copy_data_table is the BBCode, forum-only one.
    result = format_copy_data_text(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert result == (
        "Cible: Alice (Home) [PQR] [5:6]\n"
        "Attack: https://s2.natureatwar.fr/attaque-5-6\n"
        "VA: 100\n"
        "Heure de départ: 12:00:00 - TDC: 20 000\n"
        "------------------------------\n"
        "14:32:10 - 2j 3h 10m 5s: [1:2] Bob[XYZ](ColoB) - 5 000\n"
        "15:00:00 - 3j 0h 0m 0s: [3:4] Ann[ABC](ColoA) - 10 000"
    )
    assert "**" not in result


def test_format_copy_data_discord_header_uses_a_bracketed_bare_url():
    # A bare URL, not a [text](url) masked link: masked links turned out to silently
    # stop rendering - even elsewhere in the same message - when certain special
    # characters appear in the link text, or when a second ANSI escape sequence
    # appears anywhere in the message (see format_copy_data_discord's docstring). A
    # bare URL still auto-embeds as a clickable link in Discord and has shown none of
    # that fragility. Wrapped in <> to suppress Discord's preview-card embed for it.
    result = format_copy_data_discord(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert result.startswith(
        "Cible: **Alice** (Home) [PQR] [5:6]\n"
        "Attack: <https://s2.natureatwar.fr/attaque-5-6>\n"
        "VA: 100\n"
        "Heure de départ: 12:00:00 - TDC: 20 000\n"
        "\n"
        "```ansi\n"
    )


def test_format_copy_data_discord_aligns_horaire_duree_pos_but_not_joueur_colonie():
    # Horaire/Durée/Pos are padded to a consistent width across rows (safe: these
    # never contain emoji), so they line up vertically. Joueur/Colonie are NOT padded
    # - they can contain emoji, and len(str(value)) miscounts emoji width, which
    # would misalign every column after one containing an emoji (see the emoji test
    # below - a first attempt padded every column, including these, and broke on
    # real data). Same field order/punctuation as format_copy_data_text's rows
    # otherwise. Horaire and Alli carry the ally/enemy color (bold+color combined
    # into one escape prefix); Durée/Joueur/Colonie/Pos/TDC stay unstyled.
    result = format_copy_data_discord(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    ESC = "\x1b"
    RED = f"{ESC}[1;31m"
    RESET = f"{ESC}[0m"
    assert result.rstrip().endswith("```")
    assert result.endswith(
        "```ansi\n"
        f"{RED}14:32:10{RESET} - 2j 3h 10m 5s: [1:2] Bob[{RED}XYZ{RESET}](ColoB) - 5 000\n"
        # Ann's Durée ("3j 0h 0m 0s", 11 chars) right-padded to Bob's width (12) with
        # a LEADING space - not trailing - so both durations' final unit letter lines
        # up in the same column, rather than their first character.
        f"{RED}15:00:00{RESET} -  3j 0h 0m 0s: [3:4] Ann[{RED}ABC{RESET}](ColoA) - 10 000\n"
        "```"
    )


def test_format_copy_data_discord_right_aligns_duree_so_unit_letters_match_up():
    # Durées can switch unit sets by magnitude ("24M 46S" vs "6h 11m 21s") - left-
    # justifying (padding with trailing spaces) would line short durations up under
    # the START of longer ones (the hours digit) instead of their end. Right-
    # justifying instead lines up each duration's last unit letter (S under s, M
    # under m before it).
    targets = _targets()
    targets.loc[0, "Durée"] = "24M 46S"
    targets.loc[1, "Durée"] = "6h 11m 21s"

    result = format_copy_data_discord(targets, _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert "   24M 46S" in result
    assert "6h 11m 21s" in result


def test_format_copy_data_discord_right_aligns_pos_coordinates_independently():
    # x and y digit counts vary independently (e.g. "1:2" vs "23:45") - padding the
    # whole "x:y" string as one unit (either direction) can't line up the ":" when
    # both sides differ in width at once. Splitting and right-justifying x and y
    # separately keeps the ":" in the same column regardless.
    targets = _targets()
    targets.loc[0, "Pos"] = "1:2"
    targets.loc[1, "Pos"] = "23:45"

    result = format_copy_data_discord(targets, _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert "[ 1: 2]" in result
    assert "[23:45]" in result


def test_format_copy_data_discord_colors_matching_alliance_green():
    targets = _targets()
    targets.loc[0, "Alli"] = "PQR"  # matches Cible Alice's own alliance -> ally

    result = format_copy_data_discord(targets, _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    ESC = "\x1b"
    assert f"{ESC}[1;32m14:32:10{ESC}[0m" in result
    assert f"{ESC}[1;32mPQR{ESC}[0m" in result


def test_format_copy_data_discord_handles_emoji_in_names():
    # Real player/colony names in this game do contain emoji (e.g. "🐼 PandaMan 🐼").
    # Joueur/Colonie are deliberately never padded (see the alignment test above), so
    # there's nothing for an emoji's miscounted width to misalign.
    targets = _targets()
    targets.loc[0, "Joueur"] = "🐼 PandaMan 🐼"
    targets.loc[0, "Colonie"] = "🗡️Tripotanus🗡️"

    result = format_copy_data_discord(targets, _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert "🐼 PandaMan 🐼[\x1b[1;31mXYZ\x1b[0m](🗡️Tripotanus🗡️)" in result


def _many_targets(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Horaire": "14:32:10",
                "Durée": "2j 3h 10m 5s",
                "Joueur": f"Joueur{i}",
                "Colonie": f"Colonie{i}",
                "Alli": "XYZ",
                "Pos": f"{i}:{i}",
                "TDC": "5 000",
            }
            for i in range(n)
        ]
    )


def test_format_copy_data_discord_falls_back_to_a_plain_fenced_block_past_discords_2000_char_limit():
    # Not about keeping the final result under 2000 - a long enough list will exceed
    # that regardless of ANSI and fall back to a file upload in Discord either way.
    # The point is that file upload's preview stays readable for plain text but is
    # garbled by raw ANSI escape bytes, so once the ANSI version would cross the
    # limit, drop ANSI entirely - but keep the fence (so row alignment survives) and
    # the header's <> URL bracketing. No bold: a plain fence disables markdown same
    # as it disables ANSI outside the ansi tag, so ** would just be literal asterisks.
    targets = _many_targets(22)
    result = format_copy_data_discord(targets, _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert "\x1b[" not in result
    assert "```ansi" not in result
    assert result.rstrip().endswith("```")
    assert "\n```\n" in result
    assert "**" not in result.split("```")[-2]  # nothing bolded inside the fenced rows
    assert "Attack: <https://s2.natureatwar.fr/attaque-5-6>" in result


def test_format_copy_data_discord_keeps_ansi_under_the_limit():
    result = format_copy_data_discord(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert len(result) <= 2000
    assert "```ansi" in result
    assert "\x1b[" in result


def test_format_copy_data_discord_with_no_targets_still_has_the_header():
    # zip(*()) over zero rows can't unpack into pos_xs, pos_ys in _discord_row_widths
    # - crashed the whole "Calcule!" action (calc_synchros calls all three formatters
    # unconditionally), not just the Discord button, whenever the alliance/TDC filter
    # matched no targets.
    result = format_copy_data_discord(_targets().iloc[0:0], _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert "Cible: **" in result
    assert "```ansi" in result


def test_format_copy_data_table_includes_the_same_target_info_header():
    # Built directly, not via the forum's paste-to-table auto-converter (which only
    # ever header-styles the first pasted line and ignores HTML entirely - see
    # format_copy_data_table's docstring). Since we own the whole payload, the
    # target-info header can just precede the table in the same clipboard string.
    # Unlike the per-target rows, the Cible colonie here is the target being synced
    # to itself, not one of the attackers - it's the most important link of all, so
    # it's linked too. BBCode's [url=...] doesn't share Discord masked-links' fragility
    # (see format_copy_data_discord), so it's fine to mask it here rather than use a
    # bare URL - forum-only output, never touches Discord's parser.
    result = format_copy_data_table(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert result.startswith(
        "Cible: [joueur]Alice[/joueur]([url=https://s2.natureatwar.fr/attaque-5-6]Home[/url])"
        "[[alliance]PQR[/alliance]] [5:6]\n"
        "VA: 100\n"
        "Heure de départ: 12:00:00 - TDC: 20 000\n"
        "\n"
        "[table]\n"
    )


def test_format_copy_data_table_groups_each_row_onto_a_single_line():
    # The forum's editor is a plain textarea, not WYSIWYG - one BBCode tag per line
    # (the converter's own style) is unreadable there. One [tr]...[/tr] per line, with
    # cells space-separated, stays legible even unrendered.
    # Durée/TDC are right-aligned and Pos is centered - the table button is
    # forum-only (the plain-text buttons cover non-BBCode targets), so there's no
    # readability trade-off to weigh against using [right]/[center] here.
    # Colonie is linked to the attack page here, built from base_url + Pos - this
    # output is BBCode-only text handed straight to the clipboard, never rendered by
    # anything of ours, so embedding the link here is safe. It must NOT be baked into
    # the shared targets DataFrame itself: that DataFrame also backs the on-screen
    # synchro_outputs table and format_copy_data_text's plain BBCode-line output,
    # neither of which renders/wants raw [url=...] BBCode.
    result = format_copy_data_table(_targets(), _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert result.endswith(
        "[table]\n"
        "[tr] [th]Horaire[/th] [th]Durée[/th] [th]Joueur[/th] [th]Colonie[/th] [th]Alli[/th] [th]Pos[/th] [th]TDC[/th] [/tr]\n"
        "[tr] [td][b]14:32:10[/b][/td] [td][right]2j 3h 10m 5s[/right][/td] [td][joueur]Bob[/joueur][/td] "
        "[td][url=https://s2.natureatwar.fr/attaque-1-2]ColoB[/url][/td] [td][alliance]XYZ[/alliance][/td] "
        "[td][center]1:2[/center][/td] [td][right]5 000[/right][/td] [/tr]\n"
        "[tr] [td][b]15:00:00[/b][/td] [td][right]3j 0h 0m 0s[/right][/td] [td][joueur]Ann[/joueur][/td] "
        "[td][url=https://s2.natureatwar.fr/attaque-3-4]ColoA[/url][/td] [td][alliance]ABC[/alliance][/td] "
        "[td][center]3:4[/center][/td] [td][right]10 000[/right][/td] [/tr]\n"
        "[/table]"
    )


def test_format_colonie_link_builds_attaque_url():
    # x/y arrive as str here, matching format_copy_data_table's real call site
    # (split straight out of the "x:y" Pos column, never converted to int).
    result = _format_colonie_link(base_url="https://s2.natureatwar.fr", x="1", y="32", colo_name="Ma Colonie")

    assert result == "[url=https://s2.natureatwar.fr/attaque-1-32]Ma Colonie[/url]"


def test_format_copy_data_table_with_no_targets_still_has_header_row():
    result = format_copy_data_table(_targets().iloc[0:0], _player(), va=100, depart=_depart(), base_url=_BASE_URL)

    assert result.endswith(
        "[table]\n"
        "[tr] [th]Horaire[/th] [th]Durée[/th] [th]Joueur[/th] [th]Colonie[/th] [th]Alli[/th] [th]Pos[/th] [th]TDC[/th] [/tr]\n"
        "[/table]"
    )
