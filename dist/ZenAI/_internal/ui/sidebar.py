from nicegui import ui
from ui import Styles, Icons
from ui.registry import UI_IDS
from ui.model_data import MODEL_INFO
from locales import get_locale
from settings import get_settings
from pathlib import Path
import os

# --- Helper Render Functions ---

def render_header(ZENA_MODE, locale, app_state, drawer, dialogs):
    """Render the sidebar header with Logo and Settings."""
    with ui.row().classes('w-full items-center justify-between mb-4'):
        # Logo & Name
        with ui.row().classes('items-center gap-3'):
            ui.avatar('Z' if ZENA_MODE else 'N', color='primary', text_color='white').classes('text-xl')
            app_name = 'Zena' if ZENA_MODE else locale.APP_NAME
            ui.label(app_name).classes('text-2xl font-bold ' + Styles.TEXT_ACCENT)
        
        # App Status (Drawer)
        with ui.row().classes('items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30'):
            app_state['drawer_status_dot'] = ui.label('●').classes('text-green-500 animate-pulse text-xs')
            app_state['drawer_status_label'] = ui.label('ONLINE').classes('text-[9px] font-black tracking-widest text-green-500')
        
        # Settings Gear Button
        if 'settings' in dialogs:
            ui.button(icon=Icons.SETTINGS, on_click=lambda: dialogs['settings'].open()).props(f'flat round dense id={UI_IDS.BTN_SETTINGS}').classes(Styles.TEXT_MUTED + ' hover:text-blue-500 transition-colors')

        # Close button (mobile)
        ui.button(icon=Icons.CLOSE, on_click=lambda: drawer.hide()).props(f'flat round dense id={UI_IDS.BTN_CLOSE_DIALOG}').classes('md:hidden ' + Styles.TEXT_MUTED)

def render_new_chat(locale, actions):
    """Render New Chat and Tour buttons."""
    # New Chat
    ui.button(locale.BTN_NEW_CHAT if hasattr(locale, 'BTN_NEW_CHAT') else '💬 New Chat', 
              icon='add_comment', on_click=actions.start_new_chat).classes('w-full mb-2 ' + Styles.BTN_PRIMARY).props(f'unelevated id={UI_IDS.BTN_NEW_CHAT}')
    
    # Tour
    ui.button('🚀 Take Tour', icon='school', on_click=actions.start_tour).classes('w-full mb-4 ' + Styles.BTN_SECONDARY).props(f'outline id=ui-tour-btn')
    
    ui.separator().classes('mb-4')

def render_appearance(locale, actions):
    """Render Theme toggle."""
    with ui.expansion(locale.SETTINGS_CAT_APPEARANCE, icon='palette').classes('w-full mb-4').props('default-opened'):
        with ui.column().classes('w-full gap-2 py-2'):
            ui.switch(locale.SETTINGS_DARK_MODE, value=get_settings().appearance.dark_mode, on_change=actions.on_theme_change).classes('text-sm').props(f'id={UI_IDS.SW_DARK_MODE}')
            ui.label(locale.SETTINGS_DARK_MODE_DESC).classes(Styles.LABEL_MUTED + ' ml-10 -mt-1 text-xs')

def render_rag(locale, app_state, actions):
    """Render Knowledge Base controls."""
    with ui.expansion(locale.SETTINGS_CAT_RAG, icon='library_books').classes('w-full mb-4').props('default-opened'):
        with ui.column().classes('w-full gap-2 py-2'):
            # Enable RAG Switch
            rag_enabled_val = app_state.get('rag_enabled', False)
            rag_toggle = ui.switch(locale.SETTINGS_RAG_ENABLED, value=rag_enabled_val, on_change=actions.on_rag_toggle).classes('text-sm')
            ui.label(locale.SETTINGS_RAG_ENABLED_DESC).classes(Styles.LABEL_MUTED + ' ml-10 -mt-1 text-xs')
            
            # Scan Button
            scan_btn = ui.button(locale.RAG_START_SCAN, icon='search', on_click=actions.open_rag_scan).props('flat dense align=left').classes('w-full ' + Styles.TEXT_ACCENT)
            scan_btn.set_visibility(rag_enabled_val)
            app_state['rag_scan_btn'] = scan_btn

    ui.separator().classes('mb-4')

def render_batch(locale, backend, actions, UI_IDS):
    """Render Batch Analysis panel."""
    with ui.expansion(locale.BATCH_MENU, icon='batch_prediction').classes('w-full mb-4'):
        with ui.column().classes('w-full gap-2 py-2'):
            ui.label(locale.BATCH_CREATE_REVIEW).classes('text-xs font-semibold ' + Styles.TEXT_PRIMARY)
            
            # File Input
            files_input = ui.input(placeholder=locale.BATCH_FILES_PLACEHOLDER).classes('w-full h-10 text-xs').props(f'outlined dense id={UI_IDS.INPUT_BATCH_FILES}')
            
            # Progress Area
            progress_container = ui.column().classes('w-full gap-1 hidden ' + Styles.BATCH_CARD)
            with progress_container:
                with ui.row().classes('items-center gap-2'):
                    ui.spinner('dots', size='xs', color='blue')
                    progress_label = ui.label('').classes('text-[10px] ' + Styles.TEXT_MUTED)
                progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full ' + Styles.BATCH_PROGRESS_BAR)
            
            # Enqueue Button
            # We defer execution to actions.start_batch but need to pass UI refs
            batch_btn = ui.button(locale.BATCH_ENQUEUE, icon='play_circle').props(f'flat dense id={UI_IDS.BTN_BATCH_START}').classes('w-full ' + Styles.TEXT_ACCENT)
            batch_btn.on_click(lambda: actions.start_batch(files_input, progress_container, progress_label, progress_bar, batch_btn))

def render_models(locale, actions, app_state, dialogs):
    """Render Model Manager."""
    # Get current models by scanning directory
    try:
        models_dir = Path("C:/AI/Models")
        if models_dir.exists():
            current_models = [f.name for f in models_dir.glob("*.gguf") if f.is_file()]
            current_models.sort(key=lambda x: x.lower())
        else:
            current_models = []
    except Exception:
        current_models = []
    
    with ui.expansion(locale.NAV_MODEL_MANAGER, icon='smart_toy').classes('w-full mb-2').props('default-opened'):
        with ui.column().classes('w-full gap-3 py-2'):
            
            # Active Model Display
            ui.label(locale.MODEL_ACTIVE_LABEL).classes('font-semibold text-sm ' + Styles.TEXT_PRIMARY)
            
            selected_model = current_models[0] if current_models else None
            # Use action helper to get info
            selected_info = actions.get_model_info(selected_model, MODEL_INFO) if selected_model else { 'name': 'None', 'desc': 'No model loaded', 'size': '-', 'icon': '❌', 'good_for': [], 'speed': '-', 'quality': '-' }
            
            # Active Card
            with ui.card().classes('w-full p-3 bg-blue-50 dark:bg-slate-800 border-l-4 border-blue-500'):
                with ui.row().classes('items-center gap-3'):
                    ui.label(selected_info['icon']).classes('text-2xl')
                    with ui.column().classes('flex-grow gap-1'):
                        active_name = ui.label(selected_info['name']).classes('font-bold ' + Styles.TEXT_PRIMARY)
                        active_desc = ui.label(selected_info['desc']).classes('text-xs ' + Styles.LABEL_MUTED)
                        with ui.row().classes('gap-1 flex-wrap') as active_tags:
                            for tag in selected_info.get('good_for', []):
                                ui.badge(tag, color='green').props('outline dense').classes('text-[10px]')
            
            # UI elements dict to pass to action
            ui_elements = {'name_label': active_name, 'desc_label': active_desc, 'tags_row': active_tags}
            
            # Model List
            if current_models:
                with ui.row().classes('items-center gap-2 mt-3'):
                    ui.label('📦 Local Models').classes('text-xs font-semibold ' + Styles.TEXT_MUTED)
                    ui.badge(str(len(current_models)), color='blue').props('dense').classes('text-[10px]')
                
                with ui.scroll_area().classes('w-full max-h-48'):
                    for mf in current_models:
                        if mf == selected_model: continue
                        info = actions.get_model_info(mf, MODEL_INFO)
                        with ui.card().classes('w-full p-2 mb-1 hover:shadow-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-all cursor-pointer') \
                             .on('click', lambda m=mf, i=info: actions.switch_to_model(m, i, ui_elements)):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(info['icon']).classes('text-lg')
                                with ui.column().classes('flex-grow gap-0'):
                                    ui.label(info['name']).classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                                    ui.badge(info['size'], color='grey').props('outline').classes('text-xs')
            else:
                 ui.label('No local models found').classes('text-xs text-gray-400 italic mt-2')

            app_state['model_select'] = None
            ui.separator().classes('my-2')
            
            # Download Section
            with ui.expansion('📥 ' + locale.MODEL_DOWNLOAD_NEW, icon=Icons.DOWNLOAD).classes('w-full'):
                with ui.column().classes('w-full gap-2 py-2'):
                     # Defined simplified list of download options
                     download_options = [
                         MODEL_INFO['qwen2.5-coder-7b-instruct-q4_k_m.gguf'],
                         MODEL_INFO['Llama-3.2-3B-Instruct-Q4_K_M.gguf'],
                         MODEL_INFO['Phi-3-mini-4k-instruct-q4.gguf']
                     ]
                     # Add Repo info which is missing in MODEL_INFO, adding it ad-hoc for simplicity or use extended data
                     # Correcting: MODEL_INFO in data.py didn't have 'repo' key.
                     # We can just hardcode the loop here as in original, or extend logic.
                     # For safety, I'll use the original list hardcoded here to ensure repos are correct.
                     download_models = [
                        {"name": "Qwen 2.5 Coder 7B", "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "size": "~5GB"},
                        {"name": "Llama 3.2 3B", "repo": "lmstudio-community/Llama-3.2-3B-Instruct-GGUF", "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf", "size": "~3GB"},
                        {"name": "Phi-3 Mini", "repo": "microsoft/Phi-3-mini-4k-instruct-gguf", "file": "Phi-3-mini-4k-instruct-q4.gguf", "size": "~2GB"}
                     ]
                     
                     for m in download_models:
                         with ui.row().classes('w-full items-center justify-between p-1 hover:bg-gray-50 dark:hover:bg-slate-800 rounded'):
                             with ui.column().classes('gap-0'):
                                 ui.label(m['name']).classes('text-xs font-bold')
                                 ui.label(m['size']).classes('text-[10px] text-gray-400')
                             ui.button(icon=Icons.DOWNLOAD, on_click=lambda mod=m: actions.download_model(mod)).props('flat dense round size=sm')
                     
                     ui.separator().classes('my-2')
                     if 'model' in dialogs:
                         ui.button('🔗 ' + locale.MODEL_CUSTOM_DOWNLOAD, icon=Icons.CLOUD_DOWNLOAD, on_click=lambda: dialogs['model'].open()).props('flat dense').classes('w-full ' + Styles.TEXT_ACCENT)

def render_smart_mode(app_state):
    """Render Smart Mode toggle."""
    with ui.expansion("🧠 Smart Mode", icon='psychology').classes('w-full mb-2'):
        with ui.column().classes('w-full gap-3 py-2'):
            ui.label("Make the AI think harder").classes('text-xs font-bold ' + Styles.TEXT_PRIMARY)
            
            with ui.card().classes('w-full p-3 bg-gray-50 dark:bg-slate-800 rounded-lg'):
                with ui.row().classes('items-center w-full'):
                    with ui.column().classes('flex-grow gap-0'):
                        ui.label("Council Mode").classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                        ui.label("Swarm Consensus").classes('text-[10px] ' + Styles.LABEL_MUTED)
                    use_swarm = ui.switch(value=False).props('color=purple')
            
            # Deep Thinking (CoT)
            with ui.row().classes('items-center w-full px-1 mt-2'):
                with ui.column().classes('flex-grow gap-0'):
                     ui.label("Deep Thinking (CoT)").classes('text-xs font-semibold ' + Styles.TEXT_PRIMARY)
                use_cot = ui.switch(value=False).props('color=primary dense size=sm')

            with ui.row().classes('items-center gap-2 px-2').bind_visibility_from(use_cot, 'value'):
                quiet_cot = ui.checkbox("Quiet Mode", value=True).classes('text-sm')
            
            app_state['council_mode'] = use_swarm
            app_state['use_cot_swarm'] = use_cot
            app_state['quiet_cot'] = quiet_cot
            ui.separator().classes('my-2')
            
            with ui.row().classes('items-center gap-2 px-2 py-1 rounded bg-green-50 dark:bg-green-900/20'):
                ui.icon('groups', size='18px').classes('text-purple-500')
                app_state['swarm_status'] = ui.label('Council Ready').classes('text-xs font-medium text-purple-600 dark:text-purple-400')

def render_labs(actions):
    """Render Labs section."""
    with ui.expansion("🔬 Labs", icon="science").classes('w-full mb-2'):
        with ui.column().classes('w-full gap-2 py-2'):
            ui.button("Voice Lab", icon=Icons.RECORD, on_click=actions.open_voice_lab).props('flat dense align=left').classes('w-full ' + Styles.TEXT_PRIMARY)

    with ui.expansion("⚖️ Intelligence Judge", icon="balance").classes('w-full mb-2'):
        with ui.column().classes('w-full gap-2 py-2 p-2'):
             ui.button("Run Evaluation", icon="analytics", on_click=actions.open_judge).props(f'flat dense align=left id={UI_IDS.BTN_JUDGE}').classes('w-full ' + Styles.TEXT_PRIMARY)

def render_system(locale, config, actions):
    """Render System Tools."""
    with ui.expansion(locale.NAV_SYSTEM, icon='build').classes('w-full mb-2'):
        with ui.column().classes('w-full gap-2 py-2'):
            with ui.card().classes('w-full p-3 bg-gray-50 dark:bg-slate-800'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('memory', size='24px').classes('text-green-500')
                    with ui.column().classes('flex-grow gap-0'):
                        ui.label('System Status').classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                        status_label = ui.label('Ready').classes('text-xs ' + Styles.LABEL_MUTED)
            
            with ui.row().classes('w-full gap-2 flex-wrap'):
                ui.button('Version', icon='update', on_click=actions.check_llama_version).props('flat dense').classes('flex-1')
                ui.button('Benchmark', icon='speed', on_click=lambda: actions.run_benchmark(status_label)).props('flat dense').classes('flex-1')
                ui.button('Diagnose', icon='healing', on_click=lambda: actions.run_diagnostics(status_label)).props('flat dense').classes('flex-1')

def render_footer():
    """Render Footer."""
    ui.space()
    with ui.row().classes('w-full justify-center mt-auto pt-4 border-t border-gray-200 dark:border-slate-700'):
        ui.label('v1.0.0').classes(Styles.LABEL_MUTED + ' text-xs')

# --- Main Entry Point ---

def create_sidebar(app_state, actions, backend, dialogs, config, ZENA_MODE, EMOJI):
    """
    Main Sidebar creation function.
    Orchestrates the sidebar layout by calling modular render functions.
    """
    locale = get_locale()
    
    with ui.left_drawer(value=True).classes(Styles.DRAWER).props('width=280 bordered') as drawer:
        render_header(ZENA_MODE, locale, app_state, drawer, dialogs)
        render_new_chat(locale, actions)
        render_appearance(locale, actions)
        render_rag(locale, app_state, actions)
        render_batch(locale, backend, actions, UI_IDS)
        ui.separator().classes('mb-4')
        render_models(locale, actions, app_state, dialogs)
        render_smart_mode(app_state)
        render_labs(actions)
        render_system(locale, config, actions)
        render_footer()
        
    return drawer
