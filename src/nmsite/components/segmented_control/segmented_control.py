__all__ = ["SegmentedControl"]

import typing as t
from functools import partial
from pathlib import Path
import gradio as gr
from gradio.events import EventListener

from nmsite.interface import _merge_elem_classes


_CSS = (Path(__file__).parent / "style.css").read_text()
_JS  = (Path(__file__).parent / "script.js").read_text()


class SegmentedControl(gr.HTML):
    """Button-strip selector with instant client-side visual feedback.

    Subclasses gr.HTML using Gradio 6's interactive HTML API. Clicking a button
    updates the selection immediately (no server roundtrip for the visual), then
    fires ``trigger('input')`` so the Python ``.input()`` handler runs.
    ``watch()`` re-syncs the highlight if the server updates the value as output.

    Per-choice events are supported via ``on_choice(label)`` or attribute access
    ``component.select_<label>``. These fire before ``input`` on each click,
    allowing ``js=True`` handlers for instant client-side interactivity updates.
    A generic ``select`` event is also fired for general selection-change listeners.

    Args:
        choices: Ordered list of option labels shown as buttons.
        value: Initially selected label; must be one of ``choices``.
        orientation: ``"vertical"`` (default) stacks buttons; ``"horizontal"`` places them side-by-side.
        **kwargs: Forwarded to ``gr.HTML`` (e.g. ``elem_id``, ``visible``).

    Wiring:
        sel = SegmentedControl(["A", "B", "C"], value="B", elem_id="my_sel")
        sel.input(fn, inputs=[sel], outputs=[...])
        sel.on_choice("A")(fn, outputs=[...], js=True)

    The component's value (accessible as an input) is the selected label string.
    """

    def __init__(
        self,
        choices: list[str],
        value: str,
        orientation: t.Literal["horizontal", "vertical"] = "vertical",
        **kwargs,
    ):
        self._choices = choices
        ctrl_class = "seg-control seg-horizontal" if orientation == "horizontal" else "seg-control"
        buttons_html = "".join(
            f'<button class="seg-btn" data-value="{c}">{c}</button>'
            for c in choices
        )
        _merge_elem_classes(kwargs, "seg-wrapper")
        kwargs.setdefault('padding', False)
        kwargs.setdefault('apply_default_css', False)
        kwargs.setdefault('show_label', False)
        super().__init__(
            value=value,
            html_template=f'<div class="{ctrl_class}">{buttons_html}</div>',
            css_template=_CSS,
            js_on_load=_JS,
            **kwargs,
        )

    def __getattr__(self, name: str):
        choices = self.__dict__.get('_choices', [])
        if name.startswith('select_') and name.removeprefix('select_') in choices:
            return partial(EventListener(event_name=name).listener, self)
        return super().__getattr__(name)

    def on_choice(self, choice: str):
        return getattr(self, f"select_{choice}")
