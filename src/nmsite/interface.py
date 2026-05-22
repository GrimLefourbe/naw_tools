import json
import gradio as gr

import nawminator as nm
import datetime as dt

import typing as t
if t.TYPE_CHECKING: 
    from gradio.components import FormComponent
### INPUTS


class ArmyInput:
    def __init__(self):
        army_state = gr.State(nm.army.Army())
        input_box = gr.Textbox(placeholder="Coller Armée", scale=0, show_label=False, container=False)
        unit_boxes = []
        with gr.Accordion("Units", open=False):
            with gr.Group():
                for _, short_name, _ in nm.army.unit_names:
                    with gr.Row():
                        gr.Text(
                            short_name,
                            max_lines=1,
                            show_label=False,
                            interactive=False,
                            container=False,
                            min_width=100,
                        )
                        unit_boxes.append(gr.Number(scale=2, precision=0, label=short_name, show_label=False, container=False))

        @gr.on(
            triggers=[input_box.input],
            inputs=input_box,
            outputs=[army_state, *unit_boxes],
            show_progress="hidden",
        )
        def parse_army(input_text):
            army = nm.army.Army.from_str(input_text)
            return army, *army._units

        @gr.on(
            triggers=[i.input for i in unit_boxes],
            inputs=unit_boxes,
            outputs=army_state,
        )
        def parse_units(*inputs: tuple[str]):
            return nm.army.Army(inputs) # type: ignore

        self.unit_boxes = unit_boxes
        self.state = army_state


class LevelsInput:
    def __init__(self, hero_enabled: bool, atk=True, min_width=200):
        self.state = gr.State(nm.levels.Levels())
        self.input_fields: list[FormComponent] = []
        # self.possible_fields = [
        #     "mandibule",
        #     "carapace",
        #     "hero_lvl",
        #     "hero_type",
        #     "train",
        #     "dome",
        #     "loge",
        #     "alliance",
        #     "special",
        # ]
        # self.enabled = {
        #     k: k in enabled for k in self.possible_fields
        # }
        self.hero_enabled = hero_enabled
        self._build_layout(atk, min_width)
        self._configure_triggers()

    def _build_layout(self, atk, min_width):
        half_min_width = (min_width // 2) - 5

        with gr.Column(min_width=200):
            self._research_block(min_width=half_min_width)
            self._hero_spe_block(min_width=half_min_width)

            self._buildings_block(atk, half_min_width)
            self.input_fields.append(self.alliance_input)

            with gr.Group(), gr.Row(equal_height=True):
                self.input_box = gr.Textbox(
                    placeholder="Coller Niveaux",
                    show_label=False, 
                    max_lines=3, 
                    scale=4, 
                    min_width=60,
                    container=False,
                    render=False,
                )
                self.paste_btn = gr.Button("📥︎", scale=1, variant="secondary", size="sm", min_width=20)
                self.input_box.render()
                self.copy_btn = gr.Button("📤︎", scale=1, variant="secondary", size="sm", min_width=20)

    def _research_block(self, min_width):
        with gr.Group(), gr.Row(): #Mandi/Cara section
            with gr.Column(min_width=min_width):
                gr.Text("Mandibule", scale=3, max_lines=0, container=False)
                self.mandi_input = gr.Number(
                    label="Mandi",
                    minimum=0,
                    scale=1,
                    show_label=False,
                    container=False,
                )
            with gr.Column(min_width=min_width):
                gr.Text("Carapace", scale=3, max_lines=0, container=False)
                self.cara_input = gr.Number(
                    label="Cara",
                    minimum=0,
                    scale=1,
                    show_label=False,
                    container=False,
                )
        self.input_fields.extend([
            self.mandi_input,
            self.cara_input,
        ])

    def _hero_spe_block(self, min_width):
        with gr.Row(): #Hero/Spe section
            with gr.Group(visible=self.hero_enabled):
                # gr.Text("Hero", max_lines=0, container=False)
                self.herolvl_input = gr.Number(
                    value=0,
                    minimum=0,
                    maximum=180,
                    scale=2,
                    container=False,
                    min_width=10,
                )
                self.herotype_input = gr.Dropdown(
                    value=nm.levels.HeroType.ATTAQUE,
                    choices=list(nm.levels.HeroType),
                    scale=3,
                    container=False,
                    min_width=10,
                )
                self.input_fields.append(self.herolvl_input)
                self.input_fields.append(self.herotype_input)
            with gr.Group(elem_classes=["smgroup"]), gr.Row():
                gr.Textbox("Spe", max_lines=0, container=False, min_width=45, scale=25)
                self.spe_input = gr.Number(
                    value=0,
                    minimum=0,
                    maximum=5,
                    container=False,
                    min_width=50,
                    scale=1,
                )
                self.input_fields.append(self.spe_input)
            self.alliance_input = gr.Dropdown(
                value=nm.levels.AllianceType.NONE,
                label="Alliance",
                choices=[
                    *list(nm.levels.AllianceType),
                ],
                container=False,
                min_width=105,
                scale=0,
            )
    def _buildings_block(self, atk: bool, min_width: int):
        with gr.Group(visible=not atk), gr.Row(): #Buildings section
            with gr.Column(min_width=min_width):
                gr.Text("Dôme", max_lines=0, container=False)
                self.dome_input = gr.Number(label="Dôme", minimum=0, show_label=False, container=False)
            with gr.Column(min_width=min_width):
                gr.Text("Loge", max_lines=0, container=False)
                self.loge_input = gr.Number(label="Loge", minimum=0, show_label=False, container=False)
        self.input_fields.extend([self.dome_input, self.loge_input])

    def _configure_triggers(self):
        @gr.on(
            triggers=self.input_box.input,
            inputs=self.input_box,
            outputs=[*self.input_fields, self.state],
            show_progress="hidden",
        )
        def on_text_change(text_input: str):
            l = nm.levels.Levels.from_str(text_input)
            print(f"Updating with {l.alliance}")
            return (
                l.mandibule,
                l.carapace,
                l.hero_lvl,
                l.hero_type,
                l.special,
                l.dome,
                l.loge,
                l.alliance,
                l,
            )

        @gr.on(
            triggers=[inp.change for inp in self.input_fields], # type: ignore
            inputs=self.input_fields,
            outputs=[self.state, self.input_box],
            show_progress="hidden",
        )
        def on_input_change(m, c, hl, ht, s, d, l, a):
            print(hl, ht)
            args = {}
            if hl is not None and ht is not None:
                args = {"hero_lvl": hl, "hero_type": ht}
            l = nm.levels.Levels(
                mandibule=m, 
                carapace=c,
                **args,
                train=0, 
                dome=d, 
                loge=l, 
                alliance=nm.levels.AllianceType(a), 
                special=s
                )
            return l, l.to_str(hero_enabled=self.hero_enabled)
        
        self.copy_btn.click(
            lambda x: x, inputs=self.input_box, outputs=None, show_progress="hidden",
            js="x => { navigator.clipboard.writeText(x); return []; }" # Gradio expects a list return for outputs
        )
        self.paste_btn.click(
            on_text_change, 
            inputs=self.input_box,
            outputs=[*self.input_fields, self.state],
            show_progress="hidden",
            js="() => navigator.clipboard.readText().then(t => [t])" # Gradio expects a list return for outputs
        )



def _merge_elem_classes(kwargs: dict, cls: str) -> None:
    existing = kwargs.pop("elem_classes", [])
    if isinstance(existing, str):
        existing = [existing]
    kwargs["elem_classes"] = list(existing) + [cls]



class SegmentedControl(gr.HTML):
    """Stacked button selector with instant client-side visual feedback.

    Subclasses gr.HTML using Gradio 6's interactive HTML API. Clicking a button
    updates the selection immediately (no server roundtrip for the visual), then
    fires ``trigger('input')`` so the Python ``.input()`` handler runs.
    ``watch()`` re-syncs the highlight if the server updates the value as output.

    Args:
        choices: Ordered list of option labels shown as stacked buttons.
        value: Initially selected label; must be one of ``choices``.
        **kwargs: Forwarded to ``gr.HTML`` (e.g. ``elem_id``, ``visible``).

    Wiring:
        sel = SegmentedControl(["A", "B", "C"], value="B", elem_id="my_sel")
        sel.input(fn, inputs=[sel], outputs=[...])

    The component's value (accessible as an input) is the selected label string.
    """

    _CSS = r"""
        .seg-control {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            border: 1px solid var(--border-color-primary, rgba(0,0,0,0.15));
            border-radius: var(--radius-lg, 8px);
            overflow: hidden;
        }
        .seg-btn {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 36px;
            padding: 8px 12px;
            cursor: pointer;
            border: none;
            background: var(--background-fill-primary, white);
            color: var(--body-text-color);
            font-size: .9rem;
            font-weight: 600;
            text-align: center;
            transition: background .1s, color .1s;
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }
        .seg-btn + .seg-btn {
            border-top: 1px solid var(--border-color-primary, rgba(0,0,0,0.1));
        }
        .seg-btn:hover:not(.selected) {
            background: color-mix(in srgb, var(--color-accent) 10%, var(--background-fill-primary, white));
        }
        .seg-btn.selected {
            background: var(--color-accent);
            color: var(--color-accent-text, white);
        }
    """

    _JS = r"""
        function updateSelection(val) {
            element.querySelectorAll('.seg-btn').forEach(btn => {
                btn.classList.toggle('selected', btn.dataset.value === String(val));
            });
        }
        updateSelection(props.value);
        watch("value", () => { updateSelection(props.value); trigger('change'); });
        element.addEventListener('click', e => {
            const btn = e.target.closest('.seg-btn');
            if (!btn) return;
            updateSelection(btn.dataset.value);
            props.value = btn.dataset.value;
            trigger('input');
            trigger('change');
        });
    """

    def __init__(self, choices: list[str], value: str, **kwargs):
        buttons_html = "".join(
            f'<button class="seg-btn" data-value="{c}">{c}</button>'
            for c in choices
        )
        _merge_elem_classes(kwargs, "seg-wrapper")
        kwargs.setdefault('container', False)
        kwargs.setdefault('padding', False)
        kwargs.setdefault('apply_default_css', False)
        kwargs.setdefault('show_label', False)
        super().__init__(
            value=value,
            html_template=f'<div class="seg-control">{buttons_html}</div>',
            css_template=self._CSS,
            js_on_load=self._JS,
            **kwargs,
        )


class ArmyInputHTML(gr.HTML):
    """HTML-based interactive army input using Gradio 6's interactive HTML API.

    props.value is a JSON string:
        {"units": [...15 ints...], "raw": "...", "recap": "...", "error": null, "panel": "none"}

    panel: "none" | "string" | "units" | "import"
    """

    _UNIT_SHORTS = [short for _, short, _ in nm.army.unit_names]

    # TODO: ArmyInputHTML doesn't pack flush inside gr.Group like native Gradio components.
    # Root cause: css_template is auto-scoped (Svelte hash on every selector), so rules with
    # ancestor selectors like `.gr-group .ai-widget` never match the group wrapper outside this
    # component. Gradio's own group rule strips border/radius from the direct child (.ai-wrapper),
    # but the visible border lives on the inner .ai-widget. Moving the border to .ai-wrapper
    # doesn't work because gr.HTML with container=False applies its own border:none to the outer
    # wrapper. Global CSS in app.py can reach .gr-group but requires !important fights that are
    # brittle. The intended solution is probably a proper Svelte-based custom component rather
    # than the css_template approach — investigate if/when we need true group integration.

    # --- Widget layout: wrapper, header row, recap display, no-label / btns-right variants ---
    _CSS_LAYOUT = r"""
.ai-wrapper { position: relative; overflow: visible; padding: 0 !important; margin: 0 !important; }
.ai-widget {
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg, 8px);
    padding: 8px 10px;
    background: var(--block-background-fill);
}
.ai-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
}
.ai-label { font-size: .85rem; font-weight: 600; color: var(--body-text-color-subdued); flex: 1; }
.ai-btns { display: flex; gap: 4px; }
.ai-recap {
    font-size: .85rem;
    color: var(--body-text-color);
    min-height: 1.2em;
    word-break: break-word;
}
.ai-recap-empty { color: var(--body-text-color-subdued); font-style: italic; }

/* no label: widget is a single flex row (buttons inline with recap) */
.ai-widget.no-label { display: flex; align-items: center; gap: 8px; }
.ai-widget.no-label .ai-header { margin-bottom: 0; flex-shrink: 0; }
.ai-widget.no-label .ai-recap { flex: 1; order: 1; }
/* btns-right (no label): recap visually before buttons */
.ai-widget.no-label.btns-right .ai-recap { order: -1; }

/* popover anchoring: btns-right → right edge, otherwise left edge */
.ai-widget.btns-right .ai-string-panel,
.ai-widget.btns-right .ai-units-popover { right: 0; left: auto; }
"""

    # --- Action buttons (📋 / ✏️ / 📥) in the header ---
    _CSS_BUTTONS = r"""
.ai-btn {
    padding: 2px 7px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1.5;
    transition: background .1s;
    color: var(--body-text-color);
}
.ai-btn:hover:not(.active) {
    background: color-mix(in srgb, var(--color-accent) 15%, var(--background-fill-secondary));
}
.ai-btn.active { background: var(--color-accent); }
"""

    # --- String-paste panel (shared popover base + textarea, error, confirm) ---
    _CSS_STRING_PANEL = r"""
.ai-string-panel, .ai-units-popover {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: auto;
    z-index: 200;
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg, 8px);
    padding: 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,.18);
    max-height: 320px;
    overflow-y: auto;
}
.ai-string-panel { min-width: 280px; }
.ai-textarea {
    width: 100%;
    min-height: 60px;
    padding: 6px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    color: var(--body-text-color);
    font-size: .85rem;
    resize: vertical;
    box-sizing: border-box;
    font-family: monospace;
}
.ai-textarea:focus { outline: 2px solid var(--color-accent); outline-offset: -1px; }
.ai-error {
    color: var(--error-text-color, #dc2626);
    font-size: .8rem;
    margin-top: 4px;
}
.ai-confirm {
    margin-top: 6px;
    padding: 4px 12px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    cursor: pointer;
    font-size: .85rem;
    color: var(--body-text-color);
}
.ai-confirm:hover {
    background: color-mix(in srgb, var(--color-accent) 10%, var(--background-fill-secondary));
}
"""

    # --- Unit-by-unit editor popover ---
    _CSS_UNITS_EDITOR = r"""
.ai-units-popover { min-width: 150px; }
.ai-units-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 8px;
    align-items: center;
}
.ai-unit-label {
    font-size: .8rem;
    font-weight: 600;
    color: var(--body-text-color);
    text-align: right;
    user-select: none;
}
.ai-unit-input {
    width: 90px;
    padding: 2px 5px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    color: var(--body-text-color);
    font-size: .8rem;
    text-align: right;
}
.ai-unit-input:focus { outline: 2px solid var(--color-accent); outline-offset: -1px; }
"""

    _CSS = _CSS_LAYOUT + _CSS_BUTTONS + _CSS_STRING_PANEL + _CSS_UNITS_EDITOR

    # --- DOM setup: build unit-input grid, cache element references, state helper ---
    _JS_SETUP = r"""
const widget = element.querySelector('.ai-widget');
const unitShorts = JSON.parse(widget.dataset.unitShorts);

const grid = element.querySelector('.ai-units-grid');
unitShorts.forEach((short, i) => {
    const lbl = document.createElement('span');
    lbl.className = 'ai-unit-label';
    lbl.textContent = short;
    const inp = document.createElement('input');
    inp.type = 'number';
    inp.className = 'ai-unit-input';
    inp.dataset.idx = String(i);
    inp.min = '0';
    inp.step = '1';
    inp.value = '0';
    grid.appendChild(lbl);
    grid.appendChild(inp);
});

function getState() {
    try { return JSON.parse(props.value); }
    catch(e) { return {units: Array(unitShorts.length).fill(0), raw: '', recap: '', error: null, panel: 'none'}; }
}

const recapEl = element.querySelector('.ai-recap');
const stringPanel = element.querySelector('.ai-string-panel');
const unitsPopover = element.querySelector('.ai-units-popover');
const textarea = element.querySelector('.ai-textarea');
const errorDiv = element.querySelector('.ai-error');
const unitInputs = Array.from(grid.querySelectorAll('.ai-unit-input'));
const btns = Array.from(element.querySelectorAll('.ai-btn'));
"""

    # --- Render: sync DOM to state, react to external value updates ---
    _JS_RENDER = r"""
function render(state) {
    if (state.recap) {
        recapEl.textContent = state.recap;
        recapEl.classList.remove('ai-recap-empty');
    } else {
        recapEl.textContent = 'Armée vide';
        recapEl.classList.add('ai-recap-empty');
    }

    unitInputs.forEach((inp, i) => {
        if (document.activeElement !== inp) inp.value = (state.units || [])[i] ?? 0;
    });

    const showStr = state.panel === 'string';
    stringPanel.style.display = showStr ? '' : 'none';
    if (showStr && document.activeElement !== textarea) textarea.value = state.raw || '';

    if (state.error) { errorDiv.textContent = state.error; errorDiv.style.display = ''; }
    else errorDiv.style.display = 'none';

    unitsPopover.style.display = state.panel === 'units' ? '' : 'none';

    btns.forEach(btn => {
        const a = btn.dataset.action;
        btn.classList.toggle('active',
            (a === 'string' && state.panel === 'string') ||
            (a === 'units' && state.panel === 'units'));
    });
}

render(getState());
watch("value", () => { try { render(JSON.parse(props.value)); trigger('change'); } catch(e) {} });
"""

    # --- Server bridge: send state to Python, render result, fire Gradio events ---
    _JS_SERVER = r"""
async function processAndRender(state) {
    const newState = await server.process_army(state);
    render(newState);
    props.value = JSON.stringify(newState);
    trigger('input');
    trigger('change');
}
"""

    # --- Event listeners: buttons, string confirm, paste, unit inputs, outside click ---
    _JS_EVENTS = r"""
element.addEventListener('click', e => {
    const btn = e.target.closest('.ai-btn');
    if (!btn) return;
    const state = getState();
    const action = btn.dataset.action;
    if (action === 'string') {
        // Toggle panel client-side only — no server call needed
        state.panel = state.panel === 'string' ? 'none' : 'string';
        props.value = JSON.stringify(state);
        render(state);
        if (state.panel === 'string') setTimeout(() => textarea.focus(), 0);
    } else if (action === 'units') {
        state.panel = state.panel === 'units' ? 'none' : 'units';
        props.value = JSON.stringify(state);
        render(state);
    } else if (action === 'import') {
        state.panel = 'import';
        processAndRender(state);
    } else if (action === 'copy') {
        navigator.clipboard.writeText(getState().recap.replace(/, /g, '\n')).then(() => {
            btn.textContent = '✓';
            setTimeout(() => { btn.textContent = '📤'; }, 1200);
        });
    }
});

element.querySelector('.ai-confirm').addEventListener('click', () => {
    const state = getState();
    state.raw = textarea.value;
    state.panel = 'string';
    processAndRender(state);
});

textarea.addEventListener('paste', e => {
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    const state = getState();
    state.raw = pasted;
    state.panel = 'string';
    setTimeout(() => processAndRender(state), 0);
});

grid.addEventListener('input', e => {
    const inp = e.target.closest('.ai-unit-input');
    if (!inp) return;
    const state = getState();
    const idx = parseInt(inp.dataset.idx, 10);
    state.units[idx] = Math.max(0, parseInt(inp.value, 10) || 0);
    state.panel = 'units';
    processAndRender(state);
});

// Close any open popover on outside click (client-side only)
document.addEventListener('click', e => {
    if (!element.isConnected || element.contains(e.target)) return;
    const state = getState();
    if (state.panel === 'units' || state.panel === 'string') {
        state.panel = 'none';
        props.value = JSON.stringify(state);
        render(state);
    }
});
"""

    _JS = _JS_SETUP + _JS_RENDER + _JS_SERVER + _JS_EVENTS

    def __init__(
        self,
        label: str | None = None,
        value: nm.army.Army | None = None,
        recap_format: t.Literal["compact", "full"] = "compact",
        show_import: bool = True,
        show_copy: bool = True,
        btn_align: t.Literal["left", "right"] = "right",
        **kwargs,
    ):
        army = value or nm.army.Army()
        self._recap_format = recap_format

        _merge_elem_classes(kwargs, "ai-wrapper")
        kwargs.setdefault("container", False)
        kwargs.setdefault("show_label", False)
        kwargs.setdefault("apply_default_css", False)
        kwargs.setdefault("padding", False)

        recap = self._fmt(army)

        def process_army(state: dict) -> dict:
            panel = state.get("panel", "none")
            current = nm.army.Army([int(x) for x in state.get("units", [0] * 15)])
            result_army = current
            try:
                if panel == "string":
                    result_army = nm.army.Army.from_str(state.get("raw", ""))
                    state["units"] = result_army._units.tolist()
                    state["error"] = None
                    state["panel"] = "none"
                elif panel == "units":
                    state["error"] = None
                elif panel == "import":
                    result_army = nm.army.Army()
                    state["units"] = result_army._units.tolist()
                    state["raw"] = ""
                    state["error"] = None
                    state["panel"] = "none"
            except ValueError as e:
                result_army = current
                state["error"] = str(e)
            state["recap"] = self._fmt(result_army)
            return state

        super().__init__(
            value=json.dumps({
                "units": army._units.tolist(),
                "raw": recap,
                "recap": recap,
                "error": None,
                "panel": "none",
            }),
            html_template=self._make_html_template(label, btn_align, show_import, show_copy),
            css_template=self._CSS,
            js_on_load=self._JS,
            server_functions=[process_army],
            **kwargs,
        )

    def _fmt(self, a: nm.army.Army) -> str:
        return (a.to_str_compact(sep=", ") if self._recap_format == "compact" else a.to_str()) if a.count > 0 else ""

    @classmethod
    def _make_html_template(cls, label: str | None, btn_align: str, show_import: bool, show_copy: bool) -> str:
        unit_shorts_json = json.dumps(cls._UNIT_SHORTS)
        import_btn = (
            "<button class='ai-btn' data-action='import' title='Importer'>\U0001f4e5</button>"
            if show_import else ""
        )
        copy_btn = (
            "<button class='ai-btn' data-action='copy' title='Copier armée'>\U0001f4e4</button>"
            if show_copy else ""
        )
        btns_html = (
            f"<div class='ai-btns'>"
            f"<button class='ai-btn' data-action='string' title='Coller armée'>\U0001f4cb</button>"
            f"<button class='ai-btn' data-action='units' title='Saisir unités'>✏️</button>"
            f"{copy_btn}"
            f"{import_btn}"
            f"</div>"
        )
        # DOM order determines button side for the label case:
        # btn_align="right" → [label, buttons]; "left" → [buttons, label]
        label_html = f"<span class='ai-label'>{label}</span>" if label else ""
        header_content = btns_html + label_html if btn_align == "left" else label_html + btns_html

        widget_classes = ["ai-widget"]
        if btn_align == "right":
            widget_classes.append("btns-right")
        if not label:
            widget_classes.append("no-label")

        return (
            f"<div class='{' '.join(widget_classes)}' data-unit-shorts='{unit_shorts_json}'>"
            f"<div class='ai-header'>{header_content}</div>"
            f"<div class='ai-recap'></div>"
            f"<div class='ai-string-panel' style='display:none'>"
            f"<textarea class='ai-textarea' placeholder='Coller armée ici…'></textarea>"
            f"<div class='ai-error' style='display:none'></div>"
            f"<button class='ai-confirm'>Valider</button>"
            f"</div>"
            f"<div class='ai-units-popover' style='display:none'>"
            f"<div class='ai-units-grid'></div>"
            f"</div>"
            f"</div>"
        )

    def preprocess(self, payload):
        if payload is None:
            return nm.army.Army()
        try:
            state = json.loads(str(payload))
            return nm.army.Army([int(x) for x in state.get("units", [0] * 15)])
        except (json.JSONDecodeError, ValueError, OverflowError):
            return nm.army.Army()

    def postprocess(self, value):
        if isinstance(value, str):
            return value
        army = value if isinstance(value, nm.army.Army) else nm.army.Army()
        recap = self._fmt(army)
        return json.dumps({
            "units": army._units.tolist(),
            "raw": recap,
            "recap": recap,
            "error": None,
            "panel": "none",
        })


class RCInput:
    pass


class LevelsInputComponent(gr.HTML):
    """HTML-based interactive levels input using Gradio 6's interactive HTML API.

    props.value is a JSON string with keys: mandibule, carapace, hero_lvl, hero_type,
    dome, loge, alliance, special, raw, error, panel.

    The set of displayed fields is controlled by a frozenset built from constructor
    parameters.  hero_enabled and show_buildings are convenience shortcuts; future
    parameters add their fields to the same set without multiplying boolean flags.
    """

    # (id, label, layout, fields)  layout: "grid2" | "inline"
    _GROUPS: t.ClassVar[list[tuple[str, str, str, list[str]]]] = [
        ("recherche", "Recherche", "grid2", ["mandibule", "carapace"]),
        ("hero",      "Héros",     "grid2", ["hero_type", "hero_lvl"]),
        ("bonus",     "Bonus",     "grid2", ["special", "alliance"]),
        ("buildings", "Bâtiments", "grid2", ["dome", "loge"]),
    ]

    _CSS = r"""
.li-wrapper { position: relative; overflow: visible; padding: 0 !important; margin: 0 !important; }
.li-widget {
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg, 8px);
    padding: 8px 10px;
    background: var(--block-background-fill);
    container-type: inline-size;
}
.li-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
.li-label {
    font-size: .85rem; font-weight: 600; color: var(--body-text-color-subdued);
    flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.li-recap-row { display: flex; align-items: flex-start; gap: 4px; margin-bottom: 6px; }
.li-recap-input {
    flex: 1; min-width: 0;
    font-size: .82rem;
    font-family: monospace;
    color: var(--body-text-color-subdued);
    background: var(--input-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    padding: 3px 6px;
    outline: none;
    resize: none;
    overflow: hidden;
    line-height: 1.4;
    display: block;
}
.li-recap-input:focus {
    color: var(--body-text-color);
    outline: 2px solid var(--color-accent);
    outline-offset: -1px;
}
.li-recap-input::placeholder { font-style: italic; }
.li-recap-btns { display: none; flex-wrap: wrap; gap: 4px; flex-shrink: 0; }
@container (max-width: 200px) {
    .li-btn-copy { display: none; }
    .li-recap-btns { display: flex; }
}
.li-btns { display: flex; flex-wrap: wrap; gap: 4px; flex-shrink: 0; }
.li-btn {
    padding: 2px 7px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1.5;
    transition: background .1s;
    color: var(--body-text-color);
}
.li-btn:hover { background: color-mix(in srgb, var(--color-accent) 15%, var(--background-fill-secondary)); }
.li-btn.active { background: var(--color-accent); }
.li-import-hidden [data-action='import'] { display: none; }
.li-group { margin-bottom: 4px; }
/* grid2: two equal columns, field name above element */
.li-group-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 8px; }
/* middle rows: selector col gets 2× the number col */
.li-group-hero  { grid-template-columns: 2fr 1fr; }
.li-group-bonus { grid-template-columns: 1fr 2fr; }
.li-col { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.li-col-label {
    font-size: .72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--body-text-color-subdued);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* inline: flex row (kept for future use) */
.li-group-inline { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; }
.li-field-label { font-size: .8rem; font-weight: 600; color: var(--body-text-color); }
.li-input {
    padding: 5px 6px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    color: var(--body-text-color);
    font-size: .85rem;
    text-align: center;
    box-sizing: border-box;
    width: 100%;
}
.li-input-sm { width: 58px; }
.li-input:focus { outline: 2px solid var(--color-accent); outline-offset: -1px; }
/* selects inside grid2 fill their column */
.li-group-grid2 .li-select { width: 100%; box-sizing: border-box; }
/* selector stretches to match adjacent number input height */
.li-col > .li-selector { flex: 1; }
/* selector: horizontal button strip */
.li-selector { display: flex; gap: 2px; }
.li-sel-btn {
    flex: 1;
    padding: 4px 0;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    cursor: pointer;
    font-size: .78rem;
    font-weight: 700;
    color: var(--body-text-color-subdued);
    text-align: center;
    line-height: 1;
    transition: background .1s, color .1s;
}
.li-sel-btn:hover:not(.li-sel-active) {
    background: color-mix(in srgb, var(--color-accent) 15%, var(--background-fill-secondary));
    color: var(--body-text-color);
}
.li-sel-active { background: var(--color-accent); color: white; border-color: var(--color-accent); }
.li-select {
    padding: 3px 5px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--input-background-fill);
    color: var(--body-text-color);
    font-size: .85rem;
}
.li-select:focus { outline: 2px solid var(--color-accent); outline-offset: -1px; }
.li-error { color: var(--error-text-color, #dc2626); font-size: .8rem; margin-bottom: 4px; }
"""

    _JS_SETUP = r"""
const recapInput = element.querySelector('.li-recap-input');
const errorDiv = element.querySelector('.li-error');
const fieldEls = Array.from(element.querySelectorAll('input[data-field], select[data-field]'));
const selectorEls = Array.from(element.querySelectorAll('.li-selector[data-field]'));
const btnEls = Array.from(element.querySelectorAll('.li-btn'));
let wheelTimer;

function getState() {
    try { return JSON.parse(props.value); }
    catch(e) {
        return {mandibule:0, carapace:0, hero_lvl:0, hero_type:null,
                dome:0, loge:0, alliance:'None', special:0,
                raw:'', error:null, panel:'none'};
    }
}
"""

    _JS_RENDER = r"""
function render(state) {
    fieldEls.forEach(el => {
        if (document.activeElement === el) return;
        const v = state[el.dataset.field];
        if (el.tagName === 'SELECT') {
            el.value = (v == null ? '' : String(v));
        } else {
            el.value = (v == null ? 0 : v);
        }
    });
    selectorEls.forEach(container => {
        const cur = state[container.dataset.field];
        const curStr = cur == null ? '' : String(cur);
        container.querySelectorAll('.li-sel-btn').forEach(btn =>
            btn.classList.toggle('li-sel-active', btn.dataset.value === curStr));
    });
    if (document.activeElement !== recapInput)
        recapInput.value = state.raw || '';
    recapInput.style.height = 'auto';
    recapInput.style.height = recapInput.scrollHeight + 'px';
    if (state.error) { errorDiv.textContent = state.error; errorDiv.style.display = ''; }
    else errorDiv.style.display = 'none';
}

render(getState());
watch("value", () => { try { render(JSON.parse(props.value)); trigger('change'); } catch(e) {} });
"""

    _JS_SERVER = r"""
async function processAndRender(state) {
    const newState = await server.process_levels(state);
    render(newState);
    props.value = JSON.stringify(newState);
    trigger('input');
    trigger('change');
}
"""

    _JS_EVENTS = r"""
element.addEventListener('input', e => {
    if (e.target === recapInput) {
        recapInput.style.height = 'auto';
        recapInput.style.height = recapInput.scrollHeight + 'px';
        const state = getState();
        state.raw = recapInput.value;
        state.panel = 'string';
        processAndRender(state);
        return;
    }
    const el = e.target.closest('[data-field]');
    if (!el || el.tagName !== 'INPUT') return;
    const state = getState();
    state[el.dataset.field] = Math.max(0, parseInt(el.value, 10) || 0);
    processAndRender(state);
});

element.addEventListener('wheel', e => {
    const el = e.target.closest('[data-field]');
    if (!el || el.tagName !== 'INPUT') return;
    e.preventDefault();
    const min = el.min !== '' ? parseInt(el.min, 10) : 0;
    const max = el.max !== '' ? parseInt(el.max, 10) : Infinity;
    const current = parseInt(el.value, 10) || 0;
    const newVal = Math.min(max, Math.max(min, current + (e.deltaY < 0 ? 1 : -1)));
    el.value = newVal;
    const state = getState();
    state[el.dataset.field] = newVal;
    props.value = JSON.stringify(state);
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => processAndRender(state), 120);
}, { passive: false });

element.addEventListener('change', e => {
    const el = e.target.closest('[data-field]');
    if (!el || el.tagName !== 'SELECT') return;
    const state = getState();
    state[el.dataset.field] = el.value === '' ? null : el.value;
    processAndRender(state);
});

element.addEventListener('click', e => {
    const selBtn = e.target.closest('.li-sel-btn');
    if (selBtn) {
        const container = selBtn.closest('.li-selector[data-field]');
        if (!container) return;
        const state = getState();
        const val = selBtn.dataset.value;
        state[container.dataset.field] = val === '' ? null : val;
        processAndRender(state);
        return;
    }
    const btn = e.target.closest('.li-btn');
    if (!btn) return;
    const state = getState();
    const action = btn.dataset.action;
    if (action === 'string') {
        recapInput.focus();
        recapInput.select();
    } else if (action === 'import') {
        state.panel = 'import';
        processAndRender(state);
    } else if (action === 'copy') {
        navigator.clipboard.writeText(getState().raw || '').then(() => {
            btn.textContent = '✓';
            setTimeout(() => { btn.textContent = '📤'; }, 1200);
        });
    }
});

recapInput.addEventListener('paste', e => {
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    const state = getState();
    state.raw = pasted;
    state.panel = 'string';
    setTimeout(() => processAndRender(state), 0);
});
"""

    _JS = _JS_SETUP + _JS_RENDER + _JS_SERVER + _JS_EVENTS

    def __init__(
        self,
        label: str | None = None,
        value: nm.levels.Levels | None = None,
        hero_enabled: bool = True,
        show_buildings: bool = True,
        show_import: bool = False,
        recap_sep: str = "\n",
        min_width: int = 160,
        **kwargs,
    ):
        _fields: set[str] = {"mandibule", "carapace", "special", "alliance"}
        if hero_enabled:
            _fields |= {"hero_lvl", "hero_type"}
        if show_buildings:
            _fields |= {"dome", "loge"}
        self._fields = frozenset(_fields)
        self._recap_sep = recap_sep

        _merge_elem_classes(kwargs, "li-wrapper")
        kwargs.setdefault("container", False)
        kwargs.setdefault("show_label", False)
        kwargs.setdefault("apply_default_css", False)
        kwargs.setdefault("padding", False)

        levels = value or nm.levels.Levels()

        def process_levels(state: dict) -> dict:
            panel = state.get("panel", "none")
            if panel == "string":
                try:
                    lvl = nm.levels.Levels.from_str(state.get("raw", ""))
                    self._fill_state(state, lvl)
                    state["error"] = None
                    state["panel"] = "none"
                except ValueError as e:
                    state["error"] = str(e)
                    return state
            elif panel == "import":
                lvl = nm.levels.Levels()
                self._fill_state(state, lvl)
                state["error"] = None
                state["panel"] = "none"
            else:
                lvl = self._levels_from_state(state)
            state["raw"] = lvl.to_str(hero_enabled=("hero_lvl" in self._fields), sep=self._recap_sep)
            return state

        super().__init__(
            value=json.dumps(self._build_state(levels)),
            html_template=self._make_html_template(label, show_import, min_width),
            css_template=self._CSS,
            js_on_load=self._JS,
            server_functions=[process_levels],
            **kwargs,
        )

    def _fill_state(self, state: dict, lvl: nm.levels.Levels) -> None:
        state["mandibule"] = lvl.mandibule
        state["carapace"] = lvl.carapace
        state["hero_lvl"] = lvl.hero_lvl
        state["hero_type"] = lvl.hero_type.value if lvl.hero_type else None
        state["dome"] = lvl.dome
        state["loge"] = lvl.loge
        state["alliance"] = lvl.alliance.value
        state["special"] = lvl.special

    def _levels_from_state(self, state: dict) -> nm.levels.Levels:
        hero_lvl = 0
        hero_type = None
        if "hero_lvl" in self._fields:
            ht_val = state.get("hero_type")
            hero_type = nm.levels.HeroType(ht_val) if ht_val else None
            hero_lvl = int(state.get("hero_lvl") or 0)
        return nm.levels.Levels(
            mandibule=int(state.get("mandibule") or 0),
            carapace=int(state.get("carapace") or 0),
            hero_lvl=hero_lvl,
            hero_type=hero_type,
            dome=int(state.get("dome") or 0) if "dome" in self._fields else 0,
            loge=int(state.get("loge") or 0) if "loge" in self._fields else 0,
            alliance=nm.levels.AllianceType(state.get("alliance") or "None"),
            special=int(state.get("special") or 0),
        )

    _FIELD_LABELS: t.ClassVar[dict[str, str]] = {
        "mandibule": "Mandibule", "carapace": "Carapace",
        "hero_lvl": "Niv", "hero_type": "Héros",
        "special": "Spe Combat", "alliance": "Alliance",
        "dome": "Dôme", "loge": "Loge",
    }
    # (value, full_label, abbreviation)
    _FIELD_SELECTS: t.ClassVar[dict[str, list[tuple[str, str, str]]]] = {
        "hero_type": [("", "—", "—"), ("Attaque", "Attaque", "A"), ("Défense", "Défense", "D"), ("Vie", "Vie", "V")],
        "alliance":  [("None", "—", "—"), ("Guerrier", "Guerrier", "G"), ("Pacifiste", "Pacifiste", "P"), ("Neutre", "Neutre", "N")],
    }
    _FIELD_NUM_ATTRS: t.ClassVar[dict[str, str]] = {
        "hero_lvl": "min='0' max='180'", "special": "min='0' max='5'",
    }

    def _build_state(self, lvl: nm.levels.Levels) -> dict:
        state: dict = {}
        self._fill_state(state, lvl)
        state["raw"] = lvl.to_str(hero_enabled=("hero_lvl" in self._fields), sep=self._recap_sep)
        state["error"] = None
        state["panel"] = "none"
        return state

    def _make_html_template(self, label: str | None, show_import: bool, min_width: int = 160) -> str:
        widget_classes = ["li-widget"]
        if not show_import:
            widget_classes.append("li-import-hidden")

        label_html = f"<span class='li-label'>{label}</span>" if label else ""
        btns_html = (
            "<div class='li-btns'>"
            "<button class='li-btn' data-action='string' title='Coller niveaux'>\U0001f4cb</button>"
            "<button class='li-btn' data-action='import' title='Réinitialiser'>\U0001f4e5</button>"
            "<button class='li-btn li-btn-copy' data-action='copy' title='Copier niveaux'>\U0001f4e4</button>"
            "</div>"
        )

        groups_html = ""
        for group_id, _, layout, fields in self._GROUPS:
            enabled = [f for f in fields if f in self._fields]
            if not enabled:
                continue
            fields_html = "".join(self._make_field_html(f, layout) for f in enabled)
            groups_html += f"<div class='li-group li-group-{layout} li-group-{group_id}'>{fields_html}</div>"

        return (
            f"<div class='{' '.join(widget_classes)}' style='min-width:{min_width}px'>"
            f"<div class='li-header'>{label_html}{btns_html}</div>"
            f"<div class='li-recap-row'>"
            f"<textarea class='li-recap-input' rows='1' placeholder='Coller / saisir niveaux…'></textarea>"
            f"<div class='li-recap-btns'>"
            f"<button class='li-btn' data-action='copy' title='Copier niveaux'>\U0001f4e4</button>"
            f"</div>"
            f"</div>"
            f"<div class='li-error' style='display:none'></div>"
            f"<div class='li-edit-panel'>{groups_html}</div>"
            f"</div>"
        )

    @classmethod
    def _make_field_html(cls, field: str, layout: str) -> str:
        label = cls._FIELD_LABELS.get(field, field)
        if layout == "grid2":
            if field in cls._FIELD_SELECTS:
                btns = "".join(
                    f"<button class='li-sel-btn' data-value='{v}'>{a}</button>"
                    for v, _, a in cls._FIELD_SELECTS[field]
                )
                inner = f"<div class='li-selector' data-field='{field}'>{btns}</div>"
            else:
                attrs = cls._FIELD_NUM_ATTRS.get(field, "min='0'")
                inner = f"<input type='number' class='li-input' data-field='{field}' {attrs} step='1'>"
            return f"<div class='li-col'><span class='li-col-label'>{label}</span>{inner}</div>"
        # inline layout (kept for future use)
        if field in cls._FIELD_SELECTS:
            opts = "".join(f"<option value='{v}'>{t}</option>" for v, t, _ in cls._FIELD_SELECTS[field])
            return f"<select class='li-select' data-field='{field}'>{opts}</select>"
        attrs = cls._FIELD_NUM_ATTRS.get(field, "min='0'")
        return f"<span class='li-field-label'>{label}</span><input type='number' class='li-input li-input-sm' data-field='{field}' {attrs} step='1'>"

    def preprocess(self, payload):
        if payload is None:
            return nm.levels.Levels()
        try:
            state = json.loads(str(payload))
            return self._levels_from_state(state)
        except (json.JSONDecodeError, ValueError, TypeError):
            return nm.levels.Levels()

    def postprocess(self, value):
        if isinstance(value, str):
            return value
        levels = value if isinstance(value, nm.levels.Levels) else nm.levels.Levels()
        return json.dumps(self._build_state(levels))


### OUTPUTS


class WarPartyStats:
    def __init__(self, war_party_state: gr.State, show_labels=False, right_to_left=False):
        options = {
            "min_width": 10,
            "container": False,
            "max_lines": 1,
            "show_label": False,
        }

        def make_row(label_str: str, show_extra: bool) -> tuple[gr.Text, gr.Text, gr.Text]:
            label = gr.Text(
                label_str,
                max_lines=1,
                show_label=False,
                interactive=False,
                container=False,
                render=False,
            )
            value_display = gr.Text(**options, render=False, scale=4)
            extra_box = gr.Text(**options, render=False, scale=2)
            if right_to_left:
                value_display.render()
                if show_extra:
                    extra_box.render()
                if show_labels:
                    label.render()
            else:
                if show_labels:
                    label.render()
                if show_extra:
                    extra_box.render()
                value_display.render()

            return value_display, extra_box, label

        with gr.Group():
            with gr.Row():
                self.hp, self.hp_bonus, label = make_row("Vie", True)
            with gr.Row():
                self.dmg, self.dmg_bonus, label = make_row("Attaque", True)
            with gr.Row():
                self.cnt, _, label = make_row("Flood", False)
            with gr.Row():
                self.ponte, _, label = make_row("Ponte (Complet)", False)
            with gr.Row():
                self.adj_ponte, _, label = make_row("Ponte (Effectif)", False)

        @gr.on(
            triggers=war_party_state.change,
            inputs=war_party_state,
            outputs=[self.hp, self.hp_bonus, self.dmg, self.dmg_bonus, self.cnt, self.ponte, self.adj_ponte],
            show_progress="hidden",
        )
        def update_stats(p: nm.battle.WarParty):
            return (
                f"{p.total_hp:,.0f}".replace(",", " ") if p.bonuses.hp is not None else "?",
                f"+{p.bonuses.hp:.0%}" if p.bonuses.hp is not None else "?",
                f"{p.total_dmg:,.0f}".replace(",", " "),
                f"+{p.bonuses.dmg:.0%}",
                f"{p.army.count:,.0f}".replace(",", " "),
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.recruit_time()[1])))}",
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.non_xp_recruit_time()[1])))}",
            )
