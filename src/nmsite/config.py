from dataclasses import dataclass

@dataclass
class Config:
    title: str
    subtitle: str
    hero_enabled: bool

configs = {
    "S1": Config(
        title="Nawminator",
        subtitle="S1",
        hero_enabled=True,
    ),
    "S2": Config(
        title="Nawminator",
        subtitle="S2",
        hero_enabled=False,
    ),
}