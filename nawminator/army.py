import numpy as np
import regex as re
from .utils import parse_naw_int, NAW_INT_REGEX

MAX_UNIT_COUNT = 2**56

unit_names = [
    ("Esclaves", "E", r"(?:Esclaves?|\bE\b)"),
    ("Maîtres esclaves", "ME", r"(?:Maîtres? esclaves?|\bME\b)"),
    ("Jeunes soldates", "JS", r"(?:Jeunes? soldates?|\bJS\b)"),
    ("Soldates", "S", r"(?:Soldates?(?!s? d'élite)|\bS\b)"),
    ("Soldates d'élite", "SE", r"(?:Soldates? d'élite|\bSE\b)"),
    ("Gardiennes", "G", r"(?:Gardiennes?(?!s? d'élite)|\bG\b)"),
    ("Gardiennes d'élite", "GE", r"(?:Gardiennes? d'élite|\bGE\b)"),
    ("Tirailleuses", "T", r"(?:Tirailleuses?(?!s? d'élite)|\bT\b)"),
    ("Tirailleuses d'élite", "TE", r"(?:Tirailleuses? d'élite|TE\b)"),
    ("Jeunes légionnaires", "JL", r"(?:Jeunes? légionnaires?|\bJL\b)"),
    ("Légionnaires", "L", r"(?:Légionnaires?(?!s? d'élite)|\bL\b)"),
    ("Légionnaires d'élite", "LE", r"(?:Légionnaires? d'élite|\bLE\b)"),
    ("Jeunes tanks", "JTK", r"(?:Jeunes? tanks?|\bJTK\b)"),
    ("Tanks", "TK", r"(?:Tanks?(?!s? d'élite)|\bTK\b)"),
    ("Tanks d'élite", "TKE", r"(?:Tanks? d'élite|\bTKE\b)"),
]

unit_stats = np.array(
    [
        [4, 4, 3, 5 * 60 + 36],
        [6, 6, 4, 8 * 60 + 24],
        [16, 8, 7, 9 * 60 + 48],
        [20, 11, 10, 12 * 60 + 36],
        [26, 17, 14, 16 * 60 + 48],
        [25, 1, 27, 16 * 60 + 48],
        [32, 1, 35, 22 * 60 + 24],
        [12, 32, 10, 19 * 60 + 36],
        [15, 40, 12, 25 * 60 + 12],
        [40, 45, 35, 30 * 60 + 48],
        [55, 60, 45, 42 * 60],
        [60, 65, 50, 49 * 60],
        [40, 80, 1, 50 * 60 + 24],
        [70, 140, 1, 1 * 3600 + 35 * 60 + 12],
        [80, 160, 1, 1 * 3600 + 57 * 60],
    ],
    dtype=np.int64,
)


class Army:
    def __init__(self, units: np.array = None, **units_args):
        if units is None:
            units = [units_args.setdefault(short_name, 0) for name, short_name, _ in unit_names]
        assert len(units) == len(unit_names), f"Expected array of length {len(unit_names)}, got {len(units)}"
        self._units: np.ndarray = np.array(units, dtype=np.int64)
        if (max_unit := max(self._units)) > MAX_UNIT_COUNT:
            raise ValueError(
                f"Can't have {max_unit} units of any type without risking overflows, maximum is {MAX_UNIT_COUNT}"
            )

    def __add__(self, other: "Army"):
        if not isinstance(other, Army):
            raise TypeError(f"Expected type Army for addition, got {type(other)}")
        return Army(self._units + other._units)

    def __sub__(self, other: "Army"):
        if not isinstance(other, Army):
            raise TypeError(f"Expected type Army for substraction, got {type(other)}")
        new_units = self._units - other._units
        if min(new_units) < 0:
            raise ValueError(f"Can't subtract more units than there are.")
        return Army(new_units)

    def __eq__(self, other: "Army"):
        if not isinstance(other, Army):
            return False
        return (self._units == other._units).all()

    def __repr__(self):
        return self._units.__repr__()

    @property
    def count(self) -> np.int64:
        return self._units.sum()

    @property
    def base_atk(self) -> np.int64:
        return np.sum(self._units * unit_stats[:, 1].transpose()).sum()

    @property
    def base_def(self) -> np.int64:
        return np.sum(self._units * unit_stats[:, 2].transpose()).sum()

    @property
    def base_hp(self) -> np.int64:
        return np.sum(self._units * unit_stats[:, 0].transpose()).sum()

    @classmethod
    def from_str(cls, s: str) -> "Army":
        print(s)
        pattern = rf"^.*?(?={"|".join(rf"(?:{unit_regex}\s*:\s*{NAW_INT_REGEX}|{NAW_INT_REGEX}\s+{unit_regex})" for name, short_name, unit_regex in unit_names)})"
        pattern += rf"\W*".join(
            rf"(?:{unit_regex}\s*:\s*(?P<{short_name}>{NAW_INT_REGEX})|(?P<{short_name}>{NAW_INT_REGEX})\s+{unit_regex})?"
            for name, short_name, unit_regex in unit_names
        )

        match = re.search(pattern, s, flags=re.IGNORECASE)
        if match is None:
            raise ValueError(f"Cannot parse army {s}")

        armee = np.array(
            [parse_naw_int(i) if i is not None else 0 for i in match.groups()],
            dtype=np.int64,
        )
        return cls(units=armee)

    def split_by_count(self, cnt: np.int64) -> tuple["Army", "Army"]:
        armee = self._units
        lost = np.zeros_like(armee, dtype=np.int64)
        left = armee.copy()
        to_remove = cnt
        for i, unit_count in enumerate(armee):
            units_lost = min(to_remove, unit_count)
            units_left = unit_count - units_lost
            to_remove = to_remove - units_lost
            lost[i] = units_lost
            left[i] = units_left
        return Army(lost), Army(left)

    def split_by_hp(self, hp: np.float64):
        armee = self._units
        lost = np.zeros_like(armee, dtype=np.int64)
        left = armee.copy()
        unit_hps = armee * unit_stats[:, 0].transpose()
        hp_left_to_remove = hp
        for i, row_hp in enumerate(unit_hps):
            if hp_left_to_remove == 0:
                break
            dmg = min(row_hp, hp_left_to_remove)
            units_lost = np.floor(0.5 + (dmg / unit_stats[i, 0])).astype(np.int64)  # Avoids round half to even rounding
            lost[i] += units_lost
            left[i] -= units_lost
            hp_left_to_remove -= dmg

        return Army(lost), Army(left)

    def recruit_time(self, tdp=0, bonus_alli=0):
        raw_durations = self._units * unit_stats[:, 3].transpose()
        reduced_durations = raw_durations * 0.95**tdp * 0.99**bonus_alli
        total_duration = np.floor(reduced_durations).astype(np.int64).sum()

        return self._units * unit_stats[:, 3].transpose(), total_duration

    def non_xp_recruit_time(self, tdp=0, bonus_alli=0):
        units = self._units.copy()
        units[0:2] = np.sum(units[0:2]), *np.zeros(1)
        units[2:5] = np.sum(units[2:5]), *np.zeros(2)
        units[5:7] = np.sum(units[5:7]), *np.zeros(1)
        units[7:9] = np.sum(units[7:9]), *np.zeros(1)
        units[9:12] = np.sum(units[9:12]), *np.zeros(2)
        units[12:15] = np.sum(units[12:15]), *np.zeros(2)
        raw_durations = units * unit_stats[:, 3].transpose()
        reduced_durations = raw_durations * 0.95**tdp * 0.99**bonus_alli
        total_duration = np.floor(reduced_durations).astype(np.int64).sum()

        return self._units * unit_stats[:, 3].transpose(), total_duration

    def to_str(self) -> str:
        return ", ".join(
            [
                f"{n:,} {unit_name}".replace(",", " ")
                for n, (unit_name, short_name, regex) in zip(self._units, unit_names)
                if n > 0
            ]
        )

    def to_str_compact(self) -> str:
        return "\n".join(
            f"{short_name}: {n:,}".replace(",", " ") for n, (_, short_name, _) in zip(self._units, unit_names) if n > 0
        )


def last_units_hp(army: Army):
    last_unit_idx = max(army._units.nonzero()[0])
    return unit_stats[last_unit_idx, 0]
