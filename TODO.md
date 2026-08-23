# TODO

## Durées tab

- [ ] Add "Now" button on time fields — insert current time with one click
- [ ] Add input validation feedback — warn when coords are 0,0 or VA is 0 instead of silent failure
- [ ] Result field styling — left border works for all components but color/font changes don't apply to `gr.Number`
- [ ] Replace `interactivity_updates` server round-trip with client-side JS — toggling `interactive` state and CSS classes on dependent fields when `SegmentedControl` changes is a purely UI concern; no server call needed. Affects Durées and Armées tabs.
  - **Research done, shelved**: The cleanest Gradio approach would be per-choice `js=True` events: add `EventListener(event_name='btn_N')` to `SegmentedControl.EVENTS` (processed by `ComponentMeta` metaclass), fire `trigger('btn_N')` from JS, define one zero-arg `@staticmethod` per mode returning `gr.update(interactive=..., elem_classes=...)` literals (Groovy transpiles to JS, no server call). Two blockers: (1) `gr.HTML` custom events require the event name to appear as a quoted string literal in `js_on_load` for Gradio to route them — dynamically-computed names (template literals) don't work without either hardcoding all names or hijacking `__getattr__`; (2) Groovy's transpiler requires fully hardcoded literal values, no ternary on variables, forcing one separate function body per mode. Both point to missing first-class custom event support in Gradio. Revisit when Gradio adds a proper `custom_event(name)` API.

## Armées tab (was Pontes)

### Cleanup todos
- [ ] Move `_find_tdp_alli` into `nawminator` lib (currently in `nmsite/tabs/armees.py`) — pure game math, no UI dependency

### Bugs
- [ ] **Add/remove row buttons unreliable** — the army list add and remove rows buttons in the Armées tab are not reliable in practice; needs a rework of the row management system

### Future improvements
- [ ] Compact stats display per row (HP, ATK, count) — always visible alongside the paste box
- [ ] Split by DMG — répartir variant that equalises attack power across parts; needs a stats/bonuses input

## Parsing

- [ ] **`parse_joueurs_text` now splits on a literal tab, reliability on mobile unverified** — the joueurs page's copy-paste columns became user-toggleable (players can hide/show Distance, Terrain, État, etc. independently), which needed a proper rewrite (`_find_joueurs_text_columns` in `src/nawminator/parsing.py`): columns are located dynamically (header text when recognizable, else by value shape — coord's brackets, tdc's digits-and-spaces). All 5 fields (coord, tdc, colo_name, player_name, alliance) are required columns — alliance is the only one allowed to be blank *per row*, not the only one allowed to be absent as a column — and the whole parse is rejected if any is missing rather than guessing. This also fixed the old multi-word-name-plus-blank-field ambiguity bug (tried several generic-whitespace heuristics — an alliance max-length constraint, an all-blank-alliance sanity check — none closed the gap without opening a different one; a literal tab has no such ambiguity). The tradeoff: tab reliability across platforms (mobile in particular) isn't verified yet — desktop browsers reliably preserve tabs when copying a rendered `<table>`, but mobile copy-paste might not. Testing against a real mobile paste sample is in progress.

## Tests

- [ ] **Durées UI test coupled to real parser** — `test_player_dropdown_fills_coordinates` (`tests/nmsite/ui/test_durees.py`) loads `players_fixture.html` and runs it through the real `joueurs_source_code_pat` parser just to populate the player dropdown. Any parser/format change (e.g. the NAW joueurs-page format change) breaks this test even though it has nothing to do with parsing logic. Decouple by mocking/stubbing the player list instead of routing through the real HTML fixture.

## App / architecture

- [x] Upgrade Gradio 5 → 6 — **done** but with known regressions (see below).

- [ ] **Speed regression in Armées and Durées tabs** introduced by Gradio 6 upgrade.
  - **Root cause**: Gradio 6's Svelte 5 frontend processes every component update as a reactive event. The Armées tab sends 144 component updates per button click (8 rows × 18 components), plus a 3-round-trip cascade (`on_shift` → `_list_state.change` → `_on_list_change` → `_compute_total`). In Gradio 5 this was fast; Gradio 6 is significantly slower per-update.
  - **Gradio-side**: open bug gradio-app/gradio#12831, no fix in 6.10.0.
  - **Our side**: the 3-round-trip cascade can be eliminated by merging outputs directly into each handler. The 144-update payload needs the static-row architecture replaced with `@gr.render` (or custom components). Both are non-trivial refactors.
  - **Plan**: replace the `N_MAX=8` static-row pattern with custom Gradio components that manage their own state client-side, eliminating the bulk server updates entirely. See time-input component TODO below for the same approach.
  - Gradio 6.10.0 pinned due to separate tab-freeze bug in 6.11+ (gradio-app/gradio#13285, fix pending in PR #13240).

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
