import gradio as gr
import nawminator as nm

def pontes_tab():
    with gr.Row():
        with gr.Column(variant="compact"):
            army_input = nm.interface.ArmyInput()
        with gr.Column(variant="compact", scale=3):
            with gr.Group():
                with gr.Row(variant="compact"):
                    bonuses = [
                        gr.Number(label="TDP", precision=0),
                        gr.Number(label="Quête Alliance", precision=0),
                    ]
            output = gr.Text(label="Durée", scale=7, interactive=False)

    @gr.on(
        triggers=[army_input.state.change, *[i.change for i in bonuses]],
        inputs=[army_input.state, *bonuses],
        outputs=output,
    )
    def compute_ponte_duration(army: nm.army.Army, tdp, bonus_alli):
        durations, total_duration = army.recruit_time(tdp, bonus_alli)
        return nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(total_duration))