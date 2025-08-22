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

simple_bonuses_strategy = st.builds(
    nm.war.Bonuses,
    dmg=st.floats(min_value=0.0, max_value=3.5),
    hp=st.floats(min_value=0.0, max_value=3.5),
)

simple_warparty_strategy = st.builds(
    nm.war.WarParty,
    army=army_strategy_factory(max_value=nm.army.MAX_UNIT_COUNT//64),
    bonuses=simple_bonuses_strategy,
    atk=st.just(True),
)