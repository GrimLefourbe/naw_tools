import nawminator as nm
import gradio as gr
import numpy as np
from nmsite import interface, config

def combat_tab(config: config.Config):
    CombatTab(config.hero_enabled)

class CombatTab():
    def __init__(self, hero_enabled: bool):
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
        self.hero_enabled = hero_enabled
        self.attacker_party_state = gr.State(nm.battle.WarParty(nm.army.Army(), nm.battle.Bonuses(np.float64(0), np.float64(0)), True))
        self.defender_party_state = gr.State(nm.battle.WarParty(nm.army.Army(), nm.battle.Bonuses(np.float64(0), np.float64(0)), False))
        self.configure_layout()
        self.configure_triggers()

    def configure_layout(self):
        with gr.Row():
            with gr.Column(variant="panel", min_width=175, elem_classes=["left"]) as attacker_col:
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Attaquant</div>"
                )
                self.attacker_levels_input = interface.LevelsInputComponent(label="Niveaux Attaquant", hero_enabled=self.hero_enabled, show_buildings=True)
                self.attacker_army_input = interface.ArmyInputHTML(show_import=False, recap_format="full")

            with gr.Column(variant="panel", min_width=175, elem_classes=["right"]) as defender_col:
                gr.Markdown(
                    "<div style='text-align:center; font-weight:bold; font-size:18px;'>Défenseur</div>"
                )
                self.defender_levels_input = interface.LevelsInputComponent(label="Niveaux Défenseur", hero_enabled=self.hero_enabled, show_buildings=True)
                self.defender_army_input = interface.ArmyInputHTML(show_import=False, btn_align="left", recap_format="full")

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
                self.attacker_army_input.change,
                self.attacker_levels_input.change,
            ],
            inputs=[self.attacker_army_input, self.attacker_levels_input],
            outputs=self.attacker_party_state,
        )
        def attacker_update(army: nm.army.Army, levels: nm.levels.Levels):
            return nm.battle.WarParty(army, nm.battle.Bonuses(*levels.bonus_atk), atk=True)

        @gr.on(
            triggers=[
                self.defender_army_input.change,
                self.defender_levels_input.change,
                self.lieu_input.change,
            ],
            inputs=[
                self.defender_army_input,
                self.defender_levels_input,
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
            return nm.battle.WarParty(army, nm.battle.Bonuses(*bonuses), atk=False)

        @gr.on(
            triggers=self.invert_button.click,
            inputs=[
                self.attacker_army_input,
                self.defender_army_input,
                self.attacker_levels_input,
                self.defender_levels_input,
            ],
            outputs=[
                self.defender_army_input,
                self.attacker_army_input,
                self.defender_levels_input,
                self.attacker_levels_input,
            ],
            show_progress="hidden",
        )
        def invert_players(*args):
            return args

        @gr.on(
            triggers=self.simu_btn.click,
            inputs=[self.attacker_party_state, self.defender_party_state, self.lieu_input],
            outputs=self.output,
        )
        def simulate_fight(atk_party: nm.battle.WarParty, def_party: nm.battle.WarParty, lieu: nm.levels.FightZone):
            battle = nm.battle.BattleReport.simulate(attacker=atk_party, defender=def_party)
            return gr.Textbox(value=battle.to_str(), label=f"Résultat en {lieu}")

        @gr.on(
            triggers=self.analyse_button.click,
            inputs=[
                self.output,
                self.lieu_input,
                self.attacker_levels_input,
                self.defender_levels_input,
            ],
            outputs=[
                self.attacker_party_state,
                self.defender_party_state,
                self.attacker_army_input,
                self.attacker_levels_input,
                self.defender_army_input,
                self.defender_levels_input,
            ],
            show_progress="hidden",
        )
        def analyse_fight(rc: str, lieu: nm.levels.FightZone, atk_levels_in: nm.levels.Levels, def_levels_in: nm.levels.Levels):
            attacker, defender = nm.battle.BattleReport.from_str(rc).analyze()
            attacker_levels = nm.levels.Levels.from_bonuses(
                bonus_dmg=(attacker.bonuses.min_dmg, attacker.bonuses.max_dmg),
                bonus_hp=(attacker.bonuses.min_hp, attacker.bonuses.max_hp),
                lieu=lieu,
                alli_type=atk_levels_in.alliance,
                atk=True,
                hero_enabled=self.hero_enabled,
            )
            defender_levels = nm.levels.Levels.from_bonuses(
                bonus_dmg=(defender.bonuses.min_dmg, defender.bonuses.max_dmg),
                bonus_hp=(defender.bonuses.min_hp, defender.bonuses.max_hp),
                lieu=lieu,
                alli_type=def_levels_in.alliance,
                atk=False,
                hero_enabled=self.hero_enabled,
            )
            return (
                attacker,
                defender,
                attacker.army,
                attacker_levels,
                defender.army,
                defender_levels,
            )

