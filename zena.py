# -*- coding: utf-8 -*-
"""
zena.py - Zena AI Chat Interface
Elegant, professional chatbot with RAG capabilities
"""
import sys
import subprocess

# Safe NiceGUI installation (no auto-restart)
try:
    from nicegui import ui, app
except ImportError:
    print("[!] NiceGUI not found. Installing...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "nicegui"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("[✓] NiceGUI installed successfully. Please restart the application manually.")
        sys.exit(0)
    else:
        print(f"[✗] Installation failed: {result.stderr}")
        sys.exit(1)

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
from config_system import config, EMOJI, load_config
from security import FileValidator
from utils import format_message_with_attachment, normalize_input, sanitize_prompt
from ui_components import setup_app_theme, setup_common_dialogs, setup_drawer

# Import localization and UI modules
from locales import get_locale, L
from ui import Styles, Icons, Formatters

# Optional deps
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    import pyttsx3
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    sd = wav = pyttsx3 = SentenceTransformer = None

# Logging - output to BOTH file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('nebula_debug.log', mode='w'),
        logging.StreamHandler(sys.stdout)  # Also print to console
    ]
)
logger = logging.getLogger("NebulaUI")


API_URL = "http://127.0.0.1:8001/v1/chat/completions"

# Import async backend and arbitrator
from async_backend import AsyncNebulaBackend
from zena_mode.arbitrage import get_arbitrator

# Backend Implementation (Async HTTP with httpx)
class NebulaBackend:
    """Legacy sync backend - deprecated, use AsyncNebulaBackend instead."""
    
    def get_models(self):
        """Fetch available models from Hub API (port 8002)."""
        try:
            response = requests.get("http://127.0.0.1:8002/models/available", timeout=2)
            if response.status_code == 200:
                models = response.json()
                if isinstance(models, list):
                    logger.info(f"[Hub] Fetched {len(models)} models from API")
                    return models
        except Exception as e:
            logger.warning(f"[Hub] API unavailable: {e}")
        
        # Fallback: return static list if Hub API fails
        fallback = ["qwen2.5-coder.gguf", "llama-3.2-3b.gguf"]
        logger.info(f"[Hub] Using fallback models: {fallback}")
        return fallback

# Global backend instances
backend = NebulaBackend()
async_backend = AsyncNebulaBackend()
arbitrator = get_arbitrator()

# Load Zena Mode Configuration
ZENA_MODE = False
ZENA_CONFIG = {}
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        ZENA_CONFIG = config.get('zena_mode', {})
        ZENA_MODE = ZENA_CONFIG.get('enabled', False)
        logger.info(f"[Config] Zena Mode: {ZENA_MODE}")
except Exception as e:
    logger.warning(f"[Config] Could not load config.json: {e}")

# Initialize RAG if Zena mode enabled
rag_system = None
if ZENA_MODE:
    try:
        from zena_mode import LocalRAG, WebsiteScraper
        from pathlib import Path
        
        ROOT_DIR = Path(__file__).parent.resolve()
        rag_cache = ROOT_DIR / "rag_cache"
        rag_cache.mkdir(exist_ok=True)
        
        rag_system = LocalRAG(cache_dir=rag_cache)
        
        # Try to load existing index
        if not rag_system.load(rag_cache):
            logger.info("[RAG] No cached index found, will build on first use")
    except Exception as e:
        logger.error(f"[RAG] Failed to initialize: {e}")

# Initialize Conversation Memory (separate from knowledge RAG)
conversation_memory = None
try:
    from zena_mode import ConversationMemory
    from pathlib import Path
    
    ROOT_DIR = Path(__file__).parent.resolve()
    conv_cache = ROOT_DIR / "conversation_cache"
    conv_cache.mkdir(exist_ok=True)
    
    conversation_memory = ConversationMemory(cache_dir=conv_cache)
    logger.info("[Memory] Conversation memory initialized")
except Exception as e:
    logger.error(f"[Memory] Failed to initialize conversation memory: {e}")

# Import state management
from state_management import attachment_state, chat_history, handle_error

# TTS Setup
tts_engine = None
if pyttsx3:
    try:
        tts_engine = pyttsx3.init()
    except:
        pass

# UI State Container - holds per-client UI references
class UIState:
    """Container for per-client UI element references."""
    def __init__(self):
        self.chat_log = None
        self.scroll_container = None
        self.status_text = None
        self.attachment_preview = None
        self.user_input = None
        self.is_valid = True  # Track if client is still connected
        self.session_id = None  # Unique session ID for conversation memory
    
    def safe_update(self, element):
        """Safely update a UI element, handling disconnected clients."""
        if not self.is_valid:
            return
        try:
            if element is not None:
                element.update()
        except RuntimeError as e:
            if 'client' in str(e).lower() and 'deleted' in str(e).lower():
                logger.debug("[UI] Client disconnected, marking invalid")
                self.is_valid = False
            else:
                raise
    
    def safe_scroll(self):
        """Safely scroll to bottom, handling disconnected clients."""
        if not self.is_valid:
            return
        try:
            if self.scroll_container is not None:
                self.scroll_container.scroll_to(percent=1.0)
        except RuntimeError as e:
            if 'client' in str(e).lower() and 'deleted' in str(e).lower():
                logger.debug("[UI] Client disconnected, marking invalid")
                self.is_valid = False
            else:
                raise

@ui.page('/')
async def nebula_page():
    # Create per-client UI state (NOT global!)
    ui_state = UIState()
    
    # Generate unique session ID for conversation memory
    import uuid
    ui_state.session_id = str(uuid.uuid4())[:8]  # Short session ID
    logger.info(f"[Session] New client session: {ui_state.session_id}")
    
    # Theme & Layout
    setup_app_theme()
    
    # App State (Shared)
    app_state = {}

    # Initialize Dialogs (Components)
    dialogs = setup_common_dialogs(backend, app_state)
    model_dialog = dialogs['model']
    llama_dialog = dialogs['llama']
    llama_info = dialogs['llama'].info_label
    
    # --- LEFT SIDEBAR (Drawer) ---
    drawer = setup_drawer(backend, async_backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state)

    def scan_swarm():
        """Refresh the arbitrator's knowledge of live experts."""
        try:
            arbitrator.discover_swarm()
            count = len(arbitrator.ports)
            status = app_state.get('swarm_status')
            if status:
                if count > 1:
                    status.text = f"{count} Experts Online"
                    status.classes(remove='text-red-500', add='text-blue-600')
                else:
                    status.text = "Standalone Mode"
                    status.classes(remove='text-blue-600', add='text-gray-500')
        except Exception as e:
            logger.error(f"[Swarm] Scan failed: {e}")

    app_state['scan_swarm'] = scan_swarm
    
    # Run initial scan after UI is ready
    ui.timer(2.0, scan_swarm, once=True)

            

            
    # --- MAIN CONTENT ---
    # --- THEME MANAGEMENT ---
    # Initialize Dark Mode from saved settings
    from settings import is_dark_mode, set_dark_mode
    saved_dark_mode = is_dark_mode()
    dark_mode = ui.dark_mode(value=saved_dark_mode)
    
    # Create reactive theme colors
    
    # Initialize component references for native theme updates
    header = None
    footer = None
    # drawer is initialized below
    
    # Function to apply native Quasar theme props (Robust, No Hacks)
    def update_theme(is_dark: bool):
        # Update Native Quasar Props
        if is_dark:
            if header: header.props('dark')
            if drawer: drawer.props('dark')
            if footer: footer.props('dark')
            
            # Update body classes - removes light, adds dark
            ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
            
            # Force JavaScript sync (handles timing issues)
            ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')
        else:
            if header: header.props(remove='dark')
            if drawer: drawer.props(remove='dark')
            if footer: footer.props(remove='dark')
            
            ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
            
            # Force JavaScript sync
            ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')
            
        # Update chart colors or other non-reactive elements here if present
        pass

    # Get locale for UI strings
    locale = get_locale()

    # --- LAYOUT ---
    # Header
    with ui.header().classes(Styles.HEADER) as header:
        # Toggle sidebar
        ui.button(on_click=lambda: drawer.toggle(), icon=Icons.MENU).props('flat').classes(Styles.TEXT_PRIMARY)
        
        # Theme Toggle - Shows sun/moon based on current state
        theme_btn = ui.button(icon='light_mode' if not saved_dark_mode else 'dark_mode').props('flat').classes(Styles.TEXT_PRIMARY).tooltip(locale.TOOLTIP_DARK_MODE)
        
        def toggle_dark_mode():
            if dark_mode.value is True:
                dark_mode.disable()
                update_theme(False)
                set_dark_mode(False)
                theme_btn._props['icon'] = 'light_mode'  # Sun icon for light mode
            else:
                dark_mode.enable()
                update_theme(True)
                set_dark_mode(True)
                theme_btn._props['icon'] = 'dark_mode'  # Moon icon for dark mode
            theme_btn.update()
        
        theme_btn.on('click', toggle_dark_mode)
        
        # Scan & Read Button (Enhanced for Zena mode)
        # Create dialog ONCE - Opaque background for visibility
        with ui.dialog() as rag_dialog, ui.card().classes(Styles.DIALOG_CARD + ' w-96'):
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
                    website_input.props(f'visible={is_website}')
                    pages_input.props(f'visible={is_website}')
                    dir_input.props(f'visible={not is_website}')
                    files_input.props(f'visible={not is_website}')
                
                mode_select.on('update:model-value', on_mode_change)
                
                # Progress indicators - Enhanced Visibility
                progress_label = ui.label('').classes('text-md font-bold ' + Styles.TEXT_ACCENT + ' mb-2')
                progress_bar = ui.linear_progress(value=0, show_value=False).classes(Styles.PROGRESS).props('visible=false color=primary track-color=grey-3')
                
                async def start_website_scan():
                    url = normalize_input(website_input.value, 'url')
                    if not url:
                        ui.notify(locale.NOTIFY_RAG_ENTER_URL, color='warning')
                        return
                    
                    # Health Check
                    ui.notify(f"Checking {url}...", color='info')
                    try:
                        # Use run_in_executor to avoid blocking
                        await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: requests.get(url, timeout=5, headers={'User-Agent': 'Zena/1.0'})
                        )
                    except Exception as e:
                        logger.error(f"[RAG] Website check failed: {e}")
                        ui.notify(locale.format('ERROR_WEBSITE_UNREACHABLE', error=str(e)), color='negative')
                        return

                    try:
                        max_pages = int(pages_input.value)
                    except:
                        max_pages = 50
                    
                    # Show progress (Safe update)
                    try:
                        progress_bar.props('visible=true')
                        progress_label.text = locale.format('NOTIFY_RAG_SCANNING', url=url)
                        progress_bar.value = 0.1
                        ui.notify(f"Starting RAG scan of {url}...", color='info')
                    except RuntimeError:
                        return # Client disconnected
                        
                    logger.info(f"[RAG] Starting website scan: {url}")
                    
                    try:
                        from zena_mode import WebsiteScraper
                        
                        # Scrape website
                        start_time = time.time()
                        
                        def progress_update(count, total, current_url):
                            try:
                                # Calculate progress
                                percent = count / total
                                progress_bar.value = 0.1 + (percent * 0.5)  # 0.1 to 0.6 range
                                
                                # Calculate ETA
                                elapsed = time.time() - start_time
                                if count > 0:
                                    avg_time = elapsed / count
                                    remaining = int(avg_time * (total - count))
                                    mins, secs = divmod(remaining, 60)
                                    eta_str = f"{mins}m {secs}s"
                                else:
                                    eta_str = "Calculating..."
                                
                                # Update UI
                                progress_label.text = f"📄 Scraping ({count}/{total}) - ETA: {eta_str}"
                                progress_bar.props('visible=true') # Force visible
                            except RuntimeError: pass

                        scraper = WebsiteScraper(url)
                        documents = await asyncio.to_thread(scraper.scrape, max_pages, progress_update)
                        
                        try:
                            progress_label.text = f"✅ Scraped {len(documents)} pages. Building index..."
                            progress_bar.value = 0.6
                        except RuntimeError: pass
                        
                        await build_and_save_index(documents, url)
                    
                    except Exception as e:
                        logger.error(f"[RAG] Scan failed: {e}")
                        try:
                            ui.notify(f"RAG scan failed: {e}", color='negative')
                            progress_label.text = f"❌ Error: {str(e)}"
                            progress_bar.value = 0
                        except RuntimeError: pass

                async def start_directory_scan():
                    directory = normalize_input(dir_input.value, 'path')
                    if not directory:
                        ui.notify("Please enter a directory path", color='warning')
                        return
                    
                    # Verify directory exists
                    if not os.path.isdir(directory):
                        ui.notify(f"Directory not found: {directory}", color='warning')
                        return

                    # Show progress
                    try:
                        progress_bar.props('visible=true')
                        progress_label.text = f"🔍 Scanning directory {directory}..."
                        progress_bar.value = 0.1
                        ui.notify(f"Starting RAG scan...", color='info')
                    except RuntimeError: return

                    logger.info(f"[RAG] Starting directory scan: {directory}")

                    try:
                        from zena_mode.directory_scanner import DirectoryScanner
                        
                        try:
                            progress_label.text = f"📂 finding files..."
                            progress_bar.value = 0.2
                        except RuntimeError: pass

                        # Initialize scanner
                        scanner = DirectoryScanner(directory)
                        
                        # Use max_files input
                        try:
                            limit = int(files_input.value)
                        except: 
                            limit = 1000

                        # Run scan in thread
                        documents = await asyncio.to_thread(scanner.scan, limit)

                        if not documents:
                            ui.notify("No valid documents found in directory", color='warning')
                            progress_label.text = "❌ No documents found"
                            progress_bar.value = 0
                            return
                        
                        try:
                            progress_label.text = f"✅ Scraped {len(documents)} files. Building index..."
                            progress_bar.value = 0.6
                        except RuntimeError: pass
                        
                        await build_and_save_index(documents, f"local:{directory}")

                    except Exception as e:
                        logger.error(f"[RAG] Directory scan failed: {e}")
                        try:
                            ui.notify(f"Scan failed: {e}", color='negative')
                            progress_label.text = f"❌ Error: {str(e)}"
                        except RuntimeError: pass

                async def build_and_save_index(documents, source, stats=None):
                    """Common function to build and save RAG index."""
                    if rag_system and documents:
                        await asyncio.to_thread(rag_system.build_index, documents)
                        progress_bar.value = 0.9
                        
                        from pathlib import Path
                        rag_cache_path = ROOT_DIR / "rag_cache"
                        await asyncio.to_thread(rag_system.save, rag_cache_path)
                        
                        db_size = 0
                        if rag_cache_path.exists():
                            for file in rag_cache_path.glob("*"):
                                db_size += file.stat().st_size
                        db_size_mb = db_size / (1024 * 1024)
                        
                        progress_bar.value = 1.0
                        progress_label.text = f"✨ Success! {len(documents)} items indexed."
                        
                        ui.notify(f"✅ RAG index ready!", color='positive', position='top', timeout=5000)
                        logger.info(f"[RAG] Index built: {len(documents)} items, {db_size_mb:.2f} MB")
                        
                        if stats:
                            ext_summary = ', '.join([f"{ext}: {count}" for ext, count in list(stats['extensions'].items())[:5]])
                            add_message("system", f"✅ **RAG Index Ready!**\n\n**Database Stats:**\n- 📁 **Files**: {len(documents)}\n- 💾 **Size**: {db_size_mb:.2f} MB\n- 📂 **Path**: `{rag_cache_path.absolute()}`\n- 🗂️ **Source**: {source}\n- 📄 **Types**: {ext_summary}")
                        else:
                            add_message("system", f"✅ **RAG Index Ready!**\n\n**Database Stats:**\n- 📄 **Pages**: {len(documents)}\n- 💾 **Size**: {db_size_mb:.2f} MB\n- 📂 **Path**: `{rag_cache_path.absolute()}`\n- 🌐 **Source**: {source}")
                        
                        await asyncio.sleep(1)
                        try:
                            rag_dialog.close()
                        except: pass
                    else:
                        ui.notify("No documents found or RAG not initialized", color='warning')
                        progress_label.text = "❌ No documents found"

                async def start_scan():
                    is_website = mode_select.value == 'Website'
                    if is_website:
                        await start_website_scan()
                    else:
                        await start_directory_scan()
                
                ui.button('Start Scan', on_click=start_scan).props('color=primary').classes('w-full')
                ui.button('Cancel', on_click=rag_dialog.close).props('flat').classes('w-full mt-2')

            else:
                # Original directory-based RAG (Non-Zena)
                ui.label('RAG Document Indexing').classes('text-xl font-bold mb-4')
                path_input = ui.input('Directory Path', placeholder='C:/Documents').classes('w-full mb-2')
                
                async def start_rag_scan():
                    path = path_input.value.strip()
                    if not path:
                        ui.notify("Please enter a directory path", color='warning')
                        return
                    ui.notify(f"Scanning {path}...", color='info')
                    rag_dialog.close()
                
                ui.button('Start Scan', on_click=start_rag_scan).props('color=cyan')
                ui.button('Cancel', on_click=rag_dialog.close).props('flat')
        
        def open_rag_dialog():
            rag_dialog.open()
            



        
        
        # Scan & Read Button (Hidden by default, renamed to Start Scanning)
        scan_button = ui.button('Start Scanning', icon='book', on_click=open_rag_dialog).props('flat').classes('text-blue-600 dark:text-blue-400')
        scan_button.visible = False # Only visible when enabled

        # RAG Toggle Switch
        def toggle_rag(e):
            rag_enabled['value'] = e.value
            scan_button.visible = e.value # Toggle visibility
            status = locale.NOTIFY_RAG_ENABLED if e.value else locale.NOTIFY_RAG_DISABLED
            color = "positive" if e.value else "info"
            ui.notify(status, color=color)
            logger.info(f"[RAG] Mode {'enabled' if e.value else 'disabled'}")
        
        # Scan & Read Toggle Switch (renamed)
        rag_switch = ui.switch(locale.RAG_ENABLE, value=False, on_change=toggle_rag).props('color=cyan keep-color').classes('ml-2 ' + Styles.TEXT_PRIMARY + ' font-medium')
        
        # TTS Button
        async def speak_last_response():
            if not tts_engine:
                ui.notify(locale.VOICE_NOT_AVAILABLE, color='warning')
                return
            try:
                # Get last AI message from chat log
                # TODO: Store last AI response in a variable
                ui.notify("Speaking last response...", color='info')
                await asyncio.to_thread(tts_engine.say, "Text-to-speech feature coming soon")
                await asyncio.to_thread(tts_engine.runAndWait)
            except Exception as e:
                logger.error(f"[TTS] Error: {e}")
                ui.notify(locale.format('VOICE_ERROR', error=str(e)), color='negative')
        
        ui.button('TTS', icon=Icons.VOLUME, on_click=speak_last_response).props('flat').classes(Styles.TEXT_ACCENT)
        ui_state.status_text = ui.label(locale.CHAT_READY).classes(Styles.TEXT_SECONDARY + ' text-sm ml-auto')

    # Chat Area - Use scroll_area for proper scrolling
    # IMPORTANT: Set explicit height to fill space between header and footer
    # The calc accounts for header (~64px) and footer (~120px)
    ui_state.scroll_container = ui.scroll_area().classes('w-full').style('height: calc(100vh - 200px); min-height: 300px;')
    with ui_state.scroll_container:
        with ui.column().classes('w-full max-w-4xl mx-auto p-4 space-y-4 ' + Styles.CHAT_CONTAINER_LIGHT + ' ' + Styles.CHAT_CONTAINER_DARK) as chat_log_container:
            ui_state.chat_log = chat_log_container

    # Add message to chat
    def add_message(role: str, content: str):
        with ui_state.chat_log:
            with ui.row().classes(Styles.CHAT_ROW_USER if role == 'user' else Styles.CHAT_ROW_AI):
                # Zena-style colors
                if role == 'user':
                    color = Styles.CHAT_BUBBLE_USER
                else:
                    color = Styles.CHAT_BUBBLE_AI
                
                align = 'items-end' if role == 'user' else 'items-start'
                
                # Add circular avatar for AI messages
                if role != 'user':
                    ai_initial = 'Z' if ZENA_MODE else 'N'
                    ui.avatar(ai_initial, color='primary', text_color='white').classes(Styles.AVATAR + ' mr-2')
                
                with ui.column().classes(align):
                    ai_name = 'Zena' if ZENA_MODE else locale.APP_NAME
                    ui.label(locale.CHAT_YOU if role == 'user' else ai_name).classes(Styles.CHAT_NAME)
                    ui.markdown(content).classes(f'{color} {Styles.CHAT_BUBBLE_BASE}')
        # Auto-scroll to bottom
        ui_state.safe_scroll()
    
    # Guided Task Chips (Pill-shaped)
    def add_guided_chips():
        with ui_state.chat_log:
            ui.label(locale.CHAT_QUICK_ACTIONS).classes(Styles.LABEL_XS + ' mb-2 mt-4')
            with ui.row().classes('gap-2 flex-wrap mb-4'):
                async def chip_action(text):
                    ui_state.user_input.value = text
                    if handlers['send']:
                        await handlers['send']()
                
                # Pill-shaped buttons (fully rounded)
                ui.button(locale.CHAT_CHECK_MODEL, on_click=lambda: chip_action('What models are available?')).classes(Styles.CHIP).props('outline size=sm')
                ui.button(locale.CHAT_LATEST_LLAMA, on_click=lambda: chip_action('Check llama.cpp version')).classes(Styles.CHIP).props('outline size=sm')
                ui.button(locale.CHAT_RUN_BENCHMARK, on_click=lambda: chip_action('Run a performance benchmark')).classes(Styles.CHIP).props('outline size=sm')
                ui.button(locale.CHAT_HELP, on_click=lambda: chip_action('What can you help me with?')).classes(Styles.CHIP).props('outline size=sm')

    # Streaming response
    # RAG toggle state and handler references (mutable containers for closure access)
    rag_enabled = {'value': False}
    handlers = {'send': None}  # Will hold reference to handle_send after footer creates it
    
    async def stream_response(prompt: str):
        """Stream LLM response to chat UI with conversation memory."""
        # Check if client is still valid
        if not ui_state.is_valid:
            logger.warning("[UI] Client disconnected, skipping stream")
            return
            
        prompt = sanitize_prompt(prompt)
        add_message('user', prompt)
        
        # Save user message to conversation memory
        if conversation_memory:
            try:
                conversation_memory.add_message(
                    role='user',
                    content=prompt,
                    session_id=ui_state.session_id
                )
                logger.debug(f"[Memory] Saved user message to session {ui_state.session_id}")
            except Exception as e:
                logger.warning(f"[Memory] Failed to save user message: {e}")
        
        try:
            ui_state.status_text.text = locale.CHAT_THINKING
        except:
            pass
        
        # Yield to let UI render user message
        await asyncio.sleep(0.05)
        
        # Scroll to show user message (safely)
        ui_state.safe_scroll()
        
        # Create empty bot message - use move() for reliable DOM attachment
        msg_row = ui.row().classes(Styles.CHAT_ROW_AI)
        msg_row.move(ui_state.chat_log)
        logger.info(f"[UI] Created msg_row and moved to chat_log")
        
        with msg_row:
            with ui.column().classes('w-full max-w-3xl'):
                msg_ui = ui.markdown("⏳").classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm ' + Styles.LOADING_PULSE + ' w-full')
                sources_ui = ui.column().classes('w-full')
        
        logger.info(f"[UI] msg_ui created with initial content '⏳'")
        
        # Force UI update and scroll
        ui_state.safe_update(ui_state.chat_log)
        ui_state.safe_update(ui_state.scroll_container)
        await asyncio.sleep(0.05)
        ui_state.safe_scroll()
        
        full_text = ""
        
        # Build prompt with conversation context from memory
        final_prompt = prompt
        
        # First, inject conversation history context if available
        if conversation_memory:
            try:
                # Get contextual prompt with relevant conversation history
                final_prompt = conversation_memory.build_contextual_prompt(
                    prompt,
                    session_id=ui_state.session_id,
                    max_context_messages=6  # Last 3 exchanges
                )
                if final_prompt != prompt:
                    logger.info(f"[Memory] Injected conversation context for session {ui_state.session_id}")
            except Exception as e:
                logger.warning(f"[Memory] Failed to build contextual prompt: {e}")
                final_prompt = prompt
        
        # Then add RAG context if enabled
        if rag_enabled['value'] and rag_system and rag_system.index:
            try:
                # Query RAG for relevant context
                relevant_chunks = rag_system.search(prompt, k=5)
                
                if relevant_chunks:
                    # Spec Requirement: RAG Transparency (Subtle Blue Tint)
                    msg_ui.classes(remove=Styles.CHAT_BUBBLE_AI.split()[0], add=Styles.CHAT_BUBBLE_RAG)
                    
                    # Prepend RAG Indicator
                    full_text = locale.RAG_ANSWERED_FROM_SOURCE + "\n\n"
                    msg_ui.content = full_text
                    
                    # Build formatted context with [1] Source style
                    context_parts = []
                    sources_list = []
                    for i, c in enumerate(relevant_chunks, 1):
                         context_parts.append(f"[{i}] Source: {c.get('title', 'Untitled')}\n{c['text']}")
                         sources_list.append(f"[{i}] **{c.get('title', 'Untitled')}**\n   📍 Location: {c.get('url', 'N/A')}")
                    
                    context = "\n\n".join(context_parts)
                    
                    final_prompt = f"""Based on the following sources, answer the user's question. 
Cite your sources using [1], [2], etc. when referring to specific information.

SOURCES:
{context}

USER QUESTION: {prompt}

INSTRUCTIONS:
- Answer based ONLY on the provided sources
- Cite sources like [1], [2]
- If the answer isn't in the sources, say "I couldn't find this in my knowledge base."

ANSWER:"""
                    logger.info(f"[RAG] Using {len(relevant_chunks)} chunks for context")
            except Exception as e:
                logger.error(f"[RAG] Query failed: {e}")
        
        # Use CoT Swarm Arbitrator if enabled
        if app_state.get('use_cot_swarm') and app_state['use_cot_swarm'].value:
            is_quiet = app_state.get('quiet_cot') and app_state['quiet_cot'].value
            async for chunk in arbitrator.get_cot_response(final_prompt, "You are Zena, working within an Expert Swarm.", verbose=not is_quiet):
                if not ui_state.is_valid:
                    break
                full_text += chunk
                msg_ui.content = full_text
                msg_ui.classes(remove=Styles.LOADING_PULSE)
                ui_state.safe_update(msg_ui)
                await asyncio.sleep(0.02)
        else:
            # Standard single-model streaming
            try:
                chunk_count = 0
                async with async_backend:
                    async for chunk in async_backend.send_message_async(final_prompt):
                        if not ui_state.is_valid:
                            logger.info("[UI] Client disconnected mid-stream, stopping")
                            break
                        chunk_count += 1
                        full_text += chunk
                        msg_ui.content = full_text
                        msg_ui.classes(remove=Styles.LOADING_PULSE)
                        ui_state.safe_update(msg_ui)
                        if chunk_count <= 3 or chunk_count % 10 == 0:
                            logger.info(f"[UI] Chunk {chunk_count}: total_len={len(full_text)}")
                        await asyncio.sleep(0.02)  # Yield to allow UI refresh
                logger.info(f"[UI] Streaming complete: {chunk_count} chunks, {len(full_text)} chars")
            except Exception as e:
                logger.error(f"[UI] Stream error: {e}")
                if not full_text:
                    full_text = f"⚠️ Error: {str(e)}"
        
        # Append Sources Footer if RAG was used
        if rag_enabled['value'] and 'relevant_chunks' in locals() and relevant_chunks:
             with sources_ui:
                 with ui.expansion(locale.RAG_VIEW_SOURCES, icon=Icons.SOURCE).classes('w-full ' + Styles.CARD_INFO + ' rounded-xl mt-2'):
                     with ui.column().classes('gap-1 p-2'):
                         for i, c in enumerate(relevant_chunks, 1):
                             title = c.get('title', 'Untitled')
                             url = c.get('url', 'N/A')
                             # Handle Link vs Path
                             if url.startswith('http'):
                                 ui.link(f"[{i}] {title}", url).classes(Styles.TEXT_ACCENT + ' underline text-sm block')
                             else:
                                 ui.label(f"[{i}] {title}").classes('font-bold text-sm ' + Styles.TEXT_PRIMARY + ' block')
                                 ui.label(f"📍 {url}").classes(Styles.LABEL_XS + ' ml-4 break-all block')
                             
                             # Show text preview
                             text_preview = Formatters.preview(c.get('text', ''), 300)
                             ui.label(f'📝 "{text_preview}"').classes(Styles.LABEL_XS + ' italic ml-4 mb-2 border-l-2 border-gray-300 pl-2 block')

        # Final update - ensure response is visible
        if full_text and ui_state.is_valid:
            try:
                msg_ui.content = full_text
                ui_state.safe_update(msg_ui)
                
                # Save assistant response to conversation memory
                if conversation_memory:
                    try:
                        conversation_memory.add_message(
                            role='assistant',
                            content=full_text,
                            session_id=ui_state.session_id
                        )
                        logger.debug(f"[Memory] Saved assistant response to session {ui_state.session_id}")
                    except Exception as e:
                        logger.warning(f"[Memory] Failed to save assistant response: {e}")
                        
            except RuntimeError:
                logger.debug("[UI] Client disconnected during final update")
        
        try:
            ui_state.status_text.text = locale.CHAT_READY
        except RuntimeError:
            pass
        
        # Force final UI refresh
        ui_state.safe_update(ui_state.chat_log)
        ui_state.safe_update(ui_state.scroll_container)
        await asyncio.sleep(0.05)
        
        # Auto-scroll to bottom after response complete
        ui_state.safe_scroll()

    # Helper for robust content extraction
    def extract_text(raw_data, filename):
        """Extracts text from raw bytes based on extension."""
        text = ""
        try:
            # Check for PDF
            if filename.lower().endswith('.pdf') and pypdf:
                try:
                    # pypdf needs a file-like object
                    file_obj = io.BytesIO(raw_data)
                    pdf_reader = pypdf.PdfReader(file_obj)
                    extracted = []
                    for page in pdf_reader.pages:
                        extracted.append(page.extract_text() or "")
                    text = "\n".join(extracted)
                    logger.info(f"[Upload] Extracted {len(text)} chars from PDF")
                except Exception as e:
                    logger.error(f"[Upload] PDF extraction failed: {e}")
                    text = f"[Error extracting PDF: {e}]"
            else:
                # Assume text/binary
                # Simple binary check (null bytes)
                if b'\x00' in raw_data[:1024] and not filename.lower().endswith('.txt'):
                     text = f"[Attached binary file: {filename}]"
                else:
                     text = raw_data.decode('utf-8', errors='replace')
        except Exception as e:
             logger.error(f"[Upload] Helper extraction failed: {e}")
             text = f"[Error reading file: {e}]"
             
        return text

    # File upload handler (Drag and Drop via UI.upload)
    async def on_upload(e):
        try:
            # Debug extraction
            logger.info(f"[Upload] Event: {e}")
            
            # --- Name Extraction ---
            name = getattr(e, 'name', getattr(e, 'filename', 'unknown_file'))
            if name == 'unknown_file' and hasattr(e, 'file'):
                 name = getattr(e.file, 'filename', getattr(e.file, 'name', 'unknown_file'))
                 
            # --- Content Extraction ---
            # We need the RAW BYTES.
            # Sources: e.content (NiceGUI), e.file (Starlette), or e.file.file (Spooled)
            raw_content = b""
            
            # 1. Determine Source Object
            source = getattr(e, 'content', None)
            if not source:
                 source = getattr(e, 'file', None)
            
            # 2. Extract Bytes from Source
            if source:
                # If it's a file-like object with read()
                if hasattr(source, 'read'):
                    try:
                        # CRITICAL: Do NOT call read() twice if it's a coroutine
                        # Check if read itself is a coroutine function (unlikely but possible)
                        # More likely: result of read() is a coroutine
                        
                        potential = source.read()
                        
                        if asyncio.iscoroutine(potential):
                            raw_content = await potential
                        else:
                            raw_content = potential
                            
                    except Exception as read_err:
                        logger.error(f"[Upload] Read error: {read_err}")
                        raw_content = b""
                        
                # If it's pure bytes/string
                elif isinstance(source, bytes):
                    raw_content = source
                elif isinstance(source, str):
                    raw_content = source.encode('utf-8')
                    
                # If it's a wrapper with a .file attribute (Starlette UploadFile)
                elif hasattr(source, 'file'):
                    try:
                        inner = source.file
                        if hasattr(inner, 'read'):
                            potential = inner.read()
                            if asyncio.iscoroutine(potential):
                                raw_content = await potential
                            else:
                                raw_content = potential
                    except Exception as inner_err:
                        logger.error(f"[Upload] Inner read error: {inner_err}")
            
            # 3. Final Type Safety Gate
            if not isinstance(raw_content, bytes):
                 logger.warning(f"[Upload] raw_content is {type(raw_content)}, converting...")
                 # Force conversion to prevent "not subscriptable" crash in extract_text
                 raw_content = str(raw_content).encode('utf-8', errors='replace')

            # 4. Extract Text
            content = extract_text(raw_content, name)
            
            logger.info(f"[Upload] Final content length: {len(content)} chars")


            
            # Use attachment_state instead of global dict
            attachment_state.set(name, content, content[:100])
            
            ui_state.attachment_preview.text = f"📎 {name} ({len(content)} chars)"
            ui_state.attachment_preview.visible = True
            ui.notify(locale.format('NOTIFY_ATTACHED', name=name), color='positive')
            logger.info(f"[Upload] Successfully attached {name}")
        except Exception as ex:
            logger.error(f"[Upload] Error: {ex}")
            ui.notify(locale.format('NOTIFY_UPLOAD_FAILED', error=str(ex)), color='negative')

    # Voice Handler
    async def on_voice_click():
        if not sd:
            ui.notify(locale.NOTIFY_SOUNDDEVICE_MISSING, color='red')
            return
            
        ui_state.status_text.text = locale.CHAT_RECORDING
        ui_state.status_text.classes(Styles.TEXT_ERROR + ' ' + Styles.LOADING_PULSE)
        
        # Audio Config
        fs = 16000
        duration = 5  # seconds
        
        try:
            # Record in thread
            def record():
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()
                return recording
            
            audio_data = await asyncio.to_thread(record)
            
            # Convert to WAV in memory
            ui_state.status_text.text = locale.CHAT_TRANSCRIBING
            ui_state.status_text.classes(Styles.TEXT_WARNING)
            
            wav_buffer = io.BytesIO()
            wav.write(wav_buffer, fs, audio_data)
            wav_buffer.seek(0)
            
            # Send to Backend API
            # Note: start_llm.py endpoint expects data in body
            response = await asyncio.to_thread(requests.post, "http://127.0.0.1:8001/voice/transcribe", data=wav_buffer.read())
            
            if response.status_code == 200:
                transcription = response.json().get('text', '')
                if transcription:
                    ui_state.user_input.value += transcription + " "
                    ui.notify(locale.NOTIFY_TRANSCRIBED, color='green')
                else:
                    ui.notify(locale.NOTIFY_NO_SPEECH, color='orange')
            else:
                ui.notify(locale.format('NOTIFY_TRANSCRIPTION_FAILED', error=response.text), color='red')
                
        except Exception as e:
            ui.notify(locale.format('NOTIFY_VOICE_ERROR', error=str(e)), color='red')
        finally:
            ui_state.status_text.text = locale.CHAT_READY
            ui_state.status_text.classes(remove=Styles.TEXT_ERROR + ' ' + Styles.LOADING_PULSE + ' ' + Styles.TEXT_WARNING)
            ui_state.status_text.classes(Styles.LABEL_XS)

    # Footer (Compact input bar like LM Studio / Ollama)
    # Message state tracker (outside UI blocks for persistence)
    msg_state = {'current': ''}
    
    with ui.footer().classes(Styles.FOOTER) as footer:
        with ui.column().classes('w-full max-w-4xl mx-auto gap-1'):
            # Attachment Preview
            ui_state.attachment_preview = ui.label('').classes(Styles.TEXT_ACCENT + ' text-sm mb-2 bg-blue-50 dark:bg-gray-800 px-3 py-1 rounded-full shadow-sm self-start').props('visible=false')
            
            # Input Bar Container (Compact rounded bar)
            with ui.row().classes(Styles.INPUT_BAR):
                
                # --- File Upload (Hidden Pattern) ---
                # 1. The actual uploader is hidden
                uploader = ui.upload(on_upload=on_upload, auto_upload=True).classes('hidden')
                
                # 2. A clean button triggers it
                ui.button(on_click=lambda: uploader.run_method('pickFiles'), icon=Icons.ATTACH) \
                    .props('flat round dense') \
                    .classes(Styles.LABEL_MUTED + ' hover:text-blue-600')
                
                # Input Field - simple approach with on_change
                placeholder_text = locale.CHAT_PLACEHOLDER_ZENA if ZENA_MODE else locale.CHAT_PLACEHOLDER
                
                def track_input(e):
                    msg_state['current'] = e.value
                
                ui_state.user_input = ui.input(placeholder=placeholder_text, on_change=track_input).props('outlined dense').classes('flex-1')
                
                # Define send handler
                async def handle_send(e=None):
                    """Handle send button click or Enter key press."""
                    logger.info("[UI] handle_send triggered")
                    
                    # Get value from state tracker
                    text = msg_state['current'].strip() if msg_state['current'] else ""
                    logger.info(f"[UI] Message: '{text[:50] if text else '(empty)'}...'")
                    
                    if not text:
                        logger.warning("[UI] Empty message, skipping")
                        return
                    
                    # Add attachment if present
                    if attachment_state.has_attachment():
                        name, content, _ = attachment_state.get()
                        text = format_message_with_attachment(text, name, content)
                        attachment_state.clear()
                        ui_state.attachment_preview.visible = False
                        ui_state.attachment_preview.text = ""
                    
                    ui_state.user_input.value = ""
                    msg_state['current'] = ""  # Clear state
                    logger.info(f"[UI] Calling stream_response...")
                    await stream_response(text)
                
                # Store handler reference for chip_action to use
                handlers['send'] = handle_send
                
                ui_state.user_input.on('keydown.enter.prevent', handle_send)
                
                # Actions
                ui.button(icon=Icons.RECORD, on_click=on_voice_click).props('flat round dense icon-size=24px').classes(Styles.LABEL_MUTED + ' hover:text-blue-600')
                ui.button(icon=Icons.SEND, on_click=handle_send).props('round dense unelevated').classes(Styles.BTN_PRIMARY + ' w-10 h-10')

    # Apply Dark Mode on Initial Load based on saved settings
    # This must be called AFTER all UI elements are created
    update_theme(saved_dark_mode)

    # Initial Welcome (Dynamic based on mode)
    if ZENA_MODE:
        rag_source = ZENA_CONFIG.get('rag_source', 'knowledge_base')
        
        if rag_source == 'website':
             source_val = ZENA_CONFIG.get('website_url', 'configured website')
             source_msg = locale.format('WELCOME_SOURCE_WEBSITE', url=source_val)
        elif rag_source == 'filesystem':
             source_val = ZENA_CONFIG.get('directory_path', 'local directory')
             source_msg = locale.format('WELCOME_SOURCE_FILESYSTEM', path=source_val)
        else:
             source_msg = locale.WELCOME_SOURCE_KB

        add_message("system", locale.format('WELCOME_ZENA', source_msg=source_msg))
    else:
        add_message("system", locale.WELCOME_DEFAULT)
    add_guided_chips()

def start_app():
    """Entry point for NiceGUI application."""
    import sys
    from settings import is_dark_mode
    
    # --- Fix 1: NICEGUI_SCREEN_TEST_PORT KeyError ---
    # NiceGUI checks this env var if it detects 'pytest' in sys.modules.
    # Sometimes IDEs or other tools might trigger this detection unintentionally.
    # To be safe, we ALWAYS ensure this variable exists to prevent a crash.
    if 'NICEGUI_SCREEN_TEST_PORT' not in os.environ:
        os.environ['NICEGUI_SCREEN_TEST_PORT'] = '8081'

    # --- Fix 2: pyttsx3 AttributeError on exit ---
    # "AttributeError: 'NoneType' object has no attribute 'suppress'"
    try:
        import pyttsx3
        if hasattr(pyttsx3, 'driver') and pyttsx3.driver:
            pass
    except:
        pass

    # Use saved dark mode preference
    ui.run(title='ZenAI', dark=is_dark_mode(), port=8080, reload=False)

if __name__ == "__main__":
    start_app()
