import nawminator as nm
import gradio as gr
import numpy as np
from nmsite import interface

def combat_tab():
    CombatTab()

class CombatTab():
    def configure_layout(self):
        with gr.Row():
            with gr.Column(variant="panel", min_width=175, elem_classes=["left"]) as attacker_col:
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Attaquant</div>"
                )
                self.attacker_levels_input = interface.LevelsInput(atk=False)
                self.attacker_army_input = interface.ArmyInput()

            with gr.Column(variant="panel", min_width=175, elem_classes=["right"]) as defender_col:
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Défenseur</div>"
                )
                self.defender_levels_input = interface.LevelsInput(atk=False)
                self.defender_army_input = interface.ArmyInput()

            with gr.Column(scale=2, min_width=400, elem_classes=["middle"]):
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Combat</div>"
                )
                with gr.Row():
                    gr.Text(scale=1, show_label=False, max_lines=1, interactive=False)
                    self.invert_button = gr.Button("<--->", scale=0, min_width=75)
                    self.lieu_input = gr.Radio(
                        value=nm.levels.FightZone.DOME,
                        choices=list(nm.levels.FightZone),
                        scale=1,
                        show_label=False,
                    )
                with gr.Group(), gr.Row():
                    with gr.Column(scale=1, min_width=10):
                        interface.WarPartyStats(
                            self.attacker_party_state,
                            show_labels=False,
                        )
                    center_col_width = 75
                    with gr.Column(scale=0, min_width=center_col_width):
                        gr.Text(
                            "Vie",
                            show_label=False,
                            min_width=center_col_width,
                            scale=0,
                            container=False,
                            max_lines=1,
                        )
                        gr.Text(
                            "Attaque",
                            show_label=False,
                            min_width=center_col_width,
                            scale=0,
                            container=False,
                            max_lines=1,
                        )
                        gr.Text(
                            "Flood",
                            show_label=False,
                            min_width=center_col_width,
                            scale=0,
                            container=False,
                            max_lines=1,
                        )
                        gr.Text(
                            "HOF",
                            show_label=False,
                            min_width=center_col_width,
                            scale=0,
                            container=False,
                            max_lines=1,
                        )
                        gr.Text(
                            "Adj. HOF",
                            show_label=False,
                            min_width=center_col_width,
                            scale=0,
                            container=False,
                            max_lines=1,
                        )
                    with gr.Column(scale=1, min_width=10):
                        interface.WarPartyStats(
                            self.defender_party_state,
                            show_labels=False,
                            right_to_left=True,
                        )
                with gr.Row():
                    self.analyse_button = gr.Button("Analyse!")
                    self.simu_btn = gr.Button("Bagarre!")
                self.output = gr.Textbox(label="Rapport de Combat")

    def configure_triggers(self):
        @gr.on(
            triggers=[
                self.attacker_army_input.state.change,
                self.attacker_levels_input.state.change,
            ],
            inputs=[self.attacker_army_input.state, self.attacker_levels_input.state],
            outputs=self.attacker_party_state,
        )
        def attacker_update(army: nm.army.Army, levels: nm.levels.Levels):
            return nm.war.WarParty(army, nm.war.Bonuses(*levels.bonus_atk), atk=True)

        @gr.on(
            triggers=[
                self.defender_army_input.state.change,
                self.defender_levels_input.state.change,
                self.lieu_input.change,
            ],
            inputs=[
                self.defender_army_input.state,
                self.defender_levels_input.state,
                self.lieu_input,
            ],
            outputs=self.defender_party_state,
        )
        def defender_update(army: nm.army.Army, levels: nm.levels.Levels, lieu: nm.levels.FightZone):
            match lieu:
                case nm.levels.FightZone.TDC:
                    bonuses = levels.bonus_tdc
                case nm.levels.FightZone.DOME:
                    bonuses = levels.bonus_dome
                case nm.levels.FightZone.LOGE:
                    bonuses = levels.bonus_loge
                case _:
                    raise AssertionError
            return nm.war.WarParty(army, nm.war.Bonuses(*bonuses), atk=False)

        @gr.on(
            triggers=self.invert_button.click,
            inputs=[
                self.attacker_army_input.state,
                self.defender_army_input.state,
                self.attacker_levels_input.state,
                self.defender_levels_input.state,
                self.attacker_levels_input.input_box,
                self.defender_levels_input.input_box,
                *self.attacker_army_input.unit_boxes,
                *self.defender_army_input.unit_boxes,
                *self.attacker_levels_input.input_fields,
                *self.defender_levels_input.input_fields,
            ],
            outputs=[
                self.defender_army_input.state,
                self.attacker_army_input.state,
                self.defender_levels_input.state,
                self.attacker_levels_input.state,
                self.defender_levels_input.input_box,
                self.attacker_levels_input.input_box,
                *self.defender_army_input.unit_boxes,
                *self.attacker_army_input.unit_boxes,
                *self.defender_levels_input.input_fields,
                *self.attacker_levels_input.input_fields,
            ],
            show_progress="hidden",
        )
        def invert_players(*args):
            print("Invert!")
            return args

        @gr.on(
            triggers=self.simu_btn.click,
            inputs=[self.attacker_party_state, self.defender_party_state, self.lieu_input],
            outputs=self.output,
        )
        def simulate_fight(atk_party: nm.war.WarParty, def_party: nm.war.WarParty, lieu: nm.levels.FightZone):
            battle = nm.war.simulate_battle(attacker=atk_party, defender=def_party)
            return gr.Textbox(value=battle.to_rc(), label=f"Résultat en {lieu}")

        @gr.on(
            triggers=self.analyse_button.click,
            inputs=[
                self.output,
                self.lieu_input,
                self.attacker_levels_input.alliance_input,
                self.defender_levels_input.alliance_input,
            ],
            outputs=[
                self.attacker_party_state,
                self.defender_party_state,
                self.attacker_army_input.state,
                *self.attacker_army_input.unit_boxes,
                self.attacker_levels_input.state,
                *self.attacker_levels_input.input_fields,
                self.defender_army_input.state,
                *self.defender_army_input.unit_boxes,
                self.defender_levels_input.state,
                *self.defender_levels_input.input_fields,
            ],
            show_progress="hidden",
        )
        def analyse_fight(rc: str, lieu: nm.levels.FightZone, atk_alli, def_alli):
            attacker, defender = nm.war.analyze_battle(nm.battle.Battle.from_rc(rc))
            attacker_levels = l = nm.levels.Levels.from_bonuses(
                attacker.bonuses.dmg, attacker.bonuses.hp, lieu=lieu, alli_type=atk_alli, atk=True
            )
            if l.hero_lvl is None:
                raise ValueError("Hero lvl can't be None")
            attacker_levels_fields = [
                l.mandibule,
                l.carapace,
                l.hero_lvl,
                l.hero_type,
                l.special,
                l.dome,
                l.loge,
                l.alliance,
            ]
            defender_levels = l = nm.levels.Levels.from_bonuses(
                defender.bonuses.dmg, defender.bonuses.hp, lieu=lieu, alli_type=def_alli, atk=False
            )
            if l.hero_lvl is None:
                raise ValueError("Hero lvl can't be None")
            defender_levels_fields = [
                l.mandibule,
                l.carapace,
                l.hero_lvl,
                l.hero_type,
                l.special,
                l.dome,
                l.loge,
                l.alliance,
            ]

            return (
                attacker,
                defender,
                attacker.army,
                *attacker.army._units,
                attacker_levels,
                *attacker_levels_fields,
                defender.army,
                *defender.army._units,
                defender_levels,
                *defender_levels_fields,
            )

    def __init__(self):
        gr.HTML("""
        <style>
        /* Desktop order */
        .left   { order: 1; }
        .middle { order: 2; }
        .right  { order: 3; }

        /* When screen < 900px, middle wraps first */
        @media (max-width: 900px) {
            .middle { order: 3; }  /* move to last -> wraps first */
            .right  { order: 2; }
        }
        </style>
        """, container=False, elem_classes=["css-injector"], render=True, visible=True)
        self.attacker_party_state = gr.State(nm.war.WarParty(nm.army.Army(), nm.war.Bonuses(np.float64(0), np.float64(0)), True))
        self.defender_party_state = gr.State(nm.war.WarParty(nm.army.Army(), nm.war.Bonuses(np.float64(0), np.float64(0)), False))
        self.configure_layout()
        self.configure_triggers()



            # defender_col.render()
