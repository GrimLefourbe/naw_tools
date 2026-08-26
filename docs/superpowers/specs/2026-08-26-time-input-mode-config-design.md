# TimeInput mode as an init-time config flag

## Context

`TimeInput` is currently wired into `durees.py`/`synchro.py` as a runtime opt-in:
both the old plain-text fields and the new `TimeInput` fields are always
constructed and mounted, a Réglages-tab checkbox (persisted to localStorage)
picks which pair is visible, and a `_mirror_to_new`-style sync keeps the
hidden pair truthful. This is "Hybrid" mode in the terms below, and as of
2026-08-26 it's the *only* mode — every server always builds both field sets
regardless of who's actually looking at them.

Two problems with that as a permanent state:

- **Performance**: every extra mounted component, extra `.input()`/`.then()`
  chain, and extra visibility-toggle round trip is overhead paid by everyone,
  including people who never touch the new fields. There's no way to measure
  "how much does TimeInput really cost" without also measuring "and the
  dual-mount plumbing on top of it" — the two are conflated.
- **Fairness**: comparing the old and new UI for real testing means comparing
  them dual-mounted-and-toggled vs. neither is being run standalone the way a
  real deployment would run it.

The fix: make which field set gets built a decision made once, at server
startup, from `Config` — not a per-request runtime branch. Three modes:

- **Legacy** — only the old plain-text fields. No `TimeInput`, no toggle, no
  mirroring. This is (almost exactly) what `durees.py`/`synchro.py` looked
  like before `TimeInput` was ever wired in.
- **Hybrid** — today's behavior, unchanged: both field sets, Réglages
  checkbox, dual-mount.
- **Experimental** — only the `TimeInput` fields. No old fields, no toggle,
  no mirroring (there's nothing to mirror to).

Presets (`src/nmsite/config.py`): `S1="hybrid"`, `S2="legacy"`,
`DEV="experimental"`. New presets for other combinations (e.g. an
`S1_LEGACY` for an A/B run) are just new dict entries — this design doesn't
need to anticipate them.

Out of scope: `armees.py`/`hunt.py` (never had `TimeInput` wired in, not
touched by this change either).

## `Config`

```python
@dataclass
class Config:
    ...
    time_input_mode: t.Literal["legacy", "hybrid", "experimental"] = "legacy"
```

Default `"legacy"` matches pre-TimeInput reality for any preset that doesn't
set it explicitly.

## `durees.py`: one file, four classes

Per discussion, `durees.py` stays a single file (it's still "the Durées tab"
as a unit) but splits internally:

- **`DureesCore`** — a stateless namespace (staticmethods, no instances) for
  everything mode-agnostic:
  - The existing pure functions, unchanged: `_parse_time`, `_times_to_secs`,
    `_apply_time_defaults`, `_shift_time`, `_compute`, `_TARGETS`.
  - The `TimeInput` ↔ str adapters, unchanged: `_duration_str_to_td`,
    `_duration_td_to_str`, `_time_obj_to_str`. Used by both `DureesHybrid`
    and `DureesExperimental`; unused (but harmless) for `DureesLegacy`.
  - These move from module-level functions into `DureesCore` as
    `@staticmethod`s so all three mode classes call them the same way
    (`DureesCore.compute(...)`), rather than a mix of bare-function calls and
    class-qualified ones.

- **`DureesLegacy`** — ports the pre-`TimeInput` implementation (the version
  in git history before `TimeInput` was wired in) as directly as possible:
  4-tuple interactivity methods, `_va`/`_duration`/`_start_time`/
  `_arrival_time` as the only fields, no `TimeInput` import needed, no
  visibility toggling, no `tab.select()` handler.

- **`DureesHybrid`** — today's `DureesTab`, renamed, with its own pure-logic
  calls redirected to `DureesCore`. Behaviorally unchanged: dual-mount,
  Réglages toggle, `_mirror_to_new` with the `skip=` echo guard, `tab.select()`
  re-applying visibility. This class is the one under the least risk of
  regression — it's already fixed and tested.

- **`DureesExperimental`** — new. `_va` stays `gr.Number`; `_duration`,
  `_start_time`, `_arrival_time` are `TimeInput` directly (no old sibling,
  no dual-mount, no `tab.select()` visibility handler needed since there's
  only one set of fields to show).

  Needs the **same self-write echo guard as Hybrid**, applied differently:
  Hybrid's bug was `_mirror_to_new` writing back into the very `TimeInput`
  that triggered the chain; Experimental doesn't have a separate mirror step,
  but `DureesCore.compute`'s own output tuple includes the field currently
  being edited (e.g. editing `start` in Arrivée mode — `compute` returns
  `start` unchanged, but "unchanged" still means Gradio pushes that value
  back to the client as an update). Each of the three `TimeInput.input()`
  handlers here wraps `DureesCore.compute` with a small adapter that converts
  its own field to/from string and returns `gr.skip()` for its own output
  slot — same principle as Hybrid's `skip=`, just applied directly to
  `compute`'s outputs instead of a separate mirror call.

  Interactivity: only the plain non-`js=True` `select` pass is needed (all
  editable fields are `TimeInput`, so the `js=True` per-choice fast path
  would never reach any of them — no point registering it).

  The echo guard only applies to the duration/start/arrival trio. `_va`
  stays a plain `gr.Number` in every mode — it has no edit-mode concept to
  knock a user out of, so `compute`'s unchanged echo back into it is
  harmless and needs no `gr.skip()`.

- **`durees_tab(settings, tab, config)`** — factory:
  ```python
  _MODES = {"legacy": DureesLegacy, "hybrid": DureesHybrid, "experimental": DureesExperimental}
  def durees_tab(settings, tab, config):
      return _MODES[config.time_input_mode](settings, tab)
  ```
  `DureesLegacy`/`DureesExperimental` accept and ignore `tab` (kept for a
  uniform constructor signature across the three; only Hybrid uses it).

`app.py` threads `config` into the existing `durees.durees_tab(settings,
durees_tab)` call.

## `synchro.py`: one class, inline branching

Small enough (one field pair) that splitting it into classes isn't worth it.
`SynchroTab.set_layout`/`configure_triggers` gain a `mode` (read from
`self.config.time_input_mode`, already available) with a plain
`if mode == "hybrid": ... elif mode == "legacy": ... else: ...` per method —
each branch is a handful of lines (construct one `gr.DateTime` or one
`TimeInput`, or both + the visibility `.change()`).

## `settings.py`

`Settings.__init__` only builds `time_input_toggle` /
`time_input_enabled_state` (checkbox, `gr.State`, localStorage JS) when
`self._config.time_input_mode == "hybrid"`. Not just hidden — not
constructed at all, so a legacy/experimental server carries zero trace of
the toggle. `synchro.py`'s hybrid branch is the only remaining reader of
`settings.time_input_enabled_state`; `DureesHybrid` is the other.

## Tests

`tests/nmsite/conftest.py`'s `gradio_server` (and the `live_page` fixture
built on it) gains a `mode` parameter, default `"experimental"` (matching
DEV's new default) — most existing test files pass nothing and keep testing
DEV as-is. `test_durees_toggle.py`/`test_synchro_toggle.py` (the Hybrid-only
toggle-flow tests) request `mode="hybrid"` explicitly.

Because the fixture launches a subprocess with `NMSITE_CONFIG=<name>`, and
DEV's mode is now fixed to `"experimental"` in the preset dict, exercising a
different mode means launching with a different preset — add `DEV_HYBRID`
(`dev=True`, `time_input_mode="hybrid"`) for the toggle-flow tests to target.
A `DEV_LEGACY` isn't needed yet since nothing currently tests Legacy
specifically (Legacy is closest to pre-TimeInput code, already covered by
the tests that predate this whole feature).

**Explicitly not in scope for this pass** (tracked as a TODO.md item, must be
resolved before closing `feature/time-input-component`): `test_time_input.py`
exercises a Settings-tab-only demo harness (`ti_demo_a`..`e`, `Config.dev`-gated)
rather than the real Durées/Synchro fields. That's a pre-existing issue this
change doesn't make worse, but doesn't fix either.

## Verification

- `just test -m "not property"` — full fast suite.
- Explicit run against each mode: `NMSITE_CONFIG=DEV` (experimental),
  `NMSITE_CONFIG=DEV_HYBRID` (hybrid), a temporary `NMSITE_CONFIG=DEV_LEGACY`
  override for manual legacy verification — confirm Durées/Synchro render
  and compute correctly in each, and that legacy/experimental servers show
  zero trace of the other modes' components (elem_ids absent from
  `demo.blocks`, not just hidden).
- Existing Hybrid-mode UI tests (`test_durees_toggle.py`,
  `test_synchro_toggle.py`, including the two regression tests from this
  session — the loopback fix and the wrap-around-carry fix) pass unchanged
  against `mode="hybrid"`.
