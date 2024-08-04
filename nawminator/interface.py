import gradio as gr
import nawminator as nm

### INPUTS


class ArmyInput:
    def __init__(self):
        import numpy as np

        army_state = gr.State(nm.army.Army())
        input_box = gr.Textbox(placeholder="Coller Armée", scale=0, show_label=False)
        unit_boxes = []
        with gr.Accordion("Units", open=False):
            with gr.Group():
                for _, short_name, _ in nm.army.unit_names:
                    with gr.Row("compact"):
                        gr.Text(
                            short_name,
                            max_lines=1,
                            show_label=False,
                            interactive=False,
                            container=False,
                            min_width=100,
                        )
                        unit_boxes.append(gr.Number(scale=2, precision=0, label=short_name, show_label=False))

        @gr.on(
            triggers=[input_box.input],
            inputs=input_box,
            outputs=[army_state, *unit_boxes],
            show_progress="hidden",
        )
        def parse_army(input_text):
            army = nm.army.Army.from_str(input_text)
            return army, *army._units

        @gr.on(
            triggers=[i.input for i in unit_boxes],
            inputs=unit_boxes,
            outputs=army_state,
        )
        def parse_units(*inputs):
            army = nm.army.Army(np.array(inputs))
            return army

        self.unit_boxes = unit_boxes
        self.state = army_state


class LevelsInput:
    def __init__(self, atk=True):
        self.state = gr.State(nm.levels.Levels())
        options = {"min_width": 50}
        with gr.Row():
            with gr.Column(min_width=100):
                with gr.Group():
                    with gr.Row():
                        gr.Text("Mandibule", **options, max_lines=0, container=False)
                        gr.Text("Carapace", **options, max_lines=0, container=False)
                    with gr.Row():
                        self.mandi_input = gr.Number(
                            label="Mandi",
                            minimum=0,
                            **options,
                            scale=1,
                            show_label=False,
                            container=False,
                        )
                        self.cara_input = gr.Number(
                            label="Cara",
                            minimum=0,
                            **options,
                            scale=1,
                            show_label=False,
                            container=False,
                        )
            with gr.Column(min_width=100):
                with gr.Group():
                    with gr.Row():
                        gr.Text("Hero", **options, max_lines=0, container=False)
                    with gr.Row():
                        self.herolvl_input = gr.Number(
                            value=180,
                            minimum=0,
                            maximum=180,
                            **options,
                            scale=2,
                            container=False,
                        )
                        self.herotype_input = gr.Dropdown(
                            value=nm.levels.HeroType.ATTAQUE,
                            choices=list(nm.levels.HeroType),
                            **options,
                            scale=3,
                            container=False,
                        )
        self.input_fields = [
            self.mandi_input,
            self.cara_input,
            self.herolvl_input,
            self.herotype_input,
        ]

        with gr.Row():
            self.alliance_input = gr.Dropdown(
                value=nm.levels.AllianceType.NEUTRE,
                label="Alliance",
                choices=[
                    *list(nm.levels.AllianceType),
                    None,
                ],
                **options,
                scale=1,
            )
            with gr.Group(visible=not atk), gr.Row():
                self.dome_input = gr.Number(label="Dôme", minimum=0, **options)
                self.loge_input = gr.Number(label="Loge", minimum=0, **options)
                self.input_fields.extend([self.dome_input, self.loge_input])
        self.input_fields.append(self.alliance_input)

        self.input_box = gr.Textbox(placeholder="Coller Niveaux", scale=0, show_label=False, max_lines=4)

        @gr.on(
            triggers=self.input_box.input,
            inputs=self.input_box,
            outputs=[*self.input_fields, self.state],
            show_progress="hidden",
        )
        def on_text_change(text_input: str):
            l = nm.levels.Levels.from_str(text_input)
            return (
                l.mandibule,
                l.carapace,
                l.hero_lvl,
                l.hero_type,
                l.dome,
                l.loge,
                l.alliance,
                l,
            )

        @gr.on(
            triggers=[inp.change for inp in self.input_fields],
            inputs=self.input_fields,
            outputs=[self.state, self.input_box],
            show_progress="hidden",
        )
        def on_input_change(m, c, hl, ht, d, l, a):
            l = nm.levels.Levels(m, c, hl, ht, 0, d, l, a)
            return l, l.to_str()


class RCInput:
    pass


### OUTPUTS


class WarPartyStats:
    def __init__(self, war_party_state: gr.State, show_labels=False):
        options = {
            "min_width": 10,
            "scale": 4,
            "container": False,
            "max_lines": 1,
            "show_label": False,
        }
        with gr.Group():
            with gr.Row("compact"):
                if show_labels:
                    gr.Text(
                        "Vie",
                        max_lines=1,
                        show_label=False,
                        interactive=False,
                        container=False,
                    )
                self.hp = hp = gr.Text(**options)
            with gr.Row("compact"):
                if show_labels:
                    gr.Text(
                        "Attaque",
                        max_lines=1,
                        show_label=False,
                        interactive=False,
                        container=False,
                    )
                self.dmg = dmg = gr.Text(**options)
            with gr.Row("compact"):
                if show_labels:
                    gr.Text(
                        "Flood",
                        max_lines=1,
                        show_label=False,
                        interactive=False,
                        container=False,
                    )
                self.cnt = cnt = gr.Text(**options)
            with gr.Row("compact"):
                if show_labels:
                    gr.Text(
                        "Ponte (Complet)",
                        max_lines=1,
                        show_label=False,
                        container=False,
                    )
                self.ponte = ponte = gr.Text(**options)
            with gr.Row("compact"):
                if show_labels:
                    gr.Text(
                        "Ponte (Effectif)",
                        max_lines=1,
                        show_label=False,
                        container=False,
                    )
                self.adj_ponte = adj_ponte = gr.Text(**options)

        @gr.on(
            triggers=war_party_state.change,
            inputs=war_party_state,
            outputs=[hp, dmg, cnt, ponte, adj_ponte],
            show_progress="hidden",
        )
        def update_stats(p: nm.war.WarParty):
            return (
                f"{p.total_hp:,.0f}".replace(",", " "),
                f"{p.total_dmg:,.0f}".replace(",", " "),
                f"{p.army.count:,.0f}".replace(",", " "),
                f"{nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(p.army.recruit_time()[1]))}",
                f"{nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(p.army.non_xp_recruit_time()[1]))}",
            )
