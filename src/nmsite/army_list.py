from nawminator.army import Army


class ArmyList:
    """Pure Python army list with checkboxes. No Gradio dependency.

    Immutable-style: every mutating operation returns a new ArmyList.
    Designed to be stored in a single gr.State in the UI layer.
    """

    def __init__(self, armies: list[Army] | None = None, checks: list[bool] | None = None):
        self.armies = list(armies) if armies is not None else [Army(), Army()]
        self.checks = list(checks) if checks is not None else [False] * len(self.armies)
        assert len(self.armies) == len(self.checks)

    def add(self) -> "ArmyList":
        return ArmyList(self.armies + [Army()], self.checks + [False])

    def remove(self, idx: int) -> "ArmyList":
        return ArmyList(
            [a for i, a in enumerate(self.armies) if i != idx],
            [c for i, c in enumerate(self.checks) if i != idx],
        )

    def update_army(self, idx: int, army: Army) -> "ArmyList":
        armies = list(self.armies)
        armies[idx] = army
        return ArmyList(armies, list(self.checks))

    def set_check(self, idx: int, checked: bool) -> "ArmyList":
        checks = list(self.checks)
        checks[idx] = checked
        return ArmyList(list(self.armies), checks)

    def fusionner(self) -> "ArmyList":
        """Merge all checked armies into the first checked slot."""
        sel = [i for i, c in enumerate(self.checks) if c]
        if len(sel) < 2:
            return self
        merged = sum((self.armies[i] for i in sel), Army())
        armies = [a for i, a in enumerate(self.armies) if i not in sel[1:]]
        armies[sel[0]] = merged
        return ArmyList(armies, [False] * len(armies))

    def repartir(self, n: int) -> "ArmyList":
        """Merge all checked armies then split into n equal parts.

        Parts replace the checked rows at the position of the first checked row.
        Unchecked rows are untouched. No-op if nothing is checked.
        """
        sel = [i for i, c in enumerate(self.checks) if c]
        if not sel:
            return self
        merged = sum((self.armies[i] for i in sel), Army())
        parts = split_army(merged, n)
        sel_set = set(sel)
        before = [a for i, a in enumerate(self.armies) if i not in sel_set and i < sel[0]]
        after = [a for i, a in enumerate(self.armies) if i not in sel_set and i > sel[-1]]
        return ArmyList(before + parts + after, [False] * (len(before) + n + len(after)))

    @property
    def total(self) -> Army:
        return sum(self.armies, Army())

    def __repr__(self) -> str:
        return f"ArmyList({len(self.armies)} rows, total={self.total.count})"


def split_army(army: Army, n: int) -> list[Army]:
    """Split army into n parts: each unit type is floor-divided by n.

    The last part receives all remainders, guaranteeing sum(parts) == army exactly.
    """
    base = army._units // n
    remainder = army._units - base * (n - 1)
    return [Army(base) for _ in range(n - 1)] + [Army(remainder)]
