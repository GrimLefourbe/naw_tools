import html
import regex as re
import pandas as pd
import nawminator as nm

import typing as t

class ParsingError(Exception):
    pass

# --- copy-paste text format ---
#
# The joueurs page's copy-paste columns are user-toggleable (players can
# hide/show Distance, Durée, Terrain, État, etc. independently), so the set
# and order of tab-separated fields on a given paste isn't fixed anymore —
# this is parsed by locating columns dynamically rather than with one
# fixed-shape regex.
#
# Tabs (not generic whitespace) are the field separator here. Generic
# whitespace was tried and rejected: it can't reliably tell an empty field
# apart from a multi-word one (e.g. a two-word colony name with a blank
# alliance vs. a one-word colony name with a real alliance look identical
# under \s+), and no combination of heuristics tried closed that gap without
# opening a different one. Tab reliability across platforms (mobile
# especially) hasn't been verified yet — see TODO.md.
#
# All 5 fields we need (coord, tdc, colo_name, player_name, alliance) are
# required columns — alliance is the only one allowed to be *blank on a
# given row*, but its column still has to be present, same as the other
# four. coord is additionally how a line is even recognized as a data row
# in the first place. colo_name/player_name/alliance always show up
# together as a block when shown at all (never independently toggleable) —
# if that block doesn't look complete, the whole parse is rejected rather
# than guessing which of the three is missing; tdc missing is rejected the
# same way.

_HEADER_COLUMN_MAP = {
    "Coordonnées": "coord",
    "Carte": "coord",
    "Terrain": "tdc",
    "Colonie": "colo_name",
    "Joueur": "player_name",
    "Alliance": "alliance",
    # recognized (so they aren't mistaken for the header being something
    # else entirely) but not needed downstream:
    "Distance": None,
    "Durée": None,
    "État": None,
}

_COORD_RE = re.compile(r"^\[[-\d]+:[-\d]+\]$")
_TDC_RE = re.compile(r"^[\d, ]+$")


def _find_joueurs_text_columns(lines: list) -> dict:
    # Prefer reading the header row when it's still recognizable — columns
    # keep the same relative order even when some are hidden, so the header
    # alone tells us everything we need. A single stray word that happens to
    # match a column name (e.g. page-chrome text saying "Alliance") isn't a
    # header — require at least 2 recognized cells before trusting it.
    for line in lines:
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) >= 2 and all(c in _HEADER_COLUMN_MAP for c in cells):
            return {_HEADER_COLUMN_MAP[c]: i for i, c in enumerate(cells) if _HEADER_COLUMN_MAP[c] is not None}

    # Header renamed beyond recognition (or absent — e.g. a partial paste):
    # fall back to detecting columns purely from a data row's shape. coord's
    # brackets and tdc's digits-and-spaces are both unambiguous; whatever's
    # left after those two is the colo_name/player_name/alliance block.
    for line in lines:
        cells = line.split("\t")
        coord_idx = next((i for i, c in enumerate(cells) if _COORD_RE.match(c.strip())), None)
        if coord_idx is None:
            continue
        tail_start = coord_idx + 1
        tdc_present = tail_start < len(cells) and bool(_TDC_RE.match(cells[tail_start].strip()))
        columns = {"coord": coord_idx}
        if tdc_present:
            columns["tdc"] = tail_start
            tail_start += 1
        tail_len = len(cells) - tail_start
        if tail_len not in (3, 4):  # the 4th slot, when present, is the dead État column
            raise ParsingError(
                f"Expected the Colonie/Joueur/Alliance columns right after Carte/Terrain, found "
                f"{tail_len} column(s) there instead — make sure Colonie, Joueur and Alliance are "
                "all enabled before copying."
            )
        columns["colo_name"] = tail_start
        columns["player_name"] = tail_start + 1
        columns["alliance"] = tail_start + 2
        return columns
    return {}


joueurs_source_code_pat = re.compile(
    r"""
    <tr[^>]*>[\t \r\n]*
    <td[^>]*>[0-9,]+</td>[\t \r\n]*
    <td[^>]*>[^<]*</td>[\t \r\n]*
    <td[^>]*><a[^>]*>(\[[0-9:-]+\])</a></td>[\t \r\n]*
    <td[^>]*><strong>([0-9 ]+)</strong></td>[\t \r\n]+
    <td[^>]*><a[^>]*\btitle='([^']*)'[^>]*>[^<]*</a></td>[\t \r\n]*
    <td[^>]*><a[^>]+href="profil-([0-9]+)">([^<]+)</a></td>[\t \r\n]*
    <td[^>]*><a[^>]*>([^<]*)</a></td>[\t \r\n]*
    <td[^>]*><span[^>]*aria-label="([^"]*)"[\s\S]*?</td>[\t \r\n]*
    </tr>
    """, flags=re.X
)


def parse_joueurs_text(s: str):
    try:
        lines = s.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        columns = _find_joueurs_text_columns(lines)
        if "coord" not in columns:
            raise ParsingError("Failed to parse: found no matching line in input_data")
        missing = [f for f in ("tdc", "colo_name", "player_name", "alliance") if f not in columns]
        if missing:
            raise ParsingError(f"Missing required column(s) in copy-pasted text: {', '.join(missing)}")

        max_idx = max(columns.values())
        rows = []
        for line in lines:
            cells = line.split("\t")
            if len(cells) <= max_idx or not _COORD_RE.match(cells[columns["coord"]].strip()):
                continue
            rows.append({field: cells[idx].strip() for field, idx in columns.items()})
        if not rows:
            raise ParsingError("Failed to parse: found no matching line in input_data")

        data = pd.DataFrame(rows)
        data["tdc"] = data["tdc"].apply(nm.utils.parse_naw_int)
    except ParsingError as e:
        raise e
    except Exception as e:
        exc = ParsingError("Failed to parse joueurs from text")
        raise exc from e
    return data[["coord", "tdc", "colo_name", "player_name", "alliance"]]


def parse_joueurs_sourcecode(s: str):
    try:
        data = joueurs_source_code_pat.findall(s)
    except Exception as e:
        raise ParsingError from e
    if len(data) == 0:
        raise ParsingError("No valid lines found")
    df = pd.DataFrame(
        data=data,
        columns=["coord", "tdc", "colo_name", "profile_link", "player_name", "alliance", "status"],
    )
    df = df.apply(lambda x: x.str.strip())
    df["tdc"] = df["tdc"].apply(nm.utils.parse_naw_int)
    df["colo_name"] = df["colo_name"].apply(html.unescape)
    return df[["coord", "tdc", "colo_name", "player_name", "alliance"]]
