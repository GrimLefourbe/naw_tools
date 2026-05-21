import gradio as gr


def interactivity_updates(value: str, interactivity_map: dict) -> tuple:
    """Build gr.update outputs when a mode selector switches which fields are editable.

    Returns (value, *gr.update(interactive=..., elem_classes=...)) — one update per
    boolean in interactivity_map[value]. Read-only fields get elem_classes=["result-field"].
    """
    return (value,) + tuple(
        gr.update(interactive=iv, elem_classes=[] if iv else ["result-field"])
        for iv in interactivity_map[value]
    )
