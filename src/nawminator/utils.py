from collections import namedtuple
import typing as t
import re
import logging
import datetime as dt

logger = logging.getLogger(__name__)

YJHMS = namedtuple("YJHMS", "Y J H M S")


def seconds_to_yjhms(d: int) -> YJHMS:
    divisions = [365, 24, 60, 60]
    numbers = []
    n = d
    for division in divisions[::-1]:
        numbers.append(n % division)
        n = n // division
    numbers.append(n)
    return YJHMS(*numbers[::-1])

def parse_YJHMS(s: str) -> YJHMS:
    found_groups = {k: parse_naw_int(v) for v, k in re.findall(rf"({NAW_INT_REGEX})\s*?([AJHMS])", s)}
    d = YJHMS(
        *(found_groups.get(k, 0) for k in "AJHMS")
    )
    logger.debug(f"Parsed {d} from {s}")
    return d

def YJHMS_to_seconds(d: YJHMS):
    return (((d.Y * 365 + d.J) * 24 + d.H) * 60 + d.M) * 60 + d.S 


def format_yjhms(d: YJHMS, pad=False):
    return " ".join(f"{i:02d}{t}" if pad else f"{i}{t}" for i, t in zip(d, ["A", "J", "H", "M", "S"]) if i != 0)


def parse_naw_int(s: str) -> int:
    return int(s.replace(" ", "").replace(",", ""))


def format_naw_int(i) -> str:
    return f"{i:,}".replace(",", " ")

def timedelta_to_ajhms(td: dt.timedelta, pad: str | bool = False):
    parts = []
    if pad is True:
        padc = ""
    elif pad == "full":
        padc = "0"
    else:
        padc = pad

    padder = lambda x: "d" if pad is False else f"{padc}{x}d"

    if (t := td.days//365) or pad == "full":
        parts.append((f"{t:d}")+"A")
    if (t := td.days%365) or pad == "full":
        parts.append(f"{t:{padder(3)}}J")
    if (t := td.seconds//3600) or pad == "full":
        parts.append(f"{t:{padder(2)}}H")
    if (t := (td.seconds%3600)//60) or pad == "full":
        parts.append(f"{t:{padder(2)}}M")
    if (t := td.seconds%60) or len(parts) == 0 or pad == "full":
        parts.append(f"{t:{padder(2)}}S")
    print(parts)
    return " ".join(parts)


NAW_INT_REGEX = r"\d[ \d]*"
