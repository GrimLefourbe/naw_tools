import gradio as gr
import nawminator as nm
import nmsite
import math
import datetime as dt

def hunt_tab():
    HuntTab()

class HuntTab:
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
                levels_input = nmsite.interface.LevelsInput()
        with gr.Row():
            start = gr.Number(minimum=0, label="TDC de départ")
            hunt = gr.Number(minimum=0, label="TDC chassé")
            hunting_speed = gr.Number(label="VT", minimum=0, maximum=40)

        with gr.Row():            
            duration = gr.Text("0S", label="Durée")
            time_efficiency = gr.Number(label="Efficacité Temporelle")

        with gr.Row():
            diff = gr.Number(0, minimum=0, label="Difficulté")
            pertes = gr.Number(0, label="Pertes estimées en OS(JS)")
            equiv_tdp = gr.Number(0, label="Equivalent TDP")

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
            triggers=[diff.change, levels_input.cara_input.change, levels_input.spe_input.change, levels_input.alliance_input.change],
            inputs=[diff, levels_input.cara_input, levels_input.spe_input, levels_input.alliance_input],
            outputs=[pertes],
            show_progress="hidden",
        )
        def compute_losses(diff, cara, spe_cbt, alli_type):
            dmg_taken = diff * 0.3596 * 0.1
            js_lost = round(dmg_taken / nm.battle.WarParty(army=nm.army.Army(JS=1), bonuses=nm.battle.Bonuses(*nm.levels.Levels(carapace=cara, special=spe_cbt, alliance=alli_type if alli_type != "None" else None).bonus_atk), atk=True).total_hp)
            # js_lost = round(dmg_taken / (nm.army.unit_stats[2][0] * (1 + 0.05 * cara + spe_cbt*0.02)))
            return js_lost
        
        @gr.on(
            triggers=[pertes.change, duration.change],
            inputs=[pertes, duration],
            outputs=[equiv_tdp],
            show_progress="hidden",
        )
        def compute_equiv_tdp(js_lost, duration):
            duration = nm.utils.YJHMS_to_seconds(nm.utils.parse_YJHMS(duration))
            if duration == 0 or js_lost == 0:
                return -1
            js_lost_per_second = js_lost/duration
            equiv_tdp = math.log((1/js_lost_per_second)/nm.army.unit_stats[2][3], 0.95)
            return equiv_tdp

    def _set_analyse_layout(self):
        pass        

    def __init__(self):
        self._set_layout()


        

