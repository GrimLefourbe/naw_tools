import html
import gradio as gr
import nawminator as nm

import pandas as pd
import datetime as dt
import io
import re

class ParsingError(Exception):
    pass

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

copy_paste_pat = r"^([\d,]+)\s+\w+\s+(\[[-\d]+:[-\d]+\])\s+([\d,]+)\s+?([^\t]*)\s+?([^\t]+)\s+([^\s]*)\s+(?:Libre|Vassal de [^\t]+|En vacances)$"
copy_paste_cpat = re.compile(copy_paste_pat, flags=re.MULTILINE)

source_code_pat = re.compile(
    r"""
    <tr[^>]*>[\t \r\n]*
    <td>[0-9,]+</td>[\t \r\n]*
    <td[^>]*>[^<]*</td>[\t \r\n]*
    <td>(\[[0-9:-]+\])</td>[\t \r\n]*
    <td>([0-9,]+)</td>[\t \r\n]+
    <td><a[^>]*>([^<]+)</a></td>[\t \r\n]*
    <td><a[^>]+href="profil-([0-9]+)">\ <b>([^<]+)</b></a></td>[\t \r\n]*
    <td><a[^>]*>\ <b>([^<]*)</b></a></td>[\t \r\n]*
    <td>(?:Vassal\ de\ <a\ href='profil-)?([^<>]+)(?:'>\ <b>[^<]+</b>)?</td>[\t \r\n]*
    </tr>
    """, flags=re.X
)


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

    def parse_table(self, input_data: str) -> pd.DataFrame:
        try:
            lines = [i.group(0) for i in copy_paste_cpat.finditer(input_data)]
            if len(lines) == 0:
                raise ParsingError("Found no matching line in input_data")
            data = pd.read_table(
                io.StringIO("\n".join(lines)),
                names=["distance", "duration", "coord", "tdc", "colo_name", "player_name", "alliance", "status"],
                usecols=["coord", "tdc", "colo_name", "player_name", "alliance"],
            )
            data = data.apply(lambda x: x.str.strip())
            data["tdc"] = data["tdc"].apply(nm.utils.parse_naw_int)
        except Exception as e:
            raise ParsingError from e
        return data

    def parse_source_code(self, input_data: str) -> pd.DataFrame:
        try:
            data = source_code_pat.findall(input_data)
        except Exception as e:
            raise ParsingError from e
        if len(data) == 0:
            raise ParsingError("No valid lines found")
        df = pd.DataFrame(
            data=data, 
            columns=["coord", "tdc", "colo_name", "profile_link", "player_name", "alliance", "status"]
        )
        df = df.apply(lambda x: x.str.strip())
        df["tdc"] = df["tdc"].apply(nm.utils.parse_naw_int)
        df["colo_name"] = df["colo_name"].apply(html.unescape)
        return df[["coord", "tdc", "colo_name", "player_name", "alliance"]]

    def configure_triggers(self):
        @gr.on(
            self.data_input_btn.click,
            inputs=self.data_input, 
            outputs=self.result_df,
        )
        def parse_data(input_data: str):
            print("Parsing input data")
            exceptions = []
            for parser in [self.parse_table, self.parse_source_code]:
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
        
        @gr.on(
            self.memory_btn.click,
            inputs=self.result_df,
            outputs=self.result_df,
            js=load_from_local_js,
        )
        def load_state(state: pd.DataFrame):
            return state


        self.result_df.change(
            fn=self.load_data,
            inputs=self.result_df,
            outputs=[self.player_select, self.target_alliance, self.loaded_accordion],
            js=save_to_local_js,
        )


        @gr.on(
            self.synchro_button.click,
            inputs=[self.result_df, self.va_input, self.time_input, self.player_select, self.target_alliance],
            outputs=[self.synchro_outputs, self.synchro_copy, self.synchro_copy_btn]
        )
        def calc_synchros(data: pd.DataFrame, va: int, depart: dt.datetime, target_player: str, target_allis: list[str]):
            base_pos = [int(i) for i in target_player.split(":")]
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
            targets = targets[["Horaire", "Durée", "Joueur", "Colonie", "Alli", "TDC"]]
            copy_data = f"""Cible: [joueur]{player["player_name"]}[/joueur]({player["colo_name"]})[{player["alliance"]}] [{":".join(str(i) for i in base_pos)}]\nVA: {va}\nHeure de départ: {depart.strftime("%H:%M:%S")} - TDC: {nm.utils.format_naw_int(base_tdc)}\n"""
            copy_data += f"{"-"*30}\n"
            copy_data += "\n".join(
                [f"[b]{h}[/b] - {d}: {j}({c})[{a}] - {t}" for h, d, j, c, a, t in targets.itertuples(index=False)]
            )
            print(copy_data)
            return targets, copy_data, gr.Button(visible=True)
        

        self.synchro_copy_btn.click(
            lambda x: print(f"{x=}"),
            inputs=self.synchro_copy,
            outputs=None,
            js="x => { console.log(x); navigator.clipboard.writeText(x); return []; }"
        )
        
