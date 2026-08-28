# Durées: composition-based mode engine

## Context

The 2026-08-26 mode-config split (`docs/superpowers/specs/2026-08-26-time-input-mode-config-design.md`)
gave `durees.py` three mode classes — `DureesLegacy`, `DureesHybrid`,
`DureesExperimental` — sharing pure math/parsing through a `DureesCore`
static-method namespace. A 2026-08-28 `/simplify` pass on that file removed
literal duplication (identical closures, identical layout blocks, a
redundant `gr.State` mirror, merged Hybrid's two-hop compute+mirror into
one), but left the underlying *shape* untouched: each mode class still
independently declares the full `_set_layout`/`_configure_triggers` wiring
pattern. `DureesCore` ended up as a namespace for extracted leaf functions,
not a real shared structure — the user flagged this as a miss: they'd left
the choice between inheritance and composition open, and got neither.

Separately, the Durées tab still feels slow in practice (reported
2026-08-27, partially addressed by the round-trip merge above but not fully
investigated — see `memory/project_time_input_mode_config.md`). This refactor
doesn't fix that by itself, but consolidating the wiring into one path
instead of three means any further perf fix lands once, not three times.

**Time horizon**: the three-mode split is a short-lived comparison tool —
the user expects to pick one mode within weeks and delete the other two.
This favors an abstraction that's cheap to partially unwind (delete one
spec + one dispatch entry) over a heavier, more "permanent-feeling"
structure.

## Approach: composition over inheritance

One `Durees` engine class owns the wiring *shape*. Each mode supplies a
`DureesModeSpec` — a small bundle of data/callables — that plugs into that
shape. `durees_tab()` picks the spec by `config.time_input_mode` and builds
one `Durees(settings, tab, spec)`.

Rejected: an inheritance/template-method hierarchy (base `Durees` class,
mode subclasses overriding hooks). The three modes' field counts and extra
behavior genuinely diverge (Hybrid's dual-mount sync + visibility toggle has
no equivalent in the other two), so a base class would still need
per-subclass hook overrides — same indirection cost as composition, but
harder to read (a mode's full behavior is split across a base class and a
subclass) and harder to safely delete later (removing a mode means checking
whether the base class's default hooks are still needed by the survivor).
Composition keeps each mode's entire definition in one flat spec, and
deleting a mode is "delete its spec function + one dispatch-table entry" —
no shared base class to re-audit.

`DureesCore` keeps its current role unchanged: the stateless pure-math/parse
layer (`compute`, `parse_time`, `shift_time`, `apply_time_defaults`,
`duration_str_to_td`/`_td_to_str`/`time_obj_to_str`, `parse_xy`,
`player_choices`). Specs call into it; they don't replace it.

## `DureesModeSpec`

```python
@dataclass
class EditableField:
    """One user-editable entry point (duration/start/arrival) that should
    re-run compute when edited. Hybrid has two of these per concept (old +
    new); Legacy/Experimental have exactly one each."""
    trigger: EventListenerMethod   # e.g. self._duration.input
    skip: str | None               # "duration"/"start"/"arrival", or None
                                    # if this mode has no self-echo hazard
                                    # (Legacy's plain Textbox — harmless to
                                    # overwrite with its own new value)
    pre_step: tuple[Callable, gr.Component, gr.Component] | None = None
    # (fn, source, dest) — Hybrid's *_new fields only: sync the edited
    # TimeInput value into its old-field sibling before compute runs.

@dataclass
class DureesModeSpec:
    va_field: gr.Component               # value_fields[0], exposed separately since it's read as a plain
                                          # input (all_inputs) as well as written as an output (value_fields)
    value_fields: list[gr.Component]     # ordered outputs compute() writes:
                                          # [va, duration(, duration_new), start(, start_new), arrival(, arrival_new)]
    canonical_fields: tuple[gr.Component, gr.Component, gr.Component]
                                          # (duration, start, arrival) — the "old"/canonical component for each,
                                          # i.e. value_fields[1]/[2]/[3] for Legacy+Experimental,
                                          # value_fields[1]/[3]/[5] for Hybrid. Used to read current values into
                                          # all_inputs; the *_new siblings are outputs only, never inputs.
    compute: Callable                    # (target, x1,y1,x2,y2,va, *canonical_values, skip=None) -> tuple matching value_fields
    apply_time_defaults: Callable        # (target, start, arrival) -> (start, arrival), same value type as canonical_fields[1]/[2].
                                          # DureesCore.apply_time_defaults directly for Legacy/Hybrid (string canonical
                                          # fields); Experimental needs a str<->native adapter, same shape as `compute`'s.
    editable_fields: list[EditableField] # duration/start/arrival entry points
    interactivity_fns: tuple[Callable, Callable, Callable]  # VA/Arrivée/Départ — zero-arg js=True statics, literal per SegmentedControl's transpiler constraint
    needs_select_dispatch: bool          # True when a value_field is a custom component (interactive can't be set via js=True's fast path)
    extra_wiring: Callable[["Durees", Settings, gr.Tab], None] | None = None  # Hybrid only: *_new sync handlers + tab.select() visibility toggle
```

`value_fields`'s order is the single source of truth for what `compute`
must return and what `interactivity_fns`/`.select()` dispatch write to — no
separate `all_outputs`/`value_fields` pair to keep in sync per mode, as
exists today. `canonical_fields` resolves the one place `value_fields`
alone is ambiguous: `all_inputs` (below) needs exactly one component per
concept to read a "current value" from, and Hybrid has two (old + new) per
concept where the others have one.

## `Durees` engine

```python
class Durees:
    def __init__(self, settings: Settings, tab: gr.Tab, spec: DureesModeSpec):
        self._spec = spec
        self._set_layout(settings)
        self._configure_triggers(settings, tab)

    def _set_layout(self, settings: Settings):
        (self._src_player_select, self._from_x, self._from_y,
         self._target_sel, self._tgt_player_select, self._to_x, self._to_y) = _build_coord_row()
        # spec already built value_fields during its own construction (it
        # needs the gr.Blocks context active, same as _build_coord_row) —
        # Durees just references them, doesn't build them.

    def _configure_triggers(self, settings: Settings, tab: gr.Tab):
        spec = self._spec
        settings.data_state.change(fn=DureesCore.player_choices, ...)

        all_inputs = [self._target_sel, self._from_x, self._from_y, self._to_x, self._to_y,
                      spec.va_field, *spec.canonical_fields]

        # 1. never-ambiguous fields
        gr.on(triggers=[self._from_x.input, self._from_y.input, self._to_x.input,
                         self._to_y.input, spec.va_field.input],
              fn=spec.compute, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        # 2. duration/start/arrival — one loop replaces 3 hand-copied blocks
        for ef in spec.editable_fields:
            chain = ef.trigger
            if ef.pre_step:
                fn, src, dst = ef.pre_step
                chain = chain(fn=fn, inputs=src, outputs=dst, show_progress="hidden").then
            chain(fn=functools.partial(spec.compute, skip=ef.skip) if ef.skip else spec.compute,
                  inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        # 3. interactivity: on_choice(js=True) x3 + optional .select() pass
        for choice, fn in zip(DureesCore.TARGETS, spec.interactivity_fns):
            self._target_sel.on_choice(choice)(fn, outputs=spec.value_fields, js=True, show_progress="hidden")
        if spec.needs_select_dispatch:
            by_target = dict(zip(DureesCore.TARGETS, spec.interactivity_fns))
            self._target_sel.select(fn=lambda t: by_target[t](),
                                     inputs=[self._target_sel], outputs=spec.value_fields, show_progress="hidden")

        # 4. target-selector chain
        _, start, arrival = spec.canonical_fields
        self._target_sel.input(
            fn=spec.apply_time_defaults, inputs=[self._target_sel, start, arrival], outputs=[start, arrival],
            show_progress="hidden",
        ).then(fn=spec.compute, inputs=all_inputs, outputs=spec.value_fields, show_progress="hidden")

        # 5. mode-unique extras
        if spec.extra_wiring:
            spec.extra_wiring(self, settings, tab)
```

(Sketch, not literal code to copy in — exact Gradio call syntax, error
handling, and variable naming are for the implementation plan to pin down.
The contract — engine owns wiring shape, spec supplies data/callables,
`canonical_fields`/`va_field` resolve `all_inputs` unambiguously — is what
this section commits to.)

## The three specs

- **`_legacy_spec(settings)`**: `value_fields` = `[va, duration, start, arrival]`
  (plain `gr.Number`/`gr.Text`/`gr.Textbox`). `compute` = `DureesCore.compute`
  directly (string-based, no adapter needed). `apply_time_defaults` =
  `DureesCore.apply_time_defaults` directly (string fields). `editable_fields`: 3 entries,
  `skip=None` each (no self-echo hazard), no `pre_step`. `interactivity_fns`
  = the existing 4-field literal statics (already shared with Experimental
  today — stays shared, now living as a module-level pair of functions both
  specs reference). `needs_select_dispatch=False`. `extra_wiring=None`.

- **`_experimental_spec(settings)`**: `value_fields` = `[va, duration, start,
  arrival]` (all `TimeInput`). `compute` = the native↔str adapter (today's
  `DureesExperimental._compute_native`). `apply_time_defaults` = the
  native↔str adapter (today's `_apply_time_defaults_native`). `editable_fields`: 3 entries with
  `skip="duration"/"start"/"arrival"`, no `pre_step` (TimeInput is edited
  directly, no old-field sibling to sync from). `interactivity_fns` = same
  4-field statics as Legacy. `needs_select_dispatch=True` (custom
  component). `extra_wiring=None`.

- **`_hybrid_spec(settings)`**: `value_fields` = `[va, duration,
  duration_new, start, start_new, arrival, arrival_new]`. `compute` =
  today's `_compute_and_mirror`. `apply_time_defaults` =
  `DureesCore.apply_time_defaults` directly (canonical fields are the old,
  string-based components — same as Legacy). `editable_fields`: 6 entries — 3 for the
  old fields (`skip=None`, no pre_step) + 3 for the `*_new` fields
  (`skip="duration"/"start"/"arrival"`, `pre_step` = the sync-into-old
  conversion). `interactivity_fns` = the existing 7-field literal statics.
  `needs_select_dispatch=True`. `extra_wiring` = registers the `*_new`
  handlers' pre_step+compute chain (now just iterated by the engine, so
  this may shrink to only the visibility toggle: `tab.select(fn=..., ...)`).

## `durees_tab()`

```python
def durees_tab(settings: Settings, tab: gr.Tab, config: Config) -> Durees:
    spec_builders = {"legacy": _legacy_spec, "hybrid": _hybrid_spec, "experimental": _experimental_spec}
    return Durees(settings, tab, spec_builders[config.time_input_mode](settings))
```

Same external contract as today (`durees_tab(settings, tab, config)`,
callable, return value not otherwise inspected by callers) — confirmed
nothing outside `durees.py` depends on the current `DureesLegacy`/
`DureesHybrid`/`DureesExperimental` class identities: `app.py` just calls
`durees_tab(...)`, and all Durées tests (`test_durees_modes.py`, the
Playwright suites) select by `elem_id`, never by `isinstance`.

## Testing / rollout

No new tests needed — this is a pure internal restructure, not a behavior
change. The existing suite is the regression check:
- 298 non-UI tests (`just test -m "not property"`)
- 19 Durées Playwright tests across `test_durees.py`, `test_durees_toggle.py`,
  `test_durees_experimental.py` (hybrid, experimental, toggle-on/off, and
  the echo-guard regression test)
- `test_durees_modes.py`'s `elem_id`-based mode-shape assertions

All must stay green unchanged. If the refactor needs any test file edited to
pass, that's a signal the refactor changed observable behavior, not just
internal structure — stop and reconcile before proceeding.

## Out of scope

- Actually fixing the remaining Durées perf complaint (separate, still-open
  investigation — this refactor only makes that investigation land in one
  place instead of three).
- `synchro.py`'s parallel `if mode == ...` branching (noted as a candidate
  for the same treatment in the earlier mode-config review, not touched
  here).
- Deleting any mode — stays a 3-way split until the user picks one.
