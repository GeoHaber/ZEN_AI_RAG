# -*- coding: utf-8 -*-
"""
zena.py - Zena AI Chat Interface
Elegant, professional chatbot with RAG capabilities
"""
import sys
import subprocess
import os
from pathlib import Path
import time
import traceback

# --- Global Crash Handler ---
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        with open("ui_fatal_crash.txt", "w", encoding='utf-8') as f:
            f.write(f"Timestamp: {time.ctime()}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except (OSError, IOError):
        pass  # Can't write crash log, silently continue

sys.excepthook = handle_exception
# -----------------------------

from nicegui import ui, app
import threading
import time
import logging
import os
import io
import asyncio
import json
import requests
import numpy as np
from pathlib import Path

# PDF Support
try:
    import pypdf
except ImportError:
    pypdf = None

# Import configuration and security
from config_system import config, EMOJI
from mock_backend import MockAsyncBackend
from security import FileValidator
from utils import format_message_with_attachment, normalize_input, sanitize_prompt, is_port_active
from locales import get_locale, L
from ui import Styles, Icons, Formatters
from ui.registry import UI_IDS
from ui.examples import EXAMPLES
from zena_mode.profiler import monitor
from zena_mode.help_system import index_internal_docs
from zena_mode.auto_updater import check_for_updates, get_local_version, ModelScout
from zena_mode.gateway_telegram import run_gateway as run_telegram_gateway
from zena_mode.gateway_whatsapp import run_whatsapp_gateway
from zena_mode.tutorial import start_tutorial

# Optional deps
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    # import pyttsx3 # Removed - using Piper for TTS
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    sd = wav = SentenceTransformer = None
pyttsx3 = None # Explicitly disabled

# Logging - output to BOTH file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('nebula_debug.log', mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Also print to console
    ]
)
logger = logging.getLogger("ZenAI")



# API URLs resolved from config
API_URL = config.get_api_url()

# Import async backend and arbitrator
from async_backend import AsyncZenAIBackend as async_backend
# Note: Legacy sync backend removed - all operations now async

# Load v3.1 Configuration Logic
ZENA_MODE = config.zena_mode_enabled
ZENA_CONFIG = {
    'enabled': config.zena_mode_enabled,
    'rag_enabled': True,
    'rag_source': 'knowledge_base',
    'swarm_enabled': config.swarm_enabled
}
logger.info(f"[Core] v3.1 Spec Initialization | Mode: {'Native' if ZENA_MODE else 'Legacy'} | Swarm: {config.swarm_enabled}")

# Initialize RAG if Zena mode enabled
rag_system = None
if ZENA_MODE:
    try:
        from zena_mode import LocalRAG, WebsiteScraper
        from zena_mode.universal_extractor import UniversalExtractor, DocumentType
        
        # Universal Extractor for PDF/Image OCR in chat
        universal_extractor = UniversalExtractor()
        logger.info("[RAG] Universal Extractor ready for OCR")

        rag_cache = config.BASE_DIR / "rag_cache"
        rag_cache.mkdir(exist_ok=True)

        # RAG system initialization
        rag_system = LocalRAG(cache_dir=rag_cache)
        # Default RAG to enabled in config if not present
        if 'rag_enabled' not in ZENA_CONFIG:
            ZENA_CONFIG['rag_enabled'] = True
        logger.info("[RAG] RAG system initialized")
    except Exception as e:
        logger.error(f"[RAG] Failed to initialize: {e}")

# Initialize Conversation Memory (separate from knowledge RAG)
conversation_memory = None
try:
    from zena_mode import ConversationMemory
    from pathlib import Path
    
    conv_cache = config.BASE_DIR / "conversation_cache"
    conv_cache.mkdir(exist_ok=True)
    
    conversation_memory = ConversationMemory(cache_dir=conv_cache)
    logger.info("[Memory] Conversation memory initialized")
except Exception as e:
    logger.error(f"[Memory] Failed to initialize conversation memory: {e}")

# Import state management
from state_management import attachment_state, chat_history, handle_error

# Import feature detection
from feature_detection import get_feature_detector, is_feature_available

# Initialize feature detector at startup
feature_detector = get_feature_detector()
logger.info("[Features] Feature detection complete")

# Import cleanup policy
from cleanup_policy import get_cleanup_policy

# Initialize cleanup policy for uploads directory
upload_cleanup = get_cleanup_policy(config.BASE_DIR / "uploads")
logger.info("[Cleanup] Upload cleanup policy initialized")

# Index internal documentation for Help System RAG
# This allows users to ask "how do I use ZenAI?" and get answers from docs
try:
    if rag_system:
        index_internal_docs(config.BASE_DIR, rag_system)
        logger.info("[HelpSystem] Internal documentation indexed for user assistance")
except Exception as e:
    logger.warning(f"[HelpSystem] Failed to index internal docs: {e}")


# --- Modular UI Imports ---
from ui.state import UIState
from ui.handlers import UIHandlers
from ui.layout import build_page
from ui_components import setup_app_theme, setup_common_dialogs, setup_drawer, setup_rag_dialog

# Cleanup Policy
from cleanup_policy import get_cleanup_policy
upload_cleanup = get_cleanup_policy(config.BASE_DIR / "uploads")

@ui.page('/')
async def nebula_page():
    # 1. Initialize State
    ui_state = UIState()
    import uuid
    ui_state.session_id = str(uuid.uuid4())[:8]
    logger.info(f"[Session] New client session: {ui_state.session_id}")

    # 2. Setup Theme & App State
    setup_app_theme()
    app_state = {
        'rag_enabled': ZENA_CONFIG.get('rag_enabled', True) if ZENA_MODE else False,
        'open_rag_dialog': lambda: rag_dialog.open() if 'rag_dialog' in locals() else None
    }

    # 3. Initialize Shared Services
    from async_backend import AsyncZenAIBackend
    backend = MockAsyncBackend() if "--mock" in sys.argv else AsyncZenAIBackend()
    
    # 4. Initialize Handlers
    handlers = UIHandlers(
        ui_state=ui_state,
        app_state=app_state,
        rag_system=rag_system,
        universal_extractor=universal_extractor,
        conversation_memory=conversation_memory,
        async_backend=backend
    )

    # 5. Build Page
    def on_language_change(code):
        from settings import get_settings
        ui.notify(f"Switching to {code}...", color='info')
        get_settings().save()
        ui.run_javascript('window.location.reload()')

    # Factories for modular components
    def dialog_factory():
        return setup_common_dialogs(
            backend, app_state, 
            on_language_change=on_language_change,
            on_dark_mode=lambda is_dark: update_theme(is_dark)
        )
    
    dialogs = dialog_factory()
    
    def rag_dialog_factory():
        return setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, get_locale(), rag_system, Styles)
    
    def drawer_factory():
        return setup_drawer(backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state)

    # Assemble Layout
    from ui.layout import build_page
    layout = build_page(ui_state, handlers, drawer_factory, rag_dialog_factory)
    header = layout['header']
    drawer = layout['drawer']
    
    # 6. Initialize Dark Mode
    from settings import is_dark_mode
    saved_dark_mode = is_dark_mode()
    dark_mode = ui.dark_mode(value=saved_dark_mode)

    def update_theme(is_dark: bool):
        if is_dark:
            header.props('dark'); drawer.props('dark')
            ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
        else:
            header.props(remove='dark'); drawer.props(remove='dark')
            ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
        ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')

    update_theme(saved_dark_mode)

    # 7. Background Tasks (Per-Client)
    asyncio.create_task(handlers.check_backend_health())

    # Periodic cleanup
    ui.timer(10.0, lambda: upload_cleanup.cleanup(), once=True)
    ui.timer(6 * 3600, lambda: upload_cleanup.cleanup())


# --- Background Workers Infrastructure ---
def start_background_gateways():
    """Launch messaging gateways in separate threads."""
    zena_config = config.get('zena_mode', {})
    if zena_config.get("telegram_token"):
        threading.Thread(target=run_telegram_gateway, daemon=True, name="TelegramBot").start()
    
    if zena_config.get("whatsapp_whitelist"): # Enabled via whitelist (E.164 numbers)
        threading.Thread(target=run_whatsapp_gateway, daemon=True, name="WhatsAppBot").start()

async def run_system_checks():
    """Perform background auto-update and model scout checks."""
    zena_config = config.get('zena_mode', {})
    if zena_config.get("auto_update_enabled", True):
        local_tag = await get_local_version()
        update_info = check_for_updates(current_tag=local_tag)
        if update_info:
            ui.notify(f"💎 Shiny new update available: {update_info['tag']}!", 
                      color='info', position='bottom-right')
        
        # Scouting for "Best in Class" models
        scout = ModelScout()
        coding_models = scout.find_shiny_models("coding")
        if coding_models:
             logger.info(f"[ModelScout] Found {len(coding_models)} shiny models on HF.")

@app.on_startup
async def on_startup():
    """Global startup triggers."""
    # Add hidden testing endpoint for Monkey Test
    from fastapi import Response
    @app.post("/test/click/{element_id}")
    async def test_click_element(element_id: str):
        """Simulate a click on a UI element for chaos testing."""
        logger.info(f"[Test] Simulating click on: {element_id}")
        try:
            # Broadcast click to all connected clients
            clients = app.clients
            if callable(clients):
                try: clients = clients()
                except TypeError: pass  # Not callable
            
            # Support both dict and list-like clients
            client_list = []
            if isinstance(clients, dict):
                client_list = list(clients.values())
            elif clients:
                try: client_list = list(clients)
                except (TypeError, ValueError): client_list = []

            for client in client_list:
                try:
                    client.run_javascript(f"document.getElementById('{element_id}')?.click()")
                except Exception as e:
                    logger.debug(f"[Test] Failed for client: {e}")
                    continue
            return Response(status_code=200)
        except Exception as e:
            logger.error(f"[Test] Click simulation failed: {e}")
            return Response(content=str(e), status_code=500)

    @app.get("/test/state")
    async def test_get_ui_state():
        """Retrieve a summary of the current UI state (text and visible components)."""
        # This uses JS to scrape visible text and active notifications/dialogs
        js_get_state = """
        (() => {
            const state = {
                visible_text: document.body.innerText.substring(0, 1000),
                active_dialogs: Array.from(document.querySelectorAll('.q-dialog--active')).length,
                notifications: Array.from(document.querySelectorAll('.q-notification')).map(n => n.innerText),
                current_url: window.location.href
            };
            return JSON.stringify(state);
        })()
        """
        # Note: NiceGUI run_javascript is not easily awaitable for results in this version
        # We will use a workaround: app.storage.client or just return a placeholder for now
        # Actually, let's keep it simple: the LLM will focus on the Logic of the Registry Metadata first.
        return {"active": True, "timestamp": time.time()}

    @app.post("/test/send")
    async def test_send_message(data: dict):
        """Simulate typing and sending a message for automated testing."""
        text = data.get("text", "")
        logger.info(f"[Test] Simulating send: {text}")
        try:
            # Broadcast to all clients (Super Robust)
            clients_obj = getattr(app, 'clients', None)
            
            client_list = []
            if clients_obj:
                if callable(clients_obj):
                    try: clients_obj = clients_obj()
                    except TypeError: pass  # Not callable
                
                if isinstance(clients_obj, dict):
                    client_list = list(clients_obj.values())
                elif isinstance(clients_obj, (list, set, tuple)):
                    client_list = list(clients_obj)
            
            # Fallback to NiceGUI globals if app.clients failed
            if not client_list:
                try:
                    from nicegui import globals as ng_globals
                    client_list = list(ng_globals.clients.values())
                except (ImportError, AttributeError, TypeError): pass  # NiceGUI internals unavailable

            logger.info(f"[Test] Broadasting to {len(client_list)} clients")
            
            for client in client_list:
                try:
                    js = f"""
                    (function() {{
                        const input = document.getElementById('ui-input-chat');
                        const btn = document.getElementById('ui-btn-send');
                        if (input) {{
                            input.value = {json.dumps(text)};
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            console.log('[Test] Input set to:', input.value);
                            if (btn) {{
                                setTimeout(() => {{
                                    console.log('[Test] Clicking send button');
                                    btn.click();
                                }}, 100);
                            }}
                        }}
                    }})();
                    """
                    client.run_javascript(js)
                except Exception as e:
                    logger.debug(f"[Test] Send failed for client: {e}")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"[Test] Send simulation failed: {e}")
            return Response(content=str(e), status_code=500)

    start_background_gateways()
    asyncio.create_task(run_system_checks())
    if ZENA_MODE and rag_system:
        from config_system import config as sys_config # Resolve naming conflict
        index_internal_docs(Path(sys_config.BASE_DIR), rag_system)

def start_app():
    """Entry point for NiceGUI application."""
    import sys
    from config_system import is_dark_mode
    from utils import ProcessManager
    
    # --- Zombie & Conflict Protection ---
    ui_port = getattr(config, 'ui_port', 8080)
    if is_port_active(ui_port):
        logger.warning(f"[!] Port {ui_port} is already active. Pruning existing UI...")
        if not ProcessManager.prune(ports=[ui_port], auto_confirm=True):
             logger.error(f"[!] Could not clear port {ui_port}. Startup may fail.")
    
    # Check for port conflicts and handle "Zombie junk"
    if not os.environ.get("ZENA_SKIP_PRUNE"):
        if not ProcessManager.prune(auto_confirm=True):
            print("[!] Startup cancelled due to port conflict.")
            sys.exit(0)
    
    # --- Fix 1: NICEGUI_SCREEN_TEST_PORT KeyError ---
    if 'NICEGUI_SCREEN_TEST_PORT' not in os.environ:
        os.environ['NICEGUI_SCREEN_TEST_PORT'] = '8081'

    # --- Fix 2: pyttsx3 AttributeError on exit (Handled by removal) ---
    pass

    # Use saved dark mode preference
    # Local Device Mode (Native window) enabled for speed and local testing
    # DISABLED in --mock mode to allow headless testing/automated poking
    is_mock = "--mock" in sys.argv
    ui.run(title='ZenAI', dark=is_dark_mode(), port=8080, reload=False, native=False)

if __name__ == "__main__":
    try:
        start_app()
    except Exception as e:
        import traceback
        # Use safe characters for terminal to avoid UnicodeEncodeError on Windows
        error_msg = f"\n[!] FATAL ZENA UI ERROR: {e}\n"
        try:
            print(error_msg)
        except UnicodeEncodeError:
            print(f"\n[!] FATAL ZENA UI ERROR: {str(e).encode('ascii', 'ignore').decode()}\n")
        
        # Log to file for silent crashes (force utf-8)
        with open("ui_fatal_crash.txt", "w", encoding='utf-8') as f:
            f.write(error_msg)
            traceback.print_exc(file=f)
            
        traceback.print_exc()
        time.sleep(5) # Give user time to see error
        sys.exit(1)
