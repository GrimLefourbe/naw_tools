import gradio as gr
import pandas as pd
import datetime as dt
import typing as t
import nawminator as nm

from nmsite.tabs.settings import Settings
from nmsite.components import SegmentedControl
from nmsite.utils import interactivity_updates


_TARGETS = ["VA", "Arrivée", "Départ"]


def _parse_time(s: str) -> dt.time | None:
    if not s or not s.strip():
        return None
    try:
        return dt.datetime.strptime(s.strip(), "%H:%M:%S").time()
    except ValueError:
        return None


def _times_to_secs(start: str, arrival: str) -> float | None:
    t_start = _parse_time(start)
    t_arrival = _parse_time(arrival)
    if t_start is None or t_arrival is None:
        return None
    secs_start = t_start.hour * 3600 + t_start.minute * 60 + t_start.second
    secs_arrival = t_arrival.hour * 3600 + t_arrival.minute * 60 + t_arrival.second
    secs = secs_arrival - secs_start
    return secs + 86400 if secs < 0 else secs


_TARGET_INTERACTIVITY: dict[str, tuple[bool, bool, bool, bool]] = {
    # (va, duration, start_time, arrival_time)
    "VA":      (False, True,  True,  True),
    "Arrivée": (True,  False, True,  False),
    "Départ":  (True,  False, False, True),
}


def _apply_time_defaults(target, start, arrival):
    if target == "Arrivée" and not (start and start.strip()):
        start = "00:00:00"
    elif target == "Départ" and not (arrival and arrival.strip()):
        arrival = "00:00:00"
    return start, arrival


def _shift_time(t: dt.time, secs: float) -> str:
    base = dt.datetime(2000, 1, 1, t.hour, t.minute, t.second)
    return (base + dt.timedelta(seconds=secs)).time().strftime("%H:%M:%S")


def _compute(target, x1, y1, x2, y2, va, duration, start, arrival):
    if target == "VA":
        secs = _times_to_secs(start, arrival)
        if secs is None:
            secs = nm.utils.parse_ajhms(duration).total_seconds()
        base_d = nm.formulas.duree_attaque(x1, y1, x2, y2)
        new_va = nm.formulas.from_va(secs / base_d)
        new_duration = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=secs))
        return new_va, new_duration, start, arrival

    anchor_str = start if target == "Arrivée" else arrival
    parsed = _parse_time(anchor_str)
    if parsed is None:
        return va, duration, start, arrival
    secs = nm.formulas.duree_attaque(x1, y1, x2, y2, va)
    new_duration = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=secs))
    if target == "Arrivée":
        return va, new_duration, start, _shift_time(parsed, secs)
    if target == "Départ":
        return va, new_duration, _shift_time(parsed, -secs), arrival
    return va, duration, start, arrival


def durees_tab(settings: Settings):
    return DureesTab(settings)

class DureesTab:
    def __init__(self, settings: Settings) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings)

    def _set_layout(self, settings: Settings):
        self._target_state = gr.State("Arrivée")
        args: dict[str, t.Any] = {"container": False}
        with gr.Row(equal_height=True):
            with gr.Column(min_width=100), gr.Group():
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>"
                )
                self._src_player_select = gr.Dropdown(container=False, visible=False)
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._from_x = gr.Number(value=0, scale=0, min_width=70, **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._from_y = gr.Number(value=0, scale=0, min_width=70, **args)

            with gr.Column(scale=0, min_width=90):
                self._target_sel = SegmentedControl(
                    choices=_TARGETS,
                    value="Arrivée",
                    elem_id="durees_target",
                )

            with gr.Column(min_width=100), gr.Group():
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Cible</div>"
                )
                self._tgt_player_select = gr.Dropdown(container=False, visible=False)
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._to_x = gr.Number(value=0, scale=0, min_width=70, **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._to_y = gr.Number(value=0, scale=0, min_width=70, **args)

        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque")
            with gr.Column(min_width=200):
                self._duration = gr.Text("0s", label="Durée", interactive=False, elem_classes=["result-field"])
        with gr.Row():
            with gr.Column(min_width=200):
                self._start_time = gr.Textbox(value="00:00:00", label="Heure de départ", placeholder="HH:MM:SS")
            with gr.Column(min_width=200):
                self._arrival_time = gr.Textbox(value="", label="Heure d'arrivée", placeholder="HH:MM:SS", interactive=False, elem_classes=["result-field"])

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

        all_inputs = [self._target_state, self._from_x, self._from_y, self._to_x, self._to_y, self._va, self._duration, self._start_time, self._arrival_time]
        all_outputs = [self._va, self._duration, self._start_time, self._arrival_time]

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else tuple(int(v) for v in x.split(":")),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )

        value_fields = [self._va, self._duration, self._start_time, self._arrival_time]

        self._target_sel.input(
            fn=lambda target: interactivity_updates(target, _TARGET_INTERACTIVITY),
            inputs=[self._target_sel],
            outputs=[self._target_state] + value_fields,
            show_progress="hidden",
        ).then(
            fn=_apply_time_defaults,
            inputs=[self._target_state, self._start_time, self._arrival_time],
            outputs=[self._start_time, self._arrival_time],
            show_progress="hidden",
        ).then(
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )

        gr.on(
            triggers=[
                self._from_x.input, self._from_y.input,
                self._to_x.input, self._to_y.input,
                self._va.input, self._duration.input,
                self._start_time.input, self._arrival_time.input,
            ],
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden",
        )
