import gradio as gr
import pandas as pd
import nawminator as nm
import nmsite
import datetime as dt
import logging
logger = logging.getLogger(__name__)

LOCALSTORAGE_KEY = "nawminator_settings"
load_from_browser_storage = f"""(data, metadata) => {{
    let stored_data = localStorage.getItem('{LOCALSTORAGE_KEY}_data');
    let stored_metadata = localStorage.getItem('{LOCALSTORAGE_KEY}_metadata');
    console.log("Loading", stored_data);
    console.log("Loading", stored_metadata);

    return stored_metadata ? [JSON.parse(stored_data), JSON.parse(stored_metadata)]: [data, metadata]
}}"""
save_to_browser_storage = f"""(data, metadata) => {{
    console.log("Saving", data);
    console.log("Saving", metadata);
    localStorage.setItem('{LOCALSTORAGE_KEY}_data', JSON.stringify(data)); 
    localStorage.setItem('{LOCALSTORAGE_KEY}_metadata', JSON.stringify(metadata)); 
    return [data,metadata]; 
}}"""

def settings_tab(config: nmsite.config.Config, demo: gr.Blocks):
    settings = Settings(demo)
    return settings

class Settings:
    def __init__(self, demo: gr.Blocks):
        self.data_state, self.metadata_state = self._clear_data()
        self.post_load = demo.load(
            self.load,
            inputs=[self.data_state, self.metadata_state],
            outputs=[self.data_state, self.metadata_state],
            js=load_from_browser_storage
        )
        self._create_layout()
        self._configure_triggers()

    def _clear_data(self):
        return gr.DataFrame(pd.DataFrame(columns=["player_name", "colo_name", "alliance", "x", "y", "tdc"]), visible=False), gr.BrowserState({"version": 1})

    def load(self, saved_data: pd.DataFrame, metadata: dict):
        print(f"Loading data {type(saved_data)} {saved_data}")
        print(f"Loading metadata {type(metadata)} {metadata}")
        return saved_data, metadata

    def _create_layout(self):
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
            self.result_df = gr.DataFrame(inputs=self.data_state, label="Joueurs")
        self.clear_data_btn = gr.Button("Effacer les données")
        # self.player_name_input = gr.Textbox(
        #     label="Votre pseudo", interactive=True
        # )

    
    def _on_data_load(self, data: pd.DataFrame):
        logger.debug(f"Loading data {data}")
        return data, gr.Accordion(label=f"{data.shape[0]} joueurs chargés")

    def _configure_triggers(self):
        self.data_state.change(
            fn=lambda x, y: print(f"Saving metadata {type(y)} {y}\ndata_state: {type(x)} {x}") and (x, y),
            inputs=[self.data_state, self.metadata_state],
            js=save_to_browser_storage,
        ).then(
            self._on_data_load,
            inputs=self.data_state,
            outputs=[self.result_df, self.loaded_accordion]
        )
     
        self.clear_data_btn.click(
            self._clear_data,
            outputs=[self.data_state, self.metadata_state],
        )

        self.data_input_btn.click(
            parse_data,
            inputs=self.data_input,
            outputs=self.data_state,
        )



def parse_data(s: str) -> pd.DataFrame:
    print("Parsing input data")
    exceptions = []
    for parser in [parse_table, parse_source_code]:
        print(f"With {parser.__name__}")
        try:
            data = parser(s=s)
        except nm.parsing.ParsingError as e:
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


def parse_source_code(s: str) -> pd.DataFrame:
    return nm.parsing.parse_joueurs_sourcecode(s)[["coord", "tdc", "colo_name", "player_name", "alliance"]]

def parse_table(s: str) -> pd.DataFrame:
    return nm.parsing.parse_joueurs_text(s)[["coord", "tdc", "colo_name", "player_name", "alliance"]]
