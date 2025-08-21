import gradio as gr
import pandas as pd
import typing as t
import nawminator as nm

from nmsite.tabs.settings import Settings


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
        with gr.Row():
            with gr.Column(min_width=200):
                self._va = gr.Number(value=0, label="Vitesse d'Attaque")
            with gr.Column(min_width=200):
                self._duration = gr.Text("0s", label="Durée")

    def _configure_triggers(self, settings: Settings):
        @settings.data_state.change(
            inputs=settings.data_state,
            outputs=[self._src_player_select, self._tgt_player_select],
            show_progress="hidden",
        )
        def get_colo_names(data: pd.DataFrame):
            player_names = [
                (f"{player}: {colo}[{x}:{y}]", ":".join(map(str, [x, y]))) for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].itertuples(index=False)
            ]
            return gr.Dropdown(visible=True, choices=sorted(player_names)), gr.Dropdown(visible=True, choices=sorted(player_names))

        self._src_player_select.input(
            lambda x: (0, 0) if x is None else list(map(int, x.split(":"))),
            inputs=self._src_player_select,
            outputs=[self._from_x, self._from_y],
            show_progress="hidden",
        )

        self._tgt_player_select.input(
            lambda x: (0, 0) if x is None else list(map(int, x.split(":"))),
            inputs=self._tgt_player_select,
            outputs=[self._to_x, self._to_y],
            show_progress="hidden",
        )

        self.last_used = gr.State("va")

        def _recompute_duration_va(x1, y1, x2, y2, va, duration, last_used):
            print(f"{va=} {duration=}")
            if last_used == "va":
                return va, nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(nm.formulas.duree_attaque(x1, y1, x2, y2, va)))
            elif last_used == "duration":
                d = nm.utils.YJHMS_to_seconds(nm.utils.parse_YJHMS(duration))
                base_d = nm.formulas.duree_attaque(x1, y1, x2, y2)
                observed_ratio = d/base_d
                return nm.formulas.from_va(observed_ratio), duration
            else:
                raise ValueError("Incorrect value for last_used")
            
        inputs = [self._from_x, self._from_y, self._to_x, self._to_y, self._va, self._duration, self.last_used]
        outputs = [self._va, self._duration]

        gr.on(
            triggers=[self._from_x.change, self._from_y.change, self._to_x.change, self._to_y.change],
            fn=_recompute_duration_va,
            inputs=inputs,
            outputs=outputs,
            show_progress="hidden", show_api=False,
        )

        self._duration.input(fn=lambda : "duration", outputs=self.last_used).then(
            fn=_recompute_duration_va,
            inputs=inputs,
            outputs=outputs,
            show_progress="hidden", show_api=False,
        )
        self._va.input(fn=lambda : "va", outputs=self.last_used).then(
            fn=_recompute_duration_va,
            inputs=inputs,
            outputs=outputs,
            show_progress="hidden", show_api=False,
        )

