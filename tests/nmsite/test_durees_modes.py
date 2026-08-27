import gradio as gr

from nmsite.config import Config
from nmsite.tabs.durees import durees_tab
from nmsite.tabs.settings import Settings


def _config(**overrides) -> Config:
    values = dict(title="T", subtitle="T", hero_enabled=False, base_url="https://example.com")
    values.update(overrides)
    return Config(**values)


def _elem_ids(demo: gr.Blocks) -> set[str]:
    return {eid for c in demo.blocks.values() if (eid := getattr(c, "elem_id", None))}


def _build_durees(config: Config):
    with gr.Blocks() as demo:
        settings = Settings(demo, config)
        with gr.Tab("Durées") as tab:
            durees_tab(settings, tab, config)
    return demo


def test_legacy_mode_has_old_fields_only():
    demo = _build_durees(_config(time_input_mode="legacy"))
    ids = _elem_ids(demo)
    assert "durees_duration" in ids
    assert "durees_start_time" in ids
    assert "durees_arrival_time" in ids
    assert "durees_duration_new" not in ids
    assert "durees_start_time_new" not in ids
    assert "durees_arrival_time_new" not in ids


def test_experimental_mode_has_new_fields_only():
    demo = _build_durees(_config(time_input_mode="experimental"))
    ids = _elem_ids(demo)
    assert "durees_duration" in ids
    assert "durees_start_time" in ids
    assert "durees_arrival_time" in ids
    assert "durees_duration_new" not in ids
    assert "durees_start_time_new" not in ids
    assert "durees_arrival_time_new" not in ids


def test_experimental_mode_fields_are_timeinput_not_old_style():
    import nmsite.components

    demo = _build_durees(_config(time_input_mode="experimental"))
    duration = next(c for c in demo.blocks.values() if getattr(c, "elem_id", None) == "durees_duration")
    assert isinstance(duration, nmsite.components.TimeInput)
