import gradio as gr
import pandas as pd
import datetime as dt
import typing as t
import nawminator as nm

from nmsite.tabs.settings import Settings


_TARGETS = ["Durée", "VA", "Arrivée", "Départ"]


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
    base = dt.datetime(2000, 1, 1)
    dt_s = base.replace(hour=t_start.hour, minute=t_start.minute, second=t_start.second)
    dt_a = base.replace(hour=t_arrival.hour, minute=t_arrival.minute, second=t_arrival.second)
    secs = (dt_a - dt_s).total_seconds()
    return secs + 86400 if secs < 0 else secs


def _compute(target, x1, y1, x2, y2, va, duration, start, arrival):
    try:
        if target == "VA":
            secs = _times_to_secs(start, arrival)
            if secs is None:
                secs = nm.utils.parse_ajhms(duration).total_seconds()
            base_d = nm.formulas.duree_attaque(x1, y1, x2, y2)
            return nm.formulas.from_va(secs / base_d), duration, start, arrival

        elif target == "Durée":
            secs = _times_to_secs(start, arrival)
            if secs is not None:
                new_d = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=secs))
            else:
                new_d = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=nm.formulas.duree_attaque(x1, y1, x2, y2, va)))
            return va, new_d, start, arrival

        elif target == "Arrivée":
            t = _parse_time(start)
            if t is None:
                return va, duration, start, arrival
            secs = nm.utils.parse_ajhms(duration).total_seconds()
            base = dt.datetime(2000, 1, 1, t.hour, t.minute, t.second)
            new_arrival = (base + dt.timedelta(seconds=secs)).time()
            return va, duration, start, new_arrival.strftime("%H:%M:%S")

        elif target == "Départ":
            t = _parse_time(arrival)
            if t is None:
                return va, duration, start, arrival
            secs = nm.utils.parse_ajhms(duration).total_seconds()
            base = dt.datetime(2000, 1, 1, t.hour, t.minute, t.second)
            new_start = (base - dt.timedelta(seconds=secs)).time()
            return va, duration, new_start.strftime("%H:%M:%S"), arrival

    except Exception:
        pass
    return va, duration, start, arrival


def durees_tab(settings: Settings):
    return DureesTab(settings)

class DureesTab:
    def __init__(self, settings: Settings) -> None:
        self._set_layout(settings)
        self._configure_triggers(settings)

    def _set_layout(self, settings: Settings):
        with gr.Row():
            with gr.Column(min_width=100), gr.Group():
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Source</div>"
                )
                self._src_player_select = gr.Dropdown(container=False, visible=False)
                args: dict[str, t.Any] = {"container": False}
                with gr.Row():
                    gr.Text("x", min_width=30, **args)
                    self._from_x = gr.Number(value=0, scale=0, min_width=70, **args)
                with gr.Row():
                    gr.Text("y", min_width=30, **args)
                    self._from_y = gr.Number(value=0, scale=0, min_width=70, **args)

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

        with gr.Row(equal_height=True):
            gr.HTML("<div style='display:flex; align-items:center; padding:8px 4px; white-space:nowrap;'>Calculer →</div>")
            self._target = gr.Dropdown(
                choices=_TARGETS,
                value="Durée",
                container=False,
                min_width=150,
                scale=0,
            )

        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque")
            with gr.Column(min_width=200):
                self._duration = gr.Text("0s", label="Durée")
        with gr.Row():
            with gr.Column(min_width=200):
                self._start_time = gr.Textbox(value="", label="Heure de départ", placeholder="HH:MM:SS")
            with gr.Column(min_width=200):
                self._arrival_time = gr.Textbox(value="", label="Heure d'arrivée", placeholder="HH:MM:SS")

    def _configure_triggers(self, settings: Settings):
        @settings.data_state.change(
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )
        def get_colo_names(data: pd.DataFrame):
            player_names = [
                (f"{player}: {colo}[{x}:{y}]", ":".join(map(str, [x, y])))
                for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
            ]
            return gr.Dropdown(visible=True, choices=sorted(player_names)), gr.Dropdown(visible=True, choices=sorted(player_names))

        all_inputs = [self._target, self._from_x, self._from_y, self._to_x, self._to_y, self._va, self._duration, self._start_time, self._arrival_time]
        all_outputs = [self._va, self._duration, self._start_time, self._arrival_time]

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else list(map(int, x.split(":"))),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        ).then(
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden", show_api=False,
        )

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else list(map(int, x.split(":"))),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        ).then(
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden", show_api=False,
        )

        gr.on(
            triggers=[
                self._target.change,
                self._from_x.change, self._from_y.change,
                self._to_x.change, self._to_y.change,
                self._va.change, self._duration.change,
                self._start_time.change, self._arrival_time.change,
            ],
            fn=_compute,
            inputs=all_inputs,
            outputs=all_outputs,
            show_progress="hidden", show_api=False,
        )
