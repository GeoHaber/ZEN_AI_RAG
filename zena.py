# -*- coding: utf-8 -*-
"""
zena.py - Zena AI Chat Interface
Elegant, professional chatbot with RAG capabilities
"""
import sys
import subprocess
import os
from pathlib import Path

# ZenAI Root Path Isolation
BASE_DIR = Path(__file__).parent.absolute()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Safe NiceGUI installation (no auto-restart)

# Safe Dependency Installation
def install_if_missing(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"[!] {package_name} not found. Installing...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[✗] Installation of {package_name} failed: {result.stderr}")

# Required Dependencies
install_if_missing("nicegui")
install_if_missing("python-telegram-bot", "telegram")
install_if_missing("httpx")
install_if_missing("flask")
install_if_missing("twilio")
install_if_missing("pypdf")
install_if_missing("numpy")

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
from utils import format_message_with_attachment, normalize_input, sanitize_prompt, is_port_active
from ui_components import setup_app_theme, setup_common_dialogs, setup_drawer

# Import localization and UI modules
from locales import get_locale, L
from ui import Styles, Icons, Formatters
from zena_rag_ui import setup_rag_dialog
from ui.examples import EXAMPLES
from zena_mode.profiler import monitor
from zena_mode.help_system import index_internal_docs
from zena_mode.auto_updater import check_for_updates, get_local_version, ModelScout
from zena_mode.gateway_telegram import run_gateway as run_telegram_gateway
from zena_mode.gateway_whatsapp import run_whatsapp_gateway

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
logger = logging.getLogger("ZenAI")


API_URL = "http://127.0.0.1:8001/v1/chat/completions"

# Import async backend and arbitrator
from async_backend import AsyncZenAIBackend as async_backend
# Note: Legacy sync backend removed - all operations now async

# Load Zena Mode Configuration
ZENA_MODE = False
ZENA_CONFIG = {}
try:
    with open('config.json', 'r') as f:
        config_data = json.load(f)
        ZENA_CONFIG = config_data.get('zena_mode', {})
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
    
    ROOT_DIR = Path(__file__).parent.resolve()
    conv_cache = ROOT_DIR / "conversation_cache"
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
ROOT_DIR = Path(__file__).parent.resolve()
upload_cleanup = get_cleanup_policy(ROOT_DIR / "uploads")
logger.info("[Cleanup] Upload cleanup policy initialized")

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
        self.cancellation_event = asyncio.Event()  # For cancelling streaming
        # Note: arbitrator is now managed via zena_mode.arbitrage but accessed via instance method if needed
    
    def safe_update(self, element):
        """Safely update a UI element, handling disconnected clients."""
        if not self.is_valid:
            return
        try:
            if element is not None:
                element.update()
        except RuntimeError as e:
            if 'client' in str(e).lower() and 'deleted' in str(e).lower():
                logger.debug("[UI] Client disconnected, marking invalid and cancelling streams")
                self.is_valid = False
                self.cancellation_event.set()  # Cancel any ongoing streams
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
                logger.debug("[UI] Client disconnected, marking invalid and cancelling streams")
                self.is_valid = False
                self.cancellation_event.set()  # Cancel any ongoing streams
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

    # App State (Shared) - Single source of truth for RAG
    app_state = {
        'rag_enabled': ZENA_CONFIG.get('rag_enabled', True) if ZENA_MODE else False,
        'open_rag_dialog': lambda: rag_dialog.open() if 'rag_dialog' in locals() else None
    }

    # Initialize Dialogs (Components)
    from async_backend import AsyncZenAIBackend
    async_backend = AsyncZenAIBackend()
    
    def on_language_change(code):
        """Handle hot-switch of language."""
        from settings import get_settings
        ui.notify(f"Switching to {code}...", color='info')
        # Force save settings before reload
        get_settings().save()
        # Then reload the page to refresh all static labels
        ui.run_javascript('window.location.reload()')

    dialogs = setup_common_dialogs(
        async_backend, 
        app_state,
        on_language_change=on_language_change,
        on_dark_mode=lambda is_dark: update_theme(is_dark)
    )
    model_dialog = dialogs['model']
    llama_dialog = dialogs['llama']
    llama_info = dialogs['llama'].info_label

    # --- LEFT SIDEBAR (Drawer) ---
    drawer = setup_drawer(async_backend, rag_system, config_data if 'config_data' in locals() else {}, dialogs, ZENA_MODE, EMOJI, app_state)

    # Periodic upload cleanup (run every 6 hours)
    def run_cleanup():
        """Run periodic cleanup of uploads directory."""
        try:
            stats_before = upload_cleanup.get_stats()
            logger.info(f"[Cleanup] Starting cleanup (current: {stats_before['count']} files, {stats_before['size_mb']} MB)")
            result = upload_cleanup.cleanup()
            if result['deleted'] > 0:
                logger.info(f"[Cleanup] Cleanup complete: {result['deleted']} files deleted, {result['freed_mb']} MB freed")
        except Exception as e:
            logger.error(f"[Cleanup] Failed: {e}")

    # Run cleanup on startup (after 10 seconds) and then every 6 hours
    ui.timer(10.0, run_cleanup, once=True)
    ui.timer(6 * 3600, run_cleanup)

            
    # --- MAIN CONTENT ---
    # --- THEME MANAGEMENT ---
    # Initialize Dark Mode from saved settings
    from settings import is_dark_mode, set_dark_mode
    saved_dark_mode = is_dark_mode()
    dark_mode = ui.dark_mode(value=saved_dark_mode)
    
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
            
    # Get locale for UI strings
    locale = get_locale()

    # --- LAYOUT ---
    # Setup RAG Dialog (Modular)
    rag_dialog = setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, locale, rag_system, ROOT_DIR, Styles)

    # Initial Indexing of internal docs for Help System
    if rag_system:
        try:
            index_internal_docs(ROOT_DIR, rag_system)
        except Exception as e:
            logger.warning(f"Failed to index internal docs: {e}")

    # Header
    with ui.header().classes(Styles.HEADER) as header:
        # Toggle sidebar
        ui.button(on_click=lambda: drawer.toggle(), icon=Icons.MENU).props('flat round').classes(Styles.TEXT_PRIMARY)

        # Logo in header - hidden text on mobile
        with ui.row().classes('items-center'):
            ui.label('ZenAI').classes('text-base md:text-lg font-bold ' + Styles.TEXT_ACCENT + ' ml-1 md:ml-2')
        
        ui.space()
        
        # User Avatar / Status - persistent and clear
        with ui.row().classes('items-center gap-2'):
             with ui.row().classes('items-center gap-1.5 px-3 py-1 rounded-full bg-gray-50/50 dark:bg-slate-800/50 border border-gray-100 dark:border-slate-700'):
                 ui_state.status_dot = ui.label('●').classes('text-green-500 animate-pulse text-[14px]')
                 ui_state.status_indicator = ui.label('ONLINE').classes('text-[10px] font-black tracking-widest text-green-500')
             ui.button(icon=Icons.PERSON).props('flat round dense').classes(Styles.TEXT_MUTED)

        # Status text (Right-aligned)
        ui_state.status_text = ui.label(locale.CHAT_READY).classes(Styles.TEXT_SECONDARY + ' text-xs md:text-sm ml-auto hidden xs:block')
        
    # --- PERFORMANCE DASHBOARD (NEW) ---
    with ui.row().classes('w-full px-4 py-1 bg-gray-50/50 dark:bg-slate-800/50 backdrop-blur-sm border-b border-gray-100 dark:border-slate-800 gap-4 justify-center items-center'):
        with ui.row().classes('items-center gap-1'):
            ui.label('⚡TPS:').classes('text-[10px] font-bold text-blue-500 uppercase')
            ui_state.tps_label = ui.label('0.0').classes('text-[10px] font-mono text-blue-600 dark:text-blue-400')
        with ui.row().classes('items-center gap-1'):
            ui.label('⏱️TTFT:').classes('text-[10px] font-bold text-orange-500 uppercase')
            ui_state.ttft_label = ui.label('0ms').classes('text-[10px] font-mono text-orange-600 dark:text-orange-400')
        with ui.row().classes('items-center gap-1'):
            ui.label('📚RAG:').classes('text-[10px] font-bold text-green-500 uppercase')
            ui_state.rag_latency_label = ui.label('0ms').classes('text-[10px] font-mono text-green-600 dark:text-green-400')

    def update_performance_dashboard():
        avgs = monitor.get_averages()
        # Debug logging to see why TPS might be 0
        if avgs['llm_tps'] == 0 and avgs['llm_ttft'] == 0:
            pass # Reduce noise
        else:
            logger.debug(f"[Dashboard] TPS: {avgs['llm_tps']:.1f}, TTFT: {avgs['llm_ttft']}ms")

        ui_state.tps_label.text = f"{avgs['llm_tps']:.1f}"
        ui_state.ttft_label.text = f"{int(avgs['llm_ttft'])}ms"
        ui_state.rag_latency_label.text = f"{int(avgs['rag_retrieval'])}ms"
    
    ui.timer(1.0, update_performance_dashboard)

    # Chat Area - Use scroll_area for proper scrolling
    # calc accounts for header (12-14) and footer (variable)
    ui_state.scroll_container = ui.scroll_area().classes('w-full').style('height: calc(100vh - 160px); min-height: 250px;')
    with ui_state.scroll_container:
        with ui.column().classes('w-full max-w-4xl mx-auto p-2 md:p-4 space-y-3 md:space-y-4 ' + Styles.CHAT_CONTAINER_LIGHT + ' ' + Styles.CHAT_CONTAINER_DARK) as chat_log_container:
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
    # Handler references (mutable containers for closure access)
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
                # Get appropriate loading message based on context
                import random
                use_rag = app_state.get('rag_enabled', False) and rag_system and rag_system.index
                use_swarm = app_state.get('use_cot_swarm') and app_state['use_cot_swarm'].value

                if use_swarm:
                    loading_msg = random.choice(locale.LOADING_SWARM_THINKING)
                elif use_rag:
                    loading_msg = random.choice(locale.LOADING_RAG_THINKING)
                else:
                    loading_msg = random.choice(locale.LOADING_THINKING)

                msg_ui = ui.markdown(loading_msg).classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm ' + Styles.LOADING_PULSE + ' w-full')
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
                            session_id=ui_state.session_id
                        )
                        if final_prompt != prompt:
                            logger.info(f"[Memory] Injected conversation context for session {ui_state.session_id}")
                    except Exception as e:
                        logger.warning(f"[Memory] Failed to build contextual prompt: {e}")
                        final_prompt = prompt

                # Then add RAG context if enabled
                if app_state.get('rag_enabled', False) and rag_system and rag_system.index:
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
        
        # Standard single-model streaming
        try:
            chunk_count = 0
            logger.info(f"[Debug] Starting backend stream. Valid: {ui_state.is_valid}, Cancel: {ui_state.cancellation_event.is_set() if ui_state.cancellation_event else 'None'}")
            
            async with async_backend:
                async for chunk in async_backend.send_message_async(
                    final_prompt,
                    cancellation_event=ui_state.cancellation_event
                ):
                    if not ui_state.is_valid:
                        logger.info("[UI] Client disconnected mid-stream, stopping")
                        break
                    
                    if chunk_count == 0:
                        logger.info(f"[Debug] First chunk received: {chunk[:20] if chunk else 'EMPTY'}...")

                    chunk_count += 1
                    full_text += chunk
                    msg_ui.content = full_text
                    msg_ui.classes(remove=Styles.LOADING_PULSE)
                    ui_state.safe_update(msg_ui)
                    
                    if chunk_count % 10 == 0:
                        logger.debug(f"[UI] Chunk {chunk_count}: total_len={len(full_text)}")
                    await asyncio.sleep(0.02)  # Yield to allow UI refresh
            
            if chunk_count == 0:
                logger.error("[Debug] Stream finished efficiently but with 0 chunks!")
                full_text = "⚠️ Brain Dead: 0 Chunks Received."

            logger.info(f"[UI] Streaming complete: {chunk_count} chunks, {len(full_text)} chars")
        except Exception as e:
            logger.error(f"[UI] Stream error: {e}", exc_info=True)
            if not full_text:
                full_text = f"⚠️ Error: {str(e)}"
        
        # Append Sources Footer if RAG was used
        if app_state.get('rag_enabled') and 'relevant_chunks' in locals() and relevant_chunks:
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
            if filename.lower().endswith('.pdf'):
                if not is_feature_available('pdf'):
                    reason = feature_detector.get_unavailable_reason('pdf')
                    ui.notify(f"{EMOJI['warning']} PDF Support Unavailable\\n{reason}", color='warning', timeout=5000)
                    text = f"[PDF file: {filename} - extraction unavailable, install pypdf to enable]"
                else:
                    try:
                        # pypdf needs a file-like object
                        file_obj = io.BytesIO(raw_data)
                        pdf_reader = pypdf.PdfReader(file_obj)
                        extracted = []
                        for page in pdf_reader.pages:
                            extracted.append(page.extract_text() or "")
                        text = "\\n".join(extracted)
                        logger.info(f"[Upload] Extracted {len(text)} chars from PDF")
                    except Exception as e:
                        logger.error(f"[Upload] PDF extraction failed: {e}")
                        text = f"[Error extracting PDF: {e}]"
            else:
                # Assume text/binary
                # Simple binary check (null bytes)
                if b'\\x00' in raw_data[:1024] and not filename.lower().endswith('.txt'):
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
        if not is_feature_available('audio'):
            reason = feature_detector.get_unavailable_reason('audio')
            ui.notify(f"{EMOJI['error']} Voice Recording Unavailable\\n{reason}", color='negative', timeout=5000)
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
            
            # Send to Backend API (Hub on port 8002)
            response = await asyncio.to_thread(requests.post, "http://127.0.0.1:8002/voice/transcribe", data=wav_buffer.read())
            
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

    # Footer (Minimalist Slate Input Bar)
    msg_state = {'current': ''}
    
    with ui.footer().classes(Styles.FOOTER) as footer:
        with ui.column().classes('w-full max-w-4xl mx-auto gap-1'):
            # Attachment Preview
            ui_state.attachment_preview = ui.label('').classes(Styles.TEXT_ACCENT + ' text-sm mb-2 bg-blue-50 dark:bg-blue-900/10 px-3 py-1 rounded-full border border-blue-100 dark:border-blue-800 self-start').props('visible=false')
            
            # Input Bar Container (Solid Slate Bar)
            with ui.row().classes(Styles.INPUT_BAR):
                
                # --- File Upload ---
                uploader = ui.upload(on_upload=on_upload, auto_upload=True).classes('hidden')
                ui.button(on_click=lambda: uploader.run_method('pickFiles'), icon=Icons.ATTACH) \
                    .props('flat round dense') \
                    .classes(Styles.LABEL_MUTED + ' hover:text-blue-600')
                
                # Input Field
                placeholder_text = getattr(locale, 'CHAT_PLACEHOLDER_ZENA', 'How can I help you?') if ZENA_MODE else getattr(locale, 'CHAT_PLACEHOLDER', 'Type a message...')
                
                def track_input(e):
                    msg_state['current'] = e.value
                
                ui_state.user_input = ui.input(placeholder=placeholder_text, on_change=track_input).props('borderless dense').classes('flex-1 bg-transparent')
                
                # Define internal command handlers
                async def run_internal_check(monkey=False):
                    add_message("system", f"🔍 **{ 'MONKEY MODE' if monkey else 'SELF-TEST' } STARTED**")
                    
                    # Run diagnostics in a background thread to avoid blocking UI
                    def run_command_bg():
                        import subprocess
                        import sys
                        cmd = [sys.executable, "tests/live_diagnostics.py"]
                        if monkey: cmd.append("--monkey")
                        
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        return process

                    process = await asyncio.to_thread(run_command_bg)
                    
                    # Create a message bubble for the output
                    msg_ui = ui.markdown("⏳ *Running diagnostics...*").classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm w-full font-mono text-xs')
                    ui_state.safe_update(ui_state.chat_log)
                    
                    full_output = ""
                    # Read output line by line (mocking the trace flow)
                    while True:
                        line = await asyncio.to_thread(process.stdout.readline)
                        if not line: break
                        full_output += line
                        # Update UI every few lines to show progress
                        msg_ui.set_content(f"```\n{full_output}\n```")
                        ui_state.safe_scroll()
                    
                    add_message("system", "✅ **DIAGNOSTICS COMPLETE**")

                # Define send handler
                async def handle_send(e=None):
                    text = msg_state['current'].strip() if msg_state['current'] else ""
                    if not text: return
                    
                    # Intercept special commands
                    cmd_clean = text.lower().strip()
                    if cmd_clean in ["run the monkey", "run monkey", "monkey test"]:
                        ui_state.user_input.value = ""
                        msg_state['current'] = ""
                        await run_internal_check(monkey=True)
                        return
                    if cmd_clean in ["run a self test", "self test", "diagnostics"]:
                        ui_state.user_input.value = ""
                        msg_state['current'] = ""
                        await run_internal_check(monkey=False)
                        return

                    if attachment_state.has_attachment():
                        name, content, _ = attachment_state.get()
                        text = format_message_with_attachment(text, name, content)
                        attachment_state.clear()
                        ui_state.attachment_preview.visible = False
                    
                    ui_state.user_input.value = ""
                    msg_state['current'] = ""
                    await stream_response(text)
                
                handlers['send'] = handle_send
                ui_state.user_input.on('keydown.enter.prevent', handle_send)
                
                # Actions (Solid & Clean)
                ui.button(icon=Icons.RECORD, on_click=on_voice_click).props('flat round dense').classes(Styles.LABEL_MUTED + ' hover:text-blue-600')
                ui.button(icon=Icons.SEND, on_click=handle_send).props('round dense unelevated').classes(Styles.BTN_PRIMARY + ' w-9 h-9')

            # Fun waiting status below input (rotating messages)
            import random
            waiting_msg = random.choice(locale.LOADING_WAITING_FOR_USER)
            waiting_status = ui.label(waiting_msg).classes('text-xs text-gray-400 italic text-center mt-1 animate-pulse')

            # Rotate waiting message every 5 seconds
            def update_waiting_message():
                try:
                    new_msg = random.choice(locale.LOADING_WAITING_FOR_USER)
                    waiting_status.text = new_msg
                except Exception:
                    pass  # Ignore if element deleted

            ui.timer(5.0, update_waiting_message)

            # --- Backend Health Monitoring ---
            async def check_backend_health():
                """Periodic background task to update status indicators."""
                import httpx
                while ui_state.is_valid:
                    try:
                        # Use existing is_port_active (already imported from utils)
                        llm_online = await asyncio.to_thread(is_port_active, 8001)
                        hub_online = await asyncio.to_thread(is_port_active, 8002)
                        
                        status_text = "OFFLINE"
                        color_add = "text-red-500"
                        color_remove = "text-green-500 text-orange-500"

                        if llm_online:
                            status_text = "ONLINE"
                            color_add = "text-green-500"
                            color_remove = "text-red-500 text-orange-500"
                        elif hub_online:
                            status_text = "BOOTING"
                            color_add = "text-orange-500"
                            color_remove = "text-green-500 text-red-500"
                            try:
                                async with httpx.AsyncClient() as client:
                                    resp = await client.get("http://127.0.0.1:8002/startup/progress", timeout=1.0)
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        pct = data.get('percent', 0)
                                        status_text = f"BOOTING ({pct}%)"
                            except Exception:
                                pass
                        
                        # Update Header Elements
                        ui_state.status_indicator.set_text(status_text)
                        ui_state.status_indicator.classes(remove=color_remove, add=color_add)
                        ui_state.status_dot.classes(remove=color_remove, add=color_add)
                        
                        # Update Drawer Elements (if they exist in app_state)
                        if 'drawer_status_label' in app_state:
                            app_state['drawer_status_label'].set_text(status_text)
                            app_state['drawer_status_label'].classes(remove=color_remove, add=color_add)
                            app_state['drawer_status_dot'].classes(remove=color_remove, add=color_add)
                            
                    except Exception as e:
                        logger.error(f"[HealthCheck] Error: {e}")
                    await asyncio.sleep(2)

            asyncio.create_task(check_backend_health())

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
    
    # Add Guided Example Chips
    with ui_state.chat_log:
        with ui.row().classes('w-full justify-center gap-2 mt-4 flex-wrap'):
            for item in EXAMPLES:
                def make_click_handler(p=item['prompt']):
                    return lambda: (setattr(ui_state.user_input, 'value', p), ui_state.user_input.run_method('focus'))
                
                ui.button(item['title'], on_click=make_click_handler()).props('outline rounded-full dense').classes('text-[11px] px-3 py-1 normal-case hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors')

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

@app.on_event('startup')
async def on_startup():
    """Global startup triggers."""
    # Add hidden testing endpoint for Monkey Test
    from fastapi import Response
    @app.post("/test/click/{element_id}")
    async def test_click_element(element_id: str):
        """Simulate a click on a UI element for chaos testing."""
        logger.info(f"[Test] Simulating click on: {element_id}")
        ui.run_javascript(f"document.getElementById('{element_id}')?.click()")
        return Response(status_code=200)

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

    start_background_gateways()
    asyncio.create_task(run_system_checks())
    if ZENA_MODE and rag_system:
        from config_system import config as sys_config # Resolve naming conflict
        index_internal_docs(Path(sys_config.BASE_DIR), rag_system)

def start_app():
    """Entry point for NiceGUI application."""
    import sys
    from settings import is_dark_mode
    from zombie_killer import prune_zombies
    
    # Check for port conflicts and handle "Zombie junk"
    # Auto-confirm kills to prevent terminal hang during startup
    # Skip if launched by Orchestrator (Server) to avoid killing the just-launched backend
    if not os.environ.get("ZENA_SKIP_PRUNE"):
        if not prune_zombies(auto_confirm=True):
            print("[!] Startup cancelled due to port conflict.")
            sys.exit(0)
    
    # --- Fix 1: NICEGUI_SCREEN_TEST_PORT KeyError ---
    if 'NICEGUI_SCREEN_TEST_PORT' not in os.environ:
        os.environ['NICEGUI_SCREEN_TEST_PORT'] = '8081'

    # --- Fix 2: pyttsx3 AttributeError on exit ---
    try:
        import pyttsx3
        if hasattr(pyttsx3, 'driver') and pyttsx3.driver:
            pass
    except:
        pass

    # Use saved dark mode preference
    ui.run(title='ZenAI', dark=is_dark_mode(), port=8080, reload=False)

if __name__ == "__main__":
    try:
        start_app()
    except Exception as e:
        import traceback
        error_msg = f"\n❌ FATAL ZENA UI ERROR: {e}\n"
        print(error_msg)
        
        # Log to file for silent crashes
        with open("ui_fatal_crash.txt", "w") as f:
            f.write(error_msg)
            traceback.print_exc(file=f)
            
        traceback.print_exc()
        input("⚠️ UI Crashed. Press Enter to Exit...")
        sys.exit(1)
