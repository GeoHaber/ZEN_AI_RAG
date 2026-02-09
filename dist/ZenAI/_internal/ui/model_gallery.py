from nicegui import ui
import requests
import logging
from config_system import config
from ui.model_data import MODEL_INFO

logger = logging.getLogger("ZenAI.UI.Gallery")

def get_model_metadata(filename):
    """Retrieve metadata for a model filename."""
    return MODEL_INFO.get(filename, {
        'name': filename.replace('.gguf', '').replace('-', ' ').title(),
        'desc': 'Local GGUF Model',
        'size': 'Unknown',
        'icon': '🤖',
        'good_for': [],
        'speed': 'Unknown',
        'quality': 'Unknown'
    })

def create_model_gallery(ui_state, app_state):
    """Create the interactive Model Gallery (Council Chamber)."""
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl h-[80vh] bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700'):
        
        # Header
        with ui.row().classes('w-full items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-700'):
            ui.label('🤖 Council of LLMs').classes('text-xl font-bold text-slate-800 dark:text-slate-100')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense')

        # Model Grid
        grid_container = ui.grid(columns=3).classes('w-full gap-4 p-4 overflow-y-auto flex-grow')
        
        def refresh_models():
            grid_container.clear()
            try:
                # Fetch available models
                resp = requests.get(f"http://127.0.0.1:{config.mgmt_port}/list", timeout=10)
                if resp.status_code == 200:
                    models = resp.json().get('models', [])
                    
                    # Fetch active swarm status (mock or api)
                    # For now just list them
                    
                    with grid_container:
                        for model_file in models:
                            meta = get_model_metadata(model_file)
                            
                            with ui.card().classes('flex flex-col gap-2 p-4 hover:shadow-lg transition-shadow bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700'):
                                # Icon & Name
                                with ui.row().classes('items-center gap-3'):
                                    ui.label(meta['icon']).classes('text-3xl')
                                    with ui.column().classes('gap-0'):
                                        ui.label(meta['name']).classes('font-bold text-slate-800 dark:text-slate-100')
                                        ui.label(meta['size']).classes('text-xs text-slate-400')
                                
                                ui.label(meta['desc']).classes('text-sm text-slate-600 dark:text-slate-400 min-h-[40px]')
                                
                                # Tags
                                with ui.row().classes('gap-1 flex-wrap'):
                                    for tag in meta.get('good_for', [])[:3]:
                                        ui.label(tag).classes('text-[10px] px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 rounded-full')
                                
                                ui.separator().classes('my-2')
                                
                                # Actions
                                with ui.row().classes('w-full justify-end gap-2'):
                                    # Swap Button
                                    def swap(m=model_file):
                                        ui.notify(f"Swapping to {m}...", color='orange')
                                        requests.post(f"http://127.0.0.1:{config.mgmt_port}/swap", json={"model": m})
                                        dialog.close()
                                        
                                    ui.button('Swap', on_click=swap).props('outline size=sm color=orange')
                                    
                                    # Launch Expert Button
                                    def launch(m=model_file):
                                        ui.notify(f"Summoning Expert: {m}...", color='purple')
                                        # Auto-assign port logic basic
                                        requests.post(f"http://127.0.0.1:{config.mgmt_port}/swarm/launch", json={"model": m, "port": 8005}) # Hardcoded for demo
                                        ui.notify("Expert Summoned!", color='positive')
                                        
                                    ui.button('Summon', on_click=launch).props('unelevated size=sm color=purple')

            except Exception as e:
                with grid_container:
                    ui.label(f"Error loading models: {e}").classes('text-red-500')

        refresh_models()
        dialog.open()
        return dialog
