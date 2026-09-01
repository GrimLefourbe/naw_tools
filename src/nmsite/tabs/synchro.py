import functools
import gradio as gr
import nawminator as nm
import nmsite
from nmsite.synchro_copy import format_copy_data_text, format_copy_data_discord, format_copy_data_table
from nmsite.tabs.settings import Settings
from nmsite.components import TimeInput
import pandas as pd
import datetime as dt
import pathlib

_DISCORD_ICON = str(pathlib.Path(__file__).parent / "assets" / "discord.svg")


def synchro_tab(config: nmsite.config.Config, settings: Settings):
    SynchroTab(settings=settings, config=config)


class SynchroTab:
    def __init__(self, settings: Settings, config: nmsite.config.Config):
        self.config = config
        self.set_layout(settings)
        self.configure_triggers(settings)

    def on_data_load(self, data: pd.DataFrame):
        print(f"Loading synchro components with {data}")
        return (
            data,
            gr.Dropdown(
                choices=[
                    (f"{player}|{colo}|{x}:{y}", (f"{x}:{y}"))
                    for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]]
                    .sort_values("player_name")
                    .values
                ]
            ),
            gr.CheckboxGroup(choices=[x for x in data["alliance"].unique() if x]),
            gr.Accordion(label=f"{data.shape[0]} joueurs chargés"),
        )

    def set_layout(self, settings: Settings):
        with gr.Accordion(label="0 joueurs chargés", open=False) as self.loaded_accordion:
            self.data_input = gr.Textbox(
                label="Copiez les données depuis la page joueur ici.",
                info=""
                "1. Allez sur la page Joueurs, mettez le tdc minimum à 1 et le tdc maximum à un très grand nombre (ajoutez plein de 0) puis appuyez sur filtrer.\n"
                "2.a Option A Code Source:\n"
                "2.a.1 Utilisez ctrl + U ou ajoutez view-source: devant l'URL pour afficher le code source puis copiez le dans la boite.\n\n"
                "2.b Option B C/C: \n"
                "2.b.1 Mettez le nom de l'alliance que vous cherchez dans la barre de recherche.\n"
                "2.b.2 Copiez le tableau ou la page complète (ctrl-A)  et copiez-collez la dans la boite.\n"
                "2.b.3 Répétez pour les alliances que vous souhaitez voir et collez à la suite du c/c précédent (vérifiez bien que vous n'avez pas collé sur la même ligne que le précédent).\n"
                '2.b.4 Sur téléphone : utilisez le collage normal, pas "coller en texte brut" (celui-ci casse la mise en forme du tableau et empêche la lecture des données).\n'
                "3. Vérifiez dans l'onglet Données Chargées qu'il y a bien ceux que vous cherchez.",
            )
            self.data_input_btn = gr.Button("Charger les données")
            self.result_df = gr.DataFrame(inputs=settings.data_state, label="Joueurs")
        with gr.Row():
            self.player_select = gr.Dropdown(label="Joueur à synchro")
            self.target_alliance = gr.Dropdown(label="Alliances Cibles", multiselect=True)
        with gr.Row():
            with gr.Column():
                mode = self.config.time_input_mode
                if mode in ("legacy", "hybrid"):
                    self.time_input = gr.DateTime(
                        label="Heure de départ",
                        value=lambda: dt.datetime.now(),
                        type="datetime",  # type: ignore
                        elem_id="synchro_time_input",
                    )
                if mode in ("hybrid", "experimental"):
                    self.time_input_new = TimeInput(
                        mode="datetime",
                        quick_fills=["today", "current_time"],
                        value=lambda: dt.datetime.now(),  # type: ignore
                        label="Heure de départ",
                        elem_id="synchro_time_input" if mode == "experimental" else "synchro_time_input_new",
                        visible=(mode == "experimental"),
                    )
            self.va_input = gr.Number(label="Vitesse d'attaque", value=0, minimum=0)
        self.synchro_button = gr.Button("Calcule!")
        with gr.Group():
            with gr.Row():
                self.synchro_copy_discord_btn = gr.Button(
                    "",
                    icon=_DISCORD_ICON,
                    visible=False,
                    scale=0,
                    min_width=48,
                    elem_classes="discord-copy-btn",
                )
                self.synchro_copy_btn = gr.Button("Copier les synchros", visible=False)
                self.synchro_copy_table_btn = gr.Button("▦", visible=False, scale=0, min_width=48)
        self.synchro_copy = gr.Textbox(visible=False)
        self.synchro_copy_discord = gr.Textbox(visible=False)
        self.synchro_copy_table = gr.Textbox(visible=False)
        self.synchro_outputs = gr.DataFrame(
            pd.DataFrame(columns=["Horaire", "Durée", "Joueur", "Colonie", "Alli", "TDC"]),
            label="Heures de passage",
            buttons=[],
        )

    def configure_triggers(self, settings: Settings):
        mode = self.config.time_input_mode

        self.data_input_btn.click(
            nmsite.tabs.settings.parse_data,
            inputs=self.data_input,
            outputs=settings.data_state,
        )

        settings.post_load.then(
            self.on_data_load,
            inputs=settings.data_state,
            outputs=[self.result_df, self.player_select, self.target_alliance, self.loaded_accordion],
        )

        settings.data_state.change(
            self.on_data_load,
            inputs=settings.data_state,
            outputs=[self.result_df, self.player_select, self.target_alliance, self.loaded_accordion],
        )

        if mode == "hybrid":
            settings.time_input_enabled_state.change(
                fn=lambda enabled: (gr.update(visible=not enabled), gr.update(visible=enabled)),
                inputs=settings.time_input_enabled_state,
                outputs=[self.time_input, self.time_input_new],
                show_progress="hidden",
            )

        depart_inputs: list = []
        if mode in ("legacy", "hybrid"):
            depart_inputs.append(self.time_input)
        else:
            depart_inputs.append(gr.State(None))
        if mode in ("hybrid", "experimental"):
            depart_inputs.append(self.time_input_new)
        else:
            depart_inputs.append(gr.State(None))

        enabled_input = settings.time_input_enabled_state if mode == "hybrid" else gr.State(False)

        self.synchro_button.click(
            fn=functools.partial(calc_synchros, base_url=self.config.base_url, mode=mode),
            inputs=[
                settings.data_state,
                self.va_input,
                *depart_inputs,
                enabled_input,
                self.player_select,
                self.target_alliance,
            ],
            outputs=[
                self.synchro_outputs,
                self.synchro_copy,
                self.synchro_copy_discord,
                self.synchro_copy_table,
                self.synchro_copy_btn,
                self.synchro_copy_discord_btn,
                self.synchro_copy_table_btn,
            ],
        )

        # fn=None keeps these JS-only: no backend round trip per click (see
        # https://www.gradio.app/guides/frontend-javascript - reverse_btn.click(None, ...) example).
        self.synchro_copy_btn.click(
            None,
            inputs=self.synchro_copy,
            outputs=None,
            js="text => { navigator.clipboard.writeText(text); return []; }",
        )

        self.synchro_copy_discord_btn.click(
            None,
            inputs=self.synchro_copy_discord,
            outputs=None,
            js="text => { navigator.clipboard.writeText(text); return []; }",
        )

        self.synchro_copy_table_btn.click(
            None,
            inputs=self.synchro_copy_table,
            outputs=None,
            js="text => { navigator.clipboard.writeText(text); return []; }",
        )


def calc_synchros(
    data: pd.DataFrame,
    va: int,
    depart: dt.datetime | None,
    depart_new: dt.datetime | None,
    enabled: bool,
    target_coords: str,
    target_allis: list[str],
    base_url: str,
    mode: str,
):
    if mode == "experimental":
        depart = depart_new
    elif mode == "hybrid" and enabled:
        depart = depart_new
    assert depart is not None, "Heure de départ manquante"
    base_pos = [int(i) for i in target_coords.split(":")]
    player = data[(data[["x", "y"]] == base_pos).all(axis=1)].iloc[0]
    base_tdc = player["tdc"]
    targets = data[
        (data["alliance"].str.strip(" ").isin(target_allis))
        & (data["tdc"] >= base_tdc * 0.5)
        & (data["tdc"] <= base_tdc * 3)
        & ~(data[["x", "y"]] == base_pos).all(axis="columns")
    ]
    print(targets)
    targets["Durée"] = targets[["x", "y"]].apply(lambda pos: nm.formulas.duree_attaque(*pos, *base_pos, va=va), axis=1)
    targets = targets.sort_values("Durée")
    targets["Horaire"] = targets["Durée"].apply(lambda x: (depart + dt.timedelta(seconds=x)).time())
    targets["Durée"] = targets["Durée"].apply(lambda x: nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=x), pad=True))
    targets["Joueur"] = targets["player_name"]
    # Keep plain: format_copy_data_table builds its own [url=...] link per-row from
    # this. This DataFrame also backs the on-screen synchro_outputs table and
    # format_copy_data_text, neither of which renders BBCode.
    targets["Colonie"] = targets["colo_name"]
    targets["Alli"] = targets["alliance"]
    targets["TDC"] = targets["tdc"].apply(nm.utils.format_naw_int)
    targets["Pos"] = targets[["x", "y"]].apply(lambda x: ":".join(str(i) for i in x), axis=1)
    targets = targets[["Horaire", "Durée", "Joueur", "Colonie", "Alli", "Pos", "TDC"]]
    copy_data_text = format_copy_data_text(targets=targets, player=player, va=va, depart=depart, base_url=base_url)
    copy_data_discord = format_copy_data_discord(
        targets=targets, player=player, va=va, depart=depart, base_url=base_url
    )
    copy_data_table = format_copy_data_table(targets=targets, player=player, va=va, depart=depart, base_url=base_url)
    print(copy_data_text)
    return (
        targets,
        copy_data_text,
        copy_data_discord,
        copy_data_table,
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Button(visible=True),
    )
