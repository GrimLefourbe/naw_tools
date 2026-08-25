import typing as t
import re
import logging
import datetime as dt

logger = logging.getLogger(__name__)

__all__ = [
    "parse_naw_int",
    "format_naw_int",
    "parse_ajhms",
    "timedelta_to_ajhms",
    "timedelta_to_ajhms_parts",
    "ajhms_parts_to_timedelta",
    "NAW_INT_REGEX",
]


def parse_naw_int(s: str) -> int:
    return int(s.replace(" ", "").replace(",", ""))


def format_naw_int(i) -> str:
    return f"{i:,}".replace(",", " ")


def timedelta_to_ajhms_parts(td: dt.timedelta) -> dict[str, int]:
    """Decompose a timedelta into {years, days, hours, minutes, seconds},
    using the game's AJHMS convention: a year is a fixed 365 days (no leap
    years). Assumes a non-negative timedelta."""
    return {
        "years": td.days // 365,
        "days": td.days % 365,
        "hours": td.seconds // 3600,
        "minutes": (td.seconds % 3600) // 60,
        "seconds": td.seconds % 60,
    }


def ajhms_parts_to_timedelta(
    years: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0
) -> dt.timedelta:
    """Inverse of timedelta_to_ajhms_parts: compose years/days/hours/minutes/
    seconds into a timedelta, using the same fixed-365-day-year convention."""
    return dt.timedelta(days=years * 365 + days, hours=hours, minutes=minutes, seconds=seconds)


def parse_ajhms(s: str) -> dt.timedelta:

    found_groups = {k: parse_naw_int(v) for v, k in re.findall(rf"({NAW_INT_REGEX})\s*?([AJHMS])", s)}
    td = ajhms_parts_to_timedelta(
        years=found_groups.get("A", 0),
        days=found_groups.get("J", 0),
        hours=found_groups.get("H", 0),
        minutes=found_groups.get("M", 0),
        seconds=found_groups.get("S", 0),
    )
    logger.debug(f"Parsed {td} from {s}")
    return td


def timedelta_to_ajhms(td: dt.timedelta, pad: str | bool = False):
    p = timedelta_to_ajhms_parts(td)
    parts = []
    if pad is True:
        padc = ""
    elif pad == "full":
        padc = "0"
    else:
        padc = pad

    padder = lambda x: "d" if pad is False else f"{padc}{x}d"

    if (t := p["years"]) or pad == "full":
        parts.append((f"{t:d}") + "A")
    if (t := p["days"]) or pad == "full":
        parts.append(f"{t:{padder(3)}}J")
    if (t := p["hours"]) or pad == "full":
        parts.append(f"{t:{padder(2)}}H")
    if (t := p["minutes"]) or pad == "full":
        parts.append(f"{t:{padder(2)}}M")
    if (t := p["seconds"]) or len(parts) == 0 or pad == "full":
        parts.append(f"{t:{padder(2)}}S")
    return " ".join(parts)


NAW_INT_REGEX = r"\d[ \d]*"
