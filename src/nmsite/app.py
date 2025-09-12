import gradio as gr
import os
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
    from nmsite.tabs import settings
    settings = settings.Settings(demo)
    gr.HTML(HEADER, container=False)
    with gr.Tabs() as tabs:
        with gr.Tab("Combat") as combat_tab:
            from nmsite.tabs import combat
            combat.combat_tab(config)

        with gr.Tab(label="Synchro") as synchro_tab:
            from nmsite.tabs import synchro
            synchro.synchro_tab(config, settings)

        with gr.Tab("Pontes") as pontes_tab:
            from nmsite.tabs import pontes
            pontes.pontes_tab()

        with gr.Tab("Chasse", id="default") as hunt_tab:
            from nmsite.tabs import hunt
            hunt.hunt_tab(config)

        with gr.Tab("Durées") as durees_tab:
            from nmsite.tabs import durees
            durees.durees_tab(settings)
    tabs.selected = "default"        



if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
