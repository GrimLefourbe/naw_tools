from collections import namedtuple

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


def format_yjhms(d: YJHMS):
    return " ".join(f"{i}{t}" for i, t in zip(d, ["A", "J", "H", "M", "S"]) if i != 0)


def parse_naw_int(s: str) -> int:
    return int(s.replace(" ", ""))


def format_naw_int(i: int) -> str:
    return f"{i:,}".replace(",", " ")


NAW_INT_REGEX = r"\d[ \d]*"
