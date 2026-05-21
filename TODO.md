# TODO

## Durées tab

- [ ] Add "Now" button on time fields — insert current time with one click
- [ ] Add input validation feedback — warn when coords are 0,0 or VA is 0 instead of silent failure
- [ ] Result field styling — left border works for all components but color/font changes don't apply to `gr.Number`
- [ ] Replace `interactivity_updates` server round-trip with client-side JS — toggling `interactive` state and CSS classes on dependent fields when `SegmentedControl` changes is a purely UI concern; no server call needed. Affects Durées and Armées tabs.

## Armées tab (was Pontes)

### Cleanup todos
- [ ] Move `_find_tdp_alli` into `nawminator` lib (currently in `nmsite/tabs/pontes.py`) — pure game math, no UI dependency

### Future improvements
- [ ] Compact stats display per row (HP, ATK, count) — always visible alongside the paste box
- [ ] Split by DMG — répartir variant that equalises attack power across parts; needs a stats/bonuses input

## App / architecture

- [x] Upgrade Gradio 5 → 6 — **done** but with known regressions (see below).

- [ ] **Speed regression in Armées and Durées tabs** introduced by Gradio 6 upgrade.
  - **Root cause**: Gradio 6's Svelte 5 frontend processes every component update as a reactive event. The Armées tab sends 144 component updates per button click (8 rows × 18 components), plus a 3-round-trip cascade (`on_shift` → `_list_state.change` → `_on_list_change` → `_compute_total`). In Gradio 5 this was fast; Gradio 6 is significantly slower per-update.
  - **Gradio-side**: open bug gradio-app/gradio#12831, no fix in 6.10.0.
  - **Our side**: the 3-round-trip cascade can be eliminated by merging outputs directly into each handler. The 144-update payload needs the static-row architecture replaced with `@gr.render` (or custom components). Both are non-trivial refactors.
  - **Plan**: replace the `N_MAX=8` static-row pattern with custom Gradio components that manage their own state client-side, eliminating the bulk server updates entirely. See time-input component TODO below for the same approach.
  - Gradio 6.10.0 pinned due to separate tab-freeze bug in 6.11+ (gradio-app/gradio#13285, fix pending in PR #13240).

- [ ] CSS modularity — move tab-specific CSS out of `app.py` (see TODO comment in that file)

- [ ] JS/CSS in custom HTML components — currently embedded as Python strings in `interface.py` (no syntax highlighting). Consider moving to separate `.js`/`.css` files read at class definition time (`Path(__file__).parent / "army_input.js"`). Only worth doing once there are enough components to establish a shared convention — revisit when a third `gr.HTML` component is added (the time input below would be it).

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

- [ ] General user feedback / error notifications
  - Gradio has built-in toast support: `gr.Warning()`, `gr.Error()`, `gr.Info()` callable from any event handler, no extra UI needed
  - Currently all tabs fail silently (bad inputs just return unchanged values with no message)
  - Plan: replace silent `return` fallbacks with `gr.Warning(...)` calls, use `gr.Error` for unexpected failures
  - Convention to establish: Warning = soft/missing input, Error = hard/unexpected failure
  - Each tab owns its own messages (no central registry needed given tab-based structure)
  - Start with Durées tab as a template, then roll out to other tabs

## Devcontainer

- [ ] Upgrade base image back to `ubuntu` (latest) once Playwright supports Ubuntu 26.04 — pinned to `ubuntu-24.04` as a workaround. Track [microsoft/playwright#40117](https://github.com/microsoft/playwright/issues/40117); they plan to start work once a GHA runner image is available. Check back ~mid-June 2026.
