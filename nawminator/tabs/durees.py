import gradio as gr
import nawminator as nm

def durees_tab():
    with gr.Row():
        with gr.Column(), gr.Group():
            args = {"container": False, "min_width": 60}
            with gr.Row():
                gr.Text("x", **args)
                from_x = gr.Number(value=0, scale=0, **args)
            with gr.Row():
                gr.Text("y", **args)
                from_y = gr.Number(value=0, scale=0, **args)
            with gr.Row():
                gr.Text("VA", **args)
                from_va = gr.Number(value=0, scale=0, **args)
        with gr.Column(), gr.Group():
            with gr.Row():
                gr.Text("x", **args)
                to_x = gr.Number(value=0, scale=0, **args)
            with gr.Row():
                gr.Text("y", **args)
                to_y = gr.Number(value=0, scale=0, **args)
    with gr.Row():
        duration = gr.Text("0s", label="Durée")

    @gr.on(
        triggers=[
            from_x.change, from_y.change, from_va.change, to_x.change, to_y.change
        ],
        inputs=[
            from_x, from_y, to_x, to_y, from_va,
        ],
        outputs=[
            duration
        ],
        show_progress="hidden",
    )
    def compute_duration(x1, y1, x2, y2, va):
        return nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(nm.formulas.duree_attaque(x1, y1, x2, y2, va)))
