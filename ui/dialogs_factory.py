from nicegui import ui
from ui import Styles, Icons, UI_IDS
from locales import get_locale
import logging

logger = logging.getLogger("UI.Dialogs")

class DialogsFactory:
    """Factory for creating application dialogs."""
    
    @staticmethod
    def setup_common_dialogs(backend, app_state, on_settings_save=None, on_language_change=None, on_dark_mode=None):
        """
        Creates reusable dialogs (Model Download, Llama Update, Settings).
        Returns a dict referencing them: {'model': dialog, 'llama': dialog, 'settings': dialog}
        """
        locale = get_locale()
        dialogs = {}
        
        # 1. Custom Model Download Dialog
        with ui.dialog() as model_dialog, ui.card().classes('w-full max-w-lg p-6 bg-white dark:bg-slate-800'):
            ui.label(locale.MODEL_CUSTOM_DOWNLOAD).classes('text-lg font-bold mb-4 ' + Styles.TEXT_PRIMARY)

            repo_input = ui.input('HuggingFace Repo', placeholder='TheBloke/Llama-2-7B-Chat-GGUF').classes('w-full mb-2').props('outlined dense')
            file_input = ui.input('Filename', placeholder='llama-2-7b-chat.Q4_K_M.gguf').classes('w-full mb-4').props('outlined dense')

            async def download_custom():
                """Download custom."""
                repo = repo_input.value.strip()
                filename = file_input.value.strip()
                if not repo or not filename:
                    ui.notify("Please fill in both fields", color='warning')
                    return

                model_dialog.close()
                # Trigger download via backend API (Action logic moved here for simplicity or delegate)
                import asyncio
                import requests
                ui.notify(f"⬇️ Requesting: {filename}...", color='info')
                try:
                    response = await asyncio.to_thread(requests.post, "http://127.0.0.1:8002/models/download", 
                                                     json={"repo_id": repo, "filename": filename}, timeout=5)
                    if response.status_code == 200:
                        ui.notify("✅ Download started!", color='positive')
                    else:
                        ui.notify(f"❌ Failed: {response.text}", color='negative')
                except Exception as e:
                    ui.notify(f"❌ Error: {e}", color='negative')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(locale.BTN_CANCEL, on_click=model_dialog.close).props('flat color=grey')
                ui.button(locale.BTN_DOWNLOAD, on_click=download_custom).props('unelevated color=primary')

        dialogs['model'] = model_dialog

        # 2. Settings Dialog
        # Use simple creation function if available, else inline
        from ui.settings_dialog import create_settings_dialog
        settings_dialog = create_settings_dialog(on_save=on_settings_save, on_language_change=on_language_change, on_dark_mode_change=on_dark_mode)
        dialogs['settings'] = settings_dialog
        
        # 3. Llama Update Dialog (Simple confirmation)
        with ui.dialog() as llama_dialog:
             with ui.card().classes('w-full max-w-md p-6 bg-white dark:bg-slate-800'):
                ui.label("Update AI Engine").classes('text-lg font-bold mb-2 ' + Styles.TEXT_PRIMARY)
                info_label = ui.label("Checking version...").classes('text-sm text-gray-500 mb-4')
                
                async def run_update():
                    """Run update."""
                    info_label.text = "Updating..."
                    # Mock update
                    import asyncio
                    await asyncio.sleep(2)
                    ui.notify("Update feature placeholder", color='info')
                    llama_dialog.close()

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=llama_dialog.close).props('flat color=grey')
                    ui.button('Update Now', on_click=run_update).props('unelevated color=primary')
                
                llama_dialog.info_label = info_label
        
        dialogs['llama'] = llama_dialog
        
        return dialogs
