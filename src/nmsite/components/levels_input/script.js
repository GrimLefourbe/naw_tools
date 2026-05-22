// === SETUP: cache element references, state helper ===
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

// === RENDER: sync DOM to state, react to external value updates ===
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

// === SERVER: send state to Python, render result, fire Gradio events ===
async function processAndRender(state) {
    const newState = await server.process_levels(state);
    render(newState);
    props.value = JSON.stringify(newState);
    trigger('input');
    trigger('change');
}

// === EVENTS: input fields, wheel scroll, select changes, buttons, paste ===
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
