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
