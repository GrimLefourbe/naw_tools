// TimeInput component script
// props.value = JSON string of the structured state object
// Configuration is embedded in data-* attributes on .ti-widget

const widget = element.querySelector('.ti-widget');
const MODE = widget.dataset.mode;                          // "duration" | "clock_time" | "datetime"
const ENABLED_KEYS = JSON.parse(widget.dataset.segments);  // ordered list of enabled segment keys
const FORMATS = JSON.parse(widget.dataset.formats);        // available display formats
const QUICK_FILLS = JSON.parse(widget.dataset.quickFills);
let INTERACTIVE = widget.dataset.interactive !== 'false';
const HIDDEN_DEFAULTS = JSON.parse(widget.dataset.hiddenDefaults || '{}');

// These containers are part of the static initial template and are never
// removed from the DOM (only .ti-field-inner's children get replaced on a
// full rebuild) — cache them once instead of re-querying on every render()/
// updateDisplayBadge() call, which happens on every wheel tick/keystroke.
const fieldEl = widget.querySelector('.ti-field-inner');
const badgeEl = widget.querySelector('.ti-display-value');

// Per-segment metadata (key, min, max [null=unbounded], display width) for
// just the enabled segments, in order — sent from Python (data-seg-meta)
// rather than re-declared here, so segment identity/order/bounds have one
// source of truth instead of two independently-maintained copies.
const META = JSON.parse(widget.dataset.segMeta);

// -- State --
let state = parseValue(props.value);
let activeFormat = FORMATS[0];
let focusedSegKey = null;
let digitBuffer = '';
let digitTimeout = null;
let touchStartY = null;
let touchLastY = null;
let isEditing = false;        // true while the segment editor is open
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
    // In duration mode, fields are unbounded in both directions: normalize()
    // carries overflow up into the next bigger unit, and (symmetrically)
    // borrows from it on underflow — so a negative intermediate value here
    // must be allowed through rather than floored at 0, or the borrow branch
    // never gets a negative value to act on in the first place.
    if (MODE === 'duration') return val;
    const m = META.find(d => d.key === key);
    if (!m) return val;
    // Wrap by the actual overshoot (modulo), not just to the opposite
    // boundary — a multi-step delta (e.g. a fast wheel scroll) can overshoot
    // by more than one unit and needs to land at the right value, not always
    // snap straight to min/max.
    if (m.min !== null && m.max !== null && (val < m.min || val > m.max)) {
        const range = m.max - m.min + 1;
        val = m.min + (((val - m.min) % range) + range) % range;
    }
    return val;
}

// Order (smallest→largest) used to carry overflow/underflow between
// adjacent bounded segments — scrolling seconds past 59 wraps it to 0 AND
// bumps minutes by 1 (and so on up the chain), symmetric to duration's own
// normalize(). Duration's segments are unbounded (normalize() handles that
// case instead); this only applies to clock_time/datetime's fixed-range
// fields, which clampField alone used to just wrap in place without
// touching the next segment.
const CARRY_ORDER = ['seconds', 'minutes', 'hours', 'day', 'month', 'year'];

function carryBounded(s) {
    for (let i = 0; i < CARRY_ORDER.length - 1; i++) {
        const key = CARRY_ORDER[i];
        const next = CARRY_ORDER[i + 1];
        // Mirrors normalize()'s own rule: only carry between a pair that's
        // actually adjacent and enabled — a disabled/missing next segment
        // just leaves this one to clampField's in-place wrap below.
        if (!ENABLED_KEYS.includes(key) || !ENABLED_KEYS.includes(next)) continue;
        const m = META.find(d => d.key === key);
        if (!m || m.min === null || m.max === null) continue;
        const range = m.max - m.min + 1;
        if (s[key] > m.max) {
            const steps = Math.floor((s[key] - m.min) / range);
            s[next] = (s[next] ?? 0) + steps;
            s[key] -= steps * range;
        } else if (s[key] < m.min) {
            const steps = Math.ceil((m.min - s[key]) / range);
            s[next] = (s[next] ?? 0) - steps;
            s[key] += steps * range;
        }
    }
}

// ---- Format-specific layout ----

// Shared between getSegmentsForFormat and formatState — kept as one
// module-level constant instead of a copy hand-typed into each.
const AJHMS_LABELS = {years: 'A', days: 'J', hours: 'H', minutes: 'M', seconds: 'S'};

// Segments the HH:MM:SS format shows, for both clock_time/datetime (all of
// META) and duration (restricted to whichever of hours/minutes/seconds are
// actually enabled for this instance) — used by both getSegmentsForFormat
// and formatState.
function hmsVisibleKeys() {
    return MODE === 'duration'
        ? ['hours', 'minutes', 'seconds'].filter(k => ENABLED_KEYS.includes(k))
        : META.map(m => m.key);
}

// Push a {type:'seg'} item per key, with a {type:'sep'} between (not
// before/after) consecutive ones — the shared shape behind the HH:MM:SS and
// DD/MM/YYYY branches below.
function pushJoined(items, keys, sep) {
    for (let i = 0; i < keys.length; i++) {
        if (i > 0) items.push({type: 'sep', text: sep});
        items.push({type: 'seg', key: keys[i]});
    }
}

function getSegmentsForFormat(fmt) {
    // Returns array of render items: {type:'seg'|'sep', key?, text?}
    if (fmt === 'AJHMS') {
        const items = [];
        for (const m of META) {
            items.push({type: 'seg', key: m.key});
            items.push({type: 'sep', text: AJHMS_LABELS[m.key] || '', cls: 'ti-unit'});
        }
        // Remove trailing space after last unit label if desired
        return items;
    }
    if (fmt === 'HH:MM:SS') {
        const items = [];
        pushJoined(items, hmsVisibleKeys(), ':');
        return items;
    }
    if (fmt === 'DD/MM/YYYY HH:MM:SS') {
        // datetime — explicit day/month/year order to match the format name
        // (META always follows the mode's declaration order, year/month/day,
        // which isn't what this format displays)
        const enabledKeys = META.map(m => m.key);
        const dateKeys = ['day', 'month', 'year'].filter(k => enabledKeys.includes(k));
        const timeKeys = ['hours', 'minutes', 'seconds'].filter(k => enabledKeys.includes(k));
        const items = [];
        pushJoined(items, dateKeys, '/');
        if (dateKeys.length > 0 && timeKeys.length > 0) {
            items.push({type: 'sep', text: ' '});
        }
        pushJoined(items, timeKeys, ':');
        return items;
    }
    return META.map(m => ({type: 'seg', key: m.key}));
}

// ---- Render ----

function pad(val, width) {
    return String(Math.abs(val)).padStart(width, '0');
}

// Identifies the DOM shape a given items list would produce (which segments/
// separators, in which order) without caring about their current values.
function itemsSignature(items) {
    return items.map(i => i.type === 'seg' ? 'S:' + i.key : 'T:' + i.text + (i.cls || '')).join('|');
}

let lastRenderedSig = null;  // shape of the .ti-field-inner DOM as of the last full rebuild
let segEls = new Map();      // data-key -> <span>, rebuilt alongside lastRenderedSig

// getSegmentsForFormat's result only actually changes when activeFormat
// changes (format toggle) — cache it instead of recomputing (plus the
// itemsSignature() derived from it) on every single render() call.
let cachedFmt = null;
let cachedItems = null;
let cachedSig = null;

function itemsForActiveFormat() {
    if (activeFormat !== cachedFmt) {
        cachedFmt = activeFormat;
        cachedItems = getSegmentsForFormat(activeFormat);
        cachedSig = itemsSignature(cachedItems);
    }
    return {items: cachedItems, sig: cachedSig};
}

function segmentText(key, displayState) {
    const m = META.find(d => d.key === key);
    const val = displayVal(key, displayState);
    return (focusedSegKey === key && digitBuffer)
        ? digitBuffer.padStart(m?.width ?? 2, '0')
        : pad(val, m?.width ?? 2);
}

function render() {
    isRendering = true;
    const displayState = toDisplayState(state, activeFormat);
    const {items, sig} = itemsForActiveFormat();

    if (sig === lastRenderedSig) {
        // Same segments/separators as last render (the overwhelmingly common
        // case — a wheel tick, arrow key or digit keystroke just changes a
        // value or which segment is focused). Patch the existing spans in
        // place instead of tearing down and rebuilding the whole field: this
        // avoids a full reflow per tick and — crucially — never destroys the
        // currently-focused element, so the browser doesn't blur/refocus on
        // every single event.
        for (const item of items) {
            if (item.type !== 'seg') continue;
            const el = segEls.get(item.key);
            if (!el) continue;
            const text = segmentText(item.key, displayState);
            if (el.textContent !== text) el.textContent = text;
            el.classList.toggle('active', focusedSegKey === item.key);
        }
    } else {
        let html = '';
        for (const item of items) {
            if (item.type === 'sep') {
                html += `<span class="ti-sep${item.cls ? ' ' + item.cls : ''}">${item.text}</span>`;
            } else {
                const focused = focusedSegKey === item.key ? ' active' : '';
                const text = segmentText(item.key, displayState);
                html += `<span class="ti-seg${focused}" data-key="${item.key}" tabindex="${INTERACTIVE ? 0 : -1}">${text}</span>`;
            }
        }
        fieldEl.innerHTML = html;
        lastRenderedSig = sig;
        segEls = new Map(
            Array.from(fieldEl.querySelectorAll('.ti-seg')).map(el => [el.dataset.key, el])
        );
    }

    // Re-attach focus to the active segment. No-op when it's already
    // focused — the common case on the patch path above, since the DOM
    // node's identity (and thus its focus) is preserved across ticks.
    if (focusedSegKey) {
        const el = segEls.get(focusedSegKey);
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
    return META.find(d => d.key === key) || {key, min: 0, max: null, width: 2};
}

function applyDelta(key, delta) {
    const displayState = toDisplayState(state, activeFormat);
    displayState[key] = (displayState[key] ?? 0) + delta;
    // Bounded modes (clock_time/datetime) carry the overflow/underflow into
    // the next segment before wrapping key itself in place; duration's own
    // fields are unbounded and normalize() (called below regardless — a
    // no-op outside duration mode) handles carrying for them instead.
    carryBounded(displayState);
    for (const k of Object.keys(displayState)) {
        displayState[k] = clampField(k, displayState[k], activeFormat);
    }
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

function updateDisplayBadge() {
    if (badgeEl) badgeEl.textContent = formatState(state, activeFormat);
}

function enterEditMode() {
    if (!INTERACTIVE || isEditing) return;
    isEditing = true;
    widget.dataset.editing = 'true';
    const firstKey = META[0]?.key;
    if (firstKey) {
        focusedSegKey = firstKey;
        digitBuffer = '';
        render();
    }
}

function exitEditMode() {
    if (!isEditing) return;
    if (focusedSegKey) applyDigitBuffer(focusedSegKey);
    focusedSegKey = null;
    digitBuffer = '';
    normalize(state);
    isEditing = false;
    widget.dataset.editing = 'false';
    commit();
}

function commit() {
    isInternalCommit = true;
    props.value = JSON.stringify(state);
    isInternalCommit = false;
    trigger('input');
    trigger('change');
    render();
    updateDisplayBadge();
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
    } else if (e.key === 'Escape') {
        e.preventDefault();
        exitEditMode();
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
    const newKey = seg.dataset.key;
    if (focusedSegKey && focusedSegKey !== newKey && digitBuffer) {
        // A digit was pending on the segment being left (clicked straight
        // into a different segment before the auto-commit timer fired) —
        // flush it instead of silently discarding it below.
        applyDigitBuffer(focusedSegKey);
        commitAndNormalize();
    }
    focusedSegKey = newKey;
    digitBuffer = '';
    render();
});

widget.addEventListener('focusout', e => {
    if (isRendering) return;  // DOM rebuild caused this, don't commit
    const nextFocused = e.relatedTarget;

    if (nextFocused && widget.contains(nextFocused)) {
        // Focus stayed inside the widget (e.g. moved to a button)
        const seg = nextFocused.closest('.ti-seg');
        if (!seg) {
            // Moved to a button — commit buffer but stay in edit mode
            applyDigitBuffer(focusedSegKey);
            commitAndNormalize();
            focusedSegKey = null;
            render();
        }
        // If it's a segment, focusin will handle the transition
        return;
    }

    // Focus left the widget entirely — exit edit mode
    exitEditMode();
});

// Click on display badge → enter edit mode
widget.querySelector('.ti-display').addEventListener('click', () => enterEditMode());

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
//
// deltaY magnitude-per-notch has no portable baseline (varies by browser/OS/
// driver) — the standard reference pattern for wheel-scrollable numeric
// inputs (e.g. jQuery UI's spinner widget) reacts to the event's sign only,
// flat +/-1 per dispatched event, for exactly that reason.
//
// TEMP EXPERIMENT — coalesced events (verified: summed, not dropped — Firefox
// APZ queues wheel events behind a content round-trip when a non-passive
// listener is present, see TODO.md) are the confirmed root cause of missed
// ticks, so scaling by deltaY magnitude recovers the correct total. There's
// no cross-hardware standard for a single notch's deltaY though — a real
// standard (v120) exists at the OS/driver layer, but browsers convert it to
// CSS pixels using their own internal, unexposed factor before JS ever sees
// it, so the observable pixel-per-notch value is specific to this browser/
// OS/mouse combination (confirmed: an earlier hardcoded 102 broke on a
// second physical mouse). Self-calibrate per session instead, tracking the
// running minimum observed |deltaY| as the current best guess at "one
// notch" — the same approach the long-established jQuery Mousewheel plugin
// uses (its `lowestDelta`). Reset after a short idle gap, also matching
// that plugin: it does this to handle switching input devices mid-session,
// but it has the convenient side effect of bounding how long a bad
// calibration (e.g. a noisy sample smaller than the true unit) can persist
// — it self-heals on the next distinct scroll gesture rather than staying
// wrong for the rest of the session. (Preferred over tracking the GCD of
// observations: GCD is corrupted by a sample landing on *either* side of
// the true unit, min-tracking only by one landing *below* it, so min is the
// less noise-sensitive of the two — and unlike GCD it doesn't self-heal
// from a bad first sample without the idle-reset backstopping it anyway, so
// there's no real cost to skipping GCD's one advantage here.)
// Seeded at 100 — the well-documented middle of the typical 100-120px
// per-notch range for standard mice (100 ≈ common Chrome-reported value,
// 120 = the actual WHEEL_DELTA Windows constant) — purely so the very first
// tick of a session, before any real sample exists, still behaves
// reasonably. Trackpads/free-spin wheels have no fixed notch at all and
// will just calibrate down toward their much smaller per-sample size.
// NOT a general fix — remove or generalize once evaluated.

const WHEEL_IDLE_RESET_MS = 200;  // matches jQuery Mousewheel's own reset window

let wheelUnitEstimate = null;  // null until the first real sample is observed (or after an idle reset)
let wheelResetTimeout = null;

// TEMP DEBUG — instrumentation for tracking down "missed" wheel ticks.
// Logs every wheel event this listener receives, including ones we end up
// ignoring, with a sequence number and time-since-last-event so the actual
// browser dispatch rate can be compared against physical scroll notches by
// eye/ear while testing. Remove once diagnosed.
let __wheelDebugCount = 0;
let __wheelDebugLastTs = null;

widget.addEventListener('wheel', e => {
    __wheelDebugCount++;
    const now = performance.now();
    const sinceLast = __wheelDebugLastTs !== null ? (now - __wheelDebugLastTs).toFixed(1) : '-';
    __wheelDebugLastTs = now;

    const seg = e.target.closest('.ti-seg');
    const targetDesc = `${e.target.tagName.toLowerCase()}.${[...e.target.classList].join('.')}`;
    console.debug(
        `[TI wheel] #${__wheelDebugCount} +${sinceLast}ms deltaY=${e.deltaY} deltaMode=${e.deltaMode}`,
        `target=${targetDesc} seg=${seg ? seg.dataset.key : 'none'} interactive=${INTERACTIVE}`,
    );

    if (!seg || !INTERACTIVE) {
        console.debug(`[TI wheel] #${__wheelDebugCount} IGNORED (no seg under pointer, or non-interactive)`);
        return;
    }
    e.preventDefault();
    const key = seg.dataset.key;
    focusedSegKey = key;
    applyDigitBuffer(key);

    // Use the best estimate available BEFORE folding this event's own
    // magnitude in — so the very first-ever event of a session divides by
    // the researched 100px seed (a real proportional guess) rather than by
    // its own magnitude (which would trivially always compute as exactly
    // +/-1, silently defeating the seed if this happened to be an
    // undetected multi-notch burst).
    const unit = wheelUnitEstimate || 100;
    const steps = Math.round(e.deltaY / unit) || (e.deltaY < 0 ? 1 : -1);
    applyDelta(key, -steps);

    const mag = Math.round(Math.abs(e.deltaY));
    if (mag > 0 && (wheelUnitEstimate === null || mag < wheelUnitEstimate)) {
        wheelUnitEstimate = mag;
    }
    clearTimeout(wheelResetTimeout);
    wheelResetTimeout = setTimeout(() => { wheelUnitEstimate = null; }, WHEEL_IDLE_RESET_MS);
    console.debug(`[TI wheel] #${__wheelDebugCount} APPLIED key=${key} unit=${unit} steps=${-steps} -> ${state[key]}`);
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
    // Copy button stays live when read-only — it's the one toolbar action
    // that doesn't mutate the field, so it's also the one CSS keeps visible
    // (see .ti-widget[data-interactive="false"] in style.css). Handled
    // before the INTERACTIVE gate below, which covers the mutating buttons.
    const copyBtn = e.target.closest('.ti-copy');
    if (copyBtn) {
        const text = formatState(state, activeFormat);
        navigator.clipboard?.writeText(text).then(() => {
            copyBtn.textContent = '✓';
            setTimeout(() => { copyBtn.textContent = '⎘'; }, 1200);
        }).catch(() => {});
        return;
    }

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
            // Math.floor((mins*60+secs)/3600) is always exactly now.getHours()
            // (minutes+seconds can never total a full hour) — use it directly.
            state = fromDisplayState(
                {hours: now.getHours(), minutes: now.getMinutes(), seconds: now.getSeconds()}, 'HH:MM:SS'
            );
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

document.addEventListener('paste', async e => {
    if (!INTERACTIVE) return;
    const active = document.activeElement;
    if (!active || !widget.contains(active) || !active.classList.contains('ti-seg')) return;
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    // Parsing (AJHMS/HH:MM:SS/DD-MM-YYYY) lives server-side so there's one
    // canonical implementation (nawminator.utils.parse_ajhms, which already
    // handles NAW-formatted space-grouped numbers) instead of a second,
    // independently-maintained parser here — paste is a rare, deliberate
    // action, so the round trip is not a concern the way it would be on a
    // per-keystroke/per-tick hot path.
    const parsed = await server.parse_pasted_text(text);
    if (parsed) {
        Object.assign(state, parsed);
        applyDefaults(state);
        commitAndNormalize();
    }
});

// ---- Format state to string (for copy) ----

function formatState(s, fmt) {
    const d = toDisplayState(s, fmt);
    if (fmt === 'AJHMS') {
        return META.map(m => `${d[m.key]}${AJHMS_LABELS[m.key]}`).join(' ');
    }
    if (fmt === 'HH:MM:SS') {
        return hmsVisibleKeys().map(k => pad(d[k]||0, k==='hours' && MODE==='duration' ? 3 : 2)).join(':');
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
    isEditing = false;
    widget.dataset.editing = 'false';
    render();
    updateDisplayBadge();
});

// ---- watch for Python-initiated interactive updates ----

watch('interactive', () => {
    // props.interactive is only populated after an explicit gr.update(interactive=...);
    // undefined means "not yet touched since mount" — the dataset value from the
    // initial html_template render already reflects the constructor's `interactive` kwarg.
    if (props.interactive === undefined) return;
    INTERACTIVE = props.interactive !== false;
    widget.dataset.interactive = String(INTERACTIVE);
    if (isEditing && !INTERACTIVE) exitEditMode();
    // The patch path in render() never regenerates each segment's tabindex
    // attribute (it only touches text/active-class), so a change that flips
    // only INTERACTIVE would otherwise leave stale tabindex values behind.
    // Force the next render() onto the full-rebuild path.
    lastRenderedSig = null;
    render();
});

// ---- Initial render ----

render();
updateDisplayBadge();

// Reserve exactly as much space in .ti-display/.ti-field as the overlaid
// .ti-btns actually needs, instead of a fixed guess (see the padding
// comment in style.css) — different instances have different numbers of
// quick-fill pills/toggle/clear/copy, so a single hardcoded reserve can't
// fit all of them. The button set is fixed at construction time (set once
// from Python props, never changes at runtime), so this only needs to run
// once, after the initial render/layout.
const btnsEl = widget.querySelector('.ti-btns');
if (btnsEl) {
    const reserve = Math.ceil(btnsEl.getBoundingClientRect().width) + 16;  // + a little breathing room
    widget.style.setProperty('--ti-btns-reserve', `${reserve}px`);
}