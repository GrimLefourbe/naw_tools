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
            return nm.army.Army(inputs)

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
    def __init__(self, war_party_state: gr.State, show_labels=False, right_to_left=False):
        options = {
            "min_width": 10,
            "container": False,
            "max_lines": 1,
            "show_label": False,
        }

        def make_row(label_str: str, show_extra: bool) -> tuple[gr.Text, gr.Text, gr.Text]:
            label = gr.Text(
                label_str,
                max_lines=1,
                show_label=False,
                interactive=False,
                container=False,
                render=False,
            )
            value_display = gr.Text(**options, render=False, scale=4)
            extra_box = gr.Text(**options, render=False, scale=2)
            if right_to_left:
                value_display.render()
                if show_extra:
                    extra_box.render()
                if show_labels:
                    label.render()
            else:
                if show_labels:
                    label.render()
                if show_extra:
                    extra_box.render()
                value_display.render()

            return value_display, extra_box, label

        with gr.Group():
            with gr.Row("compact"):
                self.hp, self.hp_bonus, label = make_row("Vie", True)
            with gr.Row("compact"):
                self.dmg, self.dmg_bonus, label = make_row("Attaque", True)
            with gr.Row("compact"):
                self.cnt, _, label = make_row("Flood", False)
            with gr.Row("compact"):
                self.ponte, _, label = make_row("Ponte (Complet)", False)
            with gr.Row("compact"):
                self.adj_ponte, _, label = make_row("Ponte (Effectif)", False)

        @gr.on(
            triggers=war_party_state.change,
            inputs=war_party_state,
            outputs=[self.hp, self.hp_bonus, self.dmg, self.dmg_bonus, self.cnt, self.ponte, self.adj_ponte],
            show_progress="hidden",
        )
        def update_stats(p: nm.war.WarParty):
            return (
                f"{p.total_hp:,.0f}".replace(",", " "),
                f"+{p.bonuses.hp:.0%}",
                f"{p.total_dmg:,.0f}".replace(",", " "),
                f"+{p.bonuses.dmg:.0%}",
                f"{p.army.count:,.0f}".replace(",", " "),
                f"{nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(p.army.recruit_time()[1]))}",
                f"{nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(p.army.non_xp_recruit_time()[1]))}",
            )
