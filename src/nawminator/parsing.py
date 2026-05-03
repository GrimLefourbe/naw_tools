import html
import io
import regex as re
import pandas as pd
import nawminator as nm

import typing as t

class ParsingError(Exception):
    pass

joueurs_copy_paste_pat = re.compile(
    r"""
    ^
    ([\d,]+)\s+
    ((?:\w+\ ?)+)\s+
    (\[[-\d]+:[-\d]+\])\s+
    ([\d,]+)\s+
    (.*?)\s+
    ([\S ]+)\s+
    (\S+)\s+
    (Libre|Vassal\ de\ [\S ]+|En\ vacances)
    $
    """, flags=re.X | re.M
)

joueurs_source_code_pat = re.compile(
    r"""
    <tr[^>]*>[\t \r\n]*
    <td>[0-9,]+</td>[\t \r\n]*
    <td[^>]*>[^<]*</td>[\t \r\n]*
    <td>(\[[0-9:-]+\])</td>[\t \r\n]*
    <td>([0-9,]+)</td>[\t \r\n]+
    <td><a[^>]*>([^<]+)</a></td>[\t \r\n]*
    <td><a[^>]+href="profil-([0-9]+)">\ <b>([^<]+)</b></a></td>[\t \r\n]*
    <td><a[^>]*>\ <b>([^<]*)</b></a></td>[\t \r\n]*
    <td>(?:Vassal\ de\ <a\ href='profil-[0-9]+'>\ <b>)?([^<>]+)(?:</b></a>)?</td>[\t \r\n]*
    </tr>
    """, flags=re.X
)


def parse_joueurs_text(s: str):
    try:
        lines = [i.groups() for i in joueurs_copy_paste_pat.finditer(s)]
        if len(lines) == 0:
            exc = ParsingError("Failed to parse: found no matching line in input_data")
            # exc.add_note(s)
            raise exc
        data = pd.DataFrame(
            data=lines,
            columns=["distance", "duration", "coord", "tdc", "colo_name", "player_name", "alliance", "status"],
            dtype=str,
        )
        data = data.apply(lambda x: x.str.strip())
        data["tdc"] = data["tdc"].apply(nm.utils.parse_naw_int)
    except ParsingError as e:
        raise e
    except Exception as e:
        exc = ParsingError("Failed to parse joueurs from text")
        # exc.add_note(s)
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
