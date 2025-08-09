import gradio as gr
from nawminator.utils import seconds_to_yjhms, format_yjhms
import nawminator as nm
import numpy as np

css = """
/* 1️⃣ Hide the HTML block itself */
.css-injector {
    opacity: 0;
    pointer-events: none;
    height: 0 !important;
    flex: 0 0 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    margin-right: -4 !important; /* cancel flex gap */
}

.smgroup {
    gap: 0.25rem;
    min-width: 0 !important;
}"""

with gr.Blocks(title="Nawminator", css=css, fill_width=True) as demo:
    with gr.Tabs() as tabs:
        with gr.Tab("Combat"):
            from nawminator.tabs import combat
            combat.combat_tab()

        with gr.Tab("Pontes"):
            from nawminator.tabs import pontes
            pontes.pontes_tab()

        with gr.Tab("Durées"):
            from nawminator.tabs import durees
            durees.durees_tab()

        with gr.Tab("Synchro"):
            from nawminator.tabs import synchro
            demo.load(**synchro.synchro_tab(demo))
        



if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
