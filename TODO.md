# TODO

## Durées tab

- [ ] Add "Now" button on time fields — insert current time with one click
- [ ] Add input validation feedback — warn when coords are 0,0 or VA is 0 instead of silent failure
- [ ] Result field styling — left border works for all components but color/font changes don't apply to `gr.Number`
- [ ] **Typing into a time field gets randomly overwritten mid-keystroke** (observed 2026-08-24, manual testing during the Gradio upgrade). Root cause: `_start_time`/`_arrival_time` (`durees.py`) are plain `gr.Textbox` fields that are both `.input` triggers *and* members of `all_outputs` for the same `_compute` chain (`durees.py:161-162, 211-222`). `_compute` always returns a value for every output — including an unchanged echo of whichever field is being typed into (e.g. `durees.py:56`) — and Gradio pushes that back to the client on every keystroke regardless of whether it changed. Because the round-trip isn't instant, the echoed value is a stale snapshot of what was typed a keystroke or two ago, clobbering what's been typed since. Already hit this same class of bug in `ArmyInputHTML` (see [[project_army_input_html]]) and in Playwright tests (see `feedback_gradio_textbox_fill.md`'s `keyboard.type` warning) — this is the first time it's been noticed as a live UX problem rather than a test-writing gotcha.
  - **Not yet decided how to fix.** Candidates to investigate rather than a chosen plan: an equality-check/no-op pattern on the `_compute` outputs (same shape as `ArmyInputHTML`'s `on_army_change`, applied to the Durées fields directly, independent of any component swap); and/or the time-input component (`feature/time-input-component`) whose segment-buffered commit model (commits per completed digit-segment, not per keystroke) narrows the race window but — per its `watch('value', ...)` handler, `script.js:641-651` — doesn't structurally remove it, since an external Python push to a field still mid-edit still resets it. Worth investigating both before picking one.
- [x] Replace `interactivity_updates` server round-trip with client-side JS — **done** (`0fb9a38`, 2026-05-23), TODO left stale since. Shipped as per-choice `js=True` events: `SegmentedControl.on_choice(label)` fires `trigger('select_<choice>')`, backed by a dynamic `EventListener` exposed through `__getattr__`; each tab defines one zero-arg `@staticmethod` per mode returning hardcoded `gr.update(...)` literals (Groovy transpiler requirement — no ternary on variables). `interactivity_updates` no longer exists anywhere in the codebase. Live today in both Durées (`durees.py`) and Armées (`armees.py`) — `self._target_sel.on_choice(...)`/`self._tdp_sel.on_choice(...)` with `js=True, show_progress="hidden"`.

## Armées tab (was Pontes)

### Cleanup todos
- [ ] Move `_find_tdp_alli` into `nawminator` lib (currently in `nmsite/tabs/armees.py`) — pure game math, no UI dependency

### Bugs
- [x] ~~Add/remove row buttons unreliable~~ — **likely fixed** (`9389cc6`, 2026-05-22, same rework that addressed the speed regression), filed only ~12h earlier. That commit's own message calls out "Removed `.then(_on_list_change)` from add/all buttons (regression from `4e82796` that caused double execution)" — exactly the shape of an "unreliable" bug. No longer reproduces in manual testing (2026-08-24). Not covered by an automated test (`test_add_row`/`test_delete_row` in `tests/nmsite/ui/test_armees.py` are still empty `pytest.mark.skip(reason="TODO")` stubs), so this is corroborating evidence, not a hard guarantee — reopen if it resurfaces.

### Future improvements
- [ ] Compact stats display per row (HP, ATK, count) — always visible alongside the paste box
- [ ] Split by DMG — répartir variant that equalises attack power across parts; needs a stats/bonuses input

## Parsing

- [ ] **`parse_joueurs_text` now splits on a literal tab, reliability on mobile unverified** — the joueurs page's copy-paste columns became user-toggleable (players can hide/show Distance, Terrain, État, etc. independently), which needed a proper rewrite (`_find_joueurs_text_columns` in `src/nawminator/parsing.py`): columns are located dynamically (header text when recognizable, else by value shape — coord's brackets, tdc's digits-and-spaces). All 5 fields (coord, tdc, colo_name, player_name, alliance) are required columns — alliance is the only one allowed to be blank *per row*, not the only one allowed to be absent as a column — and the whole parse is rejected if any is missing rather than guessing. This also fixed the old multi-word-name-plus-blank-field ambiguity bug (tried several generic-whitespace heuristics — an alliance max-length constraint, an all-blank-alliance sanity check — none closed the gap without opening a different one; a literal tab has no such ambiguity). The tradeoff: tab reliability across platforms (mobile in particular) isn't verified yet — desktop browsers reliably preserve tabs when copying a rendered `<table>`, but mobile copy-paste might not. Testing against a real mobile paste sample is in progress.

## Tests

- [ ] **Durées UI test coupled to real parser** — `test_player_dropdown_fills_coordinates` (`tests/nmsite/ui/test_durees.py`) loads `players_fixture.html` and runs it through the real `joueurs_source_code_pat` parser just to populate the player dropdown. Any parser/format change (e.g. the NAW joueurs-page format change) breaks this test even though it has nothing to do with parsing logic. Decouple by mocking/stubbing the player list instead of routing through the real HTML fixture.

## App / architecture

- [x] Upgrade Gradio 5 → 6 — **done** but with known regressions (see below).

- [ ] **Armées tab: replace the `N_MAX=8` static-row architecture with a client-side-managed list.** Originally filed 2026-05-20 as "Speed regression in Armées and Durées tabs" right after the Gradio 6 upgrade; the actual slowness was fixed two days later (see below) and TODO.md was never updated to match — reworded 2026-08-24 to describe what's still actually true.
  - **What was fixed** (`9389cc6`, 2026-05-22, "Rework Armées tab event wiring — targeted gr.update() to silence cascade"): the 3-round-trip cascade (`on_shift` → `_list_state.change` → `_on_list_change` → `_compute_total`) is now 2 hops — `_on_list_change` computes the TDP/duration fields inline instead of a separate chained `.then()`. The blanket "push values to all `N_MAX` slots" payload is gone — `_updates_add`/`_updates_toggle_all`/`_updates_repartir` (`armees.py`) send a no-op `gr.update()` to every row that didn't change. `on_army_change` short-circuits via `Army.__eq__` so a no-op edit never reaches `_list_state` at all, killing the cascade at the source. Net effect: no longer feels slow in practice (confirmed 2026-08-24).
  - **What's still true**: the row *list* itself is still server-managed — `N_MAX=8` fixed `Row` containers exist up front, and add/delete/répartir/toggle-all are still server round-trips that toggle `visible=True/False` on pre-rendered containers rather than a client-side-owned list. (Not to be confused with `ArmyInputHTML`, which already is a custom component — but it owns a single row's 15-unit-type *value*, not the list of rows.)
  - **Gradio-side**: gradio-app/gradio#12831 (the general Gradio-6-is-slower-per-update report this was originally pinned on) was closed by a maintainer with "Going to close for lack of followup" — closed for reporter inactivity, not a technical rejection of the report. Not blocking us either way since our own fix above addressed the actual symptom.
  - **Plan, if picked back up**: replace the static rows with `@gr.render` or a custom component that manages its own state client-side, eliminating server round-trips for structural operations entirely. Same direction as the time-input component TODO below. Given the 9389cc6 fix already removed the pain, this is now an architecture-cleanup nice-to-have, not an urgent fix.
  - ~~Gradio 6.10.0 pinned due to separate tab-freeze bug in 6.11+ (gradio-app/gradio#13285, fix pending in PR #13240)~~ — **resolved 2026-08-24**: fix shipped in 6.16.0 (PR #13240), upgraded to 6.25.0 (`pyproject.toml`). Verified: full test suite green (`just test`), and manually hammered tab switching in/out of Armées (dataframe/accordion-heavy tab, the exact trigger for #13285) with Playwright/Firefox against the dev server — no freeze, no console errors, no visual breakage.

- [ ] CSS modularity — move tab-specific CSS out of `app.py` (see TODO comment in that file)

- [ ] Time input component — reusable picker supporting both `HH:MM:SS` and ajhms notations
  - Both formats are interchangeable in the game (not "clock time vs duration", just two notations for the same value)
  - Affects multiple tabs; needs to work well on mobile (scroll/swipe) and desktop (mouse scroll)
  - Gradio's native `gr.DateTime` is too heavy (forces a date), plain `gr.Textbox` has no scroll/touch support
  - **Chosen direction: enhanced `gr.HTML`** — newer Gradio (5/6) makes `gr.HTML` powerful enough:
    - `server_functions`: Python functions callable directly from JS inside the component
    - `js_on_load` + `trigger`: JS can fire Gradio events natively
    - `head`: load external JS/CSS libraries (e.g. a touch-friendly time picker lib)
    - No Svelte build pipeline needed — stays within the existing project
  - Full custom Gradio component (Svelte) is the cleanest architecture but high setup cost; Gradio team aware of this pain point (issue #12074)
  - One component needed that accepts/displays both formats, auto-detecting or toggling between them
  - **Substantial unmerged progress exists on `feature/time-input-component`** (last commit 2026-08-21, titled "Tmp" — a WIP checkpoint, not a clean finish): a working `gr.HTML`-based component (`time_input.py`/`script.js`/`style.css`) covering duration/clock_time/datetime modes, AJHMS + HH:MM:SS toggle, quick-fill pills, copy, reset, scroll/keyboard/touch-editable segments; demoed in a Réglages/Settings tab; has its own Playwright UI test suite (`tests/nmsite/ui/test_time_input.py`). Not on `main`. Before starting this from scratch, check out that branch and assess how finished it actually is.

- [ ] General user feedback / error notifications
  - Gradio has built-in toast support: `gr.Warning()`, `gr.Error()`, `gr.Info()` callable from any event handler, no extra UI needed
  - Currently all tabs fail silently (bad inputs just return unchanged values with no message)
  - Plan: replace silent `return` fallbacks with `gr.Warning(...)` calls, use `gr.Error` for unexpected failures
  - Convention to establish: Warning = soft/missing input, Error = hard/unexpected failure
  - Each tab owns its own messages (no central registry needed given tab-based structure)
  - Start with Durées tab as a template, then roll out to other tabs

## Documentation conventions

- [ ] **Define a convention for hybrid human/AI code documentation, then refactor to match it.** A human reading code has small context but infers a lot from little; an AI agent (Claude) has much more context available per-session but none carried over between sessions, so it needs the "why"/design-rationale spelled out explicitly to avoid re-introducing bugs it already fixed once (e.g. the synchro tab's BBCode-link-in-shared-DataFrame bug). What's "enough" documentation differs a lot between the two audiences, and this project has no established docstring/comment convention to build on (most functions have none, by design — code is meant to be readable at a glance). Pattern applied twice now in `src/nmsite/tabs/synchro.py` (2026-08-23): `format_copy_data_table` first, then `format_copy_data_discord`/`_format_discord_row`/`_discord_row_widths` — short, caller-focused docstrings (what a function does) plus inline comments at the exact line each design decision applies to (why), rather than one dense docstring or a separate linked doc file. Consistent enough now to call a working pattern, not yet a written-down, generalizable guideline. Next steps: (1) look at what other projects/teams do for hybrid human/AI documentation for inspiration, (2) write the actual guideline once informed by that, (3) refactor the rest of the codebase's docstrings/comments to match (most files haven't been touched yet — this has so far only been applied where Claude happened to be already working).

## Devcontainer

- [ ] Upgrade base image back to `ubuntu` (latest) once Playwright supports Ubuntu 26.04 — pinned to `ubuntu-24.04` as a workaround. Track [microsoft/playwright#40117](https://github.com/microsoft/playwright/issues/40117); they plan to start work once a GHA runner image is available. Check back ~mid-June 2026.
