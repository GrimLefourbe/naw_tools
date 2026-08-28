# Durées Composition Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `durees.py`'s three parallel mode classes (`DureesLegacy`/`DureesHybrid`/`DureesExperimental`) with one `Durees` engine class that owns the shared wiring shape, plus a small `DureesModeSpec` per mode supplying what varies.

**Architecture:** Composition over inheritance — see `docs/superpowers/specs/2026-08-28-durees-composition-refactor-design.md` for the full rationale and design. `DureesCore` keeps its current role (stateless pure-math/parse layer); a new `Durees` class becomes the single wiring engine; `_legacy_spec`/`_experimental_spec`/`_hybrid_spec` become the three per-mode data/callable bundles.

**Tech Stack:** Python 3.12, Gradio 6, dataclasses. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-28-durees-composition-refactor-design.md`

## Global Constraints

- Single file touched: `src/nmsite/tabs/durees.py`. Nothing outside it changes (confirmed in the spec: `durees_tab()`'s only external contract is being callable as `durees_tab(settings, tab, config)`; all tests select by `elem_id`, never `isinstance`).
- **This is a behavior-preserving refactor, not new behavior** — there is no new failing test to write per task. Each task's verification step is: run the existing tests scoped to that task, confirm they pass unchanged. If any existing test needs editing to pass, that's a signal the refactor changed observable behavior — stop and reconcile before continuing, don't just patch the test.
- Every `elem_id` in the current file must appear unchanged in the new one (Playwright tests select by these; grep `elem_id=` in the current file to cross-check before Task 4's final commit: `durees_va`, `durees_duration`(`_new`), `durees_start_time`(`_new`), `durees_arrival_time`(`_new`), `durees_target`, `durees_src_player`, `durees_tgt_player`, `durees_from_x`, `durees_from_y`, `durees_to_x`, `durees_to_y`).
- `git commit --no-gpg-sign` — GPG signing fails in this devcontainer (no smartcard daemon); this is the project's documented workaround (`.claude/skills/commit/SKILL.md`).
- Test commands (verified working this session):
  - Non-UI: `poetry run pytest tests -vv -m "not property" -k "not ui"`
  - Durées Playwright: `poetry run pytest tests/nmsite/ui/test_durees.py tests/nmsite/ui/test_durees_toggle.py tests/nmsite/ui/test_durees_experimental.py -vv`
  - Mode-shape (Python-only, no browser): `poetry run pytest tests/nmsite/test_durees_modes.py -vv`
- **Known pre-existing gap, not fixed by this plan:** Legacy mode has no Playwright coverage (`test_durees.py` was repointed to `mode="hybrid"` only during the earlier mode-config split — tracked in TODO.md). Task 1's regression check for Legacy therefore relies on the non-UI suite + `test_durees_modes.py`'s `elem_id`-shape assertions + a manual dev-server smoke check, not an automated browser test. Don't skip the manual check for Task 1 because of this.

---

## File Structure

Everything lives in `src/nmsite/tabs/durees.py`. Top-to-bottom order after this refactor:

1. `DureesCore` — unchanged except `interactivity_for` classmethod → `dispatch_interactivity` staticmethod (Task 2)
2. `_build_coord_row()` — unchanged
3. `EditableField`, `DureesModeSpec` dataclasses — new (Task 1)
4. `durees_tab()` — dispatcher, rewritten incrementally across Tasks 1–3
5. `Durees` — new engine class (Task 1)
6. `_legacy_spec()` — new (Task 1), replaces `DureesLegacy` (deleted Task 1)
7. `_experimental_spec()` — new (Task 2), replaces `DureesExperimental` (deleted Task 2)
8. `_hybrid_interactivity_to_va/_arrivee/_depart()`, `_hybrid_spec()` — new (Task 3), replace `DureesHybrid` (deleted Task 3)

## Task 1: Scaffolding + Durees engine + Legacy migrated

**Files:**
- Modify: `src/nmsite/tabs/durees.py`
- Test: `tests/nmsite/test_durees_modes.py` (existing, unchanged), `tests/nmsite/ui/` (existing, unchanged — none touched this task)

**Interfaces:**
- Produces: `EditableField` (fields: `trigger`, `skip`, `pre_step`), `DureesModeSpec` (fields: `va_field`, `value_fields`, `canonical_fields`, `compute`, `apply_time_defaults`, `editable_fields`, `interactivity_fns`, `needs_select_dispatch`, `extra_wiring`), `Durees(settings, tab, spec_builder)`, `DureesCore.dispatch_interactivity(fns, target)`, `_legacy_spec(settings) -> DureesModeSpec`.
- Consumes (unchanged, already in file): `DureesCore.compute/parse_time/apply_time_defaults/parse_xy/player_choices/_interactivity_to_va/_interactivity_to_arrivee/_interactivity_to_depart`, `_build_coord_row()`.

- [ ] **Step 1: Add the import, dataclasses, engine class, `dispatch_interactivity`, `_legacy_spec`, and wire `durees_tab()`'s legacy branch through the new engine**

Add `from dataclasses import dataclass` to the imports at the top of `src/nmsite/tabs/durees.py`:

```python
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
```

Add `dispatch_interactivity` to `DureesCore`, right after the existing `interactivity_for` classmethod (leave `interactivity_for` in place for now — `DureesExperimental`, not yet migrated, still calls it; it's removed in Task 2):

```python
    @staticmethod
    def dispatch_interactivity(fns: tuple, target: str):
        """Generic version of interactivity_for: takes the mode's own
        3-tuple of interactivity functions instead of assuming DureesCore's
        own 4-field ones, so it works for Hybrid's 7-field versions too."""
        return dict(zip(DureesCore.TARGETS, fns))[target]()
```

Replace the current `durees_tab()` function:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    mode_classes = {
        "legacy": DureesLegacy,
        "hybrid": DureesHybrid,
        "experimental": DureesExperimental,
    }
    return mode_classes[config.time_input_mode](settings, tab)
```

with:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    if config.time_input_mode == "legacy":
        return Durees(settings, tab, _legacy_spec)
    mode_classes = {
        "hybrid": DureesHybrid,
        "experimental": DureesExperimental,
    }
    return mode_classes[config.time_input_mode](settings, tab)
```

Immediately after `durees_tab()` (before the now-dead `DureesLegacy` class, which this step also deletes — see below), add:

```python
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
```

Finally, delete the entire `DureesLegacy` class (from `class DureesLegacy:` through the line before `class DureesHybrid:`) — it's now fully replaced by `Durees` + `_legacy_spec`.

- [ ] **Step 2: Run the non-UI suite and the mode-shape test**

Run: `poetry run pytest tests -vv -m "not property" -k "not ui"`
Expected: same pass count as before this change (298 passed, 2 skipped, 2 xfailed — confirm the number matches; a drop means something broke).

Run: `poetry run pytest tests/nmsite/test_durees_modes.py -vv`
Expected: all 3 tests pass, including `test_legacy_mode_has_old_fields_only`.

- [ ] **Step 3: Manual smoke check (Legacy has no Playwright coverage yet — see Global Constraints)**

Run: `NMSITE_CONFIG=S2 poetry run gradio src/nmsite/app.py` (S2 = legacy mode), open the Durées tab in a browser, and confirm: entering coordinates updates VA/duration/arrival, clicking each of VA/Arrivée/Départ correctly locks the right field, typing a start/duration/arrival value recomputes the others. Kill the server after (`pkill -f "gradio src/nmsite/app.py"`, then verify with `ss -ltnp | grep 7860` that nothing is still listening — a `gradio` reload wrapper can leave a reparented child process behind).

- [ ] **Step 4: Commit**

```bash
git add src/nmsite/tabs/durees.py
git commit --no-gpg-sign -m "♻️ Durées: composition engine + Legacy migrated

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 2: Experimental migrated

**Files:**
- Modify: `src/nmsite/tabs/durees.py`

**Interfaces:**
- Consumes: `DureesModeSpec`, `EditableField`, `Durees` (from Task 1).
- Produces: `_experimental_spec(settings) -> DureesModeSpec`.

- [ ] **Step 1: Add `_experimental_spec`, wire it in, delete `DureesExperimental` and the now-unused `interactivity_for`**

Update `durees_tab()`:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config):
    spec_builders = {
        "legacy": _legacy_spec,
        "experimental": _experimental_spec,
    }
    if config.time_input_mode in spec_builders:
        return Durees(settings, tab, spec_builders[config.time_input_mode])
    return DureesHybrid(settings, tab)
```

Add `_experimental_spec`, placed after `_legacy_spec`:

```python
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
```

Delete the entire `DureesExperimental` class.

In `DureesCore`, delete the `interactivity_for` classmethod (its only caller, `DureesExperimental`, is now gone; `dispatch_interactivity` from Task 1 replaces it for every mode).

- [ ] **Step 2: Run the non-UI suite, mode-shape tests, and Experimental Playwright suite**

Run: `poetry run pytest tests -vv -m "not property" -k "not ui"`
Expected: same pass count as Task 1.

Run: `poetry run pytest tests/nmsite/test_durees_modes.py tests/nmsite/ui/test_durees_experimental.py -vv`
Expected: all pass (3 mode-shape tests + 3 experimental Playwright tests: `test_durees_tab_renders_timeinput_fields`, `test_arrivee_mode_computes_duration`, `test_editing_start_time_twice_does_not_close_the_editor`).

- [ ] **Step 3: Commit**

```bash
git add src/nmsite/tabs/durees.py
git commit --no-gpg-sign -m "♻️ Durées: Experimental migrated to composition engine

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 3: Hybrid migrated (all three modes now on the engine)

**Files:**
- Modify: `src/nmsite/tabs/durees.py`

**Interfaces:**
- Consumes: `DureesModeSpec`, `EditableField`, `Durees` (from Task 1).
- Produces: `_hybrid_interactivity_to_va/_arrivee/_depart()`, `_hybrid_spec(settings) -> DureesModeSpec`.

- [ ] **Step 1: Add the Hybrid interactivity functions and `_hybrid_spec`, wire in, delete `DureesHybrid`**

Update `durees_tab()` to its final form:

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config) -> Durees:
    spec_builders = {
        "legacy": _legacy_spec,
        "hybrid": _hybrid_spec,
        "experimental": _experimental_spec,
    }
    return Durees(settings, tab, spec_builders[config.time_input_mode])
```

Add, after `_experimental_spec`:

```python
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

    def compute_and_mirror(target, x1, y1, x2, y2, va, duration, start, arrival, skip=None):
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

    def toggle_visibility(enabled: bool):
        return tuple(gr.update(visible=v) for v in (not enabled, enabled) * 3)

    def extra_wiring(engine: Durees, settings: Settings, tab: gr.Tab):
        tab.select(
            fn=toggle_visibility,
            inputs=settings.time_input_enabled_state,
            outputs=[duration, duration_new, start, start_new, arrival, arrival_new],
            show_progress="hidden",
            queue=False,
        )

    return DureesModeSpec(
        va_field=va,
        value_fields=[va, duration, duration_new, start, start_new, arrival, arrival_new],
        canonical_fields=(duration, start, arrival),
        compute=compute_and_mirror,
        apply_time_defaults=DureesCore.apply_time_defaults,
        editable_fields=[
            EditableField(trigger=duration.input, skip=None),
            EditableField(trigger=start.input, skip=None),
            EditableField(trigger=arrival.input, skip=None),
            EditableField(
                trigger=duration_new.input,
                skip="duration",
                pre_step=(DureesCore.duration_td_to_str, duration_new, duration),
            ),
            EditableField(
                trigger=start_new.input,
                skip="start",
                pre_step=(DureesCore.time_obj_to_str, start_new, start),
            ),
            EditableField(
                trigger=arrival_new.input,
                skip="arrival",
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
```

Delete the entire `DureesHybrid` class.

- [ ] **Step 2: Run the non-UI suite, mode-shape tests, and both Hybrid Playwright suites**

Run: `poetry run pytest tests -vv -m "not property" -k "not ui"`
Expected: same pass count as Task 2.

Run: `poetry run pytest tests/nmsite/test_durees_modes.py tests/nmsite/ui/test_durees.py tests/nmsite/ui/test_durees_toggle.py -vv`
Expected: all pass (3 mode-shape + 11 `test_durees.py` + 5 `test_durees_toggle.py`, including `test_toggle_on_new_field_edit_does_not_echo_back_and_close` — the echo-guard regression test).

- [ ] **Step 3: Commit**

```bash
git add src/nmsite/tabs/durees.py
git commit --no-gpg-sign -m "♻️ Durées: Hybrid migrated — all three modes now on the composition engine

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 4: Cleanup, full verification, docs

**Files:**
- Modify: `src/nmsite/tabs/durees.py` (docstring only), `TODO.md`
- Modify: `memory/project_time_input_mode_config.md` (or create a new memory file — see Step 3)

- [ ] **Step 1: Update `DureesCore`'s class docstring**

It currently reads:

```python
class DureesCore:
    """Mode-agnostic pure logic shared by DureesLegacy/DureesHybrid/
    DureesExperimental. No component state — every mode calls these the
    exact same way."""
```

Change to:

```python
class DureesCore:
    """Mode-agnostic pure logic shared by all three mode specs
    (_legacy_spec/_hybrid_spec/_experimental_spec) via the Durees engine.
    No component state — every mode calls these the exact same way."""
```

- [ ] **Step 2: Full verification pass**

Run: `poetry run black --diff src/nmsite/tabs/durees.py`
Expected: "All done! 1 file would be left unchanged." If not, run `poetry run black src/nmsite/tabs/durees.py` and re-check the diff is only whitespace.

Run: `poetry run pytest tests -vv -m "not property" -k "not ui"`
Expected: same pass count as Task 3.

Run: `poetry run pytest tests/nmsite/test_durees_modes.py tests/nmsite/ui/test_durees.py tests/nmsite/ui/test_durees_toggle.py tests/nmsite/ui/test_durees_experimental.py -vv`
Expected: all 22 pass (3 + 11 + 5 + 3).

Grep-check the full set of `elem_id`s is unchanged by the refactor — this
reorganizes code, it doesn't add or remove components, so the count must
match the pre-refactor file exactly:
Run: `grep -c 'elem_id="durees_' src/nmsite/tabs/durees.py`
Expected: 22 (verified against the pre-refactor file: 7 unique coord-row
ids × 1 occurrence each via the shared `_build_coord_row()`, plus
va/duration/start_time/arrival_time's ids each appearing once per spec
builder — 1× in `_legacy_spec`, 1× in `_experimental_spec`, and 2× in
`_hybrid_spec` for duration/start_time/arrival_time's old+new pairs).
Also run `grep -o 'elem_id="durees_[a-z_]*"' src/nmsite/tabs/durees.py | sort -u`
and confirm the 14 unique ids listed in Global Constraints are all present.

Grep-check no dead code remains:
Run: `grep -n "DureesLegacy\|DureesHybrid\|DureesExperimental" src/nmsite/tabs/durees.py`
Expected: no output (both class definitions and the docstring references from Step 1 should be gone).

- [ ] **Step 3: Update TODO.md and memory**

In `TODO.md`'s "Time input component" entry, add a sub-bullet after the existing "Mode-config split landed" note:

```markdown
    - **Composition refactor landed** (2026-08-28): `durees.py`'s three
      parallel mode classes (`DureesLegacy`/`DureesHybrid`/`DureesExperimental`)
      replaced by one `Durees` engine class + a `DureesModeSpec` per mode
      (`_legacy_spec`/`_hybrid_spec`/`_experimental_spec`). Fixes the earlier
      mode-config split leaving the wiring *shape* triplicated even after a
      `/simplify` pass deduped the leaf-level logic. See
      `docs/superpowers/specs/2026-08-28-durees-composition-refactor-design.md`.
```

Update `memory/project_time_input_mode_config.md`: add a new section at the end (after the "Durées tab perf complaint" section) noting the composition refactor landed, that it's an internal restructure only (no behavior change — verified by the full existing test suite passing unchanged), and that it doesn't itself resolve the still-open perf complaint but consolidates the round-trip logic into one path for whoever picks that back up. Update `MEMORY.md`'s pointer line for this memory file if the one-line summary needs adjusting to mention the refactor.

- [ ] **Step 4: Final commit**

```bash
git add src/nmsite/tabs/durees.py TODO.md memory/project_time_input_mode_config.md MEMORY.md
git commit --no-gpg-sign -m "📝 Durées composition refactor: docs + cleanup pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
