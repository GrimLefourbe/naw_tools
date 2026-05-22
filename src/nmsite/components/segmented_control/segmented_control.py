__all__ = ["SegmentedControl"]

import typing as t
from pathlib import Path
import gradio as gr

from nmsite.interface import _merge_elem_classes


_CSS = (Path(__file__).parent / "style.css").read_text()
_JS  = (Path(__file__).parent / "script.js").read_text()


class SegmentedControl(gr.HTML):
    """Button-strip selector with instant client-side visual feedback.

    Subclasses gr.HTML using Gradio 6's interactive HTML API. Clicking a button
    updates the selection immediately (no server roundtrip for the visual), then
    fires ``trigger('input')`` so the Python ``.input()`` handler runs.
    ``watch()`` re-syncs the highlight if the server updates the value as output.

    Args:
        choices: Ordered list of option labels shown as buttons.
        value: Initially selected label; must be one of ``choices``.
        orientation: ``"vertical"`` (default) stacks buttons; ``"horizontal"`` places them side-by-side.
        **kwargs: Forwarded to ``gr.HTML`` (e.g. ``elem_id``, ``visible``).

    Wiring:
        sel = SegmentedControl(["A", "B", "C"], value="B", elem_id="my_sel")
        sel.input(fn, inputs=[sel], outputs=[...])

    The component's value (accessible as an input) is the selected label string.
    """

    def __init__(
        self,
        choices: list[str],
        value: str,
        orientation: t.Literal["horizontal", "vertical"] = "vertical",
        **kwargs,
    ):
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
