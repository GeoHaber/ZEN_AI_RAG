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

# Import async backend
from async_backend import AsyncNebulaBackend

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

# Import state management
from state_management import attachment_state, chat_history, handle_error

# TTS Setup
tts_engine = None
if pyttsx3:
    try:
        tts_engine = pyttsx3.init()
    except:
        pass

# UI state
chat_log = None 
status_text = None
attachment_preview = None
user_input = None

@ui.page('/')
async def nebula_page():
    global chat_log, status_text, attachment_preview, user_input
    
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

            

            
    # --- MAIN CONTENT ---
    # --- THEME MANAGEMENT ---
    # Initialize Dark Mode (default to system preference or False)
    dark_mode = ui.dark_mode()
    
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
            
            # Update specific Quasar classes if needed
            ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
        else:
            if header: header.props(remove='dark')
            if drawer: drawer.props(remove='dark')
            if footer: footer.props(remove='dark')
            
            ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
            
        # Update chart colors or other non-reactive elements here if present
        pass

    # --- LAYOUT ---
    # Header (Light theme with blue accent)
    with ui.header().classes('bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 p-4 shadow-sm text-gray-800 dark:text-gray-100') as header:
        # Toggle sidebar
        ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat').classes('text-gray-700 dark:text-white')
        
        # Theme Toggle - Rewritten to use direct prop application
        def toggle_dark_mode():
            if dark_mode.value is True:
                dark_mode.disable()
                update_theme(False)
            else:
                dark_mode.enable()
                update_theme(True)
        
        ui.button(on_click=toggle_dark_mode, icon='dark_mode').props('flat').classes('text-gray-700 dark:text-white').tooltip('Toggle Dark Mode')
        
        # Scan & Read Button (Enhanced for Zena mode)
        # Create dialog ONCE - Opaque background for visibility
        with ui.dialog() as rag_dialog, ui.card().classes('p-6 w-96 bg-white dark:bg-slate-800 shadow-2xl'):
            if ZENA_MODE:
                ui.label('Scan & Read').classes('text-xl font-bold mb-4 text-gray-900 dark:text-white')
                
                # Mode selector
                mode_select = ui.select(['Website', 'Local Directory'], value='Website', label='Source Type').props('outlined').classes('w-full mb-3')
                
                # Website inputs
                website_input = ui.input('Website URL', value=ZENA_CONFIG.get('website_url', '')).props('outlined input-class="text-black dark:text-white"').classes('w-full mb-2')
                pages_input = ui.input('Max Pages', value='50').props('outlined input-class="text-black dark:text-white"').classes('w-full mb-2')
                
                # Directory inputs (hidden by default)
                dir_input = ui.input('Directory Path', placeholder='C:/Users/YourName/Documents').props('outlined input-class="text-black dark:text-white" visible=false').classes('w-full mb-2')
                files_input = ui.input('Max Files', value='1000').props('outlined input-class="text-black dark:text-white" visible=false').classes('w-full mb-2')
                
                # Toggle visibility based on mode
                def on_mode_change():
                    is_website = mode_select.value == 'Website'
                    website_input.props(f'visible={is_website}')
                    pages_input.props(f'visible={is_website}')
                    dir_input.props(f'visible={not is_website}')
                    files_input.props(f'visible={not is_website}')
                
                mode_select.on('update:model-value', on_mode_change)
                
                # Progress indicators
                # Progress indicators - Enhanced Visibility
                progress_label = ui.label('').classes('text-md font-bold text-blue-600 dark:text-blue-400 mb-2')
                progress_bar = ui.linear_progress(value=0, show_value=False).classes('mb-4 h-4 rounded').props('visible=false color=primary track-color=grey-3')
                
                async def start_website_scan():
                    url = normalize_input(website_input.value, 'url')
                    if not url:
                        ui.notify("Please enter a website URL", color='warning')
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
                        ui.notify(f"Cannot access website: {e}", color='negative')
                        return

                    try:
                        max_pages = int(pages_input.value)
                    except:
                        max_pages = 50
                    
                    # Show progress (Safe update)
                    try:
                        progress_bar.props('visible=true')
                        progress_label.text = f"🔍 Scanning {url}..."
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
            status = "enabled" if e.value else "disabled"
            color = "positive" if e.value else "info"
            ui.notify(f"RAG mode {status}", color=color)
            logger.info(f"[RAG] Mode {status}")
        
        # Scan & Read Toggle Switch (renamed)
        rag_switch = ui.switch('Enable Scan & Learn (RAG)', value=False, on_change=toggle_rag).props('color=cyan keep-color').classes('ml-2 text-gray-700 dark:text-white font-medium')
        
        # TTS Button
        async def speak_last_response():
            if not tts_engine:
                ui.notify("TTS not available (pyttsx3 missing)", color='warning')
                return
            try:
                # Get last AI message from chat log
                # TODO: Store last AI response in a variable
                ui.notify("Speaking last response...", color='info')
                await asyncio.to_thread(tts_engine.say, "Text-to-speech feature coming soon")
                await asyncio.to_thread(tts_engine.runAndWait)
            except Exception as e:
                logger.error(f"[TTS] Error: {e}")
                ui.notify(f"TTS error: {e}", color='negative')
        
        ui.button('TTS', icon='volume_up', on_click=speak_last_response).props('flat').classes('text-blue-600 dark:text-blue-400')
        status_text = ui.label('Ready').classes('text-gray-600 dark:text-gray-400 text-sm ml-auto')

    # Chat Area (Light background)
    with ui.column().classes('w-full max-w-4xl mx-auto flex-1 overflow-auto p-4 space-y-4 pb-24 bg-gray-50 dark:bg-slate-950') as chat_log_container:
        chat_log = chat_log_container

    # Add message to chat (Zena Style - Light theme with circular avatar)
    def add_message(role: str, content: str):
        with chat_log:
            with ui.row().classes('w-full justify-end' if role == 'user' else 'w-full justify-start'):
                # Zena-style colors (light theme)
                if role == 'user':
                    color = 'bg-blue-500 text-white'
                else:
                    color = 'bg-gray-100 dark:bg-slate-800 text-gray-900 dark:text-gray-100'
                
                align = 'items-end' if role == 'user' else 'items-start'
                
                # Add circular avatar for AI messages (Zena-style)
                if role != 'user':
                    ai_initial = 'Z' if ZENA_MODE else 'N'
                    ui.avatar(ai_initial, color='primary', text_color='white').classes('w-10 h-10 mr-2')
                
                with ui.column().classes(align):
                    ai_name = 'Zena' if ZENA_MODE else 'ZenAI'
                    ui.label('You' if role == 'user' else ai_name).classes('text-xs text-gray-500 dark:text-gray-400 mb-1 ml-1 mr-1')
                    ui.markdown(content).classes(f'{color} px-5 py-3 rounded-3xl max-w-3xl shadow-sm text-md leading-relaxed')
        # Auto-scroll handled by scroll_to_bottom if needed, but NiceGUI/Vue does it often auto
        # We can force scroll:
        ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
    
    # Guided Task Chips (Zena-style - Pill-shaped)
    def add_guided_chips():
        with chat_log:
            ui.label('Quick Actions').classes('text-xs text-gray-600 mb-2 mt-4')
            with ui.row().classes('gap-2 flex-wrap mb-4'):
                async def chip_action(text):
                    user_input.value = text
                    if handlers['send']:
                        await handlers['send']()
                
                # Pill-shaped buttons (fully rounded)
                chip_classes = 'rounded-full border-2 border-blue-500 text-blue-600 dark:text-blue-400 px-4 py-2 hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors'
                ui.button('Check Model Status', on_click=lambda: chip_action('What models are available?')).classes(chip_classes).props('outline size=sm')
                ui.button('Latest llama.cpp', on_click=lambda: chip_action('Check llama.cpp version')).classes(chip_classes).props('outline size=sm')
                ui.button('Run Benchmark', on_click=lambda: chip_action('Run a performance benchmark')).classes(chip_classes).props('outline size=sm')
                ui.button('Help', on_click=lambda: chip_action('What can you help me with?')).classes(chip_classes).props('outline size=sm')

    # Streaming response
    # RAG toggle state and handler references (mutable containers for closure access)
    rag_enabled = {'value': False}
    handlers = {'send': None}  # Will hold reference to handle_send after footer creates it
    
    async def stream_response(prompt: str):
        prompt = sanitize_prompt(prompt)
        add_message('user', prompt)
        status_text.text = 'Thinking...'
        
        # Create empty bot message (light theme)
        with chat_log:
            with ui.row().classes('w-full justify-start'):
                with ui.column().classes('w-full max-w-3xl'):
                    msg_ui = ui.markdown("").classes('bg-gray-100 text-gray-900 p-4 rounded-3xl shadow-sm animate-pulse w-full')
                    sources_ui = ui.column().classes('w-full')
        
        full_text = ""
        
        # Build prompt with RAG context if enabled
        final_prompt = prompt
        if rag_enabled['value'] and rag_system and rag_system.index:
            try:
                # Query RAG for relevant context
                relevant_chunks = rag_system.search(prompt, k=5)
                
                if relevant_chunks:
                    # Spec Requirement: RAG Transparency (Subtle Blue Tint)
                    msg_ui.classes(remove='bg-gray-100', add='bg-blue-50 dark:bg-slate-800 border-l-4 border-blue-500 shadow-md')
                    
                    # Prepend RAG Indicator
                    full_text = "**🔍 Answered from Data Source**\n\n"
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
        
        # Use async backend for streaming
        async with async_backend:
            async for chunk in async_backend.send_message_async(final_prompt):
                full_text += chunk
                msg_ui.content = full_text
                msg_ui.classes(remove='animate-pulse')
                msg_ui.update()
        
        # Append Sources Footer if RAG was used
        if rag_enabled['value'] and 'relevant_chunks' in locals() and relevant_chunks:
             with sources_ui:
                 with ui.expansion('📂 View Source Data', icon='source').classes('w-full bg-blue-50 dark:bg-slate-900 rounded-xl mt-2'):
                     with ui.column().classes('gap-1 p-2'):
                         for i, c in enumerate(relevant_chunks, 1):
                             title = c.get('title', 'Untitled')
                             url = c.get('url', 'N/A')
                             # Handle Link vs Path
                             # Handle Link vs Path
                             if url.startswith('http'):
                                 ui.link(f"[{i}] {title}", url).classes('text-blue-600 underline text-sm block')
                             else:
                                 ui.label(f"[{i}] {title}").classes('font-bold text-sm text-gray-700 dark:text-gray-300 block')
                                 ui.label(f"📍 {url}").classes('text-xs text-gray-500 ml-4 break-all block')
                             
                             # DEBUG: Show text preview to verify what LLM sees
                             text_preview = c.get('text', '').strip()[:300].replace('\n', ' ')
                             ui.label(f"📝 \"{text_preview}...\"").classes('text-xs text-gray-500 dark:text-gray-400 italic ml-4 mb-2 border-l-2 border-gray-300 pl-2 block')

        status_text.text = 'Ready'

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
            
            attachment_preview.text = f"📎 {name} ({len(content)} chars)"
            attachment_preview.visible = True
            ui.notify(f"Attached {name}", color='positive')
            logger.info(f"[Upload] Successfully attached {name}")
        except Exception as ex:
            logger.error(f"[Upload] Error: {ex}")
            ui.notify(f"Upload failed: {ex}", color='negative')

    # Voice Handler
    async def on_voice_click():
        if not sd:
            ui.notify("Error: SoundDevice not found (Headless?)", color='red')
            return
            
        status_text.text = '🔴 Recording (5s)...'
        status_text.classes('text-red-500 animate-pulse')
        
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
            status_text.text = 'Transcribing...'
            status_text.classes('text-yellow-400')
            
            wav_buffer = io.BytesIO()
            wav.write(wav_buffer, fs, audio_data)
            wav_buffer.seek(0)
            
            # Send to Backend API
            # Note: start_llm.py endpoint expects data in body
            response = await asyncio.to_thread(requests.post, "http://127.0.0.1:8001/voice/transcribe", data=wav_buffer.read())
            
            if response.status_code == 200:
                transcription = response.json().get('text', '')
                if transcription:
                    user_input.value += transcription + " "
                    ui.notify("Transcribed!", color='green')
                else:
                    ui.notify("No speech detected", color='orange')
            else:
                ui.notify(f"Transcription Failed: {response.text}", color='red')
                
        except Exception as e:
            ui.notify(f"Voice Error: {e}", color='red')
        finally:
            status_text.text = 'Ready'
            status_text.classes(remove='text-red-500 animate-pulse text-yellow-400')
            status_text.classes('text-gray-400')

    # Footer (Standard Polish)
    with ui.footer().classes('bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 p-4 w-full flex justify-center') as footer:
        with ui.column().classes('w-full max-w-4xl'):
            # Attachment Preview
            attachment_preview = ui.label('').classes('text-blue-600 dark:text-blue-400 text-sm mb-2 bg-blue-50 dark:bg-gray-800 px-3 py-1 rounded-full shadow-sm self-start').props('visible=false')
            
            # Input Bar Container
            with ui.row().classes('w-full gap-2 items-center p-2 pr-2 px-4 rounded-3xl bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all'):
                
                # --- File Upload (Hidden Pattern) ---
                # 1. The actual uploader is hidden
                uploader = ui.upload(on_upload=on_upload, auto_upload=True).classes('hidden')
                
                # 2. A clean button triggers it
                ui.button(on_click=lambda: uploader.run_method('pickFiles'), icon='attach_file') \
                    .props('flat round dense') \
                    .classes('text-gray-500 dark:text-gray-400 hover:text-blue-600')
                
                # Input Field
                placeholder_text = 'Message ZenAI...' if not ZENA_MODE else 'Ask me anything...'
                user_input = ui.input(placeholder=placeholder_text).props('borderless dense input-style="min-height: 24px"').classes('flex-1 text-gray-900 dark:text-white text-base')
                
                # Define send handler AFTER user_input exists (closure fix)
                async def handle_send(e=None):
                    """Handle send button click or Enter key press."""
                    logger.info("[UI] handle_send triggered")
                    text = user_input.value.strip() if user_input.value else ""
                    
                    if not text:
                        return
                    
                    # Add attachment if present
                    if attachment_state.has_attachment():
                        name, content, _ = attachment_state.get()
                        text = format_message_with_attachment(text, name, content)
                        attachment_state.clear()
                        attachment_preview.visible = False
                        attachment_preview.text = ""
                    
                    user_input.value = ""
                    await stream_response(text)
                
                # Store handler reference for chip_action to use
                handlers['send'] = handle_send
                
                user_input.on('keydown.enter.prevent', handle_send)
                
                # Actions
                ui.button(icon='mic', on_click=on_voice_click).props('flat round dense icon-size=24px').classes('text-gray-400 dark:text-gray-500 hover:text-blue-600')
                ui.button(icon='arrow_upward', on_click=handle_send).props('round dense unelevated').classes('bg-blue-600 text-white w-10 h-10 hover:bg-blue-700')

    # Apply Dark Mode on Initial Load (since ui.run has dark=True)
    # This must be called AFTER all UI elements are created
    update_theme(True)

    # Initial Welcome (Dynamic based on mode)
    if ZENA_MODE:
        rag_source = ZENA_CONFIG.get('rag_source', 'knowledge_base')
        
        if rag_source == 'website':
             source_val = ZENA_CONFIG.get('website_url', 'configured website')
             source_msg = f"I scanned the website: **{source_val}**"
        elif rag_source == 'filesystem':
             source_val = ZENA_CONFIG.get('directory_path', 'local directory')
             source_msg = f"I scanned the local directory: **{source_val}**"
        else:
             source_msg = "I have access to your configured **Knowledge Base**"

        add_message("system", f"👋 **Welcome to ZenAI!**\n\n{source_msg}. I can help you with:\n- Answering questions about the content\n- Finding information quickly\n- Providing guidance\n\n*Ask me about it if you want!*")
    else:
        add_message("system", "👋 **Welcome to ZenAI!**\n\nI'm your AI assistant powered by NiceGUI. I can help you with:\n- Managing AI models\n- Analyzing code files\n- Running benchmarks\n- Voice transcription\n\n*Remember, I'm still learning and improving!*")
    add_guided_chips()

def start_app():
    """Entry point for NiceGUI application."""
    # Clear any pytest-related NiceGUI environment variables that may cause issues
    # Clear NiceGUI environment variables only if NOT running in pytest
    # (NiceGUI requires NICEGUI_SCREEN_TEST_PORT if pytest is loaded)
    import sys
    if 'pytest' in sys.modules:
        # We are in a test environment. Ensure the port var exists to prevent KeyError
        if 'NICEGUI_SCREEN_TEST_PORT' not in os.environ:
            os.environ['NICEGUI_SCREEN_TEST_PORT'] = '8081'
    else:
        # Production run: Aggressively clear potential leakage
        for key in list(os.environ.keys()):
            if key.startswith('NICEGUI_'):
                del os.environ[key]
    
    ui.run(title='ZenAI', dark=True, port=8080, reload=False)

if __name__ == "__main__":
    start_app()
