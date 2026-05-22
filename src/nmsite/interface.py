import gradio as gr
import nawminator as nm
import datetime as dt

### INPUTS


class ArmyInput:
    def __init__(self):
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


def _merge_elem_classes(kwargs: dict, cls: str) -> None:
    existing = kwargs.pop("elem_classes", [])
    if isinstance(existing, str):
        existing = [existing]
    kwargs["elem_classes"] = list(existing) + [cls]


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
                f"{p.total_hp:,.0f}".replace(",", " ") if p.bonuses.hp is not None else "?",
                f"+{p.bonuses.hp:.0%}" if p.bonuses.hp is not None else "?",
                f"{p.total_dmg:,.0f}".replace(",", " "),
                f"+{p.bonuses.dmg:.0%}",
                f"{p.army.count:,.0f}".replace(",", " "),
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.recruit_time()[1])))}",
                f"{nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(p.army.non_xp_recruit_time()[1])))}",
            )
