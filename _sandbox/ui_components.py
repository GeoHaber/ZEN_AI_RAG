from nicegui import ui
import logging
import asyncio
import requests
import httpx
import subprocess
from utils import normalize_input
import time

# Import localization and UI modules
from locales import get_locale, L
from ui import Styles, Icons, Formatters
from ui.theme import Theme, Colors
from ui.settings_dialog import create_settings_dialog
from ui_state import UIState
from zena_mode.resource_manager import resource_manager
from zena_mode.batch_manager import batch_manager


def get_model_info(filename: str) -> dict:
    """Helper to determine model metadata from filename."""
    if not filename:
        return {'name': 'None', 'desc': 'No model loaded', 'size': '-', 'icon': '❌', 
                'good_for': [], 'speed': '-', 'quality': '-'}
    
    fname_lower = filename.lower()
    if 'llama' in fname_lower:
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

logger = logging.getLogger("UI Components")

async def _on_smart_routing_change(enabled: bool, router):
    """Event handler for smart routing toggle (Module Level)."""
    if enabled and router:
        logger.info("[Router] Initializing Smart Router...")
        return await router.initialize()
    return enabled

def setup_app_theme():
    """Configures the application theme, colors, and CSS."""
    # Theme & Layout (ZenAI Style - Light & Professional)
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
            /* Dynamic animated background */
            @keyframes mesh {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            body, .q-page-container {
                background: #f8fafc;
            }
            .body--dark, .body--dark .q-page-container {
                background-color: #0b0f19;
                background-image: radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.1) 0px, transparent 50%),
                                  radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.1) 0px, transparent 50%),
                                  radial-gradient(at 100% 100%, rgba(56, 189, 248, 0.1) 0px, transparent 50%),
                                  radial-gradient(at 0% 100%, rgba(139, 92, 246, 0.1) 0px, transparent 50%);
                background-attachment: fixed;
            }
            
            /* Glassmorphism Utilities */
            .glass {
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
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
                            # Basic filename safety check
                            try:
                                from security import FileValidator
                                if FileValidator.is_path_traversal(filename):
                                    ui.notify(locale.NOTIFY_INVALID_FILENAME if hasattr(locale, 'NOTIFY_INVALID_FILENAME') else "Invalid filename", color='negative')
                                    return
                            except Exception:
                                pass

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
                try:
                    resource_manager.add_worker_thread(lambda: subprocess.Popen(["explorer", "https://github.com/ggerganov/llama.cpp/releases/latest"]), daemon=True, max_workers=4)
                except Exception:
                    # Fallback to launching in background thread via asyncio
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
        success = await backend.download_model(repo, filename)
        if success:
            ui.notify(locale.NOTIFY_DOWNLOAD_STARTED, color='positive', position='top', timeout=5000)
            # Refresh model list
            models = await backend.get_models()
            try:
                # If app_state is a UIState wrapper, use its atomic updater
                if hasattr(app_state, 'update_model_options'):
                    app_state.update_model_options(models)
                elif 'model_select' in app_state and app_state['model_select']:
                    app_state['model_select'].options = models
                    if hasattr(app_state['model_select'], 'update'):
                        app_state['model_select'].update()
            except Exception:
                # Non-fatal: UI update failure shouldn't break download flow
                pass
        else:
            ui.notify(locale.format('NOTIFY_DOWNLOAD_FAILED', error="Start failed"), color='negative', position='top')
    except Exception as e:
        logger.error(f"[UI] Download error: {e}")
        ui.notify(locale.format('NOTIFY_DOWNLOAD_FAILED', error=str(e)), color='negative', position='top')
        ui.notify(locale.format('NOTIFY_DOWNLOAD_ERROR', error=str(e)), color='negative', position='top')



def setup_layout(backend, async_backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state):
    """
    Setup the Modern ZenAI Layout (Glass Header + Hidden Overlay Drawer).
    Replaces the old permanent sidebar.
    """
    locale = get_locale()
    ui_state = UIState(app_state)
    
    # Retrieve dialogs
    model_dialog = dialogs.get('model')
    llama_dialog = dialogs.get('llama')
    llama_info = getattr(llama_dialog, 'info_label', None) if llama_dialog else None
    
    from settings import get_settings as _get_settings, set_dark_mode as _set_dark_mode

    # --- 1. HIDDEN OVERLAY DRAWER (The "Engine Room") ---
    # Defaults to closed (value=False). Overlay behavior. Right side? No, left is standard.
    with ui.left_drawer(value=False).classes(Styles.DRAWER).props('overlay elevated behavioral=mobile') as drawer:
        # Drawer Header
        with ui.row().classes('w-full items-center justify-between mb-6'):
            ui.label(locale.SETTINGS_TITLE).classes('text-xl font-bold ' + Styles.TEXT_PRIMARY)
            ui.button(icon=Icons.CLOSE, on_click=drawer.close).props('flat round dense')
            
        # --- DRAWER CONTENT (Settings, Swarm, RAG) ---
        with ui.column().classes('w-full gap-4'):
             # New Chat (Also in Drawer for mobile access)
            def start_new_chat():
                ui_state.clear_chat()
                ui.notify(locale.CHAT_CLEARED, color='positive')
                drawer.close()

            ui.button(locale.BTN_NEW_CHAT, icon='add_comment', on_click=start_new_chat).classes('w-full ' + Styles.BTN_PRIMARY)
            
            ui.separator()
            
            # Dark Mode Toggle
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Dark Mode').classes(Styles.LABEL_SM)
                def _on_dark_mode_change(is_dark: bool):
                    dark_mode_ctrl = ui.dark_mode()
                    if is_dark:
                        dark_mode_ctrl.enable()
                        ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
                    else:
                        dark_mode_ctrl.disable()
                        ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
                    _set_dark_mode(is_dark)
                    ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')
                
                # Check current state
                is_dark = _get_settings().get('dark_mode', False)
                ui.switch(value=is_dark, on_change=lambda e: _on_dark_mode_change(e.value))

            # Settings Dialog Button
            def _on_save(): _get_settings().save()
            settings_dialog = create_settings_dialog(on_save=_on_save, on_language_change=lambda x: None, on_dark_mode_change=_on_dark_mode_change)
            ui.button(locale.SETTINGS_TITLE, icon=Icons.SETTINGS, on_click=settings_dialog.open).classes('w-full ' + Styles.BTN_SECONDARY)

    # --- 2. GLASS HEADER (The "Cockpit") ---
    # Fixed at top, glassmorphism
    with ui.header(elevated=False).classes('backdrop-blur-xl bg-white/80 dark:bg-[#0b0f19]/80 border-b border-gray-200 dark:border-white/5 h-[70px] flex items-center px-4 justify-between z-50'):
        
        # Left: Identity (Avatar + Name)
        with ui.row().classes('items-center gap-3 cursor-pointer').on('click', lambda: ui.notify("ZenAI Flow 1.0")):
            with ui.avatar('Z', color='blue-600', text_color='white').classes('shadow-lg shadow-blue-500/30'):
                ui.image('https://robohash.org/zenai?set=set4').classes('object-cover') if False else None # Placeholder
            
            with ui.column().classes('gap-0'):
                ui.label('ZenAI').classes('text-lg font-bold leading-none ' + Styles.TEXT_PRIMARY)
                ui.label('Flow State').classes('text-xs font-medium text-blue-500 dark:text-blue-400')

        # Right: Actions (New Chat, Batch, Menu)
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='add', on_click=start_new_chat).props('round flat').classes(Styles.BTN_GHOST + ' w-10 h-10').tooltip('New Chat')
            ui.button(icon='play_arrow', on_click=lambda: open_batch_modal()).props('round flat').classes(Styles.BTN_GHOST + ' w-10 h-10').tooltip('Batch Jobs')
            ui.button(icon='menu', on_click=drawer.toggle).props('round flat').classes(Styles.BTN_GHOST + ' w-10 h-10').tooltip('Menu')

# =============================================================================
# ZENAI FLOW COMPONENTS
# =============================================================================

class LivingLogo:
    """
    A state-aware logo component.
    States: 'idle', 'thinking', 'speaking'
    """
    def __init__(self):
        self.state = 'idle'
        self.container = None
        self._build()

    def _build(self):
        # Base container with transition
        self.container = ui.element('div').classes(
            'w-10 h-10 rounded-full flex items-center justify-center '
            'text-white font-bold cursor-pointer shadow-lg transition-all duration-500 ease-in-out'
        )
        self.container.text = 'Z'
        self._update_style()
        
    def set_state(self, new_state: str):
        if new_state != self.state:
            self.state = new_state
            self._update_style()

    def _update_style(self):
        # Reset base
        base_classes = 'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold cursor-pointer shadow-lg transition-all duration-500 ease-in-out '
        
        if self.state == 'idle':
            # Blue-Violet Gradient, Soft Glow
            self.container.classes(replace=base_classes + 'bg-gradient-to-br from-blue-600 to-violet-600 shadow-blue-500/30 hover:shadow-blue-500/50')
            self.container.style('transform: scale(1); animation: none;')
            
        elif self.state == 'thinking':
            # Pulsing Fast, Bright
            self.container.classes(replace=base_classes + 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-cyan-400/50')
            self.container.style('animation: spin 3s linear infinite;')
            
        elif self.state == 'speaking':
            # Green-Emerald, Active
            self.container.classes(replace=base_classes + 'bg-gradient-to-br from-emerald-500 to-green-600 shadow-emerald-500/40')
            self.container.style('animation: bounce 1s infinite;')


class SmartChips:
    """
    Context-aware suggestion chips.
    """
    def __init__(self, on_click):
        self.on_click = on_click
        self.current_context = 'default'
        self.container = ui.row().classes('gap-2 justify-center mb-2 w-full transition-opacity duration-300')
        self.render()

    def update_context(self, context: str):
        if self.current_context != context:
            self.current_context = context
            self.render()

    def render(self):
        self.container.clear()
        
        suggestions = []
        if self.current_context == 'default':
            suggestions = ["Compare models", "Help me code", "Summarize text"]
        elif self.current_context == 'coding':
            suggestions = ["Refactor this", "Add comments", "Find bugs", "Write tests"]
        elif self.current_context == 'writing':
            suggestions = ["Fix grammar", "Make it professional", "Shorten this"]
            
        with self.container:
            for text in suggestions:
                ui.button(text, on_click=lambda t=text: self.on_click(t)) \
                    .props('rounded flat dense no-caps') \
                    .classes('bg-white/50 dark:bg-slate-800/50 backdrop-blur-md border border-gray-200 dark:border-white/10 text-xs text-gray-700 dark:text-gray-300 hover:bg-white/80 dark:hover:bg-slate-700/80 transition-all')


class GlassCapsule:
    """
    The floating input cockpit.
    Contains: Input, Voice, Attach, Send
    """
    def __init__(self, on_send):
        self.on_send = on_send
        self.text_value = ""
        self.input_element = None
        self._build()

    def _build(self):
        # Floating Capsule Container
        with ui.card().classes('w-full max-w-4xl mx-auto rounded-full glass shadow-2xl border border-white/20 dark:border-white/5 p-1 flex items-center gap-2 relative z-50 transition-all duration-300 focus-within:ring-2 ring-blue-500/30'):
            
            # 1. Attachment Button (Left)
            ui.button(icon='attach_file', on_click=lambda: ui.notify('Attachments coming soon')) \
                .props('round flat dense').classes('text-gray-500 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-white/10 transition-colors h-10 w-10')

            # 2. Input Field (Center - Transparent)
            with ui.row().classes('flex-grow relative'):
                self.input_element = ui.input(placeholder='Message ZenAI...').props('borderless dense autogrow').classes('w-full text-lg px-2 text-gray-900 dark:text-gray-100 placeholder-gray-400') \
                    .on('keydown.enter.prevent', self.handle_send)
                # Bind value manually or via property if needed
                
            # 3. Voice Button (Right)
            ui.button(icon='mic') \
                .props('round flat dense').classes('text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-white/10 transition-colors h-10 w-10')

            # 4. Send Button (Right - Action)
            ui.button(icon='arrow_upward', on_click=self.handle_send) \
                .props('round flat dense').classes('bg-blue-600 text-white hover:bg-blue-700 shadow-md h-10 w-10 transition-transform active:scale-95')

    def handle_send(self):
        text = self.input_element.value
        if text and text.strip():
            self.on_send(text)
            self.input_element.value = ""
            self.input_element.run_method('focus')
