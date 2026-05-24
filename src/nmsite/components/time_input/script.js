// TimeInput component script
// props.value = JSON string of the structured state object
// Configuration is embedded in data-* attributes on .ti-widget

const widget = element.querySelector('.ti-widget');
const MODE = widget.dataset.mode;                          // "duration" | "clock_time" | "datetime"
const ENABLED_KEYS = JSON.parse(widget.dataset.segments);  // ordered list of enabled segment keys
const FORMATS = JSON.parse(widget.dataset.formats);        // available display formats
const QUICK_FILLS = JSON.parse(widget.dataset.quickFills);
const INTERACTIVE = widget.dataset.interactive !== 'false';
const HIDDEN_DEFAULTS = JSON.parse(widget.dataset.hiddenDefaults || '{}');

// All segment definitions per mode: {key, min, max (null=unbounded), ajhmsLabel}
const SEG_META = {
    duration: [
        {key: 'years',   min: 0, max: null, width: 2},
        {key: 'days',    min: 0, max: null, width: 3},
        {key: 'hours',   min: 0, max: null, width: 2},
        {key: 'minutes', min: 0, max: null, width: 2},
        {key: 'seconds', min: 0, max: null, width: 2},
    ],
    clock_time: [
        {key: 'hours',   min: 0, max: 23,   width: 2},
        {key: 'minutes', min: 0, max: 59,   width: 2},
        {key: 'seconds', min: 0, max: 59,   width: 2},
    ],
    datetime: [
        {key: 'year',    min: 1970, max: 9999, width: 4},
        {key: 'month',   min: 1,    max: 12,   width: 2},
        {key: 'day',     min: 1,    max: 31,   width: 2},
        {key: 'hours',   min: 0,    max: 23,   width: 2},
        {key: 'minutes', min: 0,    max: 59,   width: 2},
        {key: 'seconds', min: 0,    max: 59,   width: 2},
    ],
};

// Ordered meta for enabled segments only
const META = SEG_META[MODE].filter(d => ENABLED_KEYS.includes(d.key));

// -- State --
let state = parseValue(props.value);
let activeFormat = FORMATS[0];
let focusedSegKey = null;
let digitBuffer = '';
let digitTimeout = null;
let touchStartY = null;
let touchLastY = null;
let isRendering = false;     // guard: suppress focusin/focusout during DOM rebuild
let isInternalCommit = false; // guard: skip watch during own commit

function parseValue(raw) {
    try { return JSON.parse(raw); } catch { return buildEmptyState(); }
}

function buildEmptyState() {
    if (MODE === 'duration')
        return {years: 0, days: 0, hours: 0, minutes: 0, seconds: 0};
    if (MODE === 'clock_time')
        return {hours: 0, minutes: 0, seconds: 0};
    return {year: 1970, month: 1, day: 1, hours: 0, minutes: 0, seconds: 0};
}

// Apply hidden defaults over empty state
function applyDefaults(s) {
    for (const [k, v] of Object.entries(HIDDEN_DEFAULTS)) s[k] = v;
    return s;
}

if (!props.value || props.value === 'null') {
    state = applyDefaults(buildEmptyState());
}

// ---- Display helpers ----

// For duration + HH:MM:SS format: aggregate all higher units into hours
function toDisplayState(s, fmt) {
    if (MODE !== 'duration' || fmt !== 'HH:MM:SS') return s;
    const totalHours = (s.years || 0) * 365 * 24 + (s.days || 0) * 24 + (s.hours || 0);
    return {years: 0, days: 0, hours: totalHours, minutes: s.minutes, seconds: s.seconds};
}

// For duration + HH:MM:SS: split aggregated hours back to state fields
function fromDisplayState(display, fmt) {
    if (MODE !== 'duration' || fmt !== 'HH:MM:SS') return display;
    const h = display.hours || 0;
    // Only distribute to enabled higher segments
    let remaining = h;
    const out = {...state, hours: remaining, minutes: display.minutes, seconds: display.seconds};
    out.seconds = display.seconds;
    out.minutes = display.minutes;
    if (ENABLED_KEYS.includes('days')) {
        out.days = Math.floor(remaining / 24);
        out.hours = remaining % 24;
        remaining = out.days;
        if (ENABLED_KEYS.includes('years')) {
            out.years = Math.floor(remaining / 365);
            out.days = remaining % 365;
        } else {
            out.years = 0;
        }
    } else {
        out.hours = remaining;
        out.days = 0;
        out.years = 0;
    }
    return out;
}

// Value shown in a segment span (may differ from state for HH:MM:SS duration)
function displayVal(key, displayState) {
    return displayState[key] ?? state[key] ?? 0;
}

// ---- Normalization (duration only) ----
function normalize(s) {
    if (MODE !== 'duration') return;
    // Carry upward through enabled segments (from smallest to largest)
    const order = ['seconds', 'minutes', 'hours', 'days', 'years'];
    const limits = {seconds: 60, minutes: 60, hours: 24, days: 365};
    for (let i = 0; i < order.length - 1; i++) {
        const key = order[i];
        const next = order[i + 1];
        if (!ENABLED_KEYS.includes(next)) continue;
        const lim = limits[key];
        if (s[key] >= lim) {
            s[next] = (s[next] || 0) + Math.floor(s[key] / lim);
            s[key] = s[key] % lim;
        }
        // Underflow
        if (s[key] < 0) {
            const borrow = Math.ceil(-s[key] / lim);
            s[next] = (s[next] || 0) - borrow;
            s[key] = s[key] + borrow * lim;
        }
    }
    // Clamp highest enabled segment to >= 0
    const highest = [...order].reverse().find(k => ENABLED_KEYS.includes(k));
    if (highest && s[highest] < 0) s[highest] = 0;
}

function clampField(key, val, displayFmt) {
    // In duration mode all fields are unbounded from above (normalization handles carry)
    if (MODE === 'duration') return Math.max(0, val);
    const m = SEG_META[MODE].find(d => d.key === key);
    if (!m) return val;
    if (m.min !== null && val < m.min) return m.max;   // wrap around
    if (m.max !== null && val > m.max) return m.min;
    return val;
}

// ---- Format-specific layout ----

function getSegmentsForFormat(fmt) {
    // Returns array of render items: {type:'seg'|'sep', key?, text?}
    if (fmt === 'AJHMS') {
        const LABELS = {years:'A', days:'J', hours:'H', minutes:'M', seconds:'S'};
        const items = [];
        for (const m of META) {
            items.push({type: 'seg', key: m.key});
            items.push({type: 'sep', text: LABELS[m.key] || '', cls: 'ti-unit'});
        }
        // Remove trailing space after last unit label if desired
        return items;
    }
    if (fmt === 'HH:MM:SS') {
        // For duration: shows aggregated hours:minutes:seconds
        // For clock_time: same
        const items = [];
        const visKeys = MODE === 'duration' ? ['hours', 'minutes', 'seconds']
                                            : META.map(m => m.key);
        for (let i = 0; i < visKeys.length; i++) {
            if (i > 0) items.push({type: 'sep', text: ':'});
            items.push({type: 'seg', key: visKeys[i]});
        }
        return items;
    }
    if (fmt === 'DD/MM/YYYY HH:MM:SS') {
        // datetime
        const dateKeys = META.map(m => m.key).filter(k => ['year','month','day'].includes(k));
        const timeKeys = META.map(m => m.key).filter(k => ['hours','minutes','seconds'].includes(k));
        const items = [];
        for (let i = 0; i < dateKeys.length; i++) {
            if (i > 0) items.push({type: 'sep', text: '/'});
            items.push({type: 'seg', key: dateKeys[i]});
        }
        if (dateKeys.length > 0 && timeKeys.length > 0) {
            items.push({type: 'sep', text: ' '});
        }
        for (let i = 0; i < timeKeys.length; i++) {
            if (i > 0) items.push({type: 'sep', text: ':'});
            items.push({type: 'seg', key: timeKeys[i]});
        }
        return items;
    }
    return META.map(m => ({type: 'seg', key: m.key}));
}

// ---- Render ----

function pad(val, width) {
    return String(Math.abs(val)).padStart(width, '0');
}

function render() {
    isRendering = true;
    const displayState = toDisplayState(state, activeFormat);
    const items = getSegmentsForFormat(activeFormat);

    const fieldEl = widget.querySelector('.ti-field-inner');
    if (!fieldEl) { isRendering = false; return; }

    let html = '';
    for (const item of items) {
        if (item.type === 'sep') {
            html += `<span class="ti-sep${item.cls ? ' ' + item.cls : ''}">${item.text}</span>`;
        } else {
            const key = item.key;
            const m = SEG_META[MODE].find(d => d.key === key);
            const val = displayVal(key, displayState);
            const focused = focusedSegKey === key ? ' active' : '';
            const displayText = (focusedSegKey === key && digitBuffer)
                ? digitBuffer.padStart(m?.width ?? 2, '0')
                : pad(val, m?.width ?? 2);
            html += `<span class="ti-seg${focused}" data-key="${key}" tabindex="${INTERACTIVE ? 0 : -1}">${displayText}</span>`;
        }
    }
    fieldEl.innerHTML = html;

    // Re-attach focus to active segment
    if (focusedSegKey) {
        const el = fieldEl.querySelector(`[data-key="${focusedSegKey}"]`);
        if (el && document.activeElement !== el) el.focus({preventScroll: true});
    }
    isRendering = false;
}

// ---- Segment value update ----

function getDisplayMeta(key) {
    // For HH:MM:SS duration, "hours" is an aggregated field with no max
    if (MODE === 'duration' && activeFormat === 'HH:MM:SS' && key === 'hours') {
        return {key, min: 0, max: null, width: 4};
    }
    return SEG_META[MODE].find(d => d.key === key) || {key, min: 0, max: null, width: 2};
}

function applyDelta(key, delta) {
    const displayState = toDisplayState(state, activeFormat);
    const m = getDisplayMeta(key);
    let newVal = (displayState[key] ?? 0) + delta;
    newVal = clampField(key, newVal, activeFormat);
    displayState[key] = newVal;
    state = applyDefaults(fromDisplayState(displayState, activeFormat));
    normalize(state);
    commit();
}

function applyDigitBuffer(key) {
    if (!digitBuffer) return;
    const val = parseInt(digitBuffer, 10);
    if (!isNaN(val)) {
        const displayState = toDisplayState(state, activeFormat);
        displayState[key] = clampField(key, val, activeFormat);
        state = applyDefaults(fromDisplayState(displayState, activeFormat));
    }
    digitBuffer = '';
    clearTimeout(digitTimeout);
    digitTimeout = null;
}

function commitAndNormalize() {
    normalize(state);
    commit();
}

function commit() {
    isInternalCommit = true;
    props.value = JSON.stringify(state);
    isInternalCommit = false;
    trigger('input');
    trigger('change');
    render();
}

// ---- Keyboard ----

function nextSegKey(key, dir) {
    const items = getSegmentsForFormat(activeFormat).filter(i => i.type === 'seg');
    const idx = items.findIndex(i => i.key === key);
    const nextIdx = idx + dir;
    if (nextIdx < 0 || nextIdx >= items.length) return null;
    return items[nextIdx].key;
}

function focusSeg(key) {
    focusedSegKey = key;
    digitBuffer = '';
    render();  // render() re-focuses the active segment internally
}

widget.addEventListener('keydown', e => {
    if (!INTERACTIVE || !focusedSegKey) return;
    const key = focusedSegKey;

    if (e.key === 'ArrowUp') {
        e.preventDefault();
        applyDigitBuffer(key);
        applyDelta(key, 1);
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        applyDigitBuffer(key);
        applyDelta(key, -1);
    } else if (e.key === 'Tab') {
        applyDigitBuffer(key);
        commitAndNormalize();
        // Let default tab behaviour move focus; focusout handler clears focusedSegKey
    } else if (e.key === ':' || e.key === '/' || e.key === ' ') {
        e.preventDefault();
        applyDigitBuffer(key);
        commitAndNormalize();
        const next = nextSegKey(key, 1);
        if (next) focusSeg(next);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        applyDigitBuffer(key);
        commitAndNormalize();
    } else if (e.key === 'Backspace') {
        e.preventDefault();
        digitBuffer = digitBuffer.slice(0, -1);
        render();
    } else if (/^\d$/.test(e.key)) {
        e.preventDefault();
        const m = getDisplayMeta(key);
        const maxLen = m.width ?? 2;
        digitBuffer += e.key;
        render();
        clearTimeout(digitTimeout);
        // Auto-commit when buffer fills max digits
        if (digitBuffer.length >= maxLen) {
            applyDigitBuffer(key);
            commitAndNormalize();
            const next = nextSegKey(key, 1);
            if (next) focusSeg(next);
        } else {
            digitTimeout = setTimeout(() => {
                applyDigitBuffer(key);
                commitAndNormalize();
            }, 1200);
        }
    }
});

// ---- Click / Focus on segment spans ----

widget.addEventListener('focusin', e => {
    if (isRendering) return;  // focus caused by render's own el.focus(), already handled
    const seg = e.target.closest('.ti-seg');
    if (!seg) return;
    focusedSegKey = seg.dataset.key;
    digitBuffer = '';
    render();
});

widget.addEventListener('focusout', e => {
    if (isRendering) return;  // DOM rebuild caused this, don't commit
    const seg = e.relatedTarget?.closest('.ti-seg');
    if (!seg || seg.closest('.ti-widget') !== widget) {
        applyDigitBuffer(focusedSegKey);
        commitAndNormalize();
        focusedSegKey = null;
        render();
    }
});

// Click anywhere in the field (not on a segment/button) → focus first segment
widget.querySelector('.ti-field').addEventListener('click', e => {
    if (!INTERACTIVE) return;
    if (e.target.closest('.ti-seg, .ti-btns')) return;
    const key = widget.querySelector('.ti-seg')?.dataset.key;
    if (!key) return;
    focusedSegKey = key;
    digitBuffer = '';
    render();  // render() re-focuses the active segment after rebuilding DOM
});

// ---- Mouse wheel ----

widget.addEventListener('wheel', e => {
    const seg = e.target.closest('.ti-seg');
    if (!seg || !INTERACTIVE) return;
    e.preventDefault();
    const key = seg.dataset.key;
    focusedSegKey = key;
    applyDigitBuffer(key);
    applyDelta(key, e.deltaY < 0 ? 1 : -1);
}, {passive: false});

// ---- Touch drag ----

widget.addEventListener('touchstart', e => {
    const seg = e.target.closest('.ti-seg');
    if (!seg || !INTERACTIVE) return;
    touchStartY = e.touches[0].clientY;
    touchLastY = touchStartY;
    focusedSegKey = seg.dataset.key;
    digitBuffer = '';
    render();
}, {passive: true});

widget.addEventListener('touchmove', e => {
    const seg = e.target.closest('.ti-seg');
    if (!seg || touchLastY === null || !INTERACTIVE) return;
    e.preventDefault();
    const currentY = e.touches[0].clientY;
    const delta = touchLastY - currentY;
    const THRESHOLD = 5;
    if (Math.abs(delta) >= THRESHOLD) {
        applyDelta(seg.dataset.key, delta > 0 ? 1 : -1);
        touchLastY = currentY;
    }
}, {passive: false});

widget.addEventListener('touchend', () => {
    touchLastY = null;
    touchStartY = null;
});

// ---- Format toggle ----

widget.addEventListener('click', e => {
    if (!INTERACTIVE) return;

    // Format toggle button
    const toggleBtn = e.target.closest('.ti-toggle');
    if (toggleBtn) {
        const currentIdx = FORMATS.indexOf(activeFormat);
        const nextIdx = (currentIdx + 1) % FORMATS.length;
        const nextFmt = FORMATS[nextIdx];

        // Convert state through display representation
        const displayState = toDisplayState(state, activeFormat);
        state = applyDefaults(fromDisplayState(displayState, nextFmt));
        normalize(state);
        activeFormat = nextFmt;
        toggleBtn.textContent = activeFormat;
        commit();
        return;
    }

    // Copy button
    const copyBtn = e.target.closest('.ti-copy');
    if (copyBtn) {
        const text = formatState(state, activeFormat);
        navigator.clipboard?.writeText(text).catch(() => {});
        return;
    }

    // Clear/reset button
    const clearBtn = e.target.closest('.ti-clear');
    if (clearBtn) {
        state = applyDefaults(buildEmptyState());
        normalize(state);
        focusedSegKey = null;
        digitBuffer = '';
        commit();
        return;
    }

    // Quick-fill buttons
    const pill = e.target.closest('.ti-pill[data-fill]');
    if (pill) {
        applyQuickFill(pill.dataset.fill);
        return;
    }
});

// ---- Quick fills ----

function applyQuickFill(fill) {
    const now = new Date();
    if (fill === 'now') {
        if (MODE === 'duration') {
            const totalSecs = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
            const displayState = {hours: totalSecs};  // will normalize
            state = applyDefaults(fromDisplayState({hours: Math.floor(totalSecs / 3600),
                minutes: now.getMinutes(), seconds: now.getSeconds()}, 'HH:MM:SS'));
        } else if (MODE === 'clock_time') {
            state.hours = now.getHours();
            state.minutes = now.getMinutes();
            state.seconds = now.getSeconds();
        } else {
            state.year = now.getFullYear();
            state.month = now.getMonth() + 1;
            state.day = now.getDate();
            state.hours = now.getHours();
            state.minutes = now.getMinutes();
            state.seconds = now.getSeconds();
        }
    } else if (fill === 'today') {
        state.year = now.getFullYear();
        state.month = now.getMonth() + 1;
        state.day = now.getDate();
    } else if (fill === 'current_time') {
        state.hours = now.getHours();
        state.minutes = now.getMinutes();
        state.seconds = now.getSeconds();
    }
    applyDefaults(state);
    commitAndNormalize();
}

// ---- Paste ----
// Spans with tabindex don't receive browser paste events, so we use document-level.

document.addEventListener('paste', e => {
    if (!INTERACTIVE) return;
    const active = document.activeElement;
    if (!active || !widget.contains(active) || !active.classList.contains('ti-seg')) return;
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    const parsed = parseTimeString(text);
    if (parsed) {
        Object.assign(state, parsed);
        applyDefaults(state);
        commitAndNormalize();
    }
});

function parseTimeString(s) {
    s = s.trim();

    // AJHMS: e.g. "2A 3J 4H 30M 15S" or "4H 30M" etc.
    const ajhmsRe = /(?:(\d+)\s*[Aa])?[\s,]*(?:(\d+)\s*[Jj])?[\s,]*(?:(\d+)\s*[Hh])?[\s,]*(?:(\d+)\s*[Mm])?[\s,]*(?:(\d+)\s*[Ss])?/;
    const ajhmsMatch = s.match(/\d+\s*[AaJjHhMmSs]/);
    if (ajhmsMatch) {
        const m = s.match(ajhmsRe);
        if (m && (m[1]||m[2]||m[3]||m[4]||m[5])) {
            return {
                years: parseInt(m[1] || '0', 10),
                days: parseInt(m[2] || '0', 10),
                hours: parseInt(m[3] || '0', 10),
                minutes: parseInt(m[4] || '0', 10),
                seconds: parseInt(m[5] || '0', 10),
            };
        }
    }

    // HH:MM:SS or HH:MM
    const hmsMatch = s.match(/^(\d+):(\d+)(?::(\d+))?$/);
    if (hmsMatch) {
        return {
            hours: parseInt(hmsMatch[1], 10),
            minutes: parseInt(hmsMatch[2], 10),
            seconds: parseInt(hmsMatch[3] || '0', 10),
        };
    }

    // DD/MM/YYYY HH:MM:SS or DD/MM HH:MM:SS
    const dtMatch = s.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (dtMatch) {
        return {
            day: parseInt(dtMatch[1], 10),
            month: parseInt(dtMatch[2], 10),
            year: parseInt(dtMatch[3] || '2000', 10),
            hours: parseInt(dtMatch[4], 10),
            minutes: parseInt(dtMatch[5], 10),
            seconds: parseInt(dtMatch[6] || '0', 10),
        };
    }

    return null;
}

// ---- Format state to string (for copy) ----

function formatState(s, fmt) {
    const d = toDisplayState(s, fmt);
    if (fmt === 'AJHMS') {
        const LABELS = {years:'A', days:'J', hours:'H', minutes:'M', seconds:'S'};
        return META.map(m => `${d[m.key]}${LABELS[m.key]}`).join(' ');
    }
    if (fmt === 'HH:MM:SS') {
        const keys = MODE === 'duration' ? ['hours','minutes','seconds'] : META.map(m=>m.key);
        return keys.map(k => pad(d[k]||0, k==='hours' && MODE==='duration' ? 3 : 2)).join(':');
    }
    if (fmt === 'DD/MM/YYYY HH:MM:SS') {
        return `${pad(s.day,2)}/${pad(s.month,2)}/${s.year} ${pad(s.hours,2)}:${pad(s.minutes,2)}:${pad(s.seconds,2)}`;
    }
    return JSON.stringify(s);
}

// ---- watch for Python-initiated value updates ----

watch('value', () => {
    if (isInternalCommit) return;  // our own commit, already handled
    // Python pushed a new value from outside — reset and re-render
    const newState = parseValue(props.value);
    state = applyDefaults(newState || buildEmptyState());
    focusedSegKey = null;
    digitBuffer = '';
    render();
});

// ---- Initial render ----

render();
