import gradio as gr
import nawminator as nm
import nmsite
import math
import datetime as dt

def hunt_tab(config: nmsite.config.Config):
    HuntTab(config.hero_enabled)

class HuntTab:
    def __init__(self, hero_enabled: bool):
        self.hero_enabled = hero_enabled
        self._set_layout()

    def _set_layout(self):
        with gr.Tabs():
            with gr.Tab("Préparation"):
                self._set_simulate_layout()
            with gr.Tab("Analyse"):
                self._set_analyse_layout()
    
    def _set_simulate_layout(self):
        with gr.Row():
            with gr.Accordion("Mon armée (NON UTILISEE)", open=False):
                army_input = nmsite.interface.ArmyInput()
            with gr.Accordion("Mes niveaux", open=False):
                levels_input = nmsite.interface.LevelsInputComponent(hero_enabled=self.hero_enabled, show_buildings=False)
        with gr.Row():
            start = gr.Number(minimum=0, label="TDC de départ", min_width=75)
            hunt = gr.Number(minimum=0, label="TDC chassé", min_width=75)
            hunting_speed = gr.Number(label="VT", minimum=0, maximum=40, min_width=75)

        with gr.Row():
            with gr.Column(min_width=60):
                duration = gr.Text("0S", label="Durée")
                time_efficiency = gr.Number(label="Efficacité Temporelle")
            with gr.Column(min_width=60):
                diff = gr.Number(0, minimum=0, label="Difficulté")
                pertes = gr.Number(0, label="Pertes estimées en OS(JS)", visible=False, interactive=False)
                equiv_tdp = gr.Number(0, label="Equivalent TDP", visible=False)

        @gr.on(
            triggers=[start.input, hunt.input, hunting_speed.input],
            inputs=[start, hunt, hunting_speed],
            outputs = [duration, time_efficiency, diff],
            show_progress="hidden",
        )
        def simulate(start, hunt, vt):
            duration = nm.formulas.hunt_duration(start, hunt, vt)
            efficiency = (3600 * hunt/duration) / nm.formulas.max_hunt_per_hour(vt) 

            difficulty = nm.formulas.hunt_difficulty(start, hunt)

            duration_text = nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(duration)))

            return duration_text, float(efficiency), int(difficulty)

        @gr.on(
            triggers=[diff.change, levels_input.change],
            inputs=[diff, levels_input],
            outputs=[pertes],
            show_progress="hidden",
        )
        def compute_losses(diff, levels: nm.levels.Levels):
            dmg_taken = diff * 0.3596 * 0.1
            js_lost = round(dmg_taken / nm.battle.WarParty(army=nm.army.Army(JS=1), bonuses=nm.battle.Bonuses(*levels.bonus_atk), atk=True).total_hp)
            return gr.Number(js_lost, visible=True)
        
        @gr.on(
            triggers=[pertes.change, duration.change],
            inputs=[pertes, duration],
            outputs=[equiv_tdp],
            show_progress="hidden",
        )
        def compute_equiv_tdp(js_lost, duration):
            duration = nm.utils.parse_ajhms(duration).total_seconds()
            if duration == 0 or js_lost == 0:
                return -1
            js_lost_per_second = js_lost/duration
            equiv_tdp = math.log((1/js_lost_per_second)/nm.army.unit_stats[2][3], 0.95)
            return gr.Number(equiv_tdp, visible=True)

    def _set_analyse_layout(self):
        pass        



        

