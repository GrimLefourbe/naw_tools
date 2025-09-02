from collections import namedtuple
import typing as t
import re
import logging
import datetime as dt

logger = logging.getLogger(__name__)

__all__ = ["parse_naw_int", "format_naw_int", "parse_ajhms", "timedelta_to_ajhms", "NAW_INT_REGEX"]


def parse_naw_int(s: str) -> int:
    return int(s.replace(" ", "").replace(",", ""))


def format_naw_int(i) -> str:
    return f"{i:,}".replace(",", " ")


def parse_ajhms(s: str) -> dt.timedelta:

    found_groups = {k: parse_naw_int(v) for v, k in re.findall(rf"({NAW_INT_REGEX})\s*?([AJHMS])", s)}
    td = dt.timedelta(
        days=found_groups.get("A", 0) * 365 + found_groups.get("J", 0),
        hours=found_groups.get("H", 0),
        minutes=found_groups.get("M", 0),
        seconds=found_groups.get("S", 0),
    )
    logger.debug(f"Parsed {td} from {s}")
    return td


def timedelta_to_ajhms(td: dt.timedelta, pad: str | bool = False):
    parts = []
    if pad is True:
        padc = ""
    elif pad == "full":
        padc = "0"
    else:
        padc = pad

    padder = lambda x: "d" if pad is False else f"{padc}{x}d"

    if (t := td.days // 365) or pad == "full":
        parts.append((f"{t:d}") + "A")
    if (t := td.days % 365) or pad == "full":
        parts.append(f"{t:{padder(3)}}J")
    if (t := td.seconds // 3600) or pad == "full":
        parts.append(f"{t:{padder(2)}}H")
    if (t := (td.seconds % 3600) // 60) or pad == "full":
        parts.append(f"{t:{padder(2)}}M")
    if (t := td.seconds % 60) or len(parts) == 0 or pad == "full":
        parts.append(f"{t:{padder(2)}}S")
    print(parts)
    return " ".join(parts)


NAW_INT_REGEX = r"\d[ \d]*"
