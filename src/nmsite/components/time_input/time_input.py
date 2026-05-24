__all__ = ["TimeInput"]

import json
import datetime as dt
import typing as t
from pathlib import Path

import gradio as gr

from nmsite.interface import _merge_elem_classes

_CSS = (Path(__file__).parent / "style.css").read_text()
_JS  = (Path(__file__).parent / "script.js").read_text()

# Valid segment keys per mode
_MODE_KEYS: dict[str, list[str]] = {
    "duration":   ["years", "days", "hours", "minutes", "seconds"],
    "clock_time": ["hours", "minutes", "seconds"],
    "datetime":   ["year", "month", "day", "hours", "minutes", "seconds"],
}

# Default display formats per mode
_MODE_FORMATS: dict[str, list[str]] = {
    "duration":   ["HH:MM:SS", "AJHMS"],
    "clock_time": ["HH:MM:SS"],
    "datetime":   ["DD/MM/YYYY HH:MM:SS"],
}

# Valid quick-fill keys per mode
_MODE_FILLS: dict[str, set[str]] = {
    "duration":   {"now"},
    "clock_time": {"now", "current_time"},
    "datetime":   {"now", "today", "current_time"},
}

_FILL_LABELS: dict[str, str] = {
    "now":          "Maintenant",
    "today":        "Aujourd'hui",
    "current_time": "Heure actuelle",
}


class TimeInput(gr.HTML):
    """Scrollable time/duration/datetime picker as a gr.HTML subclass.

    Displays segments (hours, minutes, seconds, etc.) as individually scrollable
    spans inside a text-field-like container. Supports AJHMS and HH:MM:SS display
    formats for durations, copy/paste, touch drag, and optional quick-fill buttons.

    Args:
        mode: "duration" → timedelta; "clock_time" → dt.time; "datetime" → dt.datetime.
        segments: Which segment fields to show (subset of the mode's keys). None = all.
        formats: Display formats the user can toggle between. None = all valid for mode.
        quick_fills: Quick-fill buttons to show ("now", "today", "current_time").
        value: Initial Python value. Type must match the mode.
        defaults: Fixed values for hidden segments (not in ``segments``). Dict of key→int.
            These are included in every Python value returned, invisible to the user.
        label: Optional label text shown above the field.
        interactive: When False the component is read-only (result field styling).
    """

    def __init__(
        self,
        mode: t.Literal["duration", "clock_time", "datetime"] = "duration",
        segments: list[str] | None = None,
        formats: list[str] | None = None,
        quick_fills: list[str] | None = None,
        value: dt.timedelta | dt.time | dt.datetime | None = None,
        defaults: dict[str, int] | None = None,
        label: str | None = None,
        interactive: bool = True,
        **kwargs,
    ):
        if mode not in _MODE_KEYS:
            raise ValueError(f"mode must be one of {list(_MODE_KEYS)}, got {mode!r}")

        all_keys = _MODE_KEYS[mode]

        # Segments to display
        seg_keys = segments if segments is not None else all_keys
        for k in seg_keys:
            if k not in all_keys:
                raise ValueError(f"Segment {k!r} not valid for mode {mode!r}. Valid: {all_keys}")

        # Display formats
        valid_formats = _MODE_FORMATS[mode]
        fmt_list = formats if formats is not None else valid_formats
        for f in fmt_list:
            if f not in valid_formats:
                raise ValueError(f"Format {f!r} not valid for mode {mode!r}. Valid: {valid_formats}")

        # Quick-fill buttons (silently drop invalid ones)
        valid_fills = _MODE_FILLS[mode]
        fill_list = [f for f in (quick_fills or []) if f in valid_fills]

        # Hidden segment defaults
        hidden_defaults = dict(defaults or {})

        self._mode = mode
        self._seg_keys = seg_keys
        self._hidden_defaults = hidden_defaults

        _merge_elem_classes(kwargs, "ti-outer")
        kwargs.setdefault("container", False)
        kwargs.setdefault("show_label", False)
        kwargs.setdefault("apply_default_css", False)
        kwargs.setdefault("padding", False)

        initial_json = self.postprocess(value)

        super().__init__(
            value=initial_json,
            html_template=self._build_template(
                mode, seg_keys, fmt_list, fill_list, hidden_defaults, interactive, label
            ),
            css_template=_CSS,
            js_on_load=_JS,
            **kwargs,
        )

    @staticmethod
    def _build_template(
        mode: str,
        seg_keys: list[str],
        fmt_list: list[str],
        fill_list: list[str],
        hidden_defaults: dict[str, int],
        interactive: bool,
        label: str | None,
    ) -> str:
        label_html = f'<span class="ti-label">{label}</span>' if label else ""

        # Format toggle button (only if >1 format)
        toggle_html = (
            f'<button class="ti-btn ti-toggle" type="button">{fmt_list[0]}</button>'
            if len(fmt_list) > 1 else ""
        )

        # Copy button (always present)
        copy_html = '<button class="ti-btn ti-copy" type="button" title="Copier">⎘</button>'

        # Clear/reset button (always present)
        clear_html = '<button class="ti-btn ti-clear" type="button" title="Réinitialiser">✕</button>'

        # Quick-fill pills
        pills_html = "".join(
            f'<button class="ti-pill" data-fill="{f}" type="button">{_FILL_LABELS[f]}</button>'
            for f in fill_list
        )

        btns_html = f'<div class="ti-btns">{pills_html}{toggle_html}{clear_html}{copy_html}</div>'

        return (
            f'<div class="ti-widget"'
            f' data-mode="{mode}"'
            f' data-segments=\'{json.dumps(seg_keys)}\''
            f' data-formats=\'{json.dumps(fmt_list)}\''
            f' data-quick-fills=\'{json.dumps(fill_list)}\''
            f' data-interactive="{str(interactive).lower()}"'
            f' data-hidden-defaults=\'{json.dumps(hidden_defaults)}\'>'
            f'{label_html}'
            f'<div class="ti-field">'
            f'<div class="ti-field-inner"></div>'
            f'{btns_html}'
            f'</div>'
            f'</div>'
        )

    # --- preprocess: JS state dict → Python type ---

    def preprocess(self, payload) -> dt.timedelta | dt.time | dt.datetime | None:
        if payload is None:
            return None
        try:
            s = json.loads(str(payload)) if isinstance(payload, str) else payload
        except (json.JSONDecodeError, TypeError):
            return None

        # Merge hidden defaults
        for k, v in self._hidden_defaults.items():
            if k not in s or s[k] == 0:
                s[k] = v

        try:
            if self._mode == "duration":
                total_seconds = (
                    (s.get("years", 0) * 365 + s.get("days", 0)) * 86400
                    + s.get("hours", 0) * 3600
                    + s.get("minutes", 0) * 60
                    + s.get("seconds", 0)
                )
                return dt.timedelta(seconds=total_seconds)

            if self._mode == "clock_time":
                return dt.time(
                    hour=s.get("hours", 0),
                    minute=s.get("minutes", 0),
                    second=s.get("seconds", 0),
                )

            if self._mode == "datetime":
                return dt.datetime(
                    year=s.get("year", 1970),
                    month=s.get("month", 1),
                    day=s.get("day", 1),
                    hour=s.get("hours", 0),
                    minute=s.get("minutes", 0),
                    second=s.get("seconds", 0),
                )
        except (ValueError, OverflowError):
            return None

        return None

    # --- postprocess: Python type → JS state JSON string ---

    def postprocess(self, value: dt.timedelta | dt.time | dt.datetime | None) -> str:
        s: dict[str, int]

        if value is None:
            s = self._empty_state()
        elif self._mode == "duration" and isinstance(value, dt.timedelta):
            total_seconds = int(value.total_seconds())
            years, rem = divmod(total_seconds, 365 * 86400)
            days, rem = divmod(rem, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            s = {"years": years, "days": days, "hours": hours, "minutes": minutes, "seconds": seconds}
        elif self._mode == "clock_time" and isinstance(value, dt.time):
            s = {"hours": value.hour, "minutes": value.minute, "seconds": value.second}
        elif self._mode == "datetime" and isinstance(value, dt.datetime):
            s = {
                "year": value.year, "month": value.month, "day": value.day,
                "hours": value.hour, "minutes": value.minute, "seconds": value.second,
            }
        else:
            s = self._empty_state()

        # Merge hidden defaults for hidden segments
        for k, v in self._hidden_defaults.items():
            s.setdefault(k, v)

        return json.dumps(s)

    def _empty_state(self) -> dict[str, int]:
        if self._mode == "duration":
            s = {"years": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
        elif self._mode == "clock_time":
            s = {"hours": 0, "minutes": 0, "seconds": 0}
        else:
            s = {"year": 1970, "month": 1, "day": 1, "hours": 0, "minutes": 0, "seconds": 0}
        for k, v in self._hidden_defaults.items():
            s[k] = v
        return s
