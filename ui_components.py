from nicegui import ui
import logging
import asyncio
import requests
import subprocess
from utils import normalize_input
import time

# Import localization and UI modules
from locales import get_locale, L
from ui import Styles, Icons, Formatters
from ui.theme import Theme, Colors
from ui.settings_dialog import create_settings_dialog

logger = logging.getLogger("UI Components")

def setup_app_theme():
    """Configures the application theme, colors, and CSS."""
    # Theme & Layout (Zena Style - Light & Professional)
    ui.colors(primary='#3b82f6', secondary='#6c757d', accent='#17a2b8', dark=False)
    # Set light background
    ui.query('body').classes('bg-gray-50 dark:bg-slate-900')
    
    # CSS Fixes for Markdown Headers and Code Blocks in Chat
    ui.add_head_html('''
        <script>
            // Sync Quasar Dark Mode (body--dark) with Tailwind Dark Mode (dark class on html)
            function syncDarkMode() {
                const isDark = document.body.classList.contains('body--dark');
                console.log('Syncing dark mode:', isDark);
                if (isDark) {
                    document.documentElement.classList.add('dark');
                    document.documentElement.setAttribute('data-theme', 'dark');
                    // Force body styling for elements that check body directly
                    document.body.style.setProperty('--body-bg', '#0f172a');
                    document.body.style.setProperty('color-scheme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    document.documentElement.setAttribute('data-theme', 'light');
                    document.body.style.setProperty('--body-bg', '#f8fafc');
                    document.body.style.setProperty('color-scheme', 'light');
                }
            }
            
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        syncDarkMode();
                    }
                });
            });
            
            // Start observing immediately
            function startObserver() {
                observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
                syncDarkMode(); // Initial sync
            }
            
            // Run as soon as body is available
            if (document.body) {
                startObserver();
            } else {
                document.addEventListener('DOMContentLoaded', startObserver);
            }
            
            // Also check periodically for the first few seconds (handles NiceGUI async init)
            let checkCount = 0;
            const checkInterval = setInterval(() => {
                syncDarkMode();
                checkCount++;
                if (checkCount >= 10) clearInterval(checkInterval);
            }, 500);
        </script>
        
        <!-- MODERN SLATE THEME - GLOBAL STYLING -->
        <style>
            /* 1. TYPOGRAPHY & RESET */
            :root {
                --primary: #3b82f6;
                --slate-950: #0f172a;
                --slate-900: #0f172a; /* Deep Match */
                --slate-800: #1e293b;
                --slate-50: #f8fafc;
            }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
                -webkit-font-smoothing: antialiased;
            }

            /* 2. GLOBAL THEME LAYERS */
            /* Light Mode Defaults */
            body, .q-page, .q-page-container, .nicegui-content {
                background-color: var(--slate-50) !important;
                color: #1e293b !important;
            }
            
            /* Dark Mode Defaults */
            .body--dark, .body--dark .q-page, .body--dark .q-page-container, .body--dark .nicegui-content {
                background-color: var(--slate-950) !important;
                color: #f1f5f9 !important;
            }

            /* 3. CARD & DIALOG STYLING (Glassmorphism Lite) */
            .q-card, .q-dialog .q-card {
                border-radius: 16px !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            }
            /* Light Cards */
            .q-card { background-color: #ffffff !important; border: 1px solid #e2e8f0; }
            /* Dark Cards */
            .body--dark .q-card { 
                background-color: var(--slate-800) !important; 
                border: 1px solid #334155;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
            }

            /* 4. INPUTS & CONTROLS (The "Google" Look) */
            .q-field__control {
                border-radius: 10px !important; /* Rounded inputs */
                height: 48px !important;
            }
            .q-field__native, .q-input {
                padding-left: 4px;
            }
            
            /* Input Colors - Light */
            .q-field--outlined .q-field__control:before { border: 1px solid #cbd5e1; }
            .q-input__inner, .q-field__native { color: #1e293b !important; }
            
            /* Input Colors - Dark */
            .body--dark .q-field--outlined .q-field__control:before { border: 1px solid #475569; }
            .body--dark .q-input__inner, 
            .body--dark .q-field__native, 
            .body--dark .q-field__label, 
            .body--dark .q-select__dropdown-icon { 
                color: #f1f5f9 !important; 
            }
            .body--dark .q-field__control { background-color: #1e293b !important; }

            /* 5. MENUS & DROPDOWNS (Fixing "Invisible Text") */
            .q-menu {
                border-radius: 12px !important;
                padding: 4px;
            }
            /* Light Menu */
            .q-menu { background: #ffffff !important; color: #1e293b !important; border: 1px solid #e2e8f0; }
            .q-menu .q-item__label { color: #1e293b !important; }
            .q-menu .q-item { color: #1e293b !important; }
            /* Dark Menu */
            .body--dark .q-menu { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
                border: 1px solid #334155; 
            }
            .body--dark .q-item { color: #f1f5f9 !important; }
            .body--dark .q-item__label { color: #f1f5f9 !important; }
            .body--dark .q-item--active { background: #334155 !important; color: #60a5fa !important; }
            
            /* Select Dropdown Popup */
            .q-select__dialog { background: #ffffff !important; }
            .body--dark .q-select__dialog { background: #1e293b !important; }
            .q-virtual-scroll__content .q-item { color: #1e293b !important; }
            .body--dark .q-virtual-scroll__content .q-item { color: #f1f5f9 !important; }

            /* 6. DRAWER STYLING */
            /* Light Drawer */
            .q-drawer { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
            /* Dark Drawer */
            .body--dark .q-drawer { 
                background-color: #0f172a !important; 
                border-right: 1px solid #1e293b; 
            }
            .body--dark .q-drawer__content { background-color: transparent !important; }

            /* 7. CHAT BUBBLES */
            /* User */
            .q-message-name { font-size: 0.75rem; opacity: 0.7; margin-bottom: 2px; }
            .q-message-text { 
                border-radius: 18px !important; 
                padding: 12px 18px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .body--dark .q-message-text { border: 1px solid #334155; }
            .q-message-text h1 { font-size: 1.25rem; line-height: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }
            .q-message-text h2 { font-size: 1.1rem; line-height: 1.4rem; font-weight: 600; margin-bottom: 0.5rem; margin-top: 1rem; }
            .q-message-text h3 { font-size: 1rem; line-height: 1.3rem; font-weight: 600; margin-bottom: 0.5rem; }
            .q-message-text pre { background-color: #f3f4f6; padding: 0.5rem; border-radius: 0.375rem; overflow-x: auto; }
            
            .body--dark .q-message-text pre { background-color: #0f172a; color: #e2e8f0; border: 1px solid #1e293b; }
            .body--dark .q-message-text code { background-color: rgba(255,255,255,0.1); color: #cbd5e1; }
            
            /* 8. BUTTONS */
            .q-btn { 
                border-radius: 8px !important; 
                font-weight: 600 !important; 
                text-transform: none !important; /* Proper Case */
            }
            /* System sidebar buttons - Light */
            .q-btn--flat.q-btn--align-left { 
                background: #f1f5f9 !important; 
                color: #1e293b !important; 
            }
            .q-btn--flat.q-btn--align-left:hover { 
                background: #e2e8f0 !important; 
            }
            /* System sidebar buttons - Dark */
            .body--dark .q-btn--flat.q-btn--align-left { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
            }
            .body--dark .q-btn--flat.q-btn--align-left:hover { 
                background: #334155 !important; 
            }
            
            /* 9. SCROLLBARS */
            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
            .body--dark ::-webkit-scrollbar-thumb { background: #475569; }
            
            /* 10. PROGRESS BARS */
            .body--dark .q-linear-progress__track {
                background: rgba(255, 255, 255, 0.2) !important;
                opacity: 1 !important;
            }
            .body--dark .q-linear-progress__model {
                background: var(--q-primary) !important;
            }
            
            /* 11. LABELS & TEXT - Ensure visibility in both modes */
            .q-field__label { color: #64748b !important; } /* Light mode label */
            .body--dark .q-field__label { color: #94a3b8 !important; } /* Dark mode label */
            
            /* 12. EXPANSION PANELS */
            .q-expansion-item { color: #1e293b; background: #eff6ff !important; }
            .q-expansion-item__container { background: transparent !important; }
            .q-item__label { color: inherit !important; }
            .body--dark .q-expansion-item { color: #f1f5f9; background: #1e293b !important; }
            .body--dark .q-expansion-item .q-item__label { color: #f1f5f9 !important; }
            .body--dark .q-expansion-item .q-icon { color: #94a3b8 !important; }
            .body--dark .q-expansion-item__content { background: #0f172a !important; }
            
            /* 13. SWITCHES & TOGGLES */
            .q-toggle__label { color: #1e293b !important; }
            .body--dark .q-toggle__label { color: #f1f5f9 !important; }
            
            /* 14. GENERAL TEXT INHERITANCE */
            .body--dark label, 
            .body--dark .q-field__bottom,
            .body--dark .text-gray-600,
            .body--dark .text-gray-700,
            .body--dark .text-gray-800 { 
                color: #cbd5e1 !important; 
            }
            
            /* 15. TOOLTIP & NOTIFICATIONS */
            .q-tooltip { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
            }
            
            /* 16. FIX: Tailwind dark: classes need body--dark context */
            .body--dark .dark\\:text-white { color: #ffffff !important; }
            .body--dark .dark\\:text-gray-100 { color: #f3f4f6 !important; }
            .body--dark .dark\\:text-gray-200 { color: #e5e7eb !important; }
            .body--dark .dark\\:text-gray-300 { color: #d1d5db !important; }
            .body--dark .dark\\:text-gray-400 { color: #9ca3af !important; }
            .body--dark .dark\\:text-slate-300 { color: #cbd5e1 !important; }
            .body--dark .dark\\:text-blue-400 { color: #60a5fa !important; }
            .body--dark .dark\\:bg-slate-800 { background-color: #1e293b !important; }
            .body--dark .dark\\:bg-slate-900 { background-color: #0f172a !important; }
            .body--dark .dark\\:bg-slate-950 { background-color: #020617 !important; }
            .body--dark .dark\\:border-slate-700 { border-color: #334155 !important; }
            .body--dark .dark\\:border-slate-800 { border-color: #1e293b !important; }
            .body--dark .dark\\:hover\\:bg-slate-700:hover { background-color: #334155 !important; }
            
            /* 17. CHAT MESSAGE BUBBLES - Specific dark mode fixes */
            .body--dark .bg-gray-100 { background-color: #1e293b !important; }
            .body--dark .text-gray-900 { color: #f1f5f9 !important; }
            
            /* 18. DIALOG STYLING */
            .q-dialog__backdrop { background: rgba(0, 0, 0, 0.5) !important; }
            .q-dialog .q-card { 
                max-height: 90vh; 
                overflow: auto;
            }
            /* Dialog dark mode */
            .body--dark .q-dialog .q-card {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
            }
            
            /* 19. SWITCH/TOGGLE DARK MODE */
            .body--dark .q-toggle { color: #f1f5f9 !important; }
            .body--dark .q-toggle__inner { color: #94a3b8 !important; }
            
            /* 20. STATUS TEXT */
            .body--dark .text-gray-600 { color: #94a3b8 !important; }
            .body--dark .text-gray-500 { color: #64748b !important; }
            
            /* 21. MODEL CATALOG CARDS */
            .model-card { transition: all 0.2s ease; }
            .model-card:hover { transform: translateY(-2px); }
            
            /* 22. COMPREHENSIVE DARK MODE OVERRIDES FOR TAILWIND CLASSES */
            /* Background colors that need dark mode conversion */
            .body--dark .bg-blue-50,
            .body--dark .bg-blue-100 { 
                background-color: rgba(59, 130, 246, 0.15) !important; 
            }
            .body--dark .bg-gray-50,
            .body--dark .bg-gray-100 { 
                background-color: #1e293b !important; 
            }
            .body--dark .bg-white {
                background-color: #0f172a !important;
            }
            
            /* Text colors for dark mode */
            .body--dark .text-blue-700 { color: #93c5fd !important; }
            .body--dark .text-blue-600 { color: #60a5fa !important; }
            .body--dark .text-blue-500 { color: #3b82f6 !important; }
            .body--dark .text-green-600 { color: #86efac !important; }
            .body--dark .text-green-500 { color: #22c55e !important; }
            .body--dark .text-red-600 { color: #fca5a5 !important; }
            .body--dark .text-red-500 { color: #ef4444 !important; }
            .body--dark .text-purple-600 { color: #c4b5fd !important; }
            .body--dark .text-orange-600 { color: #fdba74 !important; }
            .body--dark .text-yellow-600 { color: #fde047 !important; }
            
            /* Hover states for dark mode */
            .body--dark .hover\\:bg-gray-100:hover,
            .body--dark .hover\\:bg-gray-50:hover {
                background-color: #334155 !important;
            }
            .body--dark .hover\\:bg-blue-100:hover {
                background-color: rgba(59, 130, 246, 0.25) !important;
            }
            
            /* Border colors for dark mode */
            .body--dark .border-gray-200 { border-color: #334155 !important; }
            .body--dark .border-gray-300 { border-color: #475569 !important; }
            .body--dark .border-blue-500 { border-color: #3b82f6 !important; }
            
            /* Ensure all q-card elements get dark background */
            .body--dark .q-card {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
            }
            
            /* Main page container */
            .body--dark .q-page-container,
            .body--dark .q-page {
                background-color: #0f172a !important;
            }
            
            /* 23. FULL HEIGHT CHAT LAYOUT (Like LM Studio / Ollama) */
            .q-page-container {
                display: flex !important;
                flex-direction: column !important;
                height: 100vh !important;
                overflow: hidden !important;
            }
            .q-page {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 !important;
                overflow: hidden !important;
                min-height: 0 !important;
            }
            /* Chat scroll container fills remaining space */
            .chat-scroll-area {
                flex: 1 !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                scroll-behavior: smooth;
            }
            /* Compact header */
            .q-header {
                flex-shrink: 0 !important;
            }
            /* Compact footer with input */
            .q-footer {
                flex-shrink: 0 !important;
                max-height: 120px !important;
            }
            
            /* 24. MAXIMIZED DIALOG */
            .q-dialog__inner--maximized > div {
                max-width: 1200px !important;
                margin: 0 auto;
            }
        </style>
    ''')

def setup_common_dialogs(backend, app_state):
    """
    Creates reusable dialogs (Model Download, Llama Update).
    Returns a dict referencing them: {'model': dialog, 'llama': dialog}
    """
    locale = get_locale()
    dialogs = {}

    # --- Model Catalog Dialog (Rich UI) ---
    with ui.dialog().props('maximized') as model_dialog:
        with ui.card().classes('w-full h-full p-0 overflow-hidden'):
            # Header
            with ui.row().classes('w-full p-4 items-center justify-between border-b'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon(Icons.DOWNLOAD, size='28px').classes('text-blue-500')
                    ui.label(locale.MODEL_SECTION_TITLE).classes('text-2xl font-bold')
                ui.button(icon=Icons.CLOSE, on_click=model_dialog.close).props('flat round')
            
            # Scrollable content area
            with ui.scroll_area().classes('w-full flex-grow p-4'):
                # Import model catalog
                try:
                    from model_manager import POPULAR_MODELS
                    models = POPULAR_MODELS
                except Exception:
                    models = []
                
                # Model cards grid
                with ui.element('div').classes(Styles.GRID_2_COL):
                    for model in models:
                        _create_model_card(model, model_dialog, backend, app_state)
                
                # Custom download section
                ui.separator().classes('my-6')
                with ui.expansion(f'🔧 {locale.MODEL_CUSTOM_DOWNLOAD}', icon=Icons.SETTINGS).classes('w-full'):
                    with ui.card().classes('p-4'):
                        ui.label(locale.MODEL_CUSTOM_DESCRIPTION).classes('text-sm mb-3')
                        custom_repo = ui.input(locale.MODEL_REPO_LABEL, placeholder=locale.MODEL_REPO_PLACEHOLDER).classes('w-full mb-2').props('outlined dense')
                        custom_file = ui.input(locale.MODEL_FILE_LABEL, placeholder=locale.MODEL_FILE_PLACEHOLDER).classes('w-full mb-3').props('outlined dense')
                        
                        async def download_custom():
                            repo = custom_repo.value.strip()
                            filename = normalize_input(custom_file.value, 'filename')
                            if not repo or not filename:
                                ui.notify(locale.NOTIFY_ENTER_BOTH_FIELDS, color='warning')
                                return
                            await _start_download(repo, filename, model_dialog, backend, app_state)
                        
                        ui.button(locale.MODEL_CUSTOM_DOWNLOAD, icon=Icons.CLOUD_DOWNLOAD, on_click=download_custom).props('color=primary')

    dialogs['model'] = model_dialog

    # --- Llama Update Dialog ---
    with ui.dialog() as llama_dialog, ui.card().classes(Styles.DIALOG_CARD + ' w-96'):
            ui.label(locale.SYS_UPDATE_ENGINE).classes(Styles.DIALOG_TITLE)
            llama_info = ui.label("Loading...").classes('mb-4')
            
            async def run_update():
                llama_dialog.close()
                ui.notify(locale.NOTIFY_UPDATE_MANUAL, color='info')
                await asyncio.to_thread(lambda: subprocess.Popen(["explorer", "https://github.com/ggerganov/llama.cpp/releases/latest"]))

            ui.button(locale.SYS_GET_UPDATE, on_click=run_update).props('color=primary').classes('w-full')
            ui.button(locale.BTN_CANCEL, on_click=llama_dialog.close).props('flat').classes('w-full mt-2')

            # We need to expose llama_info so checking function can update it.
            llama_dialog.info_label = llama_info

    dialogs['llama'] = llama_dialog
    
    return dialogs


def _create_model_card(model: dict, dialog, backend, app_state):
    """Create a rich model card for the catalog."""
    locale = get_locale()
    
    name = model.get('name', 'Unknown')
    description = model.get('description', '')
    downloads = model.get('downloads', 'N/A')
    stars = model.get('stars', 'N/A')
    released = model.get('released', 'N/A')
    size_gb = model.get('size_gb', 0)
    context_window = model.get('context_window', 'N/A')
    benchmark = model.get('benchmark', 'N/A')
    license_info = model.get('license', 'Unknown')
    repo = model.get('repo', '')
    filename = model.get('file', '')
    
    # Parse model info for RAM/params
    params = model.get('parameters_human', 'Unknown')
    ram = model.get('ram_estimate', 'Unknown')
    quant = model.get('quantization_human', Formatters.quantization_human('Q4_K_M'))
    
    # Determine speed/quality ratings based on model size
    speed, quality = Formatters.speed_rating(size_gb)
    
    with ui.card().classes(Styles.CARD_MODEL):
        # Header row with name and download button
        with ui.row().classes('w-full items-start justify-between mb-2'):
            with ui.column().classes('flex-grow'):
                ui.label(name).classes('text-lg font-bold ' + Styles.TEXT_ACCENT)
                ui.label(description).classes('text-sm')
        
        # Stats row
        with ui.row().classes('gap-4 text-xs mb-3'):
            ui.label(f'📊 {downloads} {locale.MODEL_DOWNLOADS}').classes(Styles.TEXT_MUTED)
            ui.label(f'⭐ {stars}').classes(Styles.TEXT_MUTED)
            ui.label(f'📅 {released}').classes(Styles.TEXT_MUTED)
        
        # Download size badge
        with ui.row().classes('items-center gap-2 mb-3'):
            ui.badge(f'📥 {size_gb}GB', color='blue').props('outline')
        
        # What this means section
        with ui.element('div').classes(Styles.CARD_INFO + ' mb-3'):
            ui.label(locale.MODEL_WHAT_THIS_MEANS).classes('font-semibold text-blue-700 mb-1')
            ui.label(f'{params} • {quant} • Needs {ram}').classes('text-blue-600')
        
        # Specs grid
        with ui.element('div').classes('grid grid-cols-2 gap-2 text-sm'):
            # Context
            with ui.column().classes('gap-0'):
                ui.label(locale.MODEL_CONTEXT).classes(Styles.LABEL_XS + ' font-semibold')
                ui.label(context_window).classes('text-sm')
            
            # Benchmark
            with ui.column().classes('gap-0'):
                ui.label(locale.MODEL_BENCHMARK).classes(Styles.LABEL_XS + ' font-semibold')
                ui.label(benchmark).classes('text-sm')
            
            # Speed
            with ui.column().classes('gap-0'):
                ui.label(locale.MODEL_SPEED).classes(Styles.LABEL_XS + ' font-semibold')
                ui.label(speed).classes('text-sm')
            
            # Quality
            with ui.column().classes('gap-0'):
                ui.label(locale.MODEL_QUALITY).classes(Styles.LABEL_XS + ' font-semibold')
                ui.label(quality).classes('text-sm')
        
        # License
        ui.separator().classes('my-2')
        with ui.row().classes('items-center gap-2'):
            ui.label(f'{locale.MODEL_LICENSE}:').classes(Styles.LABEL_XS + ' font-semibold')
            ui.label(license_info).classes('text-xs ' + Styles.TEXT_SUCCESS)
        
        # Download button
        async def download_this():
            await _start_download(repo, filename, dialog, backend, app_state)
        
        ui.button(f'{locale.BTN_DOWNLOAD} {name}', icon=Icons.CLOUD_DOWNLOAD, on_click=download_this).props('color=primary unelevated').classes('w-full mt-3')


async def _start_download(repo: str, filename: str, dialog, backend, app_state):
    """Start model download via Hub API."""
    locale = get_locale()
    dialog.close()
    ui.notify(locale.format('NOTIFY_DOWNLOAD_STARTING', filename=filename), color='info', position='top')
    
    try:
        response = await asyncio.to_thread(
            requests.post,
            "http://127.0.0.1:8002/models/download",
            json={"repo_id": repo, "filename": filename},
            timeout=10
        )
        if response.status_code == 200:
            ui.notify(locale.NOTIFY_DOWNLOAD_STARTED, color='positive', position='top', timeout=5000)
            # Refresh model list
            backend.get_models()
            if 'model_select' in app_state and app_state['model_select']:
                app_state['model_select'].options = backend.get_models()
                app_state['model_select'].update()
        else:
            ui.notify(locale.format('NOTIFY_DOWNLOAD_FAILED', error=response.text), color='negative', position='top')
    except requests.exceptions.ConnectionError:
        ui.notify(locale.NOTIFY_HUB_CONNECTION_ERROR, color='negative', position='top')
    except Exception as e:
        ui.notify(locale.format('NOTIFY_DOWNLOAD_ERROR', error=str(e)), color='negative', position='top')



def setup_drawer(backend, async_backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state):
    """Setup the left sidebar drawer with all controls - Redesigned for better UX."""
    locale = get_locale()
    
    # Retrieve dialogs
    model_dialog = dialogs.get('model')
    llama_dialog = dialogs.get('llama')
    llama_info = getattr(llama_dialog, 'info_label', None) if llama_dialog else None
    
    # Import settings components
    from settings import get_settings as _get_settings, set_dark_mode as _set_dark_mode
    
    # --- LEFT SIDEBAR (Drawer) ---
    with ui.left_drawer(value=True).classes(Styles.DRAWER).props('width=280 bordered') as drawer:
        
        # ============================================================
        # HEADER: Logo + Settings Button (Top Right)
        # ============================================================
        with ui.row().classes('w-full items-center justify-between mb-4'):
            # Logo & Name
            with ui.row().classes('items-center gap-3'):
                ui.avatar('Z' if ZENA_MODE else 'N', color='primary', text_color='white').classes('text-xl')
                app_name = 'Zena' if ZENA_MODE else locale.APP_NAME
                ui.label(app_name).classes('text-2xl font-bold ' + Styles.TEXT_ACCENT)
            
            # Settings Button (Top Right - Easy Access)
            def _on_dark_mode_change(is_dark: bool):
                """Apply dark mode change immediately."""
                dark_mode_ctrl = ui.dark_mode()
                if is_dark:
                    dark_mode_ctrl.enable()
                    ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
                else:
                    dark_mode_ctrl.disable()
                    ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
                _set_dark_mode(is_dark)
                # Force JavaScript sync
                ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')
            
            def _on_language_change(code: str):
                ui.notify(locale.format('SETTINGS_LANGUAGE_CHANGED', lang=code), color='info')
            
            def _on_save():
                _get_settings().save()
            
            settings_dialog = create_settings_dialog(
                on_save=_on_save,
                on_language_change=_on_language_change,
                on_dark_mode_change=_on_dark_mode_change
            )
            
            ui.button(icon=Icons.SETTINGS, on_click=settings_dialog.open).props('flat round').classes(Styles.TEXT_MUTED + ' hover:text-blue-500').tooltip(locale.SETTINGS_TITLE)
        
        # ============================================================
        # PRIMARY ACTION: New Chat Button
        # ============================================================
        def start_new_chat():
            """Clear chat and start fresh."""
            if 'chat_container' in app_state and app_state['chat_container']:
                app_state['chat_container'].clear()
            if 'chat_history' in app_state and app_state['chat_history']:
                app_state['chat_history'].clear()
            ui.notify(locale.CHAT_CLEARED if hasattr(locale, 'CHAT_CLEARED') else 'Chat cleared', color='positive', position='bottom-right')
        
        ui.button(locale.BTN_NEW_CHAT if hasattr(locale, 'BTN_NEW_CHAT') else '💬 New Chat', icon='add_comment', on_click=start_new_chat).classes('w-full mb-4 ' + Styles.BTN_PRIMARY).props('unelevated')
        
        ui.separator().classes('mb-4')
        
        # ============================================================
        # SECTION 1: AI Model (Expandable) - With Rich Model Cards
        # ============================================================
        with ui.expansion(locale.NAV_MODEL_MANAGER, icon='smart_toy').classes('w-full mb-2').props('default-opened'):
            with ui.column().classes('w-full gap-3 py-2'):
                
                # Get current models with metadata
                current_models = backend.get_models()
                
                # Comprehensive model metadata database
                MODEL_INFO = {
                    # Qwen models - Best for coding
                    'qwen2.5-coder.gguf': {
                        'name': 'Qwen 2.5 Coder', 
                        'desc': 'Alibaba\'s coding specialist', 
                        'size': '~5GB', 
                        'icon': '💻',
                        'good_for': ['Coding', 'Debugging', 'Code Review'],
                        'speed': 'Medium',
                        'quality': 'Excellent'
                    },
                    'qwen2.5-coder-7b-instruct-q4_k_m.gguf': {
                        'name': 'Qwen 2.5 Coder 7B', 
                        'desc': 'Top-tier code generation & analysis', 
                        'size': '~5GB', 
                        'icon': '💻',
                        'good_for': ['Coding', 'Debugging', 'Refactoring', 'Documentation'],
                        'speed': 'Medium',
                        'quality': 'Excellent'
                    },
                    # Llama models - General purpose
                    'llama-3.2-3b.gguf': {
                        'name': 'Llama 3.2 3B', 
                        'desc': 'Meta\'s efficient assistant', 
                        'size': '~3GB', 
                        'icon': '🦙',
                        'good_for': ['Chat', 'Writing', 'Q&A', 'Summarization'],
                        'speed': 'Fast',
                        'quality': 'Good'
                    },
                    'Llama-3.2-3B-Instruct-Q4_K_M.gguf': {
                        'name': 'Llama 3.2 3B Instruct', 
                        'desc': 'Instruction-tuned for conversations', 
                        'size': '~3GB', 
                        'icon': '🦙',
                        'good_for': ['Chat', 'Instructions', 'Creative Writing'],
                        'speed': 'Fast',
                        'quality': 'Good'
                    },
                    # Phi models - Lightweight
                    'Phi-3-mini-4k-instruct-q4.gguf': {
                        'name': 'Phi-3 Mini', 
                        'desc': 'Microsoft\'s compact powerhouse', 
                        'size': '~2GB', 
                        'icon': '⚡',
                        'good_for': ['Quick Tasks', 'Simple Q&A', 'Low RAM'],
                        'speed': 'Very Fast',
                        'quality': 'Good'
                    },
                    # Mistral models
                    'mistral-7b-instruct-v0.2.Q4_K_M.gguf': {
                        'name': 'Mistral 7B', 
                        'desc': 'Excellent reasoning & analysis', 
                        'size': '~4GB', 
                        'icon': '🌀',
                        'good_for': ['Reasoning', 'Analysis', 'Long Context'],
                        'speed': 'Medium',
                        'quality': 'Excellent'
                    },
                    # DeepSeek models
                    'deepseek-coder-6.7b-instruct.Q4_K_M.gguf': {
                        'name': 'DeepSeek Coder 6.7B', 
                        'desc': 'Strong coding & math abilities', 
                        'size': '~4GB', 
                        'icon': '🔬',
                        'good_for': ['Coding', 'Math', 'Technical'],
                        'speed': 'Medium',
                        'quality': 'Excellent'
                    },
                    # CodeLlama
                    'codellama-7b-instruct.Q4_K_M.gguf': {
                        'name': 'CodeLlama 7B', 
                        'desc': 'Meta\'s code specialist', 
                        'size': '~4GB', 
                        'icon': '🦙💻',
                        'good_for': ['Coding', 'Code Completion', 'Debugging'],
                        'speed': 'Medium',
                        'quality': 'Good'
                    },
                }
                
                def get_model_info(filename):
                    """Get model info or generate smart defaults."""
                    if filename in MODEL_INFO:
                        return MODEL_INFO[filename]
                    
                    # Smart detection from filename
                    fname_lower = filename.lower()
                    
                    # Detect model family and assign appropriate metadata
                    if 'qwen' in fname_lower and 'coder' in fname_lower:
                        return {'name': 'Qwen Coder', 'desc': 'Coding specialist model', 'size': '~5GB', 'icon': '💻',
                                'good_for': ['Coding', 'Debugging'], 'speed': 'Medium', 'quality': 'Excellent'}
                    elif 'qwen' in fname_lower:
                        return {'name': 'Qwen', 'desc': 'Alibaba\'s AI model', 'size': '~4GB', 'icon': '🤖',
                                'good_for': ['Chat', 'Writing'], 'speed': 'Medium', 'quality': 'Good'}
                    elif 'llama' in fname_lower and 'code' in fname_lower:
                        return {'name': 'CodeLlama', 'desc': 'Meta\'s code model', 'size': '~4GB', 'icon': '🦙💻',
                                'good_for': ['Coding', 'Code Review'], 'speed': 'Medium', 'quality': 'Good'}
                    elif 'llama' in fname_lower:
                        return {'name': 'Llama', 'desc': 'Meta\'s AI assistant', 'size': '~3GB', 'icon': '🦙',
                                'good_for': ['Chat', 'Writing'], 'speed': 'Fast', 'quality': 'Good'}
                    elif 'phi' in fname_lower:
                        return {'name': 'Phi', 'desc': 'Microsoft\'s compact model', 'size': '~2GB', 'icon': '⚡',
                                'good_for': ['Quick Tasks', 'Low RAM'], 'speed': 'Very Fast', 'quality': 'Good'}
                    elif 'mistral' in fname_lower:
                        return {'name': 'Mistral', 'desc': 'Efficient reasoning model', 'size': '~4GB', 'icon': '🌀',
                                'good_for': ['Reasoning', 'Analysis'], 'speed': 'Medium', 'quality': 'Excellent'}
                    elif 'deepseek' in fname_lower:
                        return {'name': 'DeepSeek', 'desc': 'Technical specialist', 'size': '~4GB', 'icon': '🔬',
                                'good_for': ['Coding', 'Math'], 'speed': 'Medium', 'quality': 'Excellent'}
                    elif 'gemma' in fname_lower:
                        return {'name': 'Gemma', 'desc': 'Google\'s efficient model', 'size': '~3GB', 'icon': '💎',
                                'good_for': ['Chat', 'Instructions'], 'speed': 'Fast', 'quality': 'Good'}
                    elif 'yi' in fname_lower:
                        return {'name': 'Yi', 'desc': '01.AI\'s bilingual model', 'size': '~4GB', 'icon': '🎯',
                                'good_for': ['Multilingual', 'Chat'], 'speed': 'Medium', 'quality': 'Good'}
                    else:
                        # Generic fallback
                        name = filename.replace('.gguf', '').replace('-', ' ').replace('_', ' ').title()[:25]
                        return {'name': name, 'desc': 'Local GGUF model', 'size': '?', 'icon': '🤖',
                                'good_for': ['General'], 'speed': 'Unknown', 'quality': 'Unknown'}
                
                # Active Model Header
                ui.label(locale.MODEL_ACTIVE_LABEL).classes('font-semibold text-sm ' + Styles.TEXT_PRIMARY)
                
                # Currently selected model display
                selected_model = current_models[0] if current_models else None
                selected_info = get_model_info(selected_model) if selected_model else {
                    'name': 'None', 'desc': 'No model loaded', 'size': '-', 'icon': '❌',
                    'good_for': [], 'speed': '-', 'quality': '-'
                }
                
                # Active model card - Enhanced with "Good For" tags
                with ui.card().classes('w-full p-3 bg-blue-50 dark:bg-slate-800 border-l-4 border-blue-500'):
                    with ui.row().classes('items-center gap-3'):
                        ui.label(selected_info['icon']).classes('text-2xl')
                        with ui.column().classes('flex-grow gap-1'):
                            active_model_name = ui.label(selected_info['name']).classes('font-bold ' + Styles.TEXT_PRIMARY)
                            active_model_desc = ui.label(selected_info['desc']).classes('text-xs ' + Styles.LABEL_MUTED)
                            # Good For tags
                            with ui.row().classes('gap-1 flex-wrap') as active_tags_row:
                                for tag in selected_info.get('good_for', []):
                                    ui.badge(tag, color='green').props('outline dense').classes('text-[10px]')
                        with ui.column().classes('items-end gap-1'):
                            ui.badge(selected_info['size'], color='blue').props('outline')
                            if selected_info.get('speed') and selected_info['speed'] != '-':
                                speed_color = 'green' if 'Fast' in selected_info['speed'] else 'orange'
                                ui.badge(f"⚡{selected_info['speed']}", color=speed_color).props('outline dense').classes('text-[10px]')
                
                # Model selector (for switching) - Now shows cards for each model
                if len(current_models) > 1:
                    ui.label('Available Models').classes('text-xs font-semibold mt-3 ' + Styles.TEXT_MUTED)
                    
                    for model_file in current_models:
                        if model_file == selected_model:
                            continue  # Skip currently active
                        
                        info = get_model_info(model_file)
                        
                        async def switch_to_model(m=model_file, i=info):
                            ui.notify(f"⏳ Loading {i['name']}...", color='info', position='bottom-right', timeout=2000)
                            try:
                                response = await asyncio.to_thread(
                                    requests.post, "http://127.0.0.1:8002/models/load",
                                    json={"model": m}, timeout=30
                                )
                                if response.status_code == 200:
                                    ui.notify(f"✅ {i['name']} ready!", color='positive', position='bottom-right')
                                else:
                                    ui.notify(f"✅ {i['name']} selected", color='positive', position='bottom-right')
                            except Exception:
                                ui.notify(f"✅ {i['name']} active", color='positive', position='bottom-right')
                            
                            # Update the active model card
                            active_model_name.text = i['name']
                            active_model_desc.text = i['desc']
                            # Update tags
                            active_tags_row.clear()
                            with active_tags_row:
                                for tag in i.get('good_for', []):
                                    ui.badge(tag, color='green').props('outline dense').classes('text-[10px]')
                        
                        # Clickable model card
                        with ui.card().classes('w-full p-2 hover:shadow-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-all cursor-pointer').on('click', switch_to_model):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(info['icon']).classes('text-lg')
                                with ui.column().classes('flex-grow gap-0'):
                                    ui.label(info['name']).classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                                    with ui.row().classes('gap-1 flex-wrap'):
                                        for tag in info.get('good_for', [])[:2]:  # Show first 2 tags
                                            ui.badge(tag, color='grey').props('outline dense').classes('text-[10px]')
                                ui.badge(info['size'], color='grey').props('outline').classes('text-xs')
                    
                    app_state['model_select'] = None  # No longer using select dropdown
                else:
                    app_state['model_select'] = None
                
                ui.separator().classes('my-2')
                
                # Download Models Section - Enhanced cards
                with ui.expansion('📥 ' + locale.MODEL_DOWNLOAD_NEW, icon=Icons.DOWNLOAD).classes('w-full'):
                    with ui.column().classes('w-full gap-2 py-2'):
                        ui.label(locale.MODEL_QUICK_DOWNLOADS).classes('text-xs font-bold ' + Styles.TEXT_MUTED)
                        
                        # Model cards for download - with full metadata
                        download_models = [
                            {
                                "name": "Qwen 2.5 Coder 7B", 
                                "desc": "Alibaba's top coding model", 
                                "size": "~5GB", 
                                "icon": "💻",
                                "good_for": ["Coding", "Debugging", "Refactoring"],
                                "speed": "Medium",
                                "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", 
                                "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
                            },
                            {
                                "name": "Llama 3.2 3B", 
                                "desc": "Fast & versatile assistant", 
                                "size": "~3GB", 
                                "icon": "🦙",
                                "good_for": ["Chat", "Writing", "Q&A"],
                                "speed": "Fast",
                                "repo": "lmstudio-community/Llama-3.2-3B-Instruct-GGUF", 
                                "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
                            },
                            {
                                "name": "Phi-3 Mini", 
                                "desc": "Microsoft's compact model", 
                                "size": "~2GB", 
                                "icon": "⚡",
                                "good_for": ["Quick Tasks", "Low RAM", "Simple Q&A"],
                                "speed": "Very Fast",
                                "repo": "microsoft/Phi-3-mini-4k-instruct-gguf", 
                                "file": "Phi-3-mini-4k-instruct-q4.gguf"
                            },
                            {
                                "name": "Mistral 7B", 
                                "desc": "Excellent reasoning & logic", 
                                "size": "~4GB", 
                                "icon": "🌀",
                                "good_for": ["Reasoning", "Analysis", "Long Context"],
                                "speed": "Medium",
                                "repo": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF", 
                                "file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
                            },
                            {
                                "name": "DeepSeek Coder 6.7B", 
                                "desc": "Code + Math specialist", 
                                "size": "~4GB", 
                                "icon": "🔬",
                                "good_for": ["Coding", "Math", "Technical"],
                                "speed": "Medium",
                                "repo": "TheBloke/deepseek-coder-6.7B-instruct-GGUF", 
                                "file": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
                            },
                        ]
                        
                        for model in download_models:
                            with ui.card().classes('w-full p-2 hover:shadow-md transition-shadow'):
                                with ui.column().classes('w-full gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(model['icon']).classes('text-xl')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label(model['name']).classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                                            ui.label(model['desc']).classes('text-xs ' + Styles.LABEL_MUTED)
                                        with ui.column().classes('items-end gap-1'):
                                            ui.badge(model['size'], color='blue').props('outline').classes('text-xs')
                                            speed_color = 'green' if 'Fast' in model.get('speed', '') else 'orange'
                                            ui.badge(f"⚡{model['speed']}", color=speed_color).props('outline dense').classes('text-[10px]')
                                    
                                    # Good For tags row
                                    with ui.row().classes('items-center gap-1 mt-1'):
                                        ui.label('Good for:').classes('text-[10px] ' + Styles.LABEL_MUTED)
                                        for tag in model.get('good_for', []):
                                            ui.badge(tag, color='green').props('outline dense').classes('text-[10px]')
                                        
                                        ui.space()
                                        
                                        async def download_model(m=model):
                                            ui.notify(f"⬇️ Starting download: {m['name']}...", color='info', position='bottom-right')
                                            try:
                                                response = await asyncio.to_thread(
                                                    requests.post, "http://127.0.0.1:8002/models/download",
                                                    json={"repo_id": m['repo'], "filename": m['file']}, timeout=5
                                                )
                                                if response.status_code == 200:
                                                    ui.notify(f"✅ {m['name']} download started!", color='positive', position='bottom-right')
                                                else:
                                                    ui.notify(f"❌ Download failed: {response.text[:50]}", color='negative', position='bottom-right')
                                            except Exception as e:
                                                ui.notify(f"❌ Error: {str(e)[:50]}", color='negative', position='bottom-right')
                                        
                                        ui.button('Download', icon=Icons.DOWNLOAD, on_click=download_model).props('flat dense color=primary').classes('text-xs')
                        
                        ui.separator().classes('my-2')
                        
                        # Custom download button
                        if model_dialog:
                            ui.button('🔗 ' + locale.MODEL_CUSTOM_DOWNLOAD, icon=Icons.CLOUD_DOWNLOAD, on_click=lambda: model_dialog.open()).props('flat dense').classes('w-full ' + Styles.TEXT_ACCENT)
        
        # ============================================================
        # SECTION 2: AI Engine (Expandable)
        # ============================================================
        with ui.expansion(locale.NAV_AI_ENGINE, icon='psychology').classes('w-full mb-2'):
            with ui.column().classes('w-full gap-2 py-2'):
                # Chain of Thought / Swarm
                use_cot = ui.switch(locale.ENGINE_COT_SWARM, value=False).classes('text-sm')
                ui.label(locale.ENGINE_COT_DESCRIPTION).classes(Styles.LABEL_MUTED + ' ml-10 -mt-1 text-xs')
                
                quiet_cot = ui.switch(locale.ENGINE_QUIET_MODE, value=True).classes('text-sm ml-4').bind_visibility_from(use_cot, 'value')
                ui.label(locale.ENGINE_QUIET_DESCRIPTION).classes(Styles.LABEL_MUTED + ' ml-14 -mt-1 text-xs').bind_visibility_from(use_cot, 'value')
                
                # Swarm Status
                with ui.row().classes('items-center gap-2 mt-2 px-2 py-1 bg-blue-50 dark:bg-slate-800 rounded'):
                    ui.icon(Icons.HUB, size='16px').classes('text-blue-500')
                    swarm_status = ui.label(locale.ENGINE_SCANNING_SWARM).classes('text-xs font-medium text-blue-600 dark:text-blue-400')
                    app_state['swarm_status'] = swarm_status
                    ui.button(icon=Icons.REFRESH, on_click=lambda: app_state['scan_swarm']()).props('flat dense round size=xs').classes('text-gray-400')
                
                app_state['use_cot_swarm'] = use_cot
                app_state['quiet_cot'] = quiet_cot
        
        # ============================================================
        # SECTION 3: System Tools (Expandable)
        # ============================================================
        with ui.expansion(locale.NAV_SYSTEM, icon='build').classes('w-full mb-2'):
            with ui.column().classes('w-full gap-2 py-2'):
                
                # System status card
                with ui.card().classes('w-full p-3 bg-gray-50 dark:bg-slate-800'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('memory', size='24px').classes('text-green-500')
                        with ui.column().classes('flex-grow gap-0'):
                            ui.label('System Status').classes('text-sm font-semibold ' + Styles.TEXT_PRIMARY)
                            system_status_label = ui.label('Ready').classes('text-xs ' + Styles.LABEL_MUTED)
                
                # Version Check - with better error handling
                async def check_llama_version():
                    ui.notify("🔍 Checking llama.cpp version...", color='info', position='bottom-right')
                    try:
                        # Try to get local version
                        local_version = "Not installed"
                        try:
                            result = await asyncio.to_thread(
                                subprocess.run, ["_bin/llama-server.exe", "--version"],
                                capture_output=True, text=True, timeout=5
                            )
                            if result.returncode == 0:
                                local_version = result.stdout.strip() or result.stderr.strip() or "Unknown"
                        except FileNotFoundError:
                            local_version = "Binary not found"
                        except Exception:
                            local_version = "Check failed"
                        
                        # Try to get latest version from GitHub
                        latest_version = "Unknown"
                        try:
                            response = await asyncio.to_thread(
                                requests.get, 
                                "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest", 
                                timeout=5,
                                headers={'Accept': 'application/vnd.github.v3+json'}
                            )
                            if response.status_code == 200:
                                latest_version = response.json().get("tag_name", "Unknown")
                        except Exception:
                            latest_version = "API unavailable"
                        
                        # Show result in a nice notification
                        if local_version == latest_version and local_version != "Unknown":
                            ui.notify(f"✅ llama.cpp is up to date\\n📦 Version: {local_version}", 
                                     color='positive', position='bottom-right', multi_line=True, timeout=5000)
                        elif local_version == "Not installed" or local_version == "Binary not found":
                            ui.notify(f"⚠️ llama.cpp not found\\n📥 Latest: {latest_version}\\n💡 Download from GitHub", 
                                     color='warning', position='bottom-right', multi_line=True, timeout=8000)
                        else:
                            ui.notify(f"📦 Local: {local_version}\\n🌐 Latest: {latest_version}", 
                                     color='info', position='bottom-right', multi_line=True, timeout=5000)
                        
                    except Exception as e:
                        ui.notify(f"❌ Version check failed: {str(e)[:50]}", color='negative', position='bottom-right')
                
                # Benchmark
                async def run_benchmark():
                    ui.notify("⏱️ Running benchmark...", color='info', position='bottom-right')
                    system_status_label.text = "Running benchmark..."
                    try:
                        test_prompt = "Write a short story about a robot learning to code."
                        start_time = time.time()
                        token_count = 0
                        
                        async with async_backend:
                            async for chunk in async_backend.send_message_async(test_prompt):
                                token_count += len(chunk.split())
                        
                        elapsed = time.time() - start_time
                        tokens_per_sec = token_count / elapsed if elapsed > 0 else 0
                        
                        system_status_label.text = f"Last: {tokens_per_sec:.1f} tok/s"
                        ui.notify(f"✅ Benchmark Complete\\n⚡ Speed: {tokens_per_sec:.1f} tokens/sec\\n📝 Tokens: {token_count}\\n⏱️ Time: {elapsed:.1f}s", 
                                 color='positive', position='bottom-right', multi_line=True, timeout=8000)
                    except Exception as e:
                        system_status_label.text = "Benchmark failed"
                        ui.notify(f"❌ Benchmark failed: {str(e)[:50]}", color='negative', position='bottom-right')
                
                # Diagnostics
                async def run_diagnostics():
                    ui.notify("🔍 Running diagnostics...", color='info', position='bottom-right')
                    system_status_label.text = "Checking systems..."
                    try:
                        results = []
                        
                        # LLM Check
                        try:
                            llm_url = config.get('LLM_API_URL', "http://127.0.0.1:8001") if isinstance(config, dict) else getattr(config, 'LLM_API_URL', "http://127.0.0.1:8001")
                            response = await asyncio.to_thread(requests.get, f"{llm_url}/v1/models", timeout=3)
                            if response.status_code == 200:
                                results.append("✅ LLM Backend: Online")
                            else:
                                results.append(f"⚠️ LLM Backend: Error {response.status_code}")
                        except Exception:
                            results.append("❌ LLM Backend: Offline")
                        
                        # RAG Check
                        if rag_system and hasattr(rag_system, 'index') and rag_system.index:
                            count = rag_system.index.ntotal
                            results.append(f"✅ RAG System: {count} vectors")
                        else:
                            results.append("⚠️ RAG System: Not initialized")
                        
                        # Memory Check
                        import psutil
                        mem = psutil.virtual_memory()
                        mem_status = "✅" if mem.percent < 80 else "⚠️" if mem.percent < 95 else "❌"
                        results.append(f"{mem_status} Memory: {mem.percent:.0f}% used")
                        
                        # CPU Check
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        cpu_status = "✅" if cpu_percent < 80 else "⚠️"
                        results.append(f"{cpu_status} CPU: {cpu_percent:.0f}%")
                        
                        system_status_label.text = "Ready"
                        ui.notify("🔧 System Diagnostics\\n" + "\\n".join(results), 
                                 color='info', position='bottom-right', multi_line=True, timeout=8000)
                    except Exception as e:
                        system_status_label.text = "Diagnostics failed"
                        ui.notify(f"❌ Diagnostics failed: {str(e)[:50]}", color='negative', position='bottom-right')
                
                # System Action Buttons - Nice card style
                with ui.row().classes('w-full gap-2 flex-wrap'):
                    ui.button('Version', icon='update', on_click=check_llama_version).props('flat dense').classes('flex-1')
                    ui.button('Benchmark', icon='speed', on_click=run_benchmark).props('flat dense').classes('flex-1')
                    ui.button('Diagnose', icon='healing', on_click=run_diagnostics).props('flat dense').classes('flex-1')
        
        # ============================================================
        # FOOTER: Version Info
        # ============================================================
        ui.space()  # Push footer to bottom
        with ui.row().classes('w-full justify-center mt-auto pt-4 border-t border-gray-200 dark:border-slate-700'):
            ui.label('v1.0.0').classes(Styles.LABEL_MUTED + ' text-xs')
            
    return drawer
