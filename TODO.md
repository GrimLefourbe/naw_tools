# TODO

## Durées tab

- [ ] Add "Now" button on time fields — insert current time with one click
- [ ] Add input validation feedback — warn when coords are 0,0 or VA is 0 instead of silent failure
- [ ] Result field styling — left border works for all components but color/font changes don't apply to `gr.Number`

## App / architecture

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
  - **First step**: check current Gradio version and whether `server_functions` / `js_on_load` API is available
  - One component needed that accepts/displays both formats, auto-detecting or toggling between them

- [ ] General user feedback / error notifications
  - Gradio has built-in toast support: `gr.Warning()`, `gr.Error()`, `gr.Info()` callable from any event handler, no extra UI needed
  - Currently all tabs fail silently (bad inputs just return unchanged values with no message)
  - Plan: replace silent `return` fallbacks with `gr.Warning(...)` calls, use `gr.Error` for unexpected failures
  - Convention to establish: Warning = soft/missing input, Error = hard/unexpected failure
  - Each tab owns its own messages (no central registry needed given tab-based structure)
  - Start with Durées tab as a template, then roll out to other tabs
