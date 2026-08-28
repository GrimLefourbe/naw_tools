import functools
import gradio as gr
import pandas as pd
import datetime as dt
import typing as t
from dataclasses import dataclass
import nawminator as nm

from nmsite.config import Config
from nmsite.tabs.settings import Settings
from nmsite.components import SegmentedControl, TimeInput


class DureesCore:
    """Mode-agnostic pure *time computation* shared by all three mode specs
    (_legacy_spec/_hybrid_spec/_experimental_spec) via the Durees engine.
    Every method here works on native dt.time/dt.timedelta values — no
    string parsing/formatting. A field that's a plain gr.Textbox in some
    mode (Legacy, Hybrid's old fields) is a string only in that mode's own
    UI layer; converting to/from that string is that spec's job (see
    _parse_canonical/_apply_time_defaults_str), not DureesCore's."""

    TARGETS = ["VA", "Arrivée", "Départ"]

    @staticmethod
    def parse_time(s: str) -> dt.time | None:
        if not s or not s.strip():
            return None
        try:
            return dt.datetime.strptime(s.strip(), "%H:%M:%S").time()
        except ValueError:
            return None

    @staticmethod
    def times_to_secs(start: dt.time | None, arrival: dt.time | None) -> float | None:
        if start is None or arrival is None:
            return None
        secs_start = start.hour * 3600 + start.minute * 60 + start.second
        secs_arrival = arrival.hour * 3600 + arrival.minute * 60 + arrival.second
        secs = secs_arrival - secs_start
        return secs + 86400 if secs < 0 else secs

    @staticmethod
    def apply_time_defaults(target, start: dt.time | None, arrival: dt.time | None):
        if target == "Arrivée" and start is None:
            start = dt.time(0, 0, 0)
        elif target == "Départ" and arrival is None:
            arrival = dt.time(0, 0, 0)
        return start, arrival

    @staticmethod
    def shift_time(t: dt.time, secs: float) -> dt.time:
        base = dt.datetime(2000, 1, 1, t.hour, t.minute, t.second)
        return (base + dt.timedelta(seconds=secs)).time()

    @staticmethod
    def compute(target, x1, y1, x2, y2, va, duration: dt.timedelta, start: dt.time | None, arrival: dt.time | None):
        if target == "VA":
            secs = DureesCore.times_to_secs(start, arrival)
            if secs is None:
                secs = duration.total_seconds()
            base_d = nm.formulas.duree_attaque(x1, y1, x2, y2)
            new_va = nm.formulas.from_va(secs / base_d)
            new_duration = dt.timedelta(seconds=secs)
            return new_va, new_duration, start, arrival

        anchor = start if target == "Arrivée" else arrival
        if anchor is None:
            return va, duration, start, arrival
        secs = nm.formulas.duree_attaque(x1, y1, x2, y2, va)
        new_duration = dt.timedelta(seconds=secs)
        if target == "Arrivée":
            return va, new_duration, start, DureesCore.shift_time(anchor, secs)
        else:  # "Départ" — TARGETS only has these three, "VA" already returned above
            return va, new_duration, DureesCore.shift_time(anchor, -secs), arrival

    @staticmethod
    def duration_str_to_td(s: str) -> dt.timedelta:
        return nm.utils.parse_ajhms(s)

    @staticmethod
    def duration_td_to_str(td: dt.timedelta | None) -> str:
        return nm.utils.timedelta_to_ajhms(td) if td is not None else "0S"

    @staticmethod
    def time_obj_to_str(t: dt.time | None) -> str:
        return t.strftime("%H:%M:%S") if t is not None else ""

    @staticmethod
    def parse_xy(key: str | None) -> tuple[int, ...]:
        """Parse a player-dropdown value ("x:y") back into coordinates."""
        return (0, 0) if key is None else tuple(int(v) for v in key.split(":"))

    @staticmethod
    def player_choices(data: pd.DataFrame):
        """(label, "x:y") choices for the src/tgt player dropdowns, built
        from the loaded player DataFrame — identical across all three modes,
        so registered once here instead of redefined per class."""
        player_names = sorted(
            (f"{player}: {colo}[{x}:{y}]", f"{x}:{y}")
            for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
        )
        update = gr.update(visible=True, choices=player_names)
        return update, update

    # Interactivity toggles for the plain 4-field layout (va, duration, start,
    # arrival) — shared by Legacy and Experimental, which both use exactly
    # these four fields. Hardcoded literal returns rather than a table lookup:
    # SegmentedControl.on_choice(..., js=True)'s Python->JS transpiler needs
    # zero-arg statics returning literal gr.update(...) values, not a dict
    # indexed at call time (see project_segmented_control_events memory).
    # _hybrid_spec keeps its own 7-field versions since its dual-mount layout
    # isn't this shape.
    @staticmethod
    def _interactivity_to_va():
        return (
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
        )

    @staticmethod
    def _interactivity_to_arrivee():
        return (
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
        )

    @staticmethod
    def _interactivity_to_depart():
        return (
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
        )

    @staticmethod
    def dispatch_interactivity(fns: tuple, target: str):
        """Generic version of interactivity_for: takes the mode's own
        3-tuple of interactivity functions instead of assuming DureesCore's
        own 4-field ones, so it works for Hybrid's 7-field versions too."""
        return dict(zip(DureesCore.TARGETS, fns))[target]()


def _build_coord_row() -> tuple[gr.Dropdown, gr.Number, gr.Number, SegmentedControl, gr.Dropdown, gr.Number, gr.Number]:
    """Source / target-selector / Cible layout — byte-for-byte identical
    across all three modes, so built once here instead of copy-pasted into
    each class's _set_layout."""
    args: dict[str, t.Any] = {"container": False}
    with gr.Row(equal_height=True):
        with gr.Column(min_width=100), gr.Group():
            gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>")
            src_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_src_player")
            with gr.Row():
                gr.Text("x", min_width=30, **args)
                from_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_x", **args)
            with gr.Row():
                gr.Text("y", min_width=30, **args)
                from_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_y", **args)

        with gr.Column(scale=0, min_width=90):
            target_sel = SegmentedControl(
                choices=DureesCore.TARGETS,
                value="Arrivée",
                elem_id="durees_target",
                container=False,
            )

        with gr.Column(min_width=100), gr.Group():
            gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Cible</div>")
            tgt_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_tgt_player")
            with gr.Row():
                gr.Text("x", min_width=30, **args)
                to_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_x", **args)
            with gr.Row():
                gr.Text("y", min_width=30, **args)
                to_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_y", **args)

    return src_player_select, from_x, from_y, target_sel, tgt_player_select, to_x, to_y


def _skip_output(compute: t.Callable, index: int, *args):
    """Wrap a compute function so its output at `index` becomes gr.skip()
    instead of whatever it actually computed. This is the shared echo-guard
    mechanism for EditableField.skip_index (see Durees._configure_triggers)
    — kept out of every mode's own compute function since it's pure Gradio
    UI plumbing, not time computation: when a chain was triggered by editing
    the field at `index` directly, that field's own recomputed value would
    just echo back what's already there, and a custom component (TimeInput)
    can't tell that echo apart from a genuine external change — it reacts by
    exiting edit mode and dropping focus, which would happen after every
    single wheel tick or arrow press otherwise."""
    result = compute(*args)
    return tuple(gr.skip() if i == index else v for i, v in enumerate(result))


def durees_tab(settings: Settings, tab: gr.Tab, config: Config) -> "Durees":
    spec_builders = {
        "legacy": _legacy_spec,
        "hybrid": _hybrid_spec,
        "experimental": _experimental_spec,
    }
    return Durees(settings, tab, spec_builders[config.time_input_mode])


@dataclass
class EditableField:
    """One user-editable entry point (duration/start/arrival) that should
    re-run compute when edited. Hybrid has two of these per concept (old +
    new); Legacy/Experimental have exactly one each."""

    trigger: t.Callable
    skip_index: int | None
    pre_step: tuple[t.Callable, gr.Component, gr.Component] | None = None


@dataclass
class DureesModeSpec:
    """Everything the Durees engine needs from one mode. value_fields'
    order is the single source of truth for what `compute` must return and
    what interactivity/`.select()` dispatch write to — it's also what
    EditableField.skip_index indexes into. canonical_fields resolves the
    one place value_fields alone is ambiguous: all_inputs needs exactly one
    component per concept to read a current value from, and Hybrid has two
    (old + new) per concept where Legacy/Experimental have one."""

    va_field: gr.Component
    value_fields: list[gr.Component]
    canonical_fields: tuple[gr.Component, gr.Component, gr.Component]
    compute: t.Callable
    apply_time_defaults: t.Callable
    editable_fields: list[EditableField]
    interactivity_fns: tuple[t.Callable, t.Callable, t.Callable]
    needs_select_dispatch: bool
    extra_wiring: t.Callable[["Durees", Settings, gr.Tab], None] | None = None


class Durees:
    """Shared wiring engine for all three Durées modes. Owns the coord row
    and the full trigger/event graph shape; each mode supplies a
    DureesModeSpec (built via `spec_builder`) for everything that varies."""

    def __init__(self, settings: Settings, tab: gr.Tab, spec_builder: t.Callable[[Settings], DureesModeSpec]) -> None:
        # spec_builder, not a pre-built spec: the coord row must render
        # before the va/duration/start/arrival rows (visual order), but both
        # are built by entering gr.Row()/gr.Column() while this Blocks
        # context is active — so build the coord row first, then run the
        # spec builder (which does its own gr.Row() building) immediately
        # after.
        (
            self._src_player_select,
            self._from_x,
            self._from_y,
            self._target_sel,
            self._tgt_player_select,
            self._to_x,
            self._to_y,
        ) = _build_coord_row()
        self._spec = spec_builder(settings)
        self._configure_triggers(settings, tab)

    def _configure_triggers(self, settings: Settings, tab: gr.Tab):
        spec = self._spec

        settings.data_state.change(
            fn=DureesCore.player_choices,
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )

        all_inputs = [
            self._target_sel,
            self._from_x,
            self._from_y,
            self._to_x,
            self._to_y,
            spec.va_field,
            *spec.canonical_fields,
        ]

        self._src_player_select.input(
            DureesCore.parse_xy,
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(fn=spec.compute, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        self._tgt_player_select.input(
            DureesCore.parse_xy,
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(fn=spec.compute, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        gr.on(
            triggers=[
                self._from_x.input,
                self._from_y.input,
                self._to_x.input,
                self._to_y.input,
                spec.va_field.input,
            ],
            fn=spec.compute,
            inputs=all_inputs,
            outputs=spec.value_fields,
            show_progress="hidden",
        )

        for ef in spec.editable_fields:
            chain = ef.trigger
            if ef.pre_step:
                pre_fn, pre_src, pre_dst = ef.pre_step
                chain = chain(fn=pre_fn, inputs=pre_src, outputs=pre_dst, show_progress="hidden").then
            compute_fn = (
                functools.partial(_skip_output, spec.compute, ef.skip_index)
                if ef.skip_index is not None
                else spec.compute
            )
            chain(fn=compute_fn, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        for choice, fn in zip(DureesCore.TARGETS, spec.interactivity_fns):
            self._target_sel.on_choice(choice)(fn, outputs=spec.value_fields, js=True, show_progress="hidden")

        if spec.needs_select_dispatch:
            self._target_sel.select(
                fn=functools.partial(DureesCore.dispatch_interactivity, spec.interactivity_fns),
                inputs=[self._target_sel],
                outputs=spec.value_fields,
                show_progress="hidden",
            )

        _, start, arrival = spec.canonical_fields
        self._target_sel.input(
            fn=spec.apply_time_defaults,
            inputs=[self._target_sel, start, arrival],
            outputs=[start, arrival],
            show_progress="hidden",
        ).then(fn=spec.compute, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        if spec.extra_wiring:
            spec.extra_wiring(self, settings, tab)


def _parse_canonical(
    duration_str: str, start_str: str, arrival_str: str
) -> tuple[dt.timedelta, dt.time | None, dt.time | None]:
    """String -> native conversion for the canonical duration/start/arrival
    fields — shared by Legacy and Hybrid, whose canonical fields are plain
    strings (gr.Textbox). Experimental's TimeInput fields are already
    native and never need this."""
    return (
        DureesCore.duration_str_to_td(duration_str),
        DureesCore.parse_time(start_str),
        DureesCore.parse_time(arrival_str),
    )


def _apply_time_defaults_str(target, start_str: str, arrival_str: str) -> tuple[str, str]:
    """String-boundary adapter for DureesCore.apply_time_defaults — shared
    by Legacy and Hybrid, whose canonical duration/start/arrival fields are
    plain strings (gr.Textbox). Experimental's TimeInput fields are already
    native and pass DureesCore.apply_time_defaults straight through."""
    start_t = DureesCore.parse_time(start_str)
    arrival_t = DureesCore.parse_time(arrival_str)
    new_start_t, new_arrival_t = DureesCore.apply_time_defaults(target, start_t, arrival_t)
    return DureesCore.time_obj_to_str(new_start_t), DureesCore.time_obj_to_str(new_arrival_t)


def _legacy_spec(settings: Settings) -> DureesModeSpec:
    """No TimeInput at all — the pre-TimeInput implementation. Zero
    TimeInput overhead: no dual-mount, no mirror chain, no visibility
    toggling, no extra_wiring."""
    with gr.Row():
        with gr.Column(min_width=200):
            va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
        with gr.Column(min_width=200):
            duration = gr.Text(
                "0s", label="Durée", interactive=False, elem_classes=["result-field"], elem_id="durees_duration"
            )
    with gr.Row():
        with gr.Column(min_width=200):
            start = gr.Textbox(
                value="00:00:00", label="Heure de départ", placeholder="HH:MM:SS", elem_id="durees_start_time"
            )
        with gr.Column(min_width=200):
            arrival = gr.Textbox(
                value="",
                label="Heure d'arrivée",
                placeholder="HH:MM:SS",
                interactive=False,
                elem_classes=["result-field"],
                elem_id="durees_arrival_time",
            )

    def compute_str(target, x1, y1, x2, y2, va, duration_str, start_str, arrival_str):
        duration_td, start_t, arrival_t = _parse_canonical(duration_str, start_str, arrival_str)
        new_va, new_duration_td, new_start_t, new_arrival_t = DureesCore.compute(
            target, x1, y1, x2, y2, va, duration_td, start_t, arrival_t
        )
        return (
            new_va,
            DureesCore.duration_td_to_str(new_duration_td),
            DureesCore.time_obj_to_str(new_start_t),
            DureesCore.time_obj_to_str(new_arrival_t),
        )

    return DureesModeSpec(
        va_field=va,
        value_fields=[va, duration, start, arrival],
        canonical_fields=(duration, start, arrival),
        compute=compute_str,
        apply_time_defaults=_apply_time_defaults_str,
        editable_fields=[
            EditableField(trigger=duration.input, skip_index=None),
            EditableField(trigger=start.input, skip_index=None),
            EditableField(trigger=arrival.input, skip_index=None),
        ],
        interactivity_fns=(
            DureesCore._interactivity_to_va,
            DureesCore._interactivity_to_arrivee,
            DureesCore._interactivity_to_depart,
        ),
        needs_select_dispatch=False,
    )


# Hybrid's interactivity toggles cover 7 fields (va, duration, duration_new,
# start, start_new, arrival, arrival_new) — a different shape from
# DureesCore's 4-field versions, so these stay separate rather than shared.
def _hybrid_interactivity_to_va():
    return (
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
    )


def _hybrid_interactivity_to_arrivee():
    return (
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=False, elem_classes=["result-field"]),
    )


def _hybrid_interactivity_to_depart():
    return (
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=False, elem_classes=["result-field"]),
        gr.update(interactive=True, elem_classes=[]),
        gr.update(interactive=True, elem_classes=[]),
    )


def _hybrid_spec(settings: Settings) -> DureesModeSpec:
    """Dual-mount: both the old plain-text fields and the new TimeInput
    fields exist, paired by visibility, behind the Réglages opt-in toggle."""
    with gr.Row():
        with gr.Column(min_width=200):
            va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
        with gr.Column(min_width=200):
            duration = gr.Text(
                "0s", label="Durée", interactive=False, elem_classes=["result-field"], elem_id="durees_duration"
            )
            duration_new = TimeInput(
                mode="duration",
                label="Durée",
                interactive=False,
                elem_id="durees_duration_new",
                visible=False,
            )
    with gr.Row():
        with gr.Column(min_width=200):
            start = gr.Textbox(
                value="00:00:00", label="Heure de départ", placeholder="HH:MM:SS", elem_id="durees_start_time"
            )
            start_new = TimeInput(
                mode="clock_time",
                segments=["hours", "minutes", "seconds"],
                formats=["HH:MM:SS"],
                label="Heure de départ",
                elem_id="durees_start_time_new",
                visible=False,
            )
        with gr.Column(min_width=200):
            arrival = gr.Textbox(
                value="",
                label="Heure d'arrivée",
                placeholder="HH:MM:SS",
                interactive=False,
                elem_classes=["result-field"],
                elem_id="durees_arrival_time",
            )
            arrival_new = TimeInput(
                mode="clock_time",
                segments=["hours", "minutes", "seconds"],
                formats=["HH:MM:SS"],
                label="Heure d'arrivée",
                interactive=False,
                elem_id="durees_arrival_time_new",
                visible=False,
            )

    def compute_and_mirror(target, x1, y1, x2, y2, va, duration_str, start_str, arrival_str):
        """Run DureesCore.compute (native) once and derive both the old
        (string) fields and their TimeInput (native) siblings from that
        single result — no re-parsing a string this function just formatted.
        The old fields are always written back (echoing a plain gr.Textbox
        back into itself is harmless); the *_new echo-guard is the engine's
        job now (see EditableField.skip_index / _skip_output), not this
        function's — it always returns the real computed native value."""
        duration_td, start_t, arrival_t = _parse_canonical(duration_str, start_str, arrival_str)
        new_va, new_duration_td, new_start_t, new_arrival_t = DureesCore.compute(
            target, x1, y1, x2, y2, va, duration_td, start_t, arrival_t
        )
        return (
            new_va,
            DureesCore.duration_td_to_str(new_duration_td),
            new_duration_td,
            DureesCore.time_obj_to_str(new_start_t),
            new_start_t,
            DureesCore.time_obj_to_str(new_arrival_t),
            new_arrival_t,
        )

    def toggle_visibility(enabled: bool):
        """Show/hide each old/new field pair together."""
        return tuple(gr.update(visible=v) for v in (not enabled, enabled) * 3)

    def extra_wiring(engine: Durees, settings: Settings, tab: gr.Tab):
        # Re-applied on tab.select() (fired every time the user switches into
        # this tab), not on the cross-tab state's own .change() — an update
        # to a field's `visible` prop triggered from another tab's event
        # (e.g. the Réglages checkbox) reliably reveals a hidden field but
        # unreliably re-hides a visible one, silently leaving stale fields
        # on screen. select() runs in this tab's own context instead.
        tab.select(
            fn=toggle_visibility,
            inputs=settings.time_input_enabled_state,
            outputs=[duration, duration_new, start, start_new, arrival, arrival_new],
            show_progress="hidden",
            queue=False,
        )

    value_fields = [va, duration, duration_new, start, start_new, arrival, arrival_new]

    return DureesModeSpec(
        va_field=va,
        value_fields=value_fields,
        canonical_fields=(duration, start, arrival),
        compute=compute_and_mirror,
        apply_time_defaults=_apply_time_defaults_str,
        editable_fields=[
            EditableField(trigger=duration.input, skip_index=None),
            EditableField(trigger=start.input, skip_index=None),
            EditableField(trigger=arrival.input, skip_index=None),
            EditableField(
                trigger=duration_new.input,
                skip_index=value_fields.index(duration_new),
                pre_step=(DureesCore.duration_td_to_str, duration_new, duration),
            ),
            EditableField(
                trigger=start_new.input,
                skip_index=value_fields.index(start_new),
                pre_step=(DureesCore.time_obj_to_str, start_new, start),
            ),
            EditableField(
                trigger=arrival_new.input,
                skip_index=value_fields.index(arrival_new),
                pre_step=(DureesCore.time_obj_to_str, arrival_new, arrival),
            ),
        ],
        interactivity_fns=(
            _hybrid_interactivity_to_va,
            _hybrid_interactivity_to_arrivee,
            _hybrid_interactivity_to_depart,
        ),
        needs_select_dispatch=True,
        extra_wiring=extra_wiring,
    )


def _experimental_spec(settings: Settings) -> DureesModeSpec:
    """TimeInput only — no old plain-text siblings, no mirror chain, no
    visibility toggling. TimeInput's values are already native, so this
    talks to DureesCore.compute/apply_time_defaults directly — no adapter,
    no string boundary to cross at all."""
    with gr.Row():
        with gr.Column(min_width=200):
            va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
        with gr.Column(min_width=200):
            duration = TimeInput(mode="duration", label="Durée", interactive=False, elem_id="durees_duration")
    with gr.Row():
        with gr.Column(min_width=200):
            start = TimeInput(
                mode="clock_time",
                segments=["hours", "minutes", "seconds"],
                formats=["HH:MM:SS"],
                label="Heure de départ",
                elem_id="durees_start_time",
            )
        with gr.Column(min_width=200):
            arrival = TimeInput(
                mode="clock_time",
                segments=["hours", "minutes", "seconds"],
                formats=["HH:MM:SS"],
                label="Heure d'arrivée",
                interactive=False,
                elem_id="durees_arrival_time",
            )

    value_fields = [va, duration, start, arrival]

    return DureesModeSpec(
        va_field=va,
        value_fields=value_fields,
        canonical_fields=(duration, start, arrival),
        compute=DureesCore.compute,
        apply_time_defaults=DureesCore.apply_time_defaults,
        editable_fields=[
            EditableField(trigger=duration.input, skip_index=value_fields.index(duration)),
            EditableField(trigger=start.input, skip_index=value_fields.index(start)),
            EditableField(trigger=arrival.input, skip_index=value_fields.index(arrival)),
        ],
        interactivity_fns=(
            DureesCore._interactivity_to_va,
            DureesCore._interactivity_to_arrivee,
            DureesCore._interactivity_to_depart,
        ),
        needs_select_dispatch=True,
    )
