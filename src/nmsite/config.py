import typing as t
from dataclasses import dataclass


@dataclass
class Config:
    title: str
    subtitle: str
    hero_enabled: bool
    base_url: str
    tabs: str | list[str] = "default"
    dev: bool = False
    time_input_mode: t.Literal["legacy", "hybrid", "experimental"] = "legacy"


configs = {
    "S1": Config(
        title="Nawminator",
        subtitle="S1",
        hero_enabled=True,
        base_url="https://s1.natureatwar.fr",
        time_input_mode="hybrid",
    ),
    "S2": Config(
        title="Nawminator",
        subtitle="S2",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
    ),
    "DEV": Config(
        title="Nawminator",
        subtitle="DEV",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
        tabs="all",
        dev=True,
        time_input_mode="experimental",
    ),
    "DEV_HYBRID": Config(
        title="Nawminator",
        subtitle="DEV",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
        tabs="all",
        dev=True,
        time_input_mode="hybrid",
    ),
}
