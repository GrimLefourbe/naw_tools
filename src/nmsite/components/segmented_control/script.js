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
    const val = btn.dataset.value;
    updateSelection(val);
    props.value = val;
    trigger(`select_${val}`);
    trigger('select');
    trigger('input');
    trigger('change');
});
