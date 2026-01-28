from nicegui import ui
import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger("ZenaRAGUI")

def setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, locale, rag_system, ROOT_DIR, Styles):
    """Setup the RAG dialog and its logic in a clean, modular way."""
    rag_dialog = ui.dialog().classes('z-50')
    app_state['open_rag_dialog'] = rag_dialog.open
    
    with rag_dialog, ui.card().classes('w-[500px] max-w-[95vw] p-6 rounded-2xl shadow-2xl bg-white dark:bg-slate-900'):
        if ZENA_MODE:
            ui.label(locale.RAG_SCAN_READ).classes(Styles.DIALOG_TITLE)
            
            # Mode selector
            mode_select = ui.select([locale.RAG_WEBSITE, locale.RAG_LOCAL_DIRECTORY], value=locale.RAG_WEBSITE, label=locale.RAG_SOURCE_TYPE).props('outlined').classes('w-full mb-3')
            
            # Website inputs
            website_input = ui.input(locale.RAG_WEBSITE_URL, value=ZENA_CONFIG.get('website_url', '')).props('outlined').classes('w-full mb-2')
            pages_input = ui.input(locale.RAG_MAX_PAGES, value='50').props('outlined').classes('w-full mb-2')
            
            # Directory inputs (hidden by default)
            dir_input = ui.input(locale.RAG_DIRECTORY_PATH, placeholder='C:/Users/YourName/Documents').props('outlined visible=false').classes('w-full mb-2')
            files_input = ui.input(locale.RAG_MAX_FILES, value='1000').props('outlined visible=false').classes('w-full mb-2')
            
            # Toggle visibility based on mode
            def on_mode_change():
                is_website = mode_select.value == locale.RAG_WEBSITE
                website_input.set_visibility(is_website)
                pages_input.set_visibility(is_website)
                dir_input.set_visibility(not is_website)
                files_input.set_visibility(not is_website)
            
            mode_select.on('update:model-value', on_mode_change)
            
            # Progress indicators
            progress_label = ui.label('').classes('text-md font-bold ' + Styles.TEXT_ACCENT + ' mb-2')
            progress_bar = ui.linear_progress(value=0, show_value=False).classes(Styles.PROGRESS).props('visible=false color=primary')
            
            async def build_and_save_index(documents, source):
                if rag_system and documents:
                    await asyncio.to_thread(rag_system.build_index, documents)
                    rag_cache_path = ROOT_DIR / "rag_cache"
                    await asyncio.to_thread(rag_system.save, rag_cache_path)
                    ui.notify(f"✅ RAG index ready!", color='positive', position='top')
                    await asyncio.sleep(1)
                    rag_dialog.close()

            async def start_scan():
                ui.notify("Starting RAG scan...", color='info')
                # Integration with scanning backend (Placeholder for move)
            
            ui.button('Start Scan', on_click=start_scan).props('color=primary').classes('w-full')
            ui.button('Cancel', on_click=rag_dialog.close).props('flat').classes('w-full mt-2')
        else:
            ui.label("RAG not enabled in Zena mode").classes('text-center text-gray-400')
            ui.button('Close', on_click=rag_dialog.close).props('flat').classes('w-full mt-2')
    
    return rag_dialog
