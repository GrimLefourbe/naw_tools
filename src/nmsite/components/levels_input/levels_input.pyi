__all__ = ["LevelsInputComponent"]

import json
import typing as t
from pathlib import Path

import gradio as gr
import nawminator as nm

from nmsite.interface import _merge_elem_classes

_CSS = (Path(__file__).parent / "style.css").read_text()
_JS  = (Path(__file__).parent / "script.js").read_text()

from gradio.events import Dependency

class LevelsInputComponent(gr.HTML):
    """HTML-based interactive levels input using Gradio 6's interactive HTML API.

    props.value is a JSON string with keys: mandibule, carapace, hero_lvl, hero_type,
    dome, loge, alliance, special, raw, error, panel.

    The set of displayed fields is controlled by a frozenset built from constructor
    parameters.  hero_enabled and show_buildings are convenience shortcuts; future
    parameters add their fields to the same set without multiplying boolean flags.
    """

    # (id, label, layout, fields)  layout: "grid2" | "inline"
    _GROUPS: t.ClassVar[list[tuple[str, str, str, list[str]]]] = [
        ("recherche", "Recherche", "grid2", ["mandibule", "carapace"]),
        ("hero",      "Héros",     "grid2", ["hero_type", "hero_lvl"]),
        ("bonus",     "Bonus",     "grid2", ["special", "alliance"]),
        ("buildings", "Bâtiments", "grid2", ["dome", "loge"]),
    ]

    _FIELD_LABELS: t.ClassVar[dict[str, str]] = {
        "mandibule": "Mandibule", "carapace": "Carapace",
        "hero_lvl": "Niv", "hero_type": "Héros",
        "special": "Spe Combat", "alliance": "Alliance",
        "dome": "Dôme", "loge": "Loge",
    }
    # (value, full_label, abbreviation)
    _FIELD_SELECTS: t.ClassVar[dict[str, list[tuple[str, str, str]]]] = {
        "hero_type": [("", "—", "—"), ("Attaque", "Attaque", "A"), ("Défense", "Défense", "D"), ("Vie", "Vie", "V")],
        "alliance":  [("None", "—", "—"), ("Guerrier", "Guerrier", "G"), ("Pacifiste", "Pacifiste", "P"), ("Neutre", "Neutre", "N")],
    }
    _FIELD_NUM_ATTRS: t.ClassVar[dict[str, str]] = {
        "hero_lvl": "min='0' max='180'", "special": "min='0' max='5'",
    }

    def __init__(
        self,
        label: str | None = None,
        value: nm.levels.Levels | None = None,
        hero_enabled: bool = True,
        show_buildings: bool = True,
        show_import: bool = False,
        recap_sep: str = "\n",
        min_width: int = 160,
        **kwargs,
    ):
        _fields: set[str] = {"mandibule", "carapace", "special", "alliance"}
        if hero_enabled:
            _fields |= {"hero_lvl", "hero_type"}
        if show_buildings:
            _fields |= {"dome", "loge"}
        self._fields = frozenset(_fields)
        self._recap_sep = recap_sep

        _merge_elem_classes(kwargs, "li-wrapper")
        kwargs.setdefault("container", False)
        kwargs.setdefault("show_label", False)
        kwargs.setdefault("apply_default_css", False)
        kwargs.setdefault("padding", False)

        levels = value or nm.levels.Levels()

        def process_levels(state: dict) -> dict:
            panel = state.get("panel", "none")
            if panel == "string":
                try:
                    lvl = nm.levels.Levels.from_str(state.get("raw", ""))
                    self._fill_state(state, lvl)
                    state["error"] = None
                    state["panel"] = "none"
                except ValueError as e:
                    state["error"] = str(e)
                    return state
            elif panel == "import":
                lvl = nm.levels.Levels()
                self._fill_state(state, lvl)
                state["error"] = None
                state["panel"] = "none"
            else:
                lvl = self._levels_from_state(state)
            state["raw"] = lvl.to_str(hero_enabled=("hero_lvl" in self._fields), sep=self._recap_sep)
            return state

        super().__init__(
            value=json.dumps(self._build_state(levels)),
            html_template=self._make_html_template(label, show_import, min_width),
            css_template=_CSS,
            js_on_load=_JS,
            server_functions=[process_levels],
            **kwargs,
        )

    def _fill_state(self, state: dict, lvl: nm.levels.Levels) -> None:
        state["mandibule"] = lvl.mandibule
        state["carapace"] = lvl.carapace
        state["hero_lvl"] = lvl.hero_lvl
        state["hero_type"] = lvl.hero_type.value if lvl.hero_type else None
        state["dome"] = lvl.dome
        state["loge"] = lvl.loge
        state["alliance"] = lvl.alliance.value
        state["special"] = lvl.special

    def _levels_from_state(self, state: dict) -> nm.levels.Levels:
        hero_lvl = 0
        hero_type = None
        if "hero_lvl" in self._fields:
            ht_val = state.get("hero_type")
            hero_type = nm.levels.HeroType(ht_val) if ht_val else None
            hero_lvl = int(state.get("hero_lvl") or 0)
        return nm.levels.Levels(
            mandibule=int(state.get("mandibule") or 0),
            carapace=int(state.get("carapace") or 0),
            hero_lvl=hero_lvl,
            hero_type=hero_type,
            dome=int(state.get("dome") or 0) if "dome" in self._fields else 0,
            loge=int(state.get("loge") or 0) if "loge" in self._fields else 0,
            alliance=nm.levels.AllianceType(state.get("alliance") or "None"),
            special=int(state.get("special") or 0),
        )

    def _build_state(self, lvl: nm.levels.Levels) -> dict:
        state: dict = {}
        self._fill_state(state, lvl)
        state["raw"] = lvl.to_str(hero_enabled=("hero_lvl" in self._fields), sep=self._recap_sep)
        state["error"] = None
        state["panel"] = "none"
        return state

    def _make_html_template(self, label: str | None, show_import: bool, min_width: int = 160) -> str:
        widget_classes = ["li-widget"]
        if not show_import:
            widget_classes.append("li-import-hidden")

        label_html = f"<span class='li-label'>{label}</span>" if label else ""
        btns_html = (
            "<div class='li-btns'>"
            "<button class='li-btn' data-action='string' title='Coller niveaux'>\U0001f4cb</button>"
            "<button class='li-btn' data-action='import' title='Réinitialiser'>\U0001f4e5</button>"
            "<button class='li-btn li-btn-copy' data-action='copy' title='Copier niveaux'>\U0001f4e4</button>"
            "</div>"
        )

        groups_html = ""
        for group_id, _, layout, fields in self._GROUPS:
            enabled = [f for f in fields if f in self._fields]
            if not enabled:
                continue
            fields_html = "".join(self._make_field_html(f, layout) for f in enabled)
            groups_html += f"<div class='li-group li-group-{layout} li-group-{group_id}'>{fields_html}</div>"

        return (
            f"<div class='{' '.join(widget_classes)}' style='min-width:{min_width}px'>"
            f"<div class='li-header'>{label_html}{btns_html}</div>"
            f"<div class='li-recap-row'>"
            f"<textarea class='li-recap-input' rows='1' placeholder='Coller / saisir niveaux…'></textarea>"
            f"<div class='li-recap-btns'>"
            f"<button class='li-btn' data-action='copy' title='Copier niveaux'>\U0001f4e4</button>"
            f"</div>"
            f"</div>"
            f"<div class='li-error' style='display:none'></div>"
            f"<div class='li-edit-panel'>{groups_html}</div>"
            f"</div>"
        )

    @classmethod
    def _make_field_html(cls, field: str, layout: str) -> str:
        label = cls._FIELD_LABELS.get(field, field)
        if layout == "grid2":
            if field in cls._FIELD_SELECTS:
                btns = "".join(
                    f"<button class='li-sel-btn' data-value='{v}'>{a}</button>"
                    for v, _, a in cls._FIELD_SELECTS[field]
                )
                inner = f"<div class='li-selector' data-field='{field}'>{btns}</div>"
            else:
                attrs = cls._FIELD_NUM_ATTRS.get(field, "min='0'")
                inner = f"<input type='number' class='li-input' data-field='{field}' {attrs} step='1'>"
            return f"<div class='li-col'><span class='li-col-label'>{label}</span>{inner}</div>"
        # inline layout (kept for future use)
        if field in cls._FIELD_SELECTS:
            opts = "".join(f"<option value='{v}'>{t}</option>" for v, t, _ in cls._FIELD_SELECTS[field])
            return f"<select class='li-select' data-field='{field}'>{opts}</select>"
        attrs = cls._FIELD_NUM_ATTRS.get(field, "min='0'")
        return f"<span class='li-field-label'>{label}</span><input type='number' class='li-input li-input-sm' data-field='{field}' {attrs} step='1'>"

    def preprocess(self, payload):
        if payload is None:
            return nm.levels.Levels()
        try:
            state = json.loads(str(payload))
            return self._levels_from_state(state)
        except (json.JSONDecodeError, ValueError, TypeError):
            return nm.levels.Levels()

    def postprocess(self, value):
        if isinstance(value, str):
            return value
        levels = value if isinstance(value, nm.levels.Levels) else nm.levels.Levels()
        return json.dumps(self._build_state(levels))
    from typing import Callable, Literal, Sequence, Any, TYPE_CHECKING
    from gradio.blocks import Block
    if TYPE_CHECKING:
        from gradio.components import Timer
        from gradio.components.base import Component