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
    """Mode-agnostic pure logic shared by DureesLegacy/DureesHybrid/
    DureesExperimental. No component state — every mode calls these the
    exact same way."""

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
    def times_to_secs(start: str, arrival: str) -> float | None:
        t_start = DureesCore.parse_time(start)
        t_arrival = DureesCore.parse_time(arrival)
        if t_start is None or t_arrival is None:
            return None
        secs_start = t_start.hour * 3600 + t_start.minute * 60 + t_start.second
        secs_arrival = t_arrival.hour * 3600 + t_arrival.minute * 60 + t_arrival.second
        secs = secs_arrival - secs_start
        return secs + 86400 if secs < 0 else secs

    @staticmethod
    def apply_time_defaults(target, start, arrival):
        if target == "Arrivée" and not (start and start.strip()):
            start = "00:00:00"
        elif target == "Départ" and not (arrival and arrival.strip()):
            arrival = "00:00:00"
        return start, arrival

    @staticmethod
    def shift_time(t: dt.time, secs: float) -> str:
        base = dt.datetime(2000, 1, 1, t.hour, t.minute, t.second)
        return (base + dt.timedelta(seconds=secs)).time().strftime("%H:%M:%S")

    @staticmethod
    def compute(target, x1, y1, x2, y2, va, duration, start, arrival):
        if target == "VA":
            secs = DureesCore.times_to_secs(start, arrival)
            if secs is None:
                secs = nm.utils.parse_ajhms(duration).total_seconds()
            base_d = nm.formulas.duree_attaque(x1, y1, x2, y2)
            new_va = nm.formulas.from_va(secs / base_d)
            new_duration = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=secs))
            return new_va, new_duration, start, arrival

        anchor_str = start if target == "Arrivée" else arrival
        parsed = DureesCore.parse_time(anchor_str)
        if parsed is None:
            return va, duration, start, arrival
        secs = nm.formulas.duree_attaque(x1, y1, x2, y2, va)
        new_duration = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=secs))
        if target == "Arrivée":
            return va, new_duration, start, DureesCore.shift_time(parsed, secs)
        else:  # "Départ" — TARGETS only has these three, "VA" already returned above
            return va, new_duration, DureesCore.shift_time(parsed, -secs), arrival

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
    # DureesHybrid keeps its own 7-field versions since its dual-mount layout
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


def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    spec_builders = {
        "legacy": _legacy_spec,
        "experimental": _experimental_spec,
    }
    if config.time_input_mode in spec_builders:
        return Durees(settings, tab, spec_builders[config.time_input_mode])
    return DureesHybrid(settings, tab)


@dataclass
class EditableField:
    """One user-editable entry point (duration/start/arrival) that should
    re-run compute when edited. Hybrid has two of these per concept (old +
    new); Legacy/Experimental have exactly one each."""

    trigger: t.Callable
    skip: str | None
    pre_step: tuple[t.Callable, gr.Component, gr.Component] | None = None


@dataclass
class DureesModeSpec:
    """Everything the Durees engine needs from one mode. value_fields'
    order is the single source of truth for what `compute` must return and
    what interactivity/`.select()` dispatch write to. canonical_fields
    resolves the one place value_fields alone is ambiguous: all_inputs
    needs exactly one component per concept to read a current value from,
    and Hybrid has two (old + new) per concept where Legacy/Experimental
    have one."""

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
            compute_fn = functools.partial(spec.compute, skip=ef.skip) if ef.skip else spec.compute
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

    return DureesModeSpec(
        va_field=va,
        value_fields=[va, duration, start, arrival],
        canonical_fields=(duration, start, arrival),
        compute=DureesCore.compute,
        apply_time_defaults=DureesCore.apply_time_defaults,
        editable_fields=[
            EditableField(trigger=duration.input, skip=None),
            EditableField(trigger=start.input, skip=None),
            EditableField(trigger=arrival.input, skip=None),
        ],
        interactivity_fns=(
            DureesCore._interactivity_to_va,
            DureesCore._interactivity_to_arrivee,
            DureesCore._interactivity_to_depart,
        ),
        needs_select_dispatch=False,
    )


class DureesHybrid:
    """Dual-mount: both the old plain-text fields and the new TimeInput
    fields exist, paired by visibility, behind the Réglages opt-in toggle."""

    def __init__(self, settings: Settings, tab: gr.Tab) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings, tab)

    @staticmethod
    def _compute_and_mirror(target, x1, y1, x2, y2, va, duration, start, arrival, skip=None):
        """Run DureesCore.compute and write its result into both the old
        (canonical) fields and their TimeInput siblings in a single server
        round trip — the old fields are always overwritten (echoing a plain
        gr.Textbox back into itself is harmless), but `skip` names the one
        TimeInput sibling ("duration"/"start"/"arrival") to leave untouched:
        when this chain was triggered by editing that very field directly,
        its value already matches what we'd write back, and TimeInput can't
        tell that server echo apart from a genuine external change — its
        `watch('value', ...)` (script.js) reacts to either by exiting edit
        mode and dropping focus, which would happen after every single wheel
        tick or arrow press otherwise."""
        new_va, new_duration, new_start, new_arrival = DureesCore.compute(
            target, x1, y1, x2, y2, va, duration, start, arrival
        )
        return (
            new_va,
            new_duration,
            gr.skip() if skip == "duration" else DureesCore.duration_str_to_td(new_duration),
            new_start,
            gr.skip() if skip == "start" else DureesCore.parse_time(new_start),
            new_arrival,
            gr.skip() if skip == "arrival" else DureesCore.parse_time(new_arrival),
        )

    # Each field below has an old + new (TimeInput) sibling that always share
    # the same interactive/elem_classes state — value_fields interleaves them
    # as (va, duration, duration_new, start, start_new, arrival, arrival_new).
    @staticmethod
    def _toggle_visibility(enabled: bool):
        """Show/hide each old/new field pair together."""
        return tuple(gr.update(visible=v) for v in (not enabled, enabled) * 3)

    @staticmethod
    def _interactivity_to_va():
        return (
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
        )

    @staticmethod
    def _interactivity_to_arrivee():
        return (
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
        )

    @staticmethod
    def _interactivity_to_depart():
        return (
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=False, elem_classes=["result-field"]),
            gr.update(interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
        )

    @classmethod
    def _interactivity_for(cls, target: str):
        return {
            "VA": cls._interactivity_to_va,
            "Arrivée": cls._interactivity_to_arrivee,
            "Départ": cls._interactivity_to_depart,
        }[target]()

    def _set_layout(self, settings: Settings):
        (
            self._src_player_select,
            self._from_x,
            self._from_y,
            self._target_sel,
            self._tgt_player_select,
            self._to_x,
            self._to_y,
        ) = _build_coord_row()

        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
            with gr.Column(min_width=200):
                self._duration = gr.Text(
                    "0s", label="Durée", interactive=False, elem_classes=["result-field"], elem_id="durees_duration"
                )
                self._duration_new = TimeInput(
                    mode="duration",
                    label="Durée",
                    interactive=False,
                    elem_id="durees_duration_new",
                    visible=False,
                )
        with gr.Row():
            with gr.Column(min_width=200):
                self._start_time = gr.Textbox(
                    value="00:00:00", label="Heure de départ", placeholder="HH:MM:SS", elem_id="durees_start_time"
                )
                self._start_time_new = TimeInput(
                    mode="clock_time",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    label="Heure de départ",
                    elem_id="durees_start_time_new",
                    visible=False,
                )
            with gr.Column(min_width=200):
                self._arrival_time = gr.Textbox(
                    value="",
                    label="Heure d'arrivée",
                    placeholder="HH:MM:SS",
                    interactive=False,
                    elem_classes=["result-field"],
                    elem_id="durees_arrival_time",
                )
                self._arrival_time_new = TimeInput(
                    mode="clock_time",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    label="Heure d'arrivée",
                    interactive=False,
                    elem_id="durees_arrival_time_new",
                    visible=False,
                )

    def _configure_triggers(self, settings: Settings, tab: gr.Tab):
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
            self._va,
            self._duration,
            self._start_time,
            self._arrival_time,
        ]
        value_fields = [
            self._va,
            self._duration,
            self._duration_new,
            self._start_time,
            self._start_time_new,
            self._arrival_time,
            self._arrival_time_new,
        ]

        visibility_outputs = [
            self._duration,
            self._duration_new,
            self._start_time,
            self._start_time_new,
            self._arrival_time,
            self._arrival_time_new,
        ]

        self._src_player_select.input(
            DureesCore.parse_xy,
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(fn=self._compute_and_mirror, inputs=all_inputs, outputs=value_fields, show_progress="hidden")

        self._tgt_player_select.input(
            DureesCore.parse_xy,
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(fn=self._compute_and_mirror, inputs=all_inputs, outputs=value_fields, show_progress="hidden")

        # js=True gives instant client-side feedback for the old (plain
        # Gradio) fields, but its transpiled JS doesn't know how to toggle
        # interactive state on a custom gr.HTML component — TimeInput's own
        # reactive interactive-prop handling (proven by the Settings-tab
        # demo's checkbox) only fires on a real server round trip. Trying a
        # second listener on the same select_<choice> event didn't work (it
        # never fired — the per-choice event only supports one listener), so
        # the generic select event carries a second, non-js pass instead,
        # to apply the same interactivity to the *_new fields too.
        self._target_sel.on_choice("VA")(
            self._interactivity_to_va, outputs=value_fields, js=True, show_progress="hidden"
        )
        self._target_sel.on_choice("Arrivée")(
            self._interactivity_to_arrivee, outputs=value_fields, js=True, show_progress="hidden"
        )
        self._target_sel.on_choice("Départ")(
            self._interactivity_to_depart, outputs=value_fields, js=True, show_progress="hidden"
        )

        self._target_sel.select(
            fn=self._interactivity_for,
            inputs=[self._target_sel],
            outputs=value_fields,
            show_progress="hidden",
        )

        self._target_sel.input(
            fn=DureesCore.apply_time_defaults,
            inputs=[self._target_sel, self._start_time, self._arrival_time],
            outputs=[self._start_time, self._arrival_time],
            show_progress="hidden",
        ).then(fn=self._compute_and_mirror, inputs=all_inputs, outputs=value_fields, show_progress="hidden")

        gr.on(
            triggers=[
                self._from_x.input,
                self._from_y.input,
                self._to_x.input,
                self._to_y.input,
                self._va.input,
                self._duration.input,
                self._start_time.input,
                self._arrival_time.input,
            ],
            fn=self._compute_and_mirror,
            inputs=all_inputs,
            outputs=value_fields,
            show_progress="hidden",
        )

        # Opt-in TimeInput: editing a new field syncs its value into the old
        # (canonical) field first, then runs the same compute+mirror pass as
        # editing the old field directly would — skip= keeps the field just
        # edited from being echoed back into itself (see _compute_and_mirror).
        self._start_time_new.input(
            fn=DureesCore.time_obj_to_str,
            inputs=self._start_time_new,
            outputs=self._start_time,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._compute_and_mirror, skip="start"),
            inputs=all_inputs,
            outputs=value_fields,
            show_progress="hidden",
        )

        self._arrival_time_new.input(
            fn=DureesCore.time_obj_to_str,
            inputs=self._arrival_time_new,
            outputs=self._arrival_time,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._compute_and_mirror, skip="arrival"),
            inputs=all_inputs,
            outputs=value_fields,
            show_progress="hidden",
        )

        self._duration_new.input(
            fn=DureesCore.duration_td_to_str,
            inputs=self._duration_new,
            outputs=self._duration,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._compute_and_mirror, skip="duration"),
            inputs=all_inputs,
            outputs=value_fields,
            show_progress="hidden",
        )

        # Re-applied on tab.select() (fired every time the user switches into
        # this tab), not on the cross-tab state's own .change() — an update
        # to a field's `visible` prop triggered from another tab's event
        # (e.g. the Réglages checkbox) reliably reveals a hidden field but
        # unreliably re-hides a visible one, silently leaving stale fields
        # on screen. select() runs in this tab's own context instead.
        tab.select(
            fn=self._toggle_visibility,
            inputs=settings.time_input_enabled_state,
            outputs=visibility_outputs,
            show_progress="hidden",
            queue=False,
        )


def _experimental_spec(settings: Settings) -> DureesModeSpec:
    """TimeInput only — no old plain-text siblings, no mirror chain, no
    visibility toggling. compute/apply_time_defaults wrap DureesCore's
    string-based core with a native<->str adapter."""
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

    def compute_native(target, x1, y1, x2, y2, va, duration_td, start_time, arrival_time, skip=None):
        duration_str = DureesCore.duration_td_to_str(duration_td)
        start_str = DureesCore.time_obj_to_str(start_time)
        arrival_str = DureesCore.time_obj_to_str(arrival_time)
        new_va, new_duration_str, new_start_str, new_arrival_str = DureesCore.compute(
            target, x1, y1, x2, y2, va, duration_str, start_str, arrival_str
        )
        return (
            new_va,
            gr.skip() if skip == "duration" else DureesCore.duration_str_to_td(new_duration_str),
            gr.skip() if skip == "start" else DureesCore.parse_time(new_start_str),
            gr.skip() if skip == "arrival" else DureesCore.parse_time(new_arrival_str),
        )

    def apply_time_defaults_native(target, start_time, arrival_time):
        start_str = DureesCore.time_obj_to_str(start_time)
        arrival_str = DureesCore.time_obj_to_str(arrival_time)
        new_start_str, new_arrival_str = DureesCore.apply_time_defaults(target, start_str, arrival_str)
        return DureesCore.parse_time(new_start_str), DureesCore.parse_time(new_arrival_str)

    return DureesModeSpec(
        va_field=va,
        value_fields=[va, duration, start, arrival],
        canonical_fields=(duration, start, arrival),
        compute=compute_native,
        apply_time_defaults=apply_time_defaults_native,
        editable_fields=[
            EditableField(trigger=duration.input, skip="duration"),
            EditableField(trigger=start.input, skip="start"),
            EditableField(trigger=arrival.input, skip="arrival"),
        ],
        interactivity_fns=(
            DureesCore._interactivity_to_va,
            DureesCore._interactivity_to_arrivee,
            DureesCore._interactivity_to_depart,
        ),
        needs_select_dispatch=True,
    )
