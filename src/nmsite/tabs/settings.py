import gradio as gr
import pandas as pd
import nawminator as nm
import nmsite
import datetime as dt
import logging

from nmsite.components import TimeInput

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

# Persisted the same way as data/metadata above (hand-rolled localStorage JS,
# not gr.BrowserState's native restore) — native restore doesn't survive this
# app's gr.Tab(render=False) + later .render() structure (every tab, including
# Réglages, is built that way in app.py), so it silently loses the value on
# reload. Kept as its own key rather than folded into the metadata dict above
# so that "Effacer les données" (which resets metadata_state) doesn't also
# reset this unrelated preference.
TIME_INPUT_STORAGE_KEY = "nawminator_time_input_enabled"
load_time_input_enabled = f"""(enabled, checked) => {{
    let stored = localStorage.getItem('{TIME_INPUT_STORAGE_KEY}');
    let value = stored !== null ? JSON.parse(stored) : enabled;
    return [value, value];
}}"""
save_time_input_enabled = f"""(enabled) => {{
    localStorage.setItem('{TIME_INPUT_STORAGE_KEY}', JSON.stringify(enabled));
    return enabled;
}}"""

def settings_tab(config: nmsite.config.Config, demo: gr.Blocks):
    settings = Settings(demo, config)
    return settings

class Settings:
    def __init__(self, demo: gr.Blocks, config: nmsite.config.Config):
        self._config = config
        self.data_state, self.metadata_state = self._clear_data()
        if self._config.time_input_mode == "hybrid":
            self.time_input_enabled_state = gr.State(False)
        self.post_load = demo.load(
            self.load,
            inputs=[self.data_state, self.metadata_state],
            outputs=[self.data_state, self.metadata_state],
            js=load_from_browser_storage
        )
        self._create_layout()
        self._configure_triggers()
        if self._config.time_input_mode == "hybrid":
            demo.load(
                fn=lambda enabled, checked: (enabled, checked),
                inputs=[self.time_input_enabled_state, self.time_input_toggle],
                outputs=[self.time_input_enabled_state, self.time_input_toggle],
                js=load_time_input_enabled,
                show_progress="hidden",
            )

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
            "2.b.4 Sur téléphone : utilisez le collage normal, pas \"coller en texte brut\" (celui-ci casse la mise en forme du tableau et empêche la lecture des données).\n" \
            "3. Vérifiez dans l'onglet Données Chargées qu'il y a bien ceux que vous cherchez."
        )
        self.data_input_btn = gr.Button("Charger les données")
        with gr.Accordion(label="0 joueurs chargés", open=False) as self.loaded_accordion:
            self.result_df = gr.DataFrame(inputs=self.data_state, label="Joueurs")
        self.clear_data_btn = gr.Button("Effacer les données")
        # self.player_name_input = gr.Textbox(
        #     label="Votre pseudo", interactive=True
        # )
        if self._config.time_input_mode == "hybrid":
            self.time_input_toggle = gr.Checkbox(
                value=False,
                label="Utiliser le nouveau sélecteur de temps (bêta)",
                elem_id="settings_time_input_toggle",
            )
        if self._config.dev:
            self._create_time_input_demo()


    def _on_data_load(self, data: pd.DataFrame):
        logger.debug(f"Loading data {data}")
        return data, gr.Accordion(label=f"{data.shape[0]} joueurs chargés")

    def _create_time_input_demo(self):
        gr.Markdown("---\n### TimeInput — démo")
        gr.Markdown(
            "Cinq configurations du composant `TimeInput`. "
            "La valeur Python reçue s'affiche en dessous de chaque champ."
        )

        with gr.Row():
            with gr.Column():
                gr.Markdown("**A** — durée H:M:S")
                self._ti_a_interactive = gr.Checkbox(
                    value=True, label="Interactif", elem_id="ti_demo_a_interactive",
                )
                self._ti_a = TimeInput(
                    mode="duration",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    label="Durée",
                    elem_id="ti_demo_a",
                )
                self._ti_a_out = gr.Text(label="Python", interactive=False, elem_id="ti_demo_a_out")

            with gr.Column():
                gr.Markdown("**B** — durée J H M S, double format")
                self._ti_b = TimeInput(
                    mode="duration",
                    segments=["days", "hours", "minutes", "seconds"],
                    formats=["AJHMS", "HH:MM:SS"],
                    label="Durée",
                    elem_id="ti_demo_b",
                )
                self._ti_b_out = gr.Text(label="Python", interactive=False, elem_id="ti_demo_b_out")

            with gr.Column():
                gr.Markdown("**C** — durée complète AJHMS + Maintenant")
                self._ti_c = TimeInput(
                    mode="duration",
                    segments=["years", "days", "hours", "minutes", "seconds"],
                    formats=["AJHMS"],
                    quick_fills=["now"],
                    label="Durée",
                    elem_id="ti_demo_c",
                )
                self._ti_c_out = gr.Text(label="Python", interactive=False, elem_id="ti_demo_c_out")

        with gr.Row():
            with gr.Column():
                gr.Markdown("**D** — heure (clock_time) + Heure actuelle")
                self._ti_d = TimeInput(
                    mode="clock_time",
                    segments=["hours", "minutes", "seconds"],
                    formats=["HH:MM:SS"],
                    quick_fills=["current_time"],
                    label="Heure",
                    elem_id="ti_demo_d",
                )
                self._ti_d_out = gr.Text(label="Python", interactive=False, elem_id="ti_demo_d_out")

            with gr.Column():
                gr.Markdown("**E** — datetime complet")
                self._ti_e = TimeInput(
                    mode="datetime",
                    formats=["DD/MM/YYYY HH:MM:SS"],
                    quick_fills=["now", "today", "current_time"],
                    label="Date et heure",
                    elem_id="ti_demo_e",
                )
                self._ti_e_out = gr.Text(label="Python", interactive=False, elem_id="ti_demo_e_out")

    def _configure_time_input_demo(self):
        self._ti_a_interactive.change(
            fn=lambda v: gr.update(interactive=v),
            inputs=self._ti_a_interactive,
            outputs=self._ti_a,
            show_progress="hidden",
        )

        for ti, out in [
            (self._ti_a, self._ti_a_out),
            (self._ti_b, self._ti_b_out),
            (self._ti_c, self._ti_c_out),
            (self._ti_d, self._ti_d_out),
            (self._ti_e, self._ti_e_out),
        ]:
            ti.change(
                fn=lambda v: repr(v),
                inputs=[ti],
                outputs=[out],
                show_progress="hidden",
            )

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

        if self._config.time_input_mode == "hybrid":
            self.time_input_toggle.change(
                fn=lambda enabled: enabled,
                inputs=self.time_input_toggle,
                outputs=self.time_input_enabled_state,
                js=save_time_input_enabled,
                show_progress="hidden",
            )

        if self._config.dev:
            self._configure_time_input_demo()



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
