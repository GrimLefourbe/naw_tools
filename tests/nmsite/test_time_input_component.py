import datetime as dt
import json

import gradio as gr

from nmsite.components import TimeInput


def test_callable_value_is_resolved_not_left_at_mode_default():
    """TimeInput(value=lambda: ...), the same pattern gr.DateTime uses for
    "now" defaults (see synchro.py), must actually call the lambda — not
    silently fall back to the mode's empty default (1970-01-01 for
    datetime)."""
    fixed = dt.datetime(2026, 1, 2, 3, 4, 5)
    with gr.Blocks():
        ti = TimeInput(mode="datetime", value=lambda: fixed)

    state = json.loads(ti.value)
    assert state == {
        "year": 2026, "month": 1, "day": 2,
        "hours": 3, "minutes": 4, "seconds": 5,
    }
