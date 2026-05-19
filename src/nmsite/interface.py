from pickle import NONE
import gradio as gr
import nawminator as nm
import datetime as dt

import typing as t
if t.TYPE_CHECKING: 
    from gradio.components import FormComponent
### INPUTS


class ArmyInput:
    def __init__(self):
        import numpy as np

        army_state = gr.State(nm.army.Army())
        input_box = gr.Textbox(placeholder="Coller Armée", scale=0, show_label=False, container=False)
        unit_boxes = []
        with gr.Accordion("Units", open=False):
            with gr.Group():
                for _, short_name, _ in nm.army.unit_names:
                    with gr.Row():
                        gr.Text(
                            short_name,
                            max_lines=1,
                            show_label=False,
                            interactive=False,
                            container=False,
                            min_width=100,
                        )
                        unit_boxes.append(gr.Number(scale=2, precision=0, label=short_name, show_label=False, container=False))

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
        def parse_units(*inputs: tuple[str]):
            return nm.army.Army(inputs) # type: ignore

        self.unit_boxes = unit_boxes
        self.state = army_state


class ListArmyInput:
    """Army input for use inside @gr.render list rows.

    No internal gr.State — creating gr.State inside @gr.render fires state.change
    on initialization, causing render cascades. State management is the caller's
    responsibility: wire paste.input and unit_boxes.input to whatever state you need.
    Accordion open/closed state is preserved across re-renders via key=.
    """

    def __init__(self, key_prefix: str, initial_army: nm.army.Army | None = None):
        army = initial_army or nm.army.Army()
        self.paste = gr.Textbox(
            value=army.to_str_compact(sep=", ") if army.count > 0 else "",
            placeholder="Coller Armée",
            show_label=False,
            container=False,
        )
        self.unit_boxes = []
        with gr.Accordion("Unités", open=False, key=f"{key_prefix}-accordion"):
            with gr.Group():
                for idx, (_, short_name, _) in enumerate(nm.army.unit_names):
                    with gr.Row():
                        gr.Text(
                            short_name,
                            max_lines=1,
                            show_label=False,
                            interactive=False,
                            container=False,
                            min_width=100,
                        )
                        self.unit_boxes.append(
                            gr.Number(
                                value=int(army._units[idx]),
                                scale=2, precision=0,
                                label=short_name, show_label=False, container=False,
                            )
                        )

        # No triggers registered — callers inside @gr.render must wire paste.input and
        # unit_boxes.input themselves. Registering triggers here would create a second
        # fn_id for the same event, and when a caller's handler triggers a re-render,
        # the still-in-flight internal handler's fn_id gets removed → KeyError.


class LevelsInput:
    def __init__(self, hero_enabled: bool, atk=True, min_width=200):
        self.state = gr.State(nm.levels.Levels())
        self.input_fields: list[FormComponent] = []
        # self.possible_fields = [
        #     "mandibule",
        #     "carapace",
        #     "hero_lvl",
        #     "hero_type",
        #     "train",
        #     "dome",
        #     "loge",
        #     "alliance",
        #     "special",
        # ]
        # self.enabled = {
        #     k: k in enabled for k in self.possible_fields
        # }
        self.hero_enabled = hero_enabled
        self._build_layout(atk, min_width)
        self._configure_triggers()

    def _build_layout(self, atk, min_width):
        half_min_width = (min_width // 2) - 5

        with gr.Column(min_width=200):
            self._research_block(min_width=half_min_width)
            self._hero_spe_block(min_width=half_min_width)

            self._buildings_block(atk, half_min_width)
            self.input_fields.append(self.alliance_input)

            with gr.Group(), gr.Row(equal_height=True):
                self.input_box = gr.Textbox(
                    placeholder="Coller Niveaux",
                    show_label=False, 
                    max_lines=3, 
                    scale=4, 
                    min_width=60,
                    container=False,
                    render=False,
                )
                self.paste_btn = gr.Button("📥︎", scale=1, variant="secondary", size="sm", min_width=20)
                self.input_box.render()
                self.copy_btn = gr.Button("📤︎", scale=1, variant="secondary", size="sm", min_width=20)

    def _research_block(self, min_width):
        with gr.Group(), gr.Row(): #Mandi/Cara section
            with gr.Column(min_width=min_width):
                gr.Text("Mandibule", scale=3, max_lines=0, container=False)
                self.mandi_input = gr.Number(
                    label="Mandi",
                    minimum=0,
                    scale=1,
                    show_label=False,
                    container=False,
                )
            with gr.Column(min_width=min_width):
                gr.Text("Carapace", scale=3, max_lines=0, container=False)
                self.cara_input = gr.Number(
                    label="Cara",
                    minimum=0,
                    scale=1,
                    show_label=False,
                    container=False,
                )
        self.input_fields.extend([
            self.mandi_input,
            self.cara_input,
        ])

    def _hero_spe_block(self, min_width):
        with gr.Row(): #Hero/Spe section
            with gr.Group(visible=self.hero_enabled):
                # gr.Text("Hero", max_lines=0, container=False)
                self.herolvl_input = gr.Number(
                    value=0,
                    minimum=0,
                    maximum=180,
                    scale=2,
                    container=False,
                    min_width=10,
                )
                self.herotype_input = gr.Dropdown(
                    value=nm.levels.HeroType.ATTAQUE,
                    choices=list(nm.levels.HeroType),
                    scale=3,
                    container=False,
                    min_width=10,
                )
                self.input_fields.append(self.herolvl_input)
                self.input_fields.append(self.herotype_input)
            with gr.Group(elem_classes=["smgroup"]), gr.Row():
                gr.Textbox("Spe", max_lines=0, container=False, min_width=45, scale=25)
                self.spe_input = gr.Number(
                    value=0,
                    minimum=0,
                    maximum=5,
                    container=False,
                    min_width=50,
                    scale=1,
                )
                self.input_fields.append(self.spe_input)
            self.alliance_input = gr.Dropdown(
                value=nm.levels.AllianceType.NONE,
                label="Alliance",
                choices=[
                    *list(nm.levels.AllianceType),
                ],
                container=False,
                min_width=105,
                scale=0,
            )
    def _buildings_block(self, atk: bool, min_width: int):
        with gr.Group(visible=not atk), gr.Row(): #Buildings section
            with gr.Column(min_width=min_width):
                gr.Text("Dôme", max_lines=0, container=False)
                self.dome_input = gr.Number(label="Dôme", minimum=0, show_label=False, container=False)
            with gr.Column(min_width=min_width):
                gr.Text("Loge", max_lines=0, container=False)
                self.loge_input = gr.Number(label="Loge", minimum=0, show_label=False, container=False)
        self.input_fields.extend([self.dome_input, self.loge_input])

    def _configure_triggers(self):
        @gr.on(
            triggers=self.input_box.input,
            inputs=self.input_box,
            outputs=[*self.input_fields, self.state],
            show_progress="hidden",
        )
        def on_text_change(text_input: str):
            l = nm.levels.Levels.from_str(text_input)
            print(f"Updating with {l.alliance}")
            return (
                l.mandibule,
                l.carapace,
                l.hero_lvl,
                l.hero_type,
                l.special,
                l.dome,
                l.loge,
                l.alliance,
                l,
            )

        @gr.on(
            triggers=[inp.change for inp in self.input_fields], # type: ignore
            inputs=self.input_fields,
            outputs=[self.state, self.input_box],
            show_progress="hidden",
        )
        def on_input_change(m, c, hl, ht, s, d, l, a):
            print(hl, ht)
            args = {}
            if hl is not None and ht is not None:
                args = {"hero_lvl": hl, "hero_type": ht}
            l = nm.levels.Levels(
                mandibule=m, 
                carapace=c,
                **args,
                train=0, 
                dome=d, 
                loge=l, 
                alliance=nm.levels.AllianceType(a), 
                special=s
                )
            return l, l.to_str(hero_enabled=self.hero_enabled)
        
        self.copy_btn.click(
            lambda x: x, inputs=self.input_box, outputs=None, show_progress="hidden",
            js="x => { navigator.clipboard.writeText(x); return []; }" # Gradio expects a list return for outputs
        )
        self.paste_btn.click(
            on_text_change, 
            inputs=self.input_box,
            outputs=[*self.input_fields, self.state],
            show_progress="hidden",
            js="() => navigator.clipboard.readText().then(t => [t])" # Gradio expects a list return for outputs
        )



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
            with gr.Row():
                self.hp, self.hp_bonus, label = make_row("Vie", True)
            with gr.Row():
                self.dmg, self.dmg_bonus, label = make_row("Attaque", True)
            with gr.Row():
                self.cnt, _, label = make_row("Flood", False)
            with gr.Row():
                self.ponte, _, label = make_row("Ponte (Complet)", False)
            with gr.Row():
                self.adj_ponte, _, label = make_row("Ponte (Effectif)", False)

        @gr.on(
            triggers=war_party_state.change,
            inputs=war_party_state,
            outputs=[self.hp, self.hp_bonus, self.dmg, self.dmg_bonus, self.cnt, self.ponte, self.adj_ponte],
            show_progress="hidden",
        )
        def update_stats(p: nm.battle.WarParty):
            return (
                f"{p.total_hp:,.0f}".replace(",", " "),
                f"+{p.bonuses.hp:.0%}",
                f"{p.total_dmg:,.0f}".replace(",", " "),
                f"+{p.bonuses.dmg:.0%}",
                f"{p.army.count:,.0f}".replace(",", " "),
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.recruit_time()[1])))}",
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.non_xp_recruit_time()[1])))}",
            )
