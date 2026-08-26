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

.seg-wrapper { padding: 0 !important; }

.smgroup {
    gap: 0.25rem;
    min-width: 0 !important;
}



/* TODO: tab-specific CSS (above and below) should live alongside each tab file,
   not here. Consider a pattern where each tab exposes a CSS constant that app.py
   assembles into the final gr.Blocks(css=...) string. */
.result-field input,
.result-field textarea {
    border-left: 3px solid var(--color-accent) !important;
    background: transparent !important;
    color: var(--body-text-color) !important;
    opacity: 1 !important;
    cursor: default !important;
}

.army-check { align-self: stretch !important; display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 !important; flex: 0 0 44px !important; min-width: 0 !important; border: none !important; background: none !important; box-shadow: none !important; }
.army-check span { display: none !important; }
.army-check input[type="checkbox"] { width: 1.75rem !important; height: 1.75rem !important; cursor: pointer; accent-color: var(--color-accent); }

/* Icon-only buttons (e.g. the Discord logo button) don't stretch to a Row's shared
   height by default the way text buttons do - force it, same fix as .army-check above. */
.discord-copy-btn { align-self: stretch !important; height: auto !important; display: flex !important; align-items: center !important; justify-content: center !important; }"""

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

if config.tabs == "default":
    config.tabs = ["settings", "combat", "armees", "synchro", "durees"]

with gr.Blocks(title=f"{config.title} - {config.subtitle}", fill_width=True) as demo:
    with gr.Tab("Réglages", render=False) as settings_tab:
        settings = nmsite.tabs.settings.settings_tab(config, demo)
    gr.HTML(HEADER, container=False)
    tabs = {"settings": settings_tab}
    if config.tabs == "all" or "combat" in config.tabs:
        with gr.Tab("Combat", render=False) as combat_tab:
            from nmsite.tabs import combat
            combat.combat_tab(config)
            tabs["combat"] = combat_tab

    if config.tabs == "all" or "synchro" in config.tabs:
        with gr.Tab(label="Synchro", id="default", render=False) as synchro_tab:
            from nmsite.tabs import synchro
            synchro.synchro_tab(config, settings)
            tabs["synchro"] = synchro_tab

    if config.tabs == "all" or "armees" in config.tabs:
        with gr.Tab("Armées", render=False) as armees_tab:
            from nmsite.tabs import armees
            armees.armees_tab()
            tabs["armees"] = armees_tab

    if config.tabs == "all" or "hunt" in config.tabs:
        with gr.Tab("Chasse", render=False) as hunt_tab:
            from nmsite.tabs import hunt
            hunt.hunt_tab(config)
            tabs["hunt"] = hunt_tab

    if config.tabs == "all" or "durees" in config.tabs:
        with gr.Tab("Durées", render=False) as durees_tab:
            from nmsite.tabs import durees
            durees.durees_tab(settings, durees_tab)
            tabs["durees"] = durees_tab

    match config.tabs:
        case "all":
            tab_order = list(tabs.keys())
        case [*elems] if set(elems) <= tabs.keys():
            tab_order = elems

    with gr.Tabs(selected="default") as t:
        for tab in tab_order:
            tabs[tab].render()



if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", css=css, head=HEADER, footer_links=["gradio", "settings"])
