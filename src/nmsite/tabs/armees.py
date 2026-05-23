import gradio as gr
import nawminator as nm
import datetime as dt
import math

from nmsite.army_list import ArmyList
from nmsite.components import ArmyInputHTML, SegmentedControl

N_MAX = 8

_TDP_MODES = ["Durée", "TDP"]


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


def armees_tab():
    return ArmeesTab()


# No-op sentinel: tells Gradio "leave this component alone" (no value push → watch() stays silent).
_NOOP = gr.update()


class ArmeesTab:
    @staticmethod
    def _interactivity_to_duree():
        return (gr.update(interactive=True,  elem_classes=[]),
                gr.update(interactive=True,  elem_classes=[]),
                gr.update(interactive=False, elem_classes=["result-field"]))

    @staticmethod
    def _interactivity_to_tdp():
        return (gr.update(interactive=False, elem_classes=["result-field"]),
                gr.update(interactive=False, elem_classes=["result-field"]),
                gr.update(interactive=True,  elem_classes=[]))

    def __init__(self):
        self._set_layout()
        self._configure_triggers()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

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
                    elem_id="armees_tdp_mode",
                    container=False,
                )
            with gr.Column():
                self._tdp = gr.Number(value=0, label="TDP", precision=0, elem_id="armees_tdp")
            with gr.Column():
                self._alli = gr.Number(value=0, label="Quête Alliance", precision=0, elem_id="armees_alli")
            with gr.Column():
                self._duration = gr.Textbox(
                    value="0S", label="Durée", interactive=False,
                    elem_classes=["result-field"], placeholder="ex: 1J 2H 30M", elem_id="armees_duration",
                )

    # ------------------------------------------------------------------
    # Row-update helpers
    #
    # Each returns a flat list [container_upd, cb_upd, ai_upd] * N_MAX.
    # Only slots that genuinely change get a real update; everything else
    # gets _NOOP so Gradio sends nothing to that component (watch stays silent).
    # ------------------------------------------------------------------

    def _noop_row(self):
        return [_NOOP, _NOOP, _NOOP]

    def _updates_add(self, lst: ArmyList) -> list:
        """Show one new row at index n; leave all existing rows untouched."""
        n = len(lst.armies) - 1  # index of the newly added army
        updates = []
        for i in range(N_MAX):
            if i == n:
                updates += [gr.update(visible=True), gr.update(value=False),
                            gr.update(value=nm.army.Army())]
            else:
                updates += self._noop_row()
        return updates

    def _updates_delete(self, new_lst: ArmyList, deleted_idx: int) -> list:
        """Shift armies down into the gap; hide the last visible row."""
        n_new = len(new_lst.armies)  # == len(old_lst.armies) - 1
        updates = []
        for i in range(N_MAX):
            if i < deleted_idx:
                updates += self._noop_row()
            elif i < n_new:
                updates += [_NOOP, gr.update(value=new_lst.checks[i]), gr.update(value=new_lst.armies[i])]
            elif i == n_new:
                updates += [gr.update(visible=False), _NOOP, _NOOP]
            else:
                updates += self._noop_row()
        return updates

    def _updates_toggle_all(self, lst: ArmyList, target: bool) -> list:
        """Flip checkboxes; army inputs are never touched (no cascade)."""
        n = len(lst.armies)
        updates = []
        for i in range(N_MAX):
            if i < n:
                updates += [_NOOP, gr.update(value=target), _NOOP]
            else:
                updates += self._noop_row()
        return updates

    def _updates_repartir(self, old_lst: ArmyList, new_lst: ArmyList) -> list:
        """Push new army values; show/hide rows to match new count."""
        n_old = len(old_lst.armies)
        n_new = len(new_lst.armies)
        updates = []
        for i in range(N_MAX):
            if i < n_new:
                container_upd = gr.update(visible=True) if i >= n_old else _NOOP
                updates += [container_upd,
                            gr.update(value=new_lst.checks[i]),
                            gr.update(value=new_lst.armies[i])]
            elif i < n_old:
                updates += [gr.update(visible=False), _NOOP, _NOOP]
            else:
                updates += self._noop_row()
        return updates

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _configure_triggers(self):
        shift_outputs = [self._list_state] + [
            comp
            for i in range(N_MAX)
            for comp in (self._row_containers[i], self._checkboxes[i], self._army_inputs[i])
        ]

        tdp_fields = [self._tdp, self._alli, self._duration]
        list_change_outputs = (
            [self._total_display, self._add_btn, self._repartir_label, *self._repartir_btns]
            + tdp_fields
        )
        list_change_inputs = [
            self._list_state, self._tdp_mode_state, self._tdp, self._alli, self._duration,
        ]

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

        # --- Structural operations (shift_outputs) ---

        def on_add(lst):
            if len(lst.armies) >= N_MAX:
                return [lst] + [_NOOP] * (3 * N_MAX)
            new_lst = lst.add()
            return [new_lst] + self._updates_add(new_lst)

        self._add_btn.click(
            on_add, inputs=self._list_state, outputs=shift_outputs, show_progress="hidden",
        )

        def on_toggle_all(lst):
            n = len(lst.armies)
            target = not all(lst.checks[:n])
            new_lst = lst
            for i in range(n):
                new_lst = new_lst.set_check(i, target)
            return [new_lst] + self._updates_toggle_all(new_lst, target)

        self._all_btn.click(
            on_toggle_all, inputs=self._list_state, outputs=shift_outputs, show_progress="hidden",
        )

        for btn, n in zip(self._repartir_btns, range(1, N_MAX + 1)):
            def on_repartir(lst, n=n):
                new_lst = lst.repartir(n)
                return [new_lst] + self._updates_repartir(lst, new_lst)

            btn.click(
                on_repartir, inputs=self._list_state, outputs=shift_outputs, show_progress="hidden",
            )

        for i in range(N_MAX):
            def on_delete(lst, i=i):
                if len(lst.armies) <= 1:
                    return [lst] + [_NOOP] * (3 * N_MAX)
                new_lst = lst.remove(i)
                return [new_lst] + self._updates_delete(new_lst, i)

            self._del_btns[i].click(
                on_delete, inputs=self._list_state, outputs=shift_outputs, show_progress="hidden",
            )

            self._checkboxes[i].change(
                lambda checked, lst, i=i: lst.set_check(i, checked) if i < len(lst.armies) else lst,
                inputs=[self._checkboxes[i], self._list_state],
                outputs=self._list_state,
                show_progress="hidden",
            )

            def on_army_change(army, lst, i=i):
                if i >= len(lst.armies) or army == lst.armies[i]:
                    return gr.update()
                return lst.update_army(i, army)

            self._army_inputs[i].change(
                on_army_change,
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

        self._tdp_sel.on_choice("Durée")(self._interactivity_to_duree, outputs=tdp_fields, js=True, show_progress="hidden")
        self._tdp_sel.on_choice("TDP")(self._interactivity_to_tdp,   outputs=tdp_fields, js=True, show_progress="hidden")

        self._tdp_sel.input(
            fn=lambda mode: mode,
            inputs=[self._tdp_sel],
            outputs=[self._tdp_mode_state],
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
