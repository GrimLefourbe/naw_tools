// === SETUP: build unit-input grid, cache element references, state helper ===
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

// === RENDER: sync DOM to state, react to external value updates ===
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

// === SERVER: send state to Python, render result, fire Gradio events ===
async function processAndRender(state) {
    const newState = await server.process_army(state);
    render(newState);
    props.value = JSON.stringify(newState);
    trigger('input');
    trigger('change');
}

// === EVENTS: buttons, string confirm, paste, unit inputs, outside click ===
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
