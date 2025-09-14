import html
import re
import gradio as gr
import pandas as pd
import nawminator as nm
import io

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

class Settings:
    def __init__(self, demo: gr.Blocks):
        self.data_state  = gr.DataFrame(pd.DataFrame(columns=["player_name", "colo_name", "alliance", "x", "y", "tdc"]), visible=False)
        self.metadata_state  = gr.BrowserState({"version": 1})
        self.post_load = demo.load(
            self.load,
            inputs=[self.data_state, self.metadata_state],
            outputs=[self.data_state, self.metadata_state],
            js=load_from_browser_storage
        )
        self._configure_triggers()

    def load(self, saved_data: pd.DataFrame, metadata: dict):
        print(f"Loading data {type(saved_data)} {saved_data}")
        print(f"Loading metadata {type(metadata)} {metadata}")
        return saved_data, metadata

    def _configure_triggers(self):
        self.data_state.change(
            fn=lambda x, y: print(f"Saving metadata {type(y)} {y}\ndata_state: {type(x)} {x}") and (x, y),
            inputs=[self.data_state, self.metadata_state],
            js=save_to_browser_storage,
        )


def parse_source_code(s: str) -> pd.DataFrame:
    return nm.parsing.parse_joueurs_sourcecode(s)[["coord", "tdc", "colo_name", "player_name", "alliance"]]

def parse_table(s: str) -> pd.DataFrame:
    return nm.parsing.parse_joueurs_text(s)[["coord", "tdc", "colo_name", "player_name", "alliance"]]
