import gradio as gr

from nmsite.config import Config
from nmsite.tabs.settings import Settings


def _config(**overrides) -> Config:
    values = dict(title="T", subtitle="T", hero_enabled=False, base_url="https://example.com")
    values.update(overrides)
    return Config(**values)


def _elem_ids(demo: gr.Blocks) -> set[str]:
    return {eid for c in demo.blocks.values() if (eid := getattr(c, "elem_id", None))}


def test_dev_config_shows_time_input_demo():
    with gr.Blocks() as demo:
        Settings(demo, _config(dev=True))
    assert "ti_demo_a" in _elem_ids(demo)


def test_non_dev_config_hides_time_input_demo():
    with gr.Blocks() as demo:
        Settings(demo, _config(dev=False))
    assert "ti_demo_a" not in _elem_ids(demo)


def test_hybrid_mode_shows_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="hybrid"))
    assert "settings_time_input_toggle" in _elem_ids(demo)


def test_legacy_mode_hides_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="legacy"))
    assert "settings_time_input_toggle" not in _elem_ids(demo)


def test_experimental_mode_hides_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="experimental"))
    assert "settings_time_input_toggle" not in _elem_ids(demo)
