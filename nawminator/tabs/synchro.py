import gradio as gr
import nawminator as nm

import pandas as pd
import datetime as dt
import io

def synchro_tab():
    data_input = gr.Textbox(
        label="Copiez les données depuis la page joueur ici.", 
        info="" \
        "1. Allez sur la page Joueurs, mettez le tdc minimum à 1 et le tdc maximum à un très grand nombre (ajoutez plein de 0).\n" \
        "2. Mettez le nom de l'alliance que vous cherchez dans la barre de recherche." \
        "3. Copiez le contenu du tableau (de la 1ère ligne sans les noms de colonnes) à la dernière et collez le dans la boite.\n" \
        "4. Répétez pour les alliances que vous souhaitez voir et collez à la suite du c/c précédent (vérifiez bien que vous n'avez pas collé sur la même ligne que le précédent).\n" \
        "5. Vérifiez dans l'onglet Données Chargées qu'il y a bien ceux que vous cherchez."
    )
    data_input_btn = gr.Button("Charger les données")
    with gr.Accordion(label="Données chargées", open=False):
        result_df = gr.DataFrame(label="Joueurs")
    with gr.Row():
        player_select = gr.Dropdown(label="Joueur à synchro", interactive=True)
        target_alliance = gr.Dropdown(label="Alliances Cibles", interactive=True, multiselect=True)
    with gr.Row():
        time_input = gr.DateTime(label="Heure de départ", value=dt.datetime.now(), type="datetime", interactive=True)
        va_input = gr.Number(label="Vitesse d'attaque", interactive=True, value=0, minimum=0)
    synchro_button = gr.Button("Calcule!")

    synchro_outputs = gr.DataFrame(pd.DataFrame(columns=["Heure d'arrivée", "Durée", "Joueur", "Colonie", "Alliance"]), label="Heures de passage")

    @gr.on(
        data_input_btn.click,
        inputs=data_input,
        outputs=[result_df, player_select, target_alliance],
    )
    def load_data(input_data: str):
        data = pd.read_table(
            io.StringIO(input_data),
            names=["distance", "duration", "coord", "tdc", "colo_name", "player_name", "alliance", "status"],
            usecols=["coord", "tdc", "colo_name", "player_name", "alliance"],
        )
        data = data.apply(lambda x: x.str.strip())
        print(data.shape)
        print(data.columns)
        data[["x", "y"]] = data["coord"].str.strip("[] ").str.split(":", expand=True).astype(int)
        del data["coord"]
        return (
            data[["player_name", "colo_name", "alliance", "x", "y", "tdc"]].sort_values("alliance"),
            gr.Dropdown(
                choices=[(f"{player}|{colo}|{x}:{y}", (f"{x}:{y}")) for player, colo, x, y in data[["player_name", "colo_name", "x", "y"]].sort_values("player_name").values]
            ),
            gr.CheckboxGroup(
                choices=[x for x in data["alliance"].unique() if x]
            ),
        )

    @gr.on(
        synchro_button.click,
        inputs=[result_df, va_input, time_input, player_select, target_alliance],
        outputs=synchro_outputs
    )
    def calc_synchros(data: pd.DataFrame, va: int, depart: dt.datetime, target_player: str, target_allis: list[str]):
        print(target_allis)
        targets = data[data["alliance"].str.strip(" ").isin(target_allis)]
        print(targets)
        base_pos = [int(i) for i in target_player.split(":")]
        targets["Durée"] = targets[["x", "y"]].apply(lambda pos : nm.formulas.duree_attaque(*pos, *base_pos, va=va), axis=1)
        targets = targets.sort_values("Durée")
        targets["Heure d'arrivée"] = targets["Durée"].apply(lambda x: depart + dt.timedelta(seconds=x))
        targets["Durée"] = targets["Durée"].apply(lambda x: nm.utils.format_yjhms(nm.utils.seconds_to_yjhms(x)))
        targets["Joueur"] = targets["player_name"]
        targets["Colonie"] = targets["colo_name"]
        targets["Alliance"] = targets["alliance"]
        return targets[["Heure d'arrivée", "Durée", "Joueur", "Colonie", "Alliance"]]