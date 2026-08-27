import gradio as gr

from nmsite.config import Config
from nmsite.tabs.settings import Settings
from nmsite.tabs.synchro import SynchroTab


def _config(**overrides) -> Config:
    values = dict(title="T", subtitle="T", hero_enabled=False, base_url="https://example.com")
    values.update(overrides)
    return Config(**values)


def _build_synchro(config: Config) -> SynchroTab:
    with gr.Blocks() as demo:
        settings = Settings(demo, config)
        with gr.Tab("Synchro"):
            synchro_tab_instance = SynchroTab(settings=settings, config=config)
    return synchro_tab_instance


def test_hybrid_mode_old_departure_field_starts_visible():
    """Regression: hybrid mode's old gr.DateTime departure field must be
    visible=True at construction time, not merely "eventually becomes
    visible" via the settings.time_input_enabled_state load-time JS
    round-trip. If the round-trip's demo.load(js=...) ever fails to fire,
    a hybrid-mode page (S1's production config) would render with NO
    visible departure field at all."""
    tab = _build_synchro(_config(time_input_mode="hybrid"))
    assert tab.time_input.visible is True


def test_hybrid_mode_new_departure_field_starts_hidden():
    tab = _build_synchro(_config(time_input_mode="hybrid"))
    assert tab.time_input_new.visible is False


def test_legacy_mode_departure_field_starts_visible():
    tab = _build_synchro(_config(time_input_mode="legacy"))
    assert tab.time_input.visible is True


def test_experimental_mode_departure_field_starts_visible():
    tab = _build_synchro(_config(time_input_mode="experimental"))
    assert tab.time_input_new.visible is True
