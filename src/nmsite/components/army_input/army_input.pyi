__all__ = ["ArmyInputHTML"]

import json
import typing as t
from pathlib import Path

import gradio as gr
import nawminator as nm

from nmsite.interface import _merge_elem_classes

_CSS = (Path(__file__).parent / "style.css").read_text()
_JS  = (Path(__file__).parent / "script.js").read_text()

from gradio.events import Dependency

class ArmyInputHTML(gr.HTML):
    """HTML-based interactive army input using Gradio 6's interactive HTML API.

    props.value is a JSON string:
        {"units": [...15 ints...], "raw": "...", "recap": "...", "error": null, "panel": "none"}

    panel: "none" | "string" | "units" | "import"
    """

    _UNIT_SHORTS = [short for _, short, _ in nm.army.unit_names]

    # TODO: ArmyInputHTML doesn't pack flush inside gr.Group like native Gradio components.
    # Root cause: css_template is auto-scoped (Svelte hash on every selector), so rules with
    # ancestor selectors like `.gr-group .ai-widget` never match the group wrapper outside this
    # component. Gradio's own group rule strips border/radius from the direct child (.ai-wrapper),
    # but the visible border lives on the inner .ai-widget. Moving the border to .ai-wrapper
    # doesn't work because gr.HTML with container=False applies its own border:none to the outer
    # wrapper. Global CSS in app.py can reach .gr-group but requires !important fights that are
    # brittle. The intended solution is probably a proper Svelte-based custom component rather
    # than the css_template approach — investigate if/when we need true group integration.

    def __init__(
        self,
        label: str | None = None,
        value: nm.army.Army | None = None,
        recap_format: t.Literal["compact", "full"] = "compact",
        show_import: bool = True,
        show_copy: bool = True,
        btn_align: t.Literal["left", "right"] = "right",
        **kwargs,
    ):
        army = value or nm.army.Army()
        self._recap_format = recap_format

        _merge_elem_classes(kwargs, "ai-wrapper")
        kwargs.setdefault("container", False)
        kwargs.setdefault("show_label", False)
        kwargs.setdefault("apply_default_css", False)
        kwargs.setdefault("padding", False)

        recap = self._fmt(army)

        def process_army(state: dict) -> dict:
            panel = state.get("panel", "none")
            current = nm.army.Army([int(x) for x in state.get("units", [0] * 15)])
            result_army = current
            try:
                if panel == "string":
                    result_army = nm.army.Army.from_str(state.get("raw", ""))
                    state["units"] = result_army._units.tolist()
                    state["error"] = None
                    state["panel"] = "none"
                elif panel == "units":
                    state["error"] = None
                elif panel == "import":
                    result_army = nm.army.Army()
                    state["units"] = result_army._units.tolist()
                    state["raw"] = ""
                    state["error"] = None
                    state["panel"] = "none"
            except ValueError as e:
                result_army = current
                state["error"] = str(e)
            state["recap"] = self._fmt(result_army)
            return state

        super().__init__(
            value=json.dumps({
                "units": army._units.tolist(),
                "raw": recap,
                "recap": recap,
                "error": None,
                "panel": "none",
            }),
            html_template=self._make_html_template(label, btn_align, show_import, show_copy),
            css_template=_CSS,
            js_on_load=_JS,
            server_functions=[process_army],
            **kwargs,
        )

    def _fmt(self, a: nm.army.Army) -> str:
        return (a.to_str_compact(sep=", ") if self._recap_format == "compact" else a.to_str()) if a.count > 0 else ""

    @classmethod
    def _make_html_template(cls, label: str | None, btn_align: str, show_import: bool, show_copy: bool) -> str:
        unit_shorts_json = json.dumps(cls._UNIT_SHORTS)
        import_btn = (
            "<button class='ai-btn' data-action='import' title='Importer'>\U0001f4e5</button>"
            if show_import else ""
        )
        copy_btn = (
            "<button class='ai-btn' data-action='copy' title='Copier armée'>\U0001f4e4</button>"
            if show_copy else ""
        )
        btns_html = (
            f"<div class='ai-btns'>"
            f"<button class='ai-btn' data-action='string' title='Coller armée'>\U0001f4cb</button>"
            f"<button class='ai-btn' data-action='units' title='Saisir unités'>✏️</button>"
            f"{copy_btn}"
            f"{import_btn}"
            f"</div>"
        )
        # DOM order determines button side for the label case:
        # btn_align="right" → [label, buttons]; "left" → [buttons, label]
        label_html = f"<span class='ai-label'>{label}</span>" if label else ""
        header_content = btns_html + label_html if btn_align == "left" else label_html + btns_html

        widget_classes = ["ai-widget"]
        if btn_align == "right":
            widget_classes.append("btns-right")
        if not label:
            widget_classes.append("no-label")

        return (
            f"<div class='{' '.join(widget_classes)}' data-unit-shorts='{unit_shorts_json}'>"
            f"<div class='ai-header'>{header_content}</div>"
            f"<div class='ai-recap'></div>"
            f"<div class='ai-string-panel' style='display:none'>"
            f"<textarea class='ai-textarea' placeholder='Coller armée ici…'></textarea>"
            f"<div class='ai-error' style='display:none'></div>"
            f"<button class='ai-confirm'>Valider</button>"
            f"</div>"
            f"<div class='ai-units-popover' style='display:none'>"
            f"<div class='ai-units-grid'></div>"
            f"</div>"
            f"</div>"
        )

    def preprocess(self, payload):
        if payload is None:
            return nm.army.Army()
        try:
            state = json.loads(str(payload))
            return nm.army.Army([int(x) for x in state.get("units", [0] * 15)])
        except (json.JSONDecodeError, ValueError, OverflowError):
            return nm.army.Army()

    def postprocess(self, value):
        if isinstance(value, str):
            return value
        army = value if isinstance(value, nm.army.Army) else nm.army.Army()
        recap = self._fmt(army)
        return json.dumps({
            "units": army._units.tolist(),
            "raw": recap,
            "recap": recap,
            "error": None,
            "panel": "none",
        })
    from typing import Callable, Literal, Sequence, Any, TYPE_CHECKING
    from gradio.blocks import Block
    if TYPE_CHECKING:
        from gradio.components import Timer
        from gradio.components.base import Component