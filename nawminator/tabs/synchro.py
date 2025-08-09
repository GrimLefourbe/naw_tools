import gradio as gr
import nawminator as nm

import pandas as pd
import datetime as dt
import io

LOCALSTORAGE_KEY = "synchro_player_data"
load_from_local_js = f"""(x) => {{
    let v = localStorage.getItem('{LOCALSTORAGE_KEY}');
    return [v? JSON.parse(v): x]
}}"""
save_to_local_js = f"""(v) => {{
    console.log("test", v);
    localStorage.setItem('{LOCALSTORAGE_KEY}', JSON.stringify(v)); 
    return [v]; 
}}"""

def synchro_tab(blocks: gr.Blocks):
    tab = SynchroTab()
    return {
        "fn": lambda x: (x, *tab.load_data(x)),
        "inputs": tab.result_df,
        "outputs": [tab.result_df, tab.player_select, tab.target_alliance, tab.loaded_accordion],
        "js": load_from_local_js,
    }
    
class SynchroTab:
    def __init__(self):
        self.set_layout()
        self.configure_triggers()

    def load_data(self, data: pd.DataFrame):
        print("Loading data")
        return (
            gr.Dropdown(
                choices=[(f"{player}|{colo}|{x}:{y}", (f"{x}:{y}")) for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].sort_values("player_name").values]
            ),
            gr.CheckboxGroup(
                choices=[x for x in data["alliance"].unique() if x]
            ),
            gr.Accordion(label=f"{data.shape[0]} joueurs chargés")
        )

    def set_layout(self):
        self.data_input = gr.Textbox(
            label="Copiez les données depuis la page joueur ici.", 
            info="" \
            "1. Allez sur la page Joueurs, mettez le tdc minimum à 1 et le tdc maximum à un très grand nombre (ajoutez plein de 0).\n" \
            "2. Mettez le nom de l'alliance que vous cherchez dans la barre de recherche." \
            "3. Copiez le contenu du tableau (de la 1ère ligne sans les noms de colonnes) à la dernière et collez le dans la boite.\n" \
            "4. Répétez pour les alliances que vous souhaitez voir et collez à la suite du c/c précédent (vérifiez bien que vous n'avez pas collé sur la même ligne que le précédent).\n" \
            "5. Vérifiez dans l'onglet Données Chargées qu'il y a bien ceux que vous cherchez."
        )
        self.data_input_btn = gr.Button("Charger les données")
        with gr.Accordion(label="0 joueurs chargés", open=False) as self.loaded_accordion:
            self.result_df = gr.DataFrame(pd.DataFrame(columns=["player_name", "colo_name", "alliance", "x", "y", "tdc"]), label="Joueurs")
            self.memory_btn = gr.Button("Charger dernières données utilisées")
        with gr.Row():
            self.player_select = gr.Dropdown(label="Joueur à synchro")
            self.target_alliance = gr.Dropdown(label="Alliances Cibles", multiselect=True)
        with gr.Row():
            self.time_input = gr.DateTime(label="Heure de départ", value=dt.datetime.now(), type="datetime")
            self.va_input = gr.Number(label="Vitesse d'attaque", value=0, minimum=0)
        self.synchro_button = gr.Button("Calcule!")

        self.synchro_outputs = gr.DataFrame(
            pd.DataFrame(columns=["Horaire", "Durée", "Joueur", "Colonie", "Alli", "TDC"]),
            label="Heures de passage",
            show_copy_button=True,
        )

    def configure_triggers(self):
        @gr.on(
            self.data_input_btn.click,
            inputs=self.data_input, 
            outputs=self.result_df,
        )
        def parse_data(input_data: str):
            data = pd.read_table(
                io.StringIO(input_data),
                names=["distance", "duration", "coord", "tdc", "colo_name", "player_name", "alliance", "status"],
                usecols=["coord", "tdc", "colo_name", "player_name", "alliance"],
            )
            data = data.apply(lambda x: x.str.strip())
            data["tdc"] = data["tdc"].apply(nm.utils.parse_naw_int)
            print(data.shape)
            print(data.columns)
            data[["x", "y"]] = data["coord"].str.strip("[] ").str.split(":", expand=True).astype(int)
            del data["coord"]
            return data[["player_name", "colo_name", "alliance", "x", "y", "tdc"]].sort_values("alliance")
        
        @gr.on(
            self.memory_btn.click,
            inputs=self.result_df,
            outputs=self.result_df,
            js=load_from_local_js,
        )
        def load_state(state: pd.DataFrame):
            return state


        gr.on(
            self.result_df.change,
            inputs=self.result_df,
            outputs=[self.player_select, self.target_alliance, self.loaded_accordion],
            js=save_to_local_js,
        )(self.load_data)


        @gr.on(
            self.synchro_button.click,
            inputs=[self.result_df, self.va_input, self.time_input, self.player_select, self.target_alliance],
            outputs=self.synchro_outputs
        )
        def calc_synchros(data: pd.DataFrame, va: int, depart: dt.datetime, target_player: str, target_allis: list[str]):
            base_pos = [int(i) for i in target_player.split(":")]
            base_tdc = data[(data[["x", "y"]] == base_pos).all(axis=1)]["tdc"].iloc[0]
            print(target_allis)
            print(data["tdc"])
            print(data["alliance"].str.strip(" ").isin(target_allis))
            print(data["tdc"] >= base_tdc * 0.5)
            print(data["tdc"] <= base_tdc * 3)
            targets = data[
                (data["alliance"].str.strip(" ").isin(target_allis))
                & (data["tdc"] >= base_tdc * 0.5)
                & (data["tdc"] <= base_tdc * 3)
            ]
            print(targets)
            targets["Durée"] = targets[["x", "y"]].apply(lambda pos : nm.formulas.duree_attaque(*pos, *base_pos, va=va), axis=1)
            targets = targets.sort_values("Durée")
            targets["Horaire"] = targets["Durée"].apply(lambda x: (depart + dt.timedelta(seconds=x)).time())
            targets["Durée"] = targets["Durée"].apply(lambda x: nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(x)))
            targets["Joueur"] = targets["player_name"]
            targets["Colonie"] = targets["colo_name"]
            targets["Alli"] = targets["alliance"]
            targets["TDC"] = targets["tdc"].apply(nm.utils.format_naw_int)
            return targets[["Horaire", "Durée", "Joueur", "Colonie", "Alli", "TDC"]]
