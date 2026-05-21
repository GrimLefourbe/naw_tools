import gradio as gr
import nawminator as nm
import datetime as dt
import math

from nmsite.army_list import ArmyList
from nmsite.interface import ArmyInputHTML, SegmentedControl
from nmsite.utils import interactivity_updates


N_MAX = 8

_TDP_MODES = ["Durée", "TDP"]

_TDP_MODE_INTERACTIVITY: dict[str, tuple[bool, bool, bool]] = {
    # (tdp_interactive, alli_interactive, duration_interactive)
    "Durée": (True,  True,  False),
    "TDP":   (False, False, True),
}


def _find_tdp_alli(army: nm.army.Army, target_secs: float) -> tuple[int, int]:
    """Find (TDP, alliance_bonus) minimising TDP to achieve target_secs recruit time.

    TDP covers ~5% steps, alliance covers 1% steps (game cap: 5 levels).
    Works in continuous log space: x = log(target/base) / log(0.95) is the total
    TDP-equivalent reduction. Integer part → TDP, fractional part → alli.
    If alli > 5, one extra TDP step is used instead (it overshoots, alli = 0).
    """
    _, base_secs = army.recruit_time()
    if base_secs <= 0 or target_secs >= base_secs:
        return 0, 0

    x = math.log(target_secs / base_secs) / math.log(0.95)
    tdp_out = math.floor(x)

    # Floor drift: recruit_time floors per-unit, so recruit_time(tdp_out, 0) can
    # already be ≤ target_secs even when fractional > 0 in log space. Check first.
    _, actual_tdp_secs = army.recruit_time(tdp_out, 0)
    if actual_tdp_secs <= target_secs:
        return tdp_out, 0

    fractional = x - tdp_out  # ∈ (0, 1)

    # round() rather than ceil(): achieved time is slightly below target due to
    # floor drift, so x on the next call is fractionally higher — ceil would
    # bump alli each round; round stays on the nearest integer.
    alli_out = round(fractional * math.log(0.95) / math.log(0.99))

    if alli_out > 5:
        return tdp_out + 1, 0

    # Float precision can make floor(x) land one step low (x computed as 1.9999...
    # instead of 2.0000...). If the result doesn't achieve the target, one extra
    # TDP step is guaranteed to work (0.95^(tdp+1) ≤ target/base in exact math).
    _, achieved_secs = army.recruit_time(tdp_out, alli_out)
    if achieved_secs > target_secs:
        return tdp_out + 1, 0

    return tdp_out, alli_out


def _compute(mode, army: nm.army.Army, tdp, alli, duration):
    if mode == "Durée":
        _, total_secs = army.recruit_time(int(tdp or 0), int(alli or 0))
        return tdp, alli, nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(total_secs)))

    elif mode == "TDP":
        if not duration or not duration.strip():
            return tdp, alli, duration
        target_secs = nm.utils.parse_ajhms(duration).total_seconds()
        if target_secs <= 0:
            return tdp, alli, duration
        tdp_out, alli_out = _find_tdp_alli(army, target_secs)
        return tdp_out, alli_out, duration

    return tdp, alli, duration


def _compute_total(mode, lst: ArmyList, tdp, alli, duration):
    return _compute(mode, lst.total, tdp, alli, duration)


def pontes_tab():
    return PontesTab()


class PontesTab:
    def __init__(self):
        self._set_layout()
        self._configure_triggers()

    def _row_outputs(self) -> list:
        """Flat list: [container, checkbox, army_input] * N_MAX."""
        out = []
        for i in range(N_MAX):
            out += [self._row_containers[i], self._checkboxes[i], self._army_inputs[i]]
        return out

    def _row_updates(self, al: ArmyList) -> list:
        """Flat list of gr.update() matching _row_outputs() order."""
        updates = []
        for i in range(N_MAX):
            if i < len(al.armies):
                army = al.armies[i]
                updates += [
                    gr.update(visible=True),
                    gr.update(value=al.checks[i]),
                    gr.update(value=army),
                ]
            else:
                updates += [
                    gr.update(visible=False),
                    gr.update(value=False),
                    gr.update(value=nm.army.Army()),
                ]
        return updates

    def _set_layout(self):
        self._list_state = gr.State(ArmyList())

        with gr.Row(equal_height=True):
            self._add_btn = gr.Button("+", scale=0, min_width=40, size="sm", variant="secondary")
            self._all_btn = gr.Button("All", scale=0, min_width=44, size="sm", variant="secondary")
            with gr.Column():
                with gr.Group():
                    with gr.Row():
                        self._repartir_label = gr.Text(
                            "Répartir — en",
                            show_label=False, container=False, interactive=False,
                            scale=0, min_width=130,
                        )
                        self._repartir_btns = [
                            gr.Button(str(n), scale=1, min_width=35)
                            for n in range(1, N_MAX + 1)
                        ]

        self._row_containers = []
        self._checkboxes = []
        self._army_inputs = []
        self._del_btns = []

        for i in range(N_MAX):
            with gr.Row(visible=(i < 2), equal_height=True) as row:
                del_btn = gr.Button("✕", scale=0, min_width=40, size="sm", variant="secondary")
                cb = gr.Checkbox(
                    value=False,
                    show_label=False, container=False,
                    scale=0, min_width=44,
                    elem_classes=["army-check"],
                )
                army_input = ArmyInputHTML(btn_align="left", show_import=False)

            self._row_containers.append(row)
            self._checkboxes.append(cb)
            self._army_inputs.append(army_input)
            self._del_btns.append(del_btn)

        self._total_display = gr.Textbox(
            label="Total", interactive=False, elem_classes=["result-field"],
        )

        self._tdp_mode_state = gr.State("Durée")
        with gr.Row(equal_height=True):
            with gr.Column(scale=0, min_width=90):
                self._tdp_sel = SegmentedControl(
                    choices=_TDP_MODES,
                    value="Durée",
                    elem_id="pontes_tdp_mode",
                )
            with gr.Column():
                self._tdp = gr.Number(value=0, label="TDP", precision=0)
            with gr.Column():
                self._alli = gr.Number(value=0, label="Quête Alliance", precision=0)
            with gr.Column():
                self._duration = gr.Textbox(
                    value="0S", label="Durée", interactive=False,
                    elem_classes=["result-field"], placeholder="ex: 1J 2H 30M",
                )

    def _configure_triggers(self):
        row_outputs = self._row_outputs()
        shift_outputs = [self._list_state] + row_outputs

        tdp_fields = [self._tdp, self._alli, self._duration]
        list_change_outputs = (
            [self._total_display, self._add_btn, self._repartir_label, *self._repartir_btns]
            + tdp_fields
        )
        list_change_inputs = [self._list_state, self._tdp_mode_state, self._tdp, self._alli, self._duration]

        def on_shift(new_lst):
            return [new_lst] + self._row_updates(new_lst)

        def _on_list_change(lst: ArmyList, mode, tdp, alli, duration):
            m = sum(lst.checks)
            n_armies = len(lst.armies)
            max_n = N_MAX - n_armies + m
            total = lst.total
            tdp_out, alli_out, dur_out = _compute(mode, total, tdp, alli, duration)
            return (
                total.to_str_compact(sep=", ") if total.count > 0 else "",
                gr.update(interactive=n_armies < N_MAX),
                gr.update(value=f"Répartir {m} en"),
                *[gr.update(interactive=(n <= max_n)) for n in range(1, N_MAX + 1)],
                tdp_out, alli_out, dur_out,
            )

        self._add_btn.click(
            lambda lst: on_shift(lst.add() if len(lst.armies) < N_MAX else lst),
            inputs=self._list_state, outputs=shift_outputs,
            show_progress="hidden",
        ).then(_on_list_change, inputs=list_change_inputs, outputs=list_change_outputs, show_progress="hidden")

        def on_toggle_all(lst: ArmyList):
            n = len(lst.armies)
            target = not all(lst.checks[:n])
            new_lst = lst
            for i in range(n):
                new_lst = new_lst.set_check(i, target)
            return on_shift(new_lst)

        self._all_btn.click(
            on_toggle_all,
            inputs=self._list_state, outputs=shift_outputs,
            show_progress="hidden",
        ).then(_on_list_change, inputs=list_change_inputs, outputs=list_change_outputs, show_progress="hidden")

        for btn, n in zip(self._repartir_btns, range(1, N_MAX + 1)):
            btn.click(
                lambda lst, n=n: on_shift(lst.repartir(n)),
                inputs=self._list_state, outputs=shift_outputs,
                show_progress="hidden",
            )

        for i in range(N_MAX):
            def on_delete(lst, i=i):
                return on_shift(lst.remove(i) if len(lst.armies) > 1 else lst)

            self._del_btns[i].click(
                on_delete,
                inputs=self._list_state, outputs=shift_outputs,
                show_progress="hidden",
            )

            self._checkboxes[i].change(
                lambda checked, lst, i=i: lst.set_check(i, checked) if i < len(lst.armies) else lst,
                inputs=[self._checkboxes[i], self._list_state], outputs=self._list_state,
                show_progress="hidden",
            )

            self._army_inputs[i].change(
                lambda army, lst, i=i: lst.update_army(i, army),
                inputs=[self._army_inputs[i], self._list_state],
                outputs=self._list_state,
                show_progress="hidden",
            )

        self._list_state.change(
            _on_list_change,
            inputs=list_change_inputs,
            outputs=list_change_outputs,
            show_progress="hidden",
        )

        self._tdp_sel.input(
            fn=lambda mode: interactivity_updates(mode, _TDP_MODE_INTERACTIVITY),
            inputs=[self._tdp_sel],
            outputs=[self._tdp_mode_state] + tdp_fields,
            show_progress="hidden",
        ).then(
            fn=_compute_total,
            inputs=[self._tdp_mode_state, self._list_state, self._tdp, self._alli, self._duration],
            outputs=tdp_fields,
            show_progress="hidden",
        )

        gr.on(
            triggers=[self._tdp.input, self._alli.input, self._duration.input],
            fn=_compute_total,
            inputs=[self._tdp_mode_state, self._list_state, self._tdp, self._alli, self._duration],
            outputs=tdp_fields,
            show_progress="hidden",
        )
