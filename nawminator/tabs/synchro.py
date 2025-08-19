import gradio as gr
import nawminator as nm
from nawminator.tabs.settings import ParsingError, Settings, parse_source_code, parse_table
import pandas as pd
import datetime as dt


def synchro_tab(settings: Settings):
    SynchroTab(settings=settings)

class SynchroTab:
    def __init__(self, settings: Settings):
        self.set_layout(settings)
        self.configure_triggers(settings)
        settings.post_load.then(
            self.on_data_load,
            inputs=settings.data_state,
            outputs=[self.result_df, self.player_select, self.target_alliance, self.loaded_accordion]
        )

    def on_data_load(self, data: pd.DataFrame):
        print(f"Loading synchro components with {data}")
        return (
            data,
            gr.Dropdown(
                choices=[(f"{player}|{colo}|{x}:{y}", (f"{x}:{y}")) for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].sort_values("player_name").values]
            ),
            gr.CheckboxGroup(
                choices=[x for x in data["alliance"].unique() if x]
            ),
            gr.Accordion(label=f"{data.shape[0]} joueurs chargés")
        )

    def set_layout(self, settings: Settings):
        self.data_input = gr.Textbox(
            label="Copiez les données depuis la page joueur ici.", 
            info="" \
            "1. Allez sur la page Joueurs, mettez le tdc minimum à 1 et le tdc maximum à un très grand nombre (ajoutez plein de 0) puis appuyez sur filtrer.\n" \
            "2.a Option A Code Source:\n" \
            "2.a.1 Utilisez ctrl + U ou ajoutez view-source: devant l'URL pour afficher le code source puis copiez le dans la boite.\n\n"
            "2.b Option B C/C: \n"
            "2.b.1 Mettez le nom de l'alliance que vous cherchez dans la barre de recherche.\n" \
            "2.b.2 Copiez le tableau ou la page complète (ctrl-A)  et copiez-collez la dans la boite.\n" \
            "2.b.3 Répétez pour les alliances que vous souhaitez voir et collez à la suite du c/c précédent (vérifiez bien que vous n'avez pas collé sur la même ligne que le précédent).\n" \
            "3. Vérifiez dans l'onglet Données Chargées qu'il y a bien ceux que vous cherchez."
        )
        self.data_input_btn = gr.Button("Charger les données")
        with gr.Accordion(label="0 joueurs chargés", open=False) as self.loaded_accordion:
            self.result_df = gr.DataFrame(inputs=settings.data_state, label="Joueurs")
            self.memory_btn = gr.Button("Charger dernières données utilisées")
        with gr.Row():
            self.player_select = gr.Dropdown(label="Joueur à synchro")
            self.target_alliance = gr.Dropdown(label="Alliances Cibles", multiselect=True)
        with gr.Row():
            self.time_input = gr.DateTime(
                label="Heure de départ", 
                value=lambda : dt.datetime.now(),  # type: ignore
                type="datetime"
            )
            self.va_input = gr.Number(label="Vitesse d'attaque", value=0, minimum=0)
        self.synchro_button = gr.Button("Calcule!")
        self.synchro_copy_btn = gr.Button("Copier les synchros", visible=False)
        self.synchro_copy = gr.Textbox(visible=False)
        self.synchro_outputs = gr.DataFrame(
            pd.DataFrame(columns=["Horaire", "Durée", "Joueur", "Colonie", "Alli", "TDC"]),
            label="Heures de passage",
            show_copy_button=False,
        )

    def configure_triggers(self, settings: Settings):
        self.data_input_btn.click(
            parse_data,
            inputs=self.data_input, 
            outputs=settings.data_state,
        )

        
        @gr.on(
            self.memory_btn.click,
            inputs=self.result_df,
            outputs=self.result_df,
        )
        def load_state(state: pd.DataFrame):
            return state


        settings.data_state.change(
            self.on_data_load,
            inputs=settings.data_state,
            outputs=[self.result_df, self.player_select, self.target_alliance, self.loaded_accordion]
        )


        self.synchro_button.click(
            fn=calc_synchros,
            inputs=[self.result_df, self.va_input, self.time_input, self.player_select, self.target_alliance],
            outputs=[self.synchro_outputs, self.synchro_copy, self.synchro_copy_btn]
        )
        
        self.synchro_copy_btn.click(
            lambda x: print(f"{x=}"),
            inputs=self.synchro_copy,
            outputs=None,
            js="x => { console.log(x); navigator.clipboard.writeText(x); return []; }"
        )

def parse_data(input_data: str) -> pd.DataFrame:
    print("Parsing input data")
    exceptions = []
    for parser in [parse_table, parse_source_code]:
        print(f"With {parser.__name__}")
        try:
            data = parser(input_data=input_data)
        except ParsingError as e:
            exceptions.append(e)
            continue
        print(f"No error with parser {parser.__name__}")
        break
    else:
        raise ExceptionGroup("No parsing worked for the input data", exceptions)

    print(data.shape)
    print(data.columns)
    data[["x", "y"]] = data["coord"].str.strip("[] ").str.split(":", expand=True).astype(int)
    del data["coord"]
    data.attrs["parsing_date"] = dt.datetime.now()
    return data[["player_name", "colo_name", "alliance", "x", "y", "tdc"]].sort_values("alliance")

def calc_synchros(data: pd.DataFrame, va: int, depart: dt.datetime, target_coords: str, target_allis: list[str]):
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
    targets["Durée"] = targets[["x", "y"]].apply(lambda pos : nm.formulas.duree_attaque(*pos, *base_pos, va=va), axis=1)
    targets = targets.sort_values("Durée")
    targets["Horaire"] = targets["Durée"].apply(lambda x: (depart + dt.timedelta(seconds=x)).time())
    targets["Durée"] = targets["Durée"].apply(lambda x: nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(x), pad=True))
    targets["Joueur"] = targets["player_name"]
    targets["Colonie"] = targets["colo_name"]
    targets["Alli"] = targets["alliance"]
    targets["TDC"] = targets["tdc"].apply(nm.utils.format_naw_int)
    targets["Pos"] = targets[["x", "y"]].apply(lambda x: ":".join(str(i) for i in x), axis=1)
    targets = targets[["Horaire", "Durée", "Joueur", "Colonie", "Alli", "Pos", "TDC"]]
    copy_data = format_copy_data(targets=targets, player=player, va=va, depart=depart)
    print(copy_data)
    return targets, copy_data, gr.Button(visible=True)    


def format_copy_data(targets: pd.DataFrame, player: pd.Series, va: int, depart: dt.datetime) -> str:
    base_tdc = player["tdc"]
    base_pos = player[["x", "y"]]

    copy_data = f"""Cible: [joueur]{player["player_name"]}[/joueur]({player["colo_name"]})[[alliance]{player["alliance"]}[/alliance]] [{":".join(str(i) for i in base_pos)}]\nVA: {va}\nHeure de départ: {depart.strftime("%H:%M:%S")} - TDC: {nm.utils.format_naw_int(base_tdc)}\n"""
    copy_data += f"{"-"*30}\n"
    copy_data += "\n".join(
        [f"[b]{h}[/b] - {d}: [{p}] {j}[{a}]({c}) - {t}" for h, d, j, c, a, p, t in targets.itertuples(index=False)]
    )
    return copy_data


