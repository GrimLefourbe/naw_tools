import functools
import gradio as gr
import pandas as pd
import datetime as dt
import typing as t
import nawminator as nm

from nmsite.config import Config
from nmsite.tabs.settings import Settings
from nmsite.components import SegmentedControl, TimeInput


class DureesCore:
    """Mode-agnostic pure logic shared by DureesLegacy/DureesHybrid/
    DureesExperimental. No Gradio components, no instance state — every
    mode calls these the exact same way."""

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
        if target == "Départ":
            return va, new_duration, DureesCore.shift_time(parsed, -secs), arrival
        return va, duration, start, arrival

    @staticmethod
    def duration_str_to_td(s: str) -> dt.timedelta:
        return nm.utils.parse_ajhms(s)

    @staticmethod
    def duration_td_to_str(td: dt.timedelta | None) -> str:
        return nm.utils.timedelta_to_ajhms(td) if td is not None else "0S"

    @staticmethod
    def time_obj_to_str(t: dt.time | None) -> str:
        return t.strftime("%H:%M:%S") if t is not None else ""


def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    mode_classes = {
        "legacy": DureesLegacy,
        "hybrid": DureesHybrid,
        "experimental": DureesExperimental,
    }
    return mode_classes[config.time_input_mode](settings, tab)


class DureesLegacy:
    """No TimeInput at all — the pre-TimeInput implementation, ported over
    DureesCore. Zero TimeInput overhead: no dual-mount, no mirror chain, no
    visibility toggling, no tab.select() handler."""

    def __init__(self, settings: Settings, tab: gr.Tab) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings)

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

    def _set_layout(self, settings: Settings):
        self._target_state = gr.State("Arrivée")
        args: dict[str, t.Any] = {"container": False}
        with gr.Row(equal_height=True):
            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>")
                self._src_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_src_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._from_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._from_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_y", **args)

            with gr.Column(scale=0, min_width=90):
                self._target_sel = SegmentedControl(
                    choices=DureesCore.TARGETS,
                    value="Arrivée",
                    elem_id="durees_target",
                    container=False,
                )

            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Cible</div>")
                self._tgt_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_tgt_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._to_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._to_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_y", **args)

        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
            with gr.Column(min_width=200):
                self._duration = gr.Text(
                    "0s", label="Durée", interactive=False, elem_classes=["result-field"], elem_id="durees_duration"
                )
        with gr.Row():
            with gr.Column(min_width=200):
                self._start_time = gr.Textbox(
                    value="00:00:00", label="Heure de départ", placeholder="HH:MM:SS", elem_id="durees_start_time"
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

    def _configure_triggers(self, settings: Settings):
        @settings.data_state.change(
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )
        def get_colo_names(data: pd.DataFrame):
            player_names = sorted(
                (f"{player}: {colo}[{x}:{y}]", f"{x}:{y}")
                for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
            )
            update = gr.update(visible=True, choices=player_names)
            return update, update

        all_inputs = [
            self._target_state,
            self._from_x,
            self._from_y,
            self._to_x,
            self._to_y,
            self._va,
            self._duration,
            self._start_time,
            self._arrival_time,
        ]
        all_outputs = [self._va, self._duration, self._start_time, self._arrival_time]

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(fn=DureesCore.compute, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(fn=DureesCore.compute, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

        value_fields = [self._va, self._duration, self._start_time, self._arrival_time]

        self._target_sel.on_choice("VA")(
            self._interactivity_to_va, outputs=value_fields, js=True, show_progress="hidden"
        )
        self._target_sel.on_choice("Arrivée")(
            self._interactivity_to_arrivee, outputs=value_fields, js=True, show_progress="hidden"
        )
        self._target_sel.on_choice("Départ")(
            self._interactivity_to_depart, outputs=value_fields, js=True, show_progress="hidden"
        )

        self._target_sel.input(
            fn=lambda target: target,
            inputs=[self._target_sel],
            outputs=[self._target_state],
            show_progress="hidden",
        ).then(
            fn=DureesCore.apply_time_defaults,
            inputs=[self._target_state, self._start_time, self._arrival_time],
            outputs=[self._start_time, self._arrival_time],
            show_progress="hidden",
        ).then(fn=DureesCore.compute, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

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
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )


class DureesHybrid:
    """Dual-mount: both the old plain-text fields and the new TimeInput
    fields exist, paired by visibility, behind the Réglages opt-in toggle."""

    def __init__(self, settings: Settings, tab: gr.Tab) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings, tab)

    @staticmethod
    def _mirror_to_new(duration: str, start: str, arrival: str, skip: str | None = None):
        """Snapshot the old (canonical) fields into the new TimeInput siblings —
        chained after every compute call so the hidden pair stays truthful
        whenever the toggle is flipped back on.

        `skip` names the one new field ("duration"/"start"/"arrival") to leave
        untouched: when this chain was triggered by editing that very field
        directly, its value already matches what we'd mirror back (compute
        only ever reads the field currently being edited as an anchor here, it
        never rewrites it — see the *_new.input() handlers below). Re-sending it
        anyway round-trips to the server and back as a value update TimeInput
        can't tell apart from a genuine external change, so it reacts the same
        way it would to someone else changing the field: exits edit mode and
        drops focus (see script.js's `watch('value', ...)`) — after every
        single wheel tick or arrow press, kicking the user out of the field
        they're mid-edit on.
        """
        return (
            gr.skip() if skip == "duration" else DureesCore.duration_str_to_td(duration),
            gr.skip() if skip == "start" else DureesCore.parse_time(start),
            gr.skip() if skip == "arrival" else DureesCore.parse_time(arrival),
        )

    # Each field below has an old + new (TimeInput) sibling that always share
    # the same interactive/elem_classes state — value_fields interleaves them
    # as (va, duration, duration_new, start, start_new, arrival, arrival_new).
    @staticmethod
    def _toggle_visibility(enabled: bool):
        """Show/hide each old/new field pair together."""
        return (
            gr.update(visible=not enabled),
            gr.update(visible=enabled),
            gr.update(visible=not enabled),
            gr.update(visible=enabled),
            gr.update(visible=not enabled),
            gr.update(visible=enabled),
        )

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
        self._target_state = gr.State("Arrivée")
        args: dict[str, t.Any] = {"container": False}
        with gr.Row(equal_height=True):
            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>")
                self._src_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_src_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._from_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._from_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_y", **args)

            with gr.Column(scale=0, min_width=90):
                self._target_sel = SegmentedControl(
                    choices=DureesCore.TARGETS,
                    value="Arrivée",
                    elem_id="durees_target",
                    container=False,
                )

            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Cible</div>")
                self._tgt_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_tgt_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._to_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._to_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_y", **args)

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
        @settings.data_state.change(
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )
        def get_colo_names(data: pd.DataFrame):
            player_names = sorted(
                (f"{player}: {colo}[{x}:{y}]", f"{x}:{y}")
                for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
            )
            update = gr.update(visible=True, choices=player_names)
            return update, update

        all_inputs = [
            self._target_state,
            self._from_x,
            self._from_y,
            self._to_x,
            self._to_y,
            self._va,
            self._duration,
            self._start_time,
            self._arrival_time,
        ]
        all_outputs = [self._va, self._duration, self._start_time, self._arrival_time]
        new_fields = [self._duration_new, self._start_time_new, self._arrival_time_new]

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=self._mirror_to_new,
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=self._mirror_to_new,
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

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

        # js=True gives instant client-side feedback for the old (plain
        # Gradio) fields, but its transpiled JS doesn't know how to toggle
        # interactive state on a custom gr.HTML component — TimeInput's own
        # reactive interactive-prop handling (proven by the Settings-tab
        # demo's checkbox) only fires on a real server round trip. Trying a
        # second listener on the same select_<choice> event didn't work (it
        # never fired — the per-choice event only supports one listener), so
        # the generic `select` event carries a second, non-js pass instead,
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
            fn=lambda target: target,
            inputs=[self._target_sel],
            outputs=[self._target_state],
            show_progress="hidden",
        ).then(
            fn=DureesCore.apply_time_defaults,
            inputs=[self._target_state, self._start_time, self._arrival_time],
            outputs=[self._start_time, self._arrival_time],
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=self._mirror_to_new,
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

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
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=self._mirror_to_new,
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

        # Opt-in TimeInput: editing a new field syncs its value into the old
        # (canonical) field first, then runs the same _compute/_mirror chain
        # as editing the old field directly would.
        self._start_time_new.input(
            fn=DureesCore.time_obj_to_str,
            inputs=self._start_time_new,
            outputs=self._start_time,
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._mirror_to_new, skip="start"),
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

        self._arrival_time_new.input(
            fn=DureesCore.time_obj_to_str,
            inputs=self._arrival_time_new,
            outputs=self._arrival_time,
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._mirror_to_new, skip="arrival"),
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
            show_progress="hidden",
        )

        self._duration_new.input(
            fn=DureesCore.duration_td_to_str,
            inputs=self._duration_new,
            outputs=self._duration,
            show_progress="hidden",
        ).then(
            fn=DureesCore.compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        ).then(
            fn=functools.partial(self._mirror_to_new, skip="duration"),
            inputs=[self._duration, self._start_time, self._arrival_time],
            outputs=new_fields,
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


class DureesExperimental:
    """TimeInput only — no old plain-text siblings, no mirror chain, no
    visibility toggling. Each duration/start/arrival field talks to
    DureesCore.compute through a small native<->str adapter that also
    guards against echoing a field's own recomputed value back into itself
    (see _compute_native's `skip` — same principle as DureesHybrid's
    _mirror_to_new skip=, applied directly to compute's own outputs since
    there's no separate mirror step here)."""

    def __init__(self, settings: Settings, tab: gr.Tab) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings)

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

    @classmethod
    def _interactivity_for(cls, target: str):
        return {
            "VA": cls._interactivity_to_va,
            "Arrivée": cls._interactivity_to_arrivee,
            "Départ": cls._interactivity_to_depart,
        }[target]()

    def _set_layout(self, settings: Settings):
        self._target_state = gr.State("Arrivée")
        args: dict[str, t.Any] = {"container": False}
        with gr.Row(equal_height=True):
            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>")
                self._src_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_src_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._from_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._from_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_from_y", **args)

            with gr.Column(scale=0, min_width=90):
                self._target_sel = SegmentedControl(
                    choices=DureesCore.TARGETS,
                    value="Arrivée",
                    elem_id="durees_target",
                    container=False,
                )

            with gr.Column(min_width=100), gr.Group():
                gr.Markdown("<div style='text-align:center; font-weight:bold; font-size:18px;'>Cible</div>")
                self._tgt_player_select = gr.Dropdown(container=False, visible=False, elem_id="durees_tgt_player")
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._to_x = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_x", **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._to_y = gr.Number(value=0, scale=0, min_width=70, elem_id="durees_to_y", **args)

        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque", elem_id="durees_va")
            with gr.Column(min_width=200):
                self._duration = TimeInput(
                    mode="duration",
                    label="Durée",
                    interactive=False,
                    elem_id="durees_duration",
                )
        with gr.Row():
            with gr.Column(min_width=200):
                self._start_time = TimeInput(
                    mode="clock_time",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    label="Heure de départ",
                    elem_id="durees_start_time",
                )
            with gr.Column(min_width=200):
                self._arrival_time = TimeInput(
                    mode="clock_time",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    label="Heure d'arrivée",
                    interactive=False,
                    elem_id="durees_arrival_time",
                )

    @staticmethod
    def _compute_native(target, x1, y1, x2, y2, va, duration_td, start_time, arrival_time, skip=None):
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

    @staticmethod
    def _apply_time_defaults_native(target, start_time, arrival_time):
        start_str = DureesCore.time_obj_to_str(start_time)
        arrival_str = DureesCore.time_obj_to_str(arrival_time)
        new_start_str, new_arrival_str = DureesCore.apply_time_defaults(target, start_str, arrival_str)
        return DureesCore.parse_time(new_start_str), DureesCore.parse_time(new_arrival_str)

    def _configure_triggers(self, settings: Settings):
        @settings.data_state.change(
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )
        def get_colo_names(data: pd.DataFrame):
            player_names = sorted(
                (f"{player}: {colo}[{x}:{y}]", f"{x}:{y}")
                for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
            )
            update = gr.update(visible=True, choices=player_names)
            return update, update

        all_inputs = [
            self._target_state,
            self._from_x,
            self._from_y,
            self._to_x,
            self._to_y,
            self._va,
            self._duration,
            self._start_time,
            self._arrival_time,
        ]
        all_outputs = [self._va, self._duration, self._start_time, self._arrival_time]

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(fn=self._compute_native, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(fn=self._compute_native, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

        value_fields = [self._va, self._duration, self._start_time, self._arrival_time]

        # No js=True fast path: every editable field here is a custom
        # TimeInput component, which js=True's transpiled fast path can't
        # reach (same finding as DureesHybrid's *_new fields) — it would
        # never do anything useful, so skip straight to the one real pass.
        self._target_sel.select(
            fn=self._interactivity_for,
            inputs=[self._target_sel],
            outputs=value_fields,
            show_progress="hidden",
        )

        self._target_sel.input(
            fn=lambda target: target,
            inputs=[self._target_sel],
            outputs=[self._target_state],
            show_progress="hidden",
        ).then(
            fn=self._apply_time_defaults_native,
            inputs=[self._target_state, self._start_time, self._arrival_time],
            outputs=[self._start_time, self._arrival_time],
            show_progress="hidden",
        ).then(fn=self._compute_native, inputs=all_inputs, outputs=all_outputs, show_progress="hidden")

        gr.on(
            triggers=[self._from_x.input, self._from_y.input, self._to_x.input, self._to_y.input, self._va.input],
            fn=self._compute_native,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )

        # Editing duration/start/arrival directly: skip= keeps _compute_native
        # from echoing the field's own (unchanged) recomputed value back into
        # itself — see the class docstring and DureesHybrid's _mirror_to_new.
        self._duration.input(
            fn=functools.partial(self._compute_native, skip="duration"),
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )
        self._start_time.input(
            fn=functools.partial(self._compute_native, skip="start"),
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )
        self._arrival_time.input(
            fn=functools.partial(self._compute_native, skip="arrival"),
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )
