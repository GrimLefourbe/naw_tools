from email.policy import default
import gradio as gr
import os
import nmsite
from nmsite.config import configs

config = configs[os.getenv("NMSITE_CONFIG", "DEV")]

css = """
/* Hide the HTML block itself */
.css-injector {
    opacity: 0;
    pointer-events: none;
    height: 0 !important;
    flex: 0 0 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    margin-right: -4 !important; /* cancel flex gap */
}

.smgroup {
    gap: 0.25rem;
    min-width: 0 !important;
}"""

HEADER = f"""
<div id="app-header" style="
  position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
  display: flex; align-items: center; justify-content: center; gap: .5rem;
  width: 100vw; padding: .4rem .75rem;
  background: rgba( var(--foreground-rgb, 255,153,0), 0.12 ); /* subtle tint fallback */
  background: color-mix(in srgb, var(--color-accent) 22%, transparent); /* modern browsers */
  color: var(--color-accent-text);
  font-weight: 700; font-size: 1.05rem; letter-spacing: .2px;
  backdrop-filter: saturate(1.1) blur(2px);
  /* optional thin underline */
  box-shadow: 0 1px 0 rgba(0,0,0,.2);
">🚀 {config.title} - {config.subtitle} 🚀</div>
"""

with gr.Blocks(title=f"{config.title} - {config.subtitle}", css=css, head=HEADER, fill_width=True) as demo:
    with gr.Tab("Réglages", render=False) as settings_tab:
        settings = nmsite.tabs.settings.settings_tab(config, demo)
    gr.HTML(HEADER, container=False)
    tabs = {"settings": settings_tab}
    with gr.Tab("Combat", render=False) as combat_tab:
        from nmsite.tabs import combat
        combat.combat_tab(config)
        tabs["combat"] = combat_tab

    with gr.Tab(label="Synchro", id="default", render=False) as synchro_tab:
        from nmsite.tabs import synchro
        synchro.synchro_tab(config, settings)
        tabs["synchro"] = synchro_tab

    with gr.Tab("Pontes", render=False) as pontes_tab:
        from nmsite.tabs import pontes
        pontes.pontes_tab()
        tabs["pontes"] = pontes_tab

    with gr.Tab("Chasse", render=False) as hunt_tab:
        from nmsite.tabs import hunt
        hunt.hunt_tab(config)
        tabs["hunt"] = hunt_tab

    with gr.Tab("Durées", render=False) as durees_tab:
        from nmsite.tabs import durees
        durees.durees_tab(settings)
        tabs["durees"] = durees_tab

    with gr.Tabs() as t:
        match config.tabs:
            case "default":
                tab_order = ["combat", "pontes", "synchro", "durees", "settings"]
            case "all":
                tab_order = list(tabs.keys())
            case [*elems] if set(elems) <= tabs.keys():
                tab_order = elems
        for tab in tab_order:
            tabs[tab].render()
    t.selected = "default"        



if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
