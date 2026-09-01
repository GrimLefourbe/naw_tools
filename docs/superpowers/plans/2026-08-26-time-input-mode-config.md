# TimeInput Mode Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make which TimeInput field set Durées/Synchro build (old plain-text, new TimeInput, or both dual-mounted behind a runtime toggle) a decision made once at server startup from `Config`, instead of always building both and toggling visibility at runtime.

**Architecture:** A new `Config.time_input_mode: Literal["legacy", "hybrid", "experimental"]`, read once when `durees_tab()`/`synchro_tab()` construct their components. `durees.py` splits into `DureesCore` (shared pure functions) + `DureesLegacy`/`DureesHybrid`/`DureesExperimental` (one class per mode, each building only the fields it needs); `synchro.py` (one field pair) stays a single class with inline `if/elif/else` branching. `settings.py`'s opt-in checkbox only gets constructed in hybrid mode.

**Tech Stack:** Gradio 6, Python 3.12, pytest + Playwright (Firefox) for UI tests.

**Spec:** `docs/superpowers/specs/2026-08-26-time-input-mode-config-design.md`

## Global Constraints

- Preset assignments (from the spec): `S1` → `"hybrid"`, `S2` → `"legacy"` (the dataclass default, so `S2`'s `Config(...)` call doesn't need to set it explicitly), `DEV` → `"experimental"`.
- A new `DEV_HYBRID` preset (`dev=True`, `time_input_mode="hybrid"`) is added for tests that need hybrid mode's fields — `armees.py`/`hunt.py` are unaffected by any of this (out of scope, never had TimeInput wired in).
- Legacy mode must construct **zero** TimeInput components — not hidden, not present in `demo.blocks` at all.
- `DureesExperimental`'s echo guard applies only to `duration`/`start`/`arrival` — never to `va` (plain `gr.Number`, no edit-mode concept to disrupt).
- Every task must leave `NMSITE_CONFIG=DEV` (and the full test suite) in a working state — see each task's ordering rationale below when it matters.

---

## File Structure

- **Modify `src/nmsite/config.py`** — add `time_input_mode` field, `DEV_HYBRID` preset.
- **Modify `src/nmsite/tabs/durees.py`** — split into `DureesCore` + `DureesLegacy` + `DureesHybrid` + `DureesExperimental`, factory `durees_tab(settings, tab, config)`.
- **Modify `src/nmsite/tabs/synchro.py`** — inline mode branching in `set_layout`/`configure_triggers`.
- **Modify `src/nmsite/tabs/settings.py`** — only build the toggle/state in hybrid mode.
- **Modify `src/nmsite/app.py`** — thread `config` into `durees.durees_tab(...)`.
- **Modify `tests/nmsite/conftest.py`** — `gradio_server` becomes mode-aware (indirect parametrization), lazily starts one server per mode actually requested.
- **Modify `tests/nmsite/ui/test_durees.py`, `test_durees_toggle.py`, `test_synchro_toggle.py`, `test_settings_toggle.py`, `test_time_input.py`** — request `mode="hybrid"` (these all exercise old-field-shaped elem_ids or the toggle itself, all of which only exist in hybrid mode).
- **New `tests/nmsite/test_config.py`** — preset assertions.
- **New `tests/nmsite/test_durees_modes.py`** — unit-level (no browser) construction checks per mode.
- **New `tests/nmsite/ui/test_durees_experimental.py`** — live E2E coverage for experimental mode (runs against the now-experimental-by-default `DEV` server).

---

### Task 1: `Config.time_input_mode` + presets

**Files:**
- Modify: `src/nmsite/config.py`
- Test: `tests/nmsite/test_config.py` (new)

**Interfaces:**
- Produces: `Config.time_input_mode: Literal["legacy", "hybrid", "experimental"]` (default `"legacy"`); `configs["DEV_HYBRID"]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/nmsite/test_config.py
from nmsite.config import configs


def test_s1_is_hybrid():
    assert configs["S1"].time_input_mode == "hybrid"


def test_s2_is_legacy():
    assert configs["S2"].time_input_mode == "legacy"


def test_dev_is_experimental():
    assert configs["DEV"].time_input_mode == "experimental"


def test_dev_hybrid_preset_exists_for_tests():
    assert configs["DEV_HYBRID"].time_input_mode == "hybrid"
    assert configs["DEV_HYBRID"].dev is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/nmsite/test_config.py -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'time_input_mode'` (and `KeyError: 'DEV_HYBRID'` for the last test).

- [ ] **Step 3: Write the implementation**

Replace `src/nmsite/config.py` with:

```python
import typing as t
from dataclasses import dataclass


@dataclass
class Config:
    title: str
    subtitle: str
    hero_enabled: bool
    base_url: str
    tabs: str | list[str] = "default"
    dev: bool = False
    time_input_mode: t.Literal["legacy", "hybrid", "experimental"] = "legacy"


configs = {
    "S1": Config(
        title="Nawminator",
        subtitle="S1",
        hero_enabled=True,
        base_url="https://s1.natureatwar.fr",
        time_input_mode="hybrid",
    ),
    "S2": Config(
        title="Nawminator",
        subtitle="S2",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
    ),
    "DEV": Config(
        title="Nawminator",
        subtitle="DEV",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
        tabs="all",
        dev=True,
        time_input_mode="experimental",
    ),
    "DEV_HYBRID": Config(
        title="Nawminator",
        subtitle="DEV",
        hero_enabled=False,
        base_url="https://s2.natureatwar.fr",
        tabs="all",
        dev=True,
        time_input_mode="hybrid",
    ),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/nmsite/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full fast suite to confirm nothing else broke**

Run: `poetry run pytest -m "not property" -q`
Expected: same pass/fail counts as before this task (this change is inert — nothing reads `time_input_mode` yet, and `DEV`'s config object gaining a field that's ignored doesn't change app behavior).

- [ ] **Step 6: Commit**

```bash
git add src/nmsite/config.py tests/nmsite/test_config.py
git commit --no-gpg-sign -m "✨ Add Config.time_input_mode + DEV_HYBRID test preset"
```

---

### Task 2: Extract `DureesCore`, rename `DureesTab` → `DureesHybrid`

Pure refactor — no new capability, no behavior change. This is the shared foundation the next two tasks build on, done first and in isolation so any mistake here is caught by the *existing* (already-passing) test suite rather than mixed in with new-feature bugs.

**Files:**
- Modify: `src/nmsite/tabs/durees.py`
- Test: none new — verified by the existing suite (Step 2 below)

**Interfaces:**
- Produces: `DureesCore` with staticmethods `parse_time`, `times_to_secs`, `apply_time_defaults`, `shift_time`, `compute`, `duration_str_to_td`, `duration_td_to_str`, `time_obj_to_str`, and class attribute `TARGETS`. `DureesHybrid` (renamed from `DureesTab`, same constructor signature `(settings, tab)`). `durees_tab(settings, tab)` still unconditionally returns `DureesHybrid(settings, tab)` — mode dispatch isn't wired until Task 4/5.

- [ ] **Step 1: Run the existing suite to capture the baseline**

Run: `poetry run pytest tests/nmsite -m "not property" -q`
Note the pass count — this must be identical after Step 2.

- [ ] **Step 2: Replace `src/nmsite/tabs/durees.py` with the refactored version**

```python
import functools
import gradio as gr
import pandas as pd
import datetime as dt
import typing as t
import nawminator as nm

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


def durees_tab(settings: Settings, tab: gr.Tab):
    return DureesHybrid(settings, tab)


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
        # (canonical) field first, then runs the same compute/mirror chain
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
```

- [ ] **Step 3: Run the same suite again, confirm identical results**

Run: `poetry run pytest tests/nmsite -m "not property" -q`
Expected: same pass count as Step 1 — this task changed nothing observable.

- [ ] **Step 4: Commit**

```bash
git add src/nmsite/tabs/durees.py
git commit --no-gpg-sign -m "♻️ Extract DureesCore, rename DureesTab to DureesHybrid"
```

---

### Task 3: Make the test fixture mode-aware, repoint hybrid-only tests

Done *before* any dispatch wiring so it's a zero-risk infra change: at this point `DEV` and `DEV_HYBRID` both still produce identical (Hybrid-only) apps, since nothing reads `config.time_input_mode` yet. This must land before Task 5 flips `DEV`'s actual behavior, or the tests this step repoints would break at that point instead.

**Files:**
- Modify: `tests/nmsite/conftest.py`
- Modify: `tests/nmsite/ui/test_durees.py`, `tests/nmsite/ui/test_durees_toggle.py`, `tests/nmsite/ui/test_synchro_toggle.py`, `tests/nmsite/ui/test_settings_toggle.py`, `tests/nmsite/ui/test_time_input.py`

**Interfaces:**
- Produces: `gradio_server` fixture accepts indirect parametrization — `@pytest.mark.parametrize("gradio_server", ["hybrid"], indirect=True)` selects the `DEV_HYBRID`-backed server; the default (no parametrization) is `"experimental"` (`DEV`-backed). `live_page` is unchanged (it just consumes whatever `gradio_server` resolves to).

- [ ] **Step 1: Replace `tests/nmsite/conftest.py`**

```python
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import Page

APP_PATH = str(pathlib.Path(__file__).parent.parent.parent / "src" / "nmsite" / "app.py")

# One fixed port + NMSITE_CONFIG preset per test mode. "legacy" isn't listed
# yet — nothing tests it via a live server yet (see TODO.md's TimeInput
# demo-harness item); add a DEV_LEGACY preset in config.py and an entry here
# if/when that changes.
_MODE_SERVERS = {
    "experimental": (17860, "DEV"),
    "hybrid": (17861, "DEV_HYBRID"),
}


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f"Gradio server did not start at {url} within {timeout}s")


def _start_server(port: int, preset: str) -> tuple[subprocess.Popen, str]:
    base_url = f"http://localhost:{port}"
    env = {
        **os.environ,
        "GRADIO_SERVER_PORT": str(port),
        "NMSITE_CONFIG": preset,
        "GRADIO_ANALYTICS_ENABLED": "False",
    }
    proc = subprocess.Popen(
        [sys.executable, APP_PATH],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_server(base_url)
    return proc, base_url


@pytest.fixture(scope="session")
def _server_pool():
    """Lazily-started, session-cached {mode: (proc, base_url)} — a mode's
    server only launches the first time a test actually requests it."""
    pool: dict[str, tuple[subprocess.Popen, str]] = {}
    yield pool
    for proc, _ in pool.values():
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def gradio_server(request, _server_pool):
    mode = getattr(request, "param", "experimental")
    if mode not in _MODE_SERVERS:
        raise ValueError(f"No test server configured for mode {mode!r} — add it to _MODE_SERVERS")
    if mode not in _server_pool:
        port, preset = _MODE_SERVERS[mode]
        _server_pool[mode] = _start_server(port, preset)
    return _server_pool[mode][1]


@pytest.fixture()
def live_page(gradio_server, page: Page):
    """Return a factory: call live_page(tab_name, ready_selector) to get a Page
    already navigated to the given tab. ready_selector, if given, is waited on
    before returning so the tab's content is fully rendered."""
    def _go(tab_name: str, ready_selector: str | None = None) -> Page:
        page.goto(gradio_server)
        page.get_by_role("tab", name=tab_name).click()
        if ready_selector:
            page.locator(ready_selector).wait_for(state="visible")
        return page
    return _go
```

- [ ] **Step 2: Repoint the 5 hybrid-only test files**

In each of `tests/nmsite/ui/test_durees.py`, `tests/nmsite/ui/test_durees_toggle.py`, `tests/nmsite/ui/test_synchro_toggle.py`, `tests/nmsite/ui/test_settings_toggle.py`, `tests/nmsite/ui/test_time_input.py`, replace:

```python
pytestmark = pytest.mark.ui
```

with:

```python
pytestmark = [pytest.mark.ui, pytest.mark.parametrize("gradio_server", ["hybrid"], indirect=True)]
```

(`test_durees.py` needs this because its helpers assert `get_by_role("textbox")` on `#durees_duration`/`#durees_start_time`/`#durees_arrival_time` — only true for the old-field type, which only exists in legacy/hybrid. `test_durees_toggle.py`/`test_synchro_toggle.py` test the dual-mount toggle itself. `test_settings_toggle.py` tests the toggle checkbox, which Task 7 makes hybrid-only. `test_time_input.py` has one test — `test_interactive_toggle_hides_toggle_button` — that navigates into Durées and flips the toggle; the rest of that file only needs `dev=True`, which both `DEV` and `DEV_HYBRID` satisfy, so repointing the whole file is simplest and has no effect on its other tests.)

- [ ] **Step 3: Run the repointed suite**

Run: `poetry run pytest tests/nmsite/ui -m "not property" -q`
Expected: same pass count as before this task — `DEV_HYBRID` behaves identically to `DEV` right now (dispatch isn't wired), so nothing observable changed.

- [ ] **Step 4: Commit**

```bash
git add tests/nmsite/conftest.py tests/nmsite/ui/test_durees.py tests/nmsite/ui/test_durees_toggle.py tests/nmsite/ui/test_synchro_toggle.py tests/nmsite/ui/test_settings_toggle.py tests/nmsite/ui/test_time_input.py
git commit --no-gpg-sign -m "✅ Make gradio_server fixture mode-aware, repoint hybrid-only tests to DEV_HYBRID"
```

---

### Task 4: Add `DureesLegacy`, wire the factory (temporary experimental→hybrid alias)

**Files:**
- Modify: `src/nmsite/tabs/durees.py`
- Modify: `src/nmsite/app.py`
- Test: `tests/nmsite/test_durees_modes.py` (new)

**Interfaces:**
- Consumes: `DureesCore` (Task 2).
- Produces: `DureesLegacy(settings, tab)` (constructor signature matches `DureesHybrid`/`DureesExperimental` for the factory's sake; `tab` accepted and unused). `durees_tab(settings, tab, config)` — new 3-arg signature, dispatches on `config.time_input_mode` (`"experimental"` temporarily aliased to `DureesHybrid` until Task 5).

- [ ] **Step 1: Write the failing test**

```python
# tests/nmsite/test_durees_modes.py
import gradio as gr

from nmsite.config import Config
from nmsite.tabs.durees import durees_tab
from nmsite.tabs.settings import Settings


def _config(**overrides) -> Config:
    values = dict(title="T", subtitle="T", hero_enabled=False, base_url="https://example.com")
    values.update(overrides)
    return Config(**values)


def _elem_ids(demo: gr.Blocks) -> set[str]:
    return {eid for c in demo.blocks.values() if (eid := getattr(c, "elem_id", None))}


def _build_durees(config: Config):
    with gr.Blocks() as demo:
        settings = Settings(demo, config)
        with gr.Tab("Durées") as tab:
            durees_tab(settings, tab, config)
    return demo


def test_legacy_mode_has_old_fields_only():
    demo = _build_durees(_config(time_input_mode="legacy"))
    ids = _elem_ids(demo)
    assert "durees_duration" in ids
    assert "durees_start_time" in ids
    assert "durees_arrival_time" in ids
    assert "durees_duration_new" not in ids
    assert "durees_start_time_new" not in ids
    assert "durees_arrival_time_new" not in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/nmsite/test_durees_modes.py -v`
Expected: FAIL — `TypeError: durees_tab() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: Add `DureesLegacy` and the factory dispatch to `src/nmsite/tabs/durees.py`**

Add a new import alongside the existing ones at the top of the file:

```python
from nmsite.config import Config
```

Replace the existing `def durees_tab(settings: Settings, tab: gr.Tab): return DureesHybrid(settings, tab)` with:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    mode_classes = {
        "legacy": DureesLegacy,
        "hybrid": DureesHybrid,
        # TODO(2026-08-26): temporary alias — swap to DureesExperimental
        # once it exists (next task). Keeps DEV (time_input_mode=
        # "experimental") bootable in the meantime.
        "experimental": DureesHybrid,
    }
    return mode_classes[config.time_input_mode](settings, tab)
```

Then append `DureesLegacy` as a new class, right after `DureesCore` and before `DureesHybrid`:

```python
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
```

- [ ] **Step 4: Update `src/nmsite/app.py`'s call site**

Change:

```python
            durees.durees_tab(settings, durees_tab)
```

to:

```python
            durees.durees_tab(settings, durees_tab, config)
```

(This is inside the `with gr.Tab("Durées", render=False) as durees_tab:` block — `config` is already in scope there, it's the module-level `Config` picked at the top of `app.py`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/nmsite/test_durees_modes.py -v`
Expected: PASS

- [ ] **Step 6: Run the full fast suite**

Run: `poetry run pytest -m "not property" -q`
Expected: same pass count as Task 3's end state — `DEV`'s `"experimental"` mode is still aliased to `DureesHybrid`, so nothing observable changed for any existing test; only the new `test_durees_modes.py` test is new.

- [ ] **Step 7: Commit**

```bash
git add src/nmsite/tabs/durees.py src/nmsite/app.py tests/nmsite/test_durees_modes.py
git commit --no-gpg-sign -m "✨ Add DureesLegacy, wire mode dispatch (experimental temporarily aliased to hybrid)"
```

---

### Task 5: Add `DureesExperimental`, finalize the factory

**Files:**
- Modify: `src/nmsite/tabs/durees.py`
- Modify: `tests/nmsite/test_durees_modes.py`
- Test: `tests/nmsite/ui/test_durees_experimental.py` (new)

**Interfaces:**
- Consumes: `DureesCore` (Task 2).
- Produces: `DureesExperimental(settings, tab)`. Factory's `"experimental"` entry now points at the real class.

- [ ] **Step 1: Write the failing unit test (extends Task 4's file)**

Add to `tests/nmsite/test_durees_modes.py`:

```python
def test_experimental_mode_has_new_fields_only():
    demo = _build_durees(_config(time_input_mode="experimental"))
    ids = _elem_ids(demo)
    assert "durees_duration" in ids
    assert "durees_start_time" in ids
    assert "durees_arrival_time" in ids
    assert "durees_duration_new" not in ids
    assert "durees_start_time_new" not in ids
    assert "durees_arrival_time_new" not in ids


def test_experimental_mode_fields_are_timeinput_not_old_style():
    import nmsite.components

    demo = _build_durees(_config(time_input_mode="experimental"))
    duration = next(c for c in demo.blocks.values() if getattr(c, "elem_id", None) == "durees_duration")
    assert isinstance(duration, nmsite.components.TimeInput)
```

- [ ] **Step 2: Run to verify it fails**

Run: `poetry run pytest tests/nmsite/test_durees_modes.py -v`
Expected: FAIL — `test_experimental_mode_fields_are_timeinput_not_old_style` fails because `#durees_duration` is currently a `gr.Text` (the temporary hybrid alias from Task 4).

- [ ] **Step 3: Add `DureesExperimental` to `src/nmsite/tabs/durees.py`**

Append this class after `DureesHybrid` (end of file):

```python
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
```

- [ ] **Step 4: Finalize the factory dispatch**

In `durees_tab()`, replace:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    mode_classes = {
        "legacy": DureesLegacy,
        "hybrid": DureesHybrid,
        # TODO(2026-08-26): temporary alias — swap to DureesExperimental
        # once it exists (next task). Keeps DEV (time_input_mode=
        # "experimental") bootable in the meantime.
        "experimental": DureesHybrid,
    }
    return mode_classes[config.time_input_mode](settings, tab)
```

with:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    mode_classes = {
        "legacy": DureesLegacy,
        "hybrid": DureesHybrid,
        "experimental": DureesExperimental,
    }
    return mode_classes[config.time_input_mode](settings, tab)
```

- [ ] **Step 5: Run the unit tests to verify they pass**

Run: `poetry run pytest tests/nmsite/test_durees_modes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Write the live E2E test for experimental mode**

```python
# tests/nmsite/ui/test_durees_experimental.py
"""E2E coverage for Durées in experimental mode (TimeInput fields only, no
dual-mount, no toggle) — runs against the default gradio_server (DEV, which
is time_input_mode="experimental")."""

import nawminator as nm
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def durees_page(live_page) -> Page:
    return live_page("Durées", "#durees_target")


def _fill_number(page: Page, elem_id: str, value: int | float) -> None:
    page.locator(f"#{elem_id} input").fill(str(value))


def test_durees_tab_renders_timeinput_fields(durees_page: Page) -> None:
    page = durees_page
    expect(page.locator("#durees_duration .ti-widget")).to_be_visible()
    expect(page.locator("#durees_start_time .ti-widget")).to_be_visible()
    expect(page.locator("#durees_arrival_time .ti-widget")).to_be_visible()
    # No old-style textarea fields anywhere in this mode.
    expect(page.locator("#durees_duration").get_by_role("textbox")).to_have_count(0)


def test_arrivee_mode_computes_duration(durees_page: Page) -> None:
    page = durees_page
    secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)

    _fill_number(page, "durees_from_x", 0)
    _fill_number(page, "durees_from_y", 0)
    _fill_number(page, "durees_to_x", 100)
    _fill_number(page, "durees_to_y", 0)

    expect(page.locator("#durees_arrival_time .ti-display-value")).to_have_text("00:01:40", timeout=10_000)


def test_editing_start_time_twice_does_not_close_the_editor(durees_page: Page) -> None:
    """Regression for the DureesHybrid loopback bug (see git history:
    'Fix three TimeInput component bugs' / 'Wire TimeInput as an opt-in
    toggle'), re-verified here since DureesExperimental reimplements the
    same skip= echo guard independently (no shared mirror step to reuse)."""
    page = durees_page
    page.locator("#durees_start_time .ti-display").click()
    page.locator("#durees_start_time .ti-field").wait_for(state="visible")
    hours_seg = page.locator("#durees_start_time .ti-seg[data-key='hours']")
    hours_seg.click()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("01", timeout=5_000)
    page.wait_for_timeout(1_000)
    expect(page.locator("#durees_start_time .ti-field")).to_be_visible()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("02", timeout=5_000)
```

- [ ] **Step 7: Run it to verify it fails without the fix, then passes with it**

Run: `poetry run pytest tests/nmsite/ui/test_durees_experimental.py -v`
Expected: PASS — Step 3 already implements the `skip=` guard, so this should be green immediately. If `test_editing_start_time_twice_does_not_close_the_editor` fails, that's a real regression in `DureesExperimental._compute_native`'s skip handling — fix it before moving on (the `gr.skip()` for the field's own slot in `_compute_native` is the mechanism to check first).

- [ ] **Step 8: Run the full fast suite**

Run: `poetry run pytest -m "not property" -q`
Expected: all green — this is the point where `DEV`'s behavior actually changes (real Experimental content instead of the Task-4 alias), but Task 3 already repointed every test that cared about the old-field elem_ids to `DEV_HYBRID`, so nothing else should be affected.

- [ ] **Step 9: Commit**

```bash
git add src/nmsite/tabs/durees.py tests/nmsite/test_durees_modes.py tests/nmsite/ui/test_durees_experimental.py
git commit --no-gpg-sign -m "✨ Add DureesExperimental, finalize durees mode dispatch"
```

---

### Task 6: `synchro.py` — inline mode branching

**Files:**
- Modify: `src/nmsite/tabs/synchro.py`
- Test: `tests/nmsite/ui/test_synchro_toggle.py` (existing, no changes needed — already hybrid-targeted from Task 3)
- Test: `tests/nmsite/ui/test_synchro_experimental.py` (new, minimal)

**Interfaces:**
- Consumes: `config.time_input_mode` (already available — `SynchroTab.__init__` already receives `config`).
- Produces: no interface change — `synchro_tab(config, settings)` keeps its existing signature.

- [ ] **Step 1: Write the failing test**

```python
# tests/nmsite/ui/test_synchro_experimental.py
"""Minimal E2E smoke test for Synchro in experimental mode (runs against the
default gradio_server, DEV)."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


def test_synchro_tab_shows_timeinput_only(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    page.get_by_role("tab", name="Synchro").click()
    page.locator("#synchro_time_input").wait_for(state="visible")
    expect(page.locator("#synchro_time_input .ti-widget")).to_be_visible()
    # No plain gr.DateTime field in this mode.
    expect(page.locator("#synchro_time_input input[type='text']")).to_have_count(0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/nmsite/ui/test_synchro_experimental.py -v`
Expected: FAIL — `#synchro_time_input` is currently always `gr.DateTime` (a text input), never a `TimeInput`, so `.ti-widget` never appears.

- [ ] **Step 3: Replace `set_layout`/`configure_triggers` and `calc_synchros` in `src/nmsite/tabs/synchro.py`**

Replace the `self.time_input = ...` / `self.time_input_new = ...` block in `set_layout` (the `with gr.Column():` under the `with gr.Row():` that also builds `self.va_input`) with:

```python
            with gr.Column():
                mode = self.config.time_input_mode
                if mode in ("legacy", "hybrid"):
                    self.time_input = gr.DateTime(
                        label="Heure de départ",
                        value=lambda: dt.datetime.now(),
                        type="datetime",  # type: ignore
                        elem_id="synchro_time_input",
                        visible=(mode == "legacy"),
                    )
                if mode in ("hybrid", "experimental"):
                    self.time_input_new = TimeInput(
                        mode="datetime",
                        quick_fills=["now"],
                        value=lambda: dt.datetime.now(),  # type: ignore
                        label="Heure de départ",
                        elem_id="synchro_time_input" if mode == "experimental" else "synchro_time_input_new",
                        visible=(mode == "experimental"),
                    )
```

(Legacy and experimental each build exactly one component, visible from construction, with `elem_id="synchro_time_input"` in both cases — matching Durées' convention of reusing the same elem_id for whichever single field exists in a single-field-set mode. Hybrid keeps today's `synchro_time_input`/`synchro_time_input_new` pair, `synchro_time_input` starting visible and `synchro_time_input_new` starting hidden, exactly as before.)

In `configure_triggers`, replace the unconditional:

```python
        settings.time_input_enabled_state.change(
            fn=lambda enabled: (gr.update(visible=not enabled), gr.update(visible=enabled)),
            inputs=settings.time_input_enabled_state,
            outputs=[self.time_input, self.time_input_new],
            show_progress="hidden",
        )
```

with:

```python
        if self.config.time_input_mode == "hybrid":
            settings.time_input_enabled_state.change(
                fn=lambda enabled: (gr.update(visible=not enabled), gr.update(visible=enabled)),
                inputs=settings.time_input_enabled_state,
                outputs=[self.time_input, self.time_input_new],
                show_progress="hidden",
            )
```

And replace the `self.synchro_button.click(...)` block's `inputs=` list — currently:

```python
            inputs=[
                settings.data_state,
                self.va_input,
                self.time_input,
                self.time_input_new,
                settings.time_input_enabled_state,
                self.player_select,
                self.target_alliance,
            ],
```

with a mode-dependent version. `calc_synchros` is bound once, so its `inputs=` list needs a fixed length regardless of mode — legacy/experimental only have one real départ component, so the other slot gets a `gr.State(None)` placeholder (always reads as `None`; `calc_synchros`'s `mode` argument decides which of the two slots is authoritative). Add `mode = self.config.time_input_mode` as the first line of `configure_triggers`, then build the inputs list:

```python
        depart_inputs: list = []
        if mode in ("legacy", "hybrid"):
            depart_inputs.append(self.time_input)
        else:
            depart_inputs.append(gr.State(None))
        if mode in ("hybrid", "experimental"):
            depart_inputs.append(self.time_input_new)
        else:
            depart_inputs.append(gr.State(None))

        self.synchro_button.click(
            fn=functools.partial(calc_synchros, base_url=self.config.base_url, mode=mode),
            inputs=[
                settings.data_state,
                self.va_input,
                *depart_inputs,
                self.player_select,
                self.target_alliance,
            ],
            outputs=[
                self.synchro_outputs,
                self.synchro_copy,
                self.synchro_copy_discord,
                self.synchro_copy_table,
                self.synchro_copy_btn,
                self.synchro_copy_discord_btn,
                self.synchro_copy_table_btn,
            ],
        )
```

Finally, update `calc_synchros`'s signature and its one line of mode logic:

```python
def calc_synchros(
    data: pd.DataFrame,
    va: int,
    depart: dt.datetime | None,
    depart_new: dt.datetime | None,
    target_coords: str,
    target_allis: list[str],
    base_url: str,
    mode: str,
):
    depart = depart_new if mode in ("hybrid", "experimental") and depart_new is not None else depart
    assert depart is not None, "Heure de départ manquante"
```

(Replaces the old `time_input_enabled: bool` parameter and its `depart = depart_new if time_input_enabled else depart` line — same position in the parameter list, `functools.partial`'s `mode=mode` keyword covers it from the call site above.)

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/nmsite/ui/test_synchro_experimental.py -v`
Expected: PASS

- [ ] **Step 5: Run the full fast suite**

Run: `poetry run pytest -m "not property" -q`
Expected: all green, including `test_synchro_toggle.py` (still targeting `DEV_HYBRID`, where `mode == "hybrid"` and behavior is unchanged from before this task).

- [ ] **Step 6: Commit**

```bash
git add src/nmsite/tabs/synchro.py tests/nmsite/ui/test_synchro_experimental.py
git commit --no-gpg-sign -m "✨ Branch Synchro's départ field on time_input_mode"
```

---

### Task 7: `settings.py` — toggle only in hybrid mode

Comes last among the wiring tasks: both `DureesHybrid` and `SynchroTab`'s hybrid branch are the only remaining readers of `settings.time_input_enabled_state`, and by this point (Tasks 5 and 6 done) both only reference it when actually in hybrid mode — so it's now safe for `Settings` to skip building it entirely otherwise.

**Files:**
- Modify: `src/nmsite/tabs/settings.py`
- Modify: `tests/nmsite/test_settings.py`

**Interfaces:**
- Produces: `Settings.time_input_enabled_state` / `Settings.time_input_toggle` only exist as attributes when `config.time_input_mode == "hybrid"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/nmsite/test_settings.py`:

```python
def test_hybrid_mode_shows_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="hybrid"))
    assert "settings_time_input_toggle" in _elem_ids(demo)


def test_legacy_mode_hides_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="legacy"))
    assert "settings_time_input_toggle" not in _elem_ids(demo)


def test_experimental_mode_hides_time_input_toggle():
    with gr.Blocks() as demo:
        Settings(demo, _config(time_input_mode="experimental"))
    assert "settings_time_input_toggle" not in _elem_ids(demo)
```

(`_config`/`_elem_ids` already exist in this file from earlier work — no new helpers needed. If `_config`'s default doesn't set `time_input_mode`, it falls back to the dataclass default `"legacy"`, which is fine for the two non-hybrid tests above.)

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/nmsite/test_settings.py -v`
Expected: FAIL — `test_legacy_mode_hides_time_input_toggle` and `test_experimental_mode_hides_time_input_toggle` fail (`settings_time_input_toggle` is currently always built).

- [ ] **Step 3: Update `src/nmsite/tabs/settings.py`**

In `Settings.__init__`, replace:

```python
        self.data_state, self.metadata_state = self._clear_data()
        self.time_input_enabled_state = gr.State(False)
        self.post_load = demo.load(
            self.load,
            inputs=[self.data_state, self.metadata_state],
            outputs=[self.data_state, self.metadata_state],
            js=load_from_browser_storage
        )
        self._create_layout()
        self._configure_triggers()
        demo.load(
            fn=lambda enabled, checked: (enabled, checked),
            inputs=[self.time_input_enabled_state, self.time_input_toggle],
            outputs=[self.time_input_enabled_state, self.time_input_toggle],
            js=load_time_input_enabled,
            show_progress="hidden",
        )
```

with:

```python
        self.data_state, self.metadata_state = self._clear_data()
        if self._config.time_input_mode == "hybrid":
            self.time_input_enabled_state = gr.State(False)
        self.post_load = demo.load(
            self.load,
            inputs=[self.data_state, self.metadata_state],
            outputs=[self.data_state, self.metadata_state],
            js=load_from_browser_storage
        )
        self._create_layout()
        self._configure_triggers()
        if self._config.time_input_mode == "hybrid":
            demo.load(
                fn=lambda enabled, checked: (enabled, checked),
                inputs=[self.time_input_enabled_state, self.time_input_toggle],
                outputs=[self.time_input_enabled_state, self.time_input_toggle],
                js=load_time_input_enabled,
                show_progress="hidden",
            )
```

In `_create_layout`, replace:

```python
        self.time_input_toggle = gr.Checkbox(
            value=False,
            label="Utiliser le nouveau sélecteur de temps (bêta)",
            elem_id="settings_time_input_toggle",
        )
        if self._config.dev:
            self._create_time_input_demo()
```

with:

```python
        if self._config.time_input_mode == "hybrid":
            self.time_input_toggle = gr.Checkbox(
                value=False,
                label="Utiliser le nouveau sélecteur de temps (bêta)",
                elem_id="settings_time_input_toggle",
            )
        if self._config.dev:
            self._create_time_input_demo()
```

In `_configure_triggers`, replace:

```python
        self.time_input_toggle.change(
            fn=lambda enabled: enabled,
            inputs=self.time_input_toggle,
            outputs=self.time_input_enabled_state,
            js=save_time_input_enabled,
            show_progress="hidden",
        )

        if self._config.dev:
            self._configure_time_input_demo()
```

with:

```python
        if self._config.time_input_mode == "hybrid":
            self.time_input_toggle.change(
                fn=lambda enabled: enabled,
                inputs=self.time_input_toggle,
                outputs=self.time_input_enabled_state,
                js=save_time_input_enabled,
                show_progress="hidden",
            )

        if self._config.dev:
            self._configure_time_input_demo()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/nmsite/test_settings.py -v`
Expected: PASS (all cases, including the pre-existing `dev`-gated ones)

- [ ] **Step 5: Run the full fast suite**

Run: `poetry run pytest -m "not property" -q`
Expected: all green — `S2` (legacy) and `DEV` (experimental) never read `time_input_enabled_state` anymore (Tasks 5/6 confirmed), so removing its construction there is safe.

- [ ] **Step 6: Commit**

```bash
git add src/nmsite/tabs/settings.py tests/nmsite/test_settings.py
git commit --no-gpg-sign -m "✨ Only build the TimeInput opt-in toggle in hybrid mode"
```

---

### Task 8: Full verification + docs

**Files:**
- Modify: `TODO.md`
- No new memory file — the design doc + this plan are already the durable record; a pointer memory would just duplicate `[[project_context]]`'s existing summary once updated.

- [ ] **Step 1: Full suite, both fast and property**

Run: `poetry run pytest -q`
Expected: all green (aside from the pre-existing, unrelated `armees.py`/`test_armees.py` failures tracked separately — confirm the failure set is *exactly* that pre-existing set and nothing new).

- [ ] **Step 2: Manual 3-mode smoke test**

Run each of these in turn (`Ctrl+C` between), confirm Durées + Synchro render and compute correctly, and that the "other" modes' elem_ids are absent from the page source (`view-source:` or browser devtools — not just hidden):

```bash
NMSITE_CONFIG=S2 poetry run python src/nmsite/app.py     # legacy
NMSITE_CONFIG=DEV_HYBRID poetry run python src/nmsite/app.py   # hybrid
NMSITE_CONFIG=DEV poetry run python src/nmsite/app.py    # experimental
```

- [ ] **Step 3: Update `TODO.md`**

In the "Time input component" entry, add a line noting the mode-config split landed, e.g. append after the existing sub-bullets:

```markdown
    - **Mode-config split landed** (2026-08-26 design, implemented via `docs/superpowers/plans/2026-08-26-time-input-mode-config.md`): `Config.time_input_mode` (`legacy`/`hybrid`/`experimental`) now decides at server startup which field set Durées/Synchro build — no more always-dual-mounted-and-toggled. `S1`=hybrid, `S2`=legacy, `DEV`=experimental.
```

- [ ] **Step 4: Commit**

```bash
git add TODO.md
git commit --no-gpg-sign -m "📝 Note TimeInput mode-config split landed in TODO.md"
```

---

## Self-Review Notes

- **Spec coverage:** `Config.time_input_mode` + presets (Task 1); `DureesCore`/`DureesLegacy`/`DureesHybrid`/`DureesExperimental` split (Tasks 2, 4, 5); `synchro.py` inline branching (Task 6); `settings.py` hybrid-only toggle (Task 7); test fixture `mode` param + `DEV_HYBRID` (Tasks 1, 3); explicitly-deferred `test_time_input.py` demo-harness rework — not attempted here, TODO.md already carries it from the brainstorming session.
- **Ordering rationale, restated:** Task 3 (test repointing) must precede Task 5 (the point where `DEV` actually stops being hybrid-shaped) — verified each task's "run full suite" step calls out what should and shouldn't change.
- **Type/interface consistency:** `DureesCore` staticmethods are named identically everywhere they're called across Tasks 2/4/5 (`compute`, `apply_time_defaults`, `parse_time`, `shift_time`, `duration_str_to_td`, `duration_td_to_str`, `time_obj_to_str`, `TARGETS`). `durees_tab(settings, tab, config)`'s 3-arg signature is consistent from Task 4 onward, including its one caller in `app.py`.
