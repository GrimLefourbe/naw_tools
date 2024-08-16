import gradio as gr
from nawminator.utils import seconds_to_yjhms, format_yjhms
import nawminator as nm
import numpy as np


with gr.Blocks(title="Nawminator") as demo:
    with gr.Tab("Simulateur pontes"):
        with gr.Row():
            with gr.Column(variant="compact"):
                army_input = nm.interface.ArmyInput()
            with gr.Column(variant="compact", scale=3):
                with gr.Group():
                    with gr.Row("compact"):
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
            def compute_duration(army: nm.army.Army, tdp, bonus_alli):
                durations, total_duration = army.recruit_time(tdp, bonus_alli)
                return format_yjhms(seconds_to_yjhms(total_duration))

    with gr.Tab("Simulateur Combat"):
        with gr.Row():
            attacker_party_state = gr.State(nm.war.WarParty(nm.army.Army(), nm.war.Bonuses(0, 0), True))
            defender_party_state = gr.State(nm.war.WarParty(nm.army.Army(), nm.war.Bonuses(0, 0), False))

            with gr.Column(variant="compact", render=False) as attacker_col:
                attacker_levels_input = nm.interface.LevelsInput(atk=True)
                attacker_army_input = nm.interface.ArmyInput()

            with gr.Column(variant="compact", render=False) as defender_col:
                defender_levels_input = nm.interface.LevelsInput(atk=False)
                defender_army_input = nm.interface.ArmyInput()

            attacker_col.render()

            with gr.Column(scale=2):
                with gr.Row():
                    gr.Text(scale=1, show_label=False, max_lines=1, interactive=False)
                    invert_button = gr.Button("<--->", scale=0, min_width=75)
                    lieu_input = gr.Radio(
                        value=nm.levels.FightZone.DOME,
                        choices=list(nm.levels.FightZone),
                        scale=1,
                        show_label=False,
                    )
                with gr.Group(), gr.Row():
                    with gr.Column(scale=1, min_width=10):
                        nm.interface.WarPartyStats(
                            attacker_party_state,
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
                        nm.interface.WarPartyStats(
                            defender_party_state,
                            show_labels=False,
                            right_to_left=True,
                        )
                with gr.Row():
                    analyse_button = gr.Button("Analyse!")
                    simu_btn = gr.Button("Bagarre!")
                output = gr.Textbox(label="Résultat")

                @gr.on(
                    triggers=[
                        attacker_army_input.state.change,
                        attacker_levels_input.state.change,
                    ],
                    inputs=[attacker_army_input.state, attacker_levels_input.state],
                    outputs=attacker_party_state,
                )
                def attacker_update(army: nm.army.Army, levels: nm.levels.Levels):
                    return nm.war.WarParty(army, nm.war.Bonuses(*levels.bonus_atk), atk=True)

                @gr.on(
                    triggers=[
                        defender_army_input.state.change,
                        defender_levels_input.state.change,
                        lieu_input.change,
                    ],
                    inputs=[
                        defender_army_input.state,
                        defender_levels_input.state,
                        lieu_input,
                    ],
                    outputs=defender_party_state,
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
                    triggers=invert_button.click,
                    inputs=[
                        attacker_army_input.state,
                        defender_army_input.state,
                        attacker_levels_input.state,
                        defender_levels_input.state,
                        attacker_levels_input.input_box,
                        defender_levels_input.input_box,
                        *attacker_army_input.unit_boxes,
                        *defender_army_input.unit_boxes,
                        *attacker_levels_input.input_fields,
                        *defender_levels_input.input_fields,
                    ],
                    outputs=[
                        defender_army_input.state,
                        attacker_army_input.state,
                        defender_levels_input.state,
                        attacker_levels_input.state,
                        defender_levels_input.input_box,
                        attacker_levels_input.input_box,
                        *defender_army_input.unit_boxes,
                        *attacker_army_input.unit_boxes,
                        *defender_levels_input.input_fields,
                        *attacker_levels_input.input_fields,
                    ],
                    show_progress="hidden",
                )
                def invert_players(*args):
                    print("Invert!")
                    return args

                @gr.on(
                    triggers=simu_btn.click,
                    inputs=[attacker_party_state, defender_party_state, lieu_input],
                    outputs=output,
                )
                def simulate_fight(atk_party: nm.war.WarParty, def_party: nm.war.WarParty, lieu: nm.levels.FightZone):
                    battle = nm.war.simulate_battle(attacker=atk_party, defender=def_party)
                    return gr.Textbox(value=battle.to_rc(), label=f"Résultat en {lieu}")

                @gr.on(
                    triggers=analyse_button.click,
                    inputs=[
                        output,
                        lieu_input,
                        attacker_levels_input.alliance_input,
                        defender_levels_input.alliance_input,
                    ],
                    outputs=[
                        attacker_party_state,
                        defender_party_state,
                        attacker_army_input.state,
                        *attacker_army_input.unit_boxes,
                        attacker_levels_input.state,
                        *attacker_levels_input.input_fields,
                        defender_army_input.state,
                        *defender_army_input.unit_boxes,
                        defender_levels_input.state,
                        *defender_levels_input.input_fields,
                    ],
                    show_progress="hidden",
                )
                def analyse_fight(rc: str, lieu: nm.levels.FightZone, atk_alli, def_alli):
                    attacker, defender = nm.war.analyze_battle(nm.battle.Battle.from_rc(rc))
                    attacker_levels = l = nm.levels.Levels.from_bonuses(
                        attacker.bonuses.dmg, attacker.bonuses.hp, lieu=lieu, alli_type=atk_alli, atk=True
                    )

                    attacker_levels_fields = [
                        l.mandibule,
                        l.carapace,
                        l.hero_lvl,
                        l.hero_type,
                        l.dome,
                        l.loge,
                        l.alliance,
                    ]
                    defender_levels = l = nm.levels.Levels.from_bonuses(
                        defender.bonuses.dmg, defender.bonuses.hp, lieu=lieu, alli_type=def_alli, atk=False
                    )
                    defender_levels_fields = [
                        l.mandibule,
                        l.carapace,
                        l.hero_lvl,
                        l.hero_type,
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

            defender_col.render()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
