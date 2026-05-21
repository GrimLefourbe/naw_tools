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

    _CSS = """
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

    _JS = """
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
    _CSS_LAYOUT = """
.ai-wrapper { position: relative; overflow: visible; padding: 0 !important; margin: 0 !important; }
.ai-widget {
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg, 8px);
    padding: 8px 10px;
    background: var(--background-fill-primary);
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
    _CSS_BUTTONS = """
.ai-btn {
    padding: 2px 7px;
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-sm, 4px);
    background: var(--background-fill-secondary);
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
    _CSS_STRING_PANEL = """
.ai-string-panel, .ai-units-popover {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: auto;
    z-index: 200;
    background: var(--background-fill-primary);
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
    background: var(--background-fill-secondary);
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
    background: var(--background-fill-secondary);
    cursor: pointer;
    font-size: .85rem;
    color: var(--body-text-color);
}
.ai-confirm:hover {
    background: color-mix(in srgb, var(--color-accent) 10%, var(--background-fill-secondary));
}
"""

    # --- Unit-by-unit editor popover ---
    _CSS_UNITS_EDITOR = """
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
    background: var(--background-fill-secondary);
    color: var(--body-text-color);
    font-size: .8rem;
    text-align: right;
}
.ai-unit-input:focus { outline: 2px solid var(--color-accent); outline-offset: -1px; }
"""

    _CSS = _CSS_LAYOUT + _CSS_BUTTONS + _CSS_STRING_PANEL + _CSS_UNITS_EDITOR

    # --- DOM setup: build unit-input grid, cache element references, state helper ---
    _JS_SETUP = """
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
    _JS_RENDER = """
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
    _JS_SERVER = """
async function processAndRender(state) {
    const newState = await server.process_army(state);
    render(newState);
    props.value = JSON.stringify(newState);
    trigger('input');
    trigger('change');
}
"""

    # --- Event listeners: buttons, string confirm, paste, unit inputs, outside click ---
    _JS_EVENTS = """
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
            html_template=self._make_html_template(label, btn_align, show_import),
            css_template=self._CSS,
            js_on_load=self._JS,
            server_functions=[process_army],
            **kwargs,
        )

    def _fmt(self, a: nm.army.Army) -> str:
        return (a.to_str_compact(sep=", ") if self._recap_format == "compact" else a.to_str()) if a.count > 0 else ""

    @classmethod
    def _make_html_template(cls, label: str | None, btn_align: str, show_import: bool) -> str:
        unit_shorts_json = json.dumps(cls._UNIT_SHORTS)
        import_btn = (
            "<button class='ai-btn' data-action='import' title='Importer'>\U0001f4e5</button>"
            if show_import else ""
        )
        btns_html = (
            f"<div class='ai-btns'>"
            f"<button class='ai-btn' data-action='string' title='Coller armée'>\U0001f4cb</button>"
            f"<button class='ai-btn' data-action='units' title='Saisir unités'>✏️</button>"
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
