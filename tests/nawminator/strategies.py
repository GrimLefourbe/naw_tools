import nawminator as nm
import hypothesis as hp
import hypothesis.strategies as st

def army_strategy_factory(min_value=0, max_value=nm.army.MAX_UNIT_COUNT):
    return st.builds(
        nm.army.Army,
        st.lists(st.integers(min_value=min_value, max_value=max_value), min_size=15, max_size=15),
    )
army_strategy = army_strategy_factory()


round_strategy = st.builds(
    nm.battle.Round,
    attacker_base_dmg=st.integers(min_value=0),
    attacker_bonus_dmg=st.integers(min_value=0),
    defender_base_dmg=st.integers(min_value=0),
    defender_bonus_dmg=st.integers(min_value=0),
    attacker_losses=army_strategy,
    defender_losses=army_strategy,
)

def levels_strategy_factory(
    mandibule=st.integers(min_value=0, max_value=40),
    carapace=st.integers(min_value=0, max_value=40),
    hero_lvl=st.integers(min_value=0, max_value=180),
    hero_type=st.sampled_from(nm.levels.HeroType),
    train=st.integers(min_value=0, max_value=40),
    dome=st.integers(min_value=0, max_value=40),
    loge=st.integers(min_value=0, max_value=40),
    alliance=st.sampled_from(nm.levels.AllianceType),
    special=st.integers(min_value=0, max_value=5),
):
    return st.builds(
        nm.levels.Levels,
        mandibule=mandibule,
        carapace=carapace,
        hero_lvl=hero_lvl,
        hero_type=hero_type,
        train=train,
        dome=dome,
        loge=loge,
        alliance=alliance,
        special=special,
    )

levels_strategy = levels_strategy_factory()

simple_bonuses_strategy = st.builds(
    nm.battle.Bonuses,
    dmg=st.floats(min_value=0.0, max_value=3.5),
    hp=st.floats(min_value=0.0, max_value=3.5),
)

simple_warparty_strategy = st.builds(
    nm.battle.WarParty,
    army=army_strategy_factory(max_value=nm.army.MAX_UNIT_COUNT//64),
    bonuses=simple_bonuses_strategy,
    atk=st.just(True),
)