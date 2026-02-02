# -*- coding: utf-8 -*-
"""
zena.py - ZenAI AI Chat Interface
Elegant, professional chatbot with RAG capabilities
"""
import sys
import subprocess

from utils import format_message_with_attachment, normalize_input, sanitize_prompt, safe_print

# Safe NiceGUI installation (no auto-restart)
try:
    from nicegui import ui, app
except ImportError:
    safe_print("[!] NiceGUI not found. Installing...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "nicegui"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        safe_print("[✓] NiceGUI installed successfully. Please restart the application manually.")
        sys.exit(0)
    else:
        safe_print(f"[✗] Installation failed: {result.stderr}")
        sys.exit(1)

from nicegui import ui, app
import threading
import time
import logging
import os
import io
import asyncio
import json
import httpx
import requests
import numpy as np
from pathlib import Path

# Initialize Logger
logger = logging.getLogger("ZenAI")

# PDF Support
try:
    import pypdf
except ImportError:
    pypdf = None

# Import configuration and security
from config_system import config, EMOJI, load_config
from security import FileValidator
from zena_mode.resource_manager import resource_manager
from zena_mode.rag_manager import RAGManager

# Global RAG manager instance (wraps any underlying rag_system implementation)
rag_manager = RAGManager()
# Backwards compat alias
rag_system = rag_manager
try:
    _loaded_cfg = load_config() or {}
    class _ConfigProxy:
        def __init__(self, obj):
            self._obj = obj
        def get(self, key, default=None):
            try:
                return getattr(self._obj, key)
            except Exception:
                try:
                    return self._obj.get(key, default)
                except Exception:
                    return default
        def __getattr__(self, name):
            return getattr(self._obj, name)
    ZENA_CONFIG = _ConfigProxy(_loaded_cfg)
except Exception:
    ZENA_CONFIG = {}
from utils import format_message_with_attachment, normalize_input, sanitize_prompt, safe_print
from ui_components import setup_app_theme, setup_common_dialogs, setup_layout, GlassCapsule, SmartChips, LivingLogo
from ui.styles import Styles

# ... (rest of imports)

# Global Backend Instance
from nicegui import Client
from async_backend import AsyncBackend
async_backend = AsyncBackend()

@ui.page('/')
async def zenai_page(client: Client):
    """
    Main Chat Interface - ZenAI Flow
    """
    # 1. Initialize UI State
    app_state = {}
    
    # 2. Inject ZenAI Flow Global Styles (Mesh Gradient, Fonts)
    ui.add_head_html(Styles.GLOBAL_CSS)

    # 3. Initialize Shared Components
    # drawer = setup_layout(...) 
    # Initialize Dialogs first
    dialogs = setup_common_dialogs(async_backend, app_state)
    # Map 'rag' key for the drawer to find it
    dialogs['rag'] = dialogs.get('rag', None) # Ensure key exists if not created by common_dialogs

    async def scan_swarm():
        """Refresh the arbitrator's knowledge of live experts."""
        try:
            # 1. Warmup Logic (Background)
            if rag_system:
                try:
                    # Use ResourceManager to track background warmup thread
                    resource_manager.add_worker_thread(rag_system.warmup, daemon=True, max_workers=4)
                except Exception:
                    # Fallback to existing asyncio thread if resource manager refuses
                    asyncio.create_task(asyncio.to_thread(rag_system.warmup))
            await arbitrator.warmup()
            
            # 2. Discovery Logic
            await arbitrator.discover_swarm()
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

    
    # --- HEADER ("ZenAI Flow" Design) ---
    with ui.header().classes(Styles.HEADER + ' bg-transparent shadow-none border-none'):
        with ui.row().classes(Styles.HEADER_GLASS):
            # 1. Living Logo (Left)
            # Status state is toggled by method set_state()
            logo = LivingLogo()
            
            # Persist reference for animations
            # We attach it to ui_state if available, or app_state if not
            if 'ui_state' in locals():
                ui_state.logo = logo
            else:
                 # If ui_state is not yet defined, we might need a placeholder or just rely on local var if needed
                 # For now, we assume ui_state is defined in the scope (as seen in later lines)
                 pass
            
            # Brand Text
            with ui.column().classes('gap-0'):
                ui.label('ZenAI').classes('text-lg font-bold leading-none ' + Styles.TEXT_GRADIENT)
                ui.label('Flow State').classes(Styles.LABEL_MUTED + ' text-[10px]')
            
            # 2. Right Actions (Command Center)
            with ui.row().classes('ml-auto items-center gap-2'):
                # Help Button
                ui.button(icon='help_outline', on_click=lambda: add_message("system", "Try asking me to summarize a document or write some code!")) \
                    .props('flat round dense').classes(Styles.BTN_GHOST)
                
                # New Chat
                ui.button(icon='edit_square', on_click=lambda: ui.open('/')) \
                    .props('flat round dense').classes(Styles.BTN_GHOST)
                
                # Menu (Drawer Toggle)
                ui.button(icon='menu', on_click=lambda: rights_drawer.toggle()) \
                    .props('flat round dense').classes(Styles.BTN_GHOST)

    # --- RIGHT DRAWER (Settings) ---
    with ui.right_drawer().classes(Styles.DRAWER).props('overlay bordered behavior=mobile') as rights_drawer:
        with ui.column().classes('w-full gap-6 p-4'):
            
            # Header
            ui.label('Settings').classes('text-xl font-bold ' + Styles.TEXT_GRADIENT)
            
            # --- Missing Features Home ---
            # 1. Models
            with ui.row().classes(Styles.DRAWER_ITEM + ' cursor-pointer').on('click', lambda: dialogs['model'].open()):
                ui.icon('smart_toy').classes('text-blue-500')
                ui.label('Switch Models').classes('font-medium')
            
            # 2. RAG Knowledge
            with ui.row().classes(Styles.DRAWER_ITEM + ' cursor-pointer').on('click', lambda: dialogs['rag'].open()):
                ui.icon('database').classes('text-violet-500')
                ui.label('Knowledge Base').classes('font-medium')
                
            ui.separator()
            
            # 3. Reading Mode (TTS)
            with ui.row().classes('items-center justify-between w-full'):
                ui.label('Reading Voice').classes('font-medium')
                ui.switch().props('dense').bind_value(app_state, 'tts_enabled')
            
            # 4. Dark Mode
            with ui.row().classes('items-center justify-between w-full'):
                ui.label('Dark Mode').classes('font-medium')
                dark_mode = ui.dark_mode()
                # Load saved state
                if is_dark_mode():
                    dark_mode.enable()
                
                def toggle_dark_mode():
                    # Toggle visual theme
                    if dark_mode.value:
                        dark_mode.disable()
                        update_theme(False)
                        set_dark_mode(False)
                    else:
                        dark_mode.enable()
                        update_theme(True)
                        set_dark_mode(True)
                        
                ui.switch(value=is_dark_mode(), on_change=toggle_dark_mode).props('dense color=blue-6')

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
                
                # --- NEW: Precision Settings ---
                with ui.expansion('Precision Settings', icon='troubleshoot').classes('w-full mt-2'):
                    ui.label('Alpha (0=Keyword, 1=Semantic)').classes('text-xs ' + Styles.TEXT_SECONDARY)
                    ui.slider(min=0, max=1, step=0.1, value=rag_params['alpha']) \
                        .on('update:model-value', lambda e: rag_params.update({'alpha': e.value})) \
                        .props('label-always')
                    
                    ui.label('Re-rank Top N').classes('text-xs mt-2 ' + Styles.TEXT_SECONDARY)
                    ui.slider(min=1, max=10, step=1, value=rag_params['rerank_top_n']) \
                        .on('update:model-value', lambda e: rag_params.update({'rerank_top_n': e.value})) \
                        .props('label-always')
                    
                    ui.switch('Agentic Query Expansion', value=rag_params['expand_queries']) \
                        .on('update:model-value', lambda e: rag_params.update({'expand_queries': e.value})) \
                        .classes('mt-2')
                
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
                        async with httpx.AsyncClient() as client:
                            await client.get(url, timeout=5.0, headers={'User-Agent': 'ZenAI/1.0'})
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
                    
                    # --- NEW: Pre-flight Ethical Scan & UI Popup ---
                    try:
                        scanner = WebCrawlScanner()
                        report = await scanner.scan(url)
                        
                        # Background check notification
                        ui.notify(f"Pre-flight Scan: {report.reason}", color='info' if report.can_crawl else 'warning')
                        
                        # If blocked or issues found, show report dialog
                        if not report.can_crawl or report.bot_protection or report.metadata.get("cookie_banner_detected"):
                            with ui.dialog() as report_dialog, ui.card().classes('w-96'):
                                ui.label("Pre-flight Crawlability Report").classes('text-xl font-bold mb-2')
                                
                                status_color = "green" if report.can_crawl else "red"
                                ui.label(f"Status: {report.reason}").classes(f'text-{status_color}-600 font-bold mb-4')
                                
                                # Details
                                with ui.column().classes('gap-1 mb-4'):
                                    if report.metadata.get("high_difficulty"):
                                        ui.label("🔴 HIGH DIFFICULTY: This site actively blocks AI consumers.").classes('text-red-600 font-bold')
                                    if report.bot_protection:
                                        ui.label(f"🛡️ Protection: {report.bot_protection}").classes('text-orange-600')
                                    if report.metadata.get("cookie_banner_detected"):
                                        ui.label("🍪 Cookie Banner: Detected (will skip under-the-hood)").classes('text-blue-600')
                                    if report.requires_js:
                                        ui.label("🖥️ JS Required: Full content may not be available").classes('text-orange-600')
                                
                                with ui.row().classes('w-full justify-end gap-2'):
                                    ui.button("Cancel", on_click=report_dialog.close).props('flat')
                                    if report.can_crawl:
                                        ui.button("Proceed Anyway", on_click=lambda: (report_dialog.close(), _execute_scrape(url, max_pages))).props('color=primary')
                                    else:
                                        ui.button("Proceed (Risk of blocking)", on_click=lambda: (report_dialog.close(), _execute_scrape(url, max_pages))).props('flat color=red')
                            
                            report_dialog.open()
                            return # Wait for user decision
                        
                        # If totally clean, just proceed
                        await _execute_scrape(url, max_pages)
                        
                    except Exception as e:
                        logger.error(f"[RAG] Pre-flight failed: {e}")
                        await _execute_scrape(url, max_pages) # Fallback to trying directly

                async def _execute_scrape(url, max_pages):
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
                        documents = await resource_manager.run_in_thread_future(scraper.scrape, max_pages, progress_update, max_workers=8)
                        
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
                        documents = await resource_manager.run_in_thread_future(scanner.scan, limit, max_workers=8)

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
                        await resource_manager.run_in_thread_future(rag_system.build_index, documents, max_workers=4)
                        progress_bar.value = 0.9
                        
                        from pathlib import Path
                        rag_cache_path = ROOT_DIR / "rag_cache"
                        await resource_manager.run_in_thread_future(rag_system.save, rag_cache_path, max_workers=4)
                        
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
                # Original directory-based RAG (Non-ZenAI)
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
            
            # Check if there is text to speak
            text_to_speak = ui_state.last_response_text
            if not text_to_speak:
                # Fallback: Try to get from last message via DOM check (less reliable)
                ui.notify("No recent response to speak.", color='warning')
                return

            try:
                ui.notify("Speaking...", color='info')
                await resource_manager.run_in_thread_future(tts_engine.say, text_to_speak, max_workers=4)
                await resource_manager.run_in_thread_future(tts_engine.runAndWait, max_workers=4)
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
                # ZenAI-style colors
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
                    ai_name = 'ZenAI' if ZENA_MODE else locale.APP_NAME
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
        # Update Logo State to Thinking
        if hasattr(ui_state, 'logo') and ui_state.logo:
            ui_state.logo.set_state('thinking')
            
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
                    session_id=ui_state.session_id
                )
                if final_prompt != prompt:
                    logger.info(f"[Memory] Injected conversation context for session {ui_state.session_id}")
            except Exception as e:
                logger.warning(f"[Memory] Failed to build contextual prompt: {e}")
                final_prompt = prompt
        
        # Then add RAG context if enabled
        if rag_enabled['value'] and rag_system and rag_system.index:
            try:
                # Precision RAG: Use smart router for expansion and reranking if available
                if SMART_ROUTING_AVAILABLE and smart_router:
                    ui_state.status_text.text = "🤵 [Precise RAG] Expanding & Re-ranking..."
                    relevant_chunks = await smart_router.precise_rag_search(
                        prompt, 
                        rag_system, 
                        k=rag_params['rerank_top_n'],
                        alpha=rag_params['alpha'],
                        expand=rag_params['expand_queries']
                    )
                else:
                    # Fallback to basic hybrid search
                    relevant_chunks = rag_system.hybrid_search(prompt, k=5, alpha=rag_params['alpha'])
                
                if relevant_chunks:
                    # Spec Requirement: RAG Transparency (Subtle Blue Tint)
                    msg_ui.classes(remove=Styles.CHAT_BUBBLE_AI.split()[0], add=Styles.CHAT_BUBBLE_RAG)
                    
                    # Prepend RAG Indicator
                    full_text = locale.RAG_ANSWERED_FROM_SOURCE + "\n\n"
                    msg_ui.content = full_text
                    
                    # Build formatted context with [1] Source style and Relevance Badges
                    context_parts = []
                    sources_list = []
                    for i, c in enumerate(relevant_chunks, 1):
                         score = c.get('rerank_score', c.get('fusion_score', 0))
                         reason = c.get('rerank_reason', 'Top match')
                         
                         badge = f" [Relevance: {score:.1%}]" if score > 0 else ""
                         context_parts.append(f"[{i}] Source: {c.get('title', 'Untitled')}{badge}\n{c['text']}")
                         
                         source_meta = f"   *{reason}*" if reason else ""
                         sources_list.append(f"[{i}] **{c.get('title', 'Untitled')}** ({score:.1%})\n{source_meta}\n   📍 {c.get('url', 'N/A')}")
                    
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
            async for chunk in arbitrator.get_cot_response(final_prompt, "You are ZenAI, working within an Expert Swarm.", verbose=not is_quiet):
                if not ui_state.is_valid:
                    break
                full_text += chunk
                msg_ui.content = full_text
                msg_ui.classes(remove=Styles.LOADING_PULSE)
                ui_state.safe_update(msg_ui)
                await asyncio.sleep(0.02)
        elif app_state.get('use_smart_routing') and app_state['use_smart_routing'].value and SMART_ROUTING_AVAILABLE:
            # 🧠 Dual LLM Flow: Butler (Fast) + Master (Robust)
            try:
                # Update routing status
                if 'routing_status' in app_state:
                    app_state['routing_status'].text = '🤵 Butler thinking...'
                    ui_state.safe_update(app_state['routing_status'])
                
                # Stream both stages sequentially
                chunk_count = 0
                async for chunk in smart_router.stream_butler_master(final_prompt):
                    if not ui_state.is_valid:
                        break
                    chunk_count += 1
                    full_text += chunk
                    msg_ui.content = full_text
                    msg_ui.classes(remove=Styles.LOADING_PULSE)
                    ui_state.safe_update(msg_ui)
                    
                    # Periodic scroll to keep up with streaming
                    if chunk_count % 10 == 0:
                        ui_state.safe_scroll()
                    
                    await asyncio.sleep(0.01)
                
                logger.info(f"[DualLLM] Complete: {chunk_count} chunks")
                if 'routing_status' in app_state:
                    app_state['routing_status'].text = '✅ Master complete'
                    ui_state.safe_update(app_state['routing_status'])
                
            except Exception as e:
                logger.error(f"[Router] Smart routing failed: {e}, falling back to standard")
                # Fallback to standard backend
                full_text = f"*[⚠️ Router fallback: {str(e)[:50]}]*\n\n"
                async with async_backend:
                    async for chunk in async_backend.send_message_async(final_prompt):
                        if not ui_state.is_valid:
                            break
                        full_text += chunk
                        msg_ui.content = full_text
                        msg_ui.classes(remove=Styles.LOADING_PULSE)
                        ui_state.safe_update(msg_ui)
                        await asyncio.sleep(0.02)
        else:
            # Orchestrator / Standard Streaming
            try:
                chunk_count = 0
                async with async_backend:
                    # Use Orchestrator if available (V2 Architecture)
                    # Use Orchestrator if available (V2 Architecture)
                    if orchestrator:
                        # V2: Orchestrator handles system prompt internall or we pass a refined one
                        sys_prompt = """You are ZenAI, a helpful AI assistant.
1. USE RAG contexts to answer questions about 'ZenAI', 'models', 'settings', or 'how to'.
2. If the user asks for help using this app, refer to the [User Manual] sections in the context.
3. Be concise and helpful."""
                        stream_gen = orchestrator.route_and_execute(final_prompt, sys_prompt)
                        logger.info("[UI] Using Orchestrator Routing")
                    else:
                        stream_gen = async_backend.send_message_async(final_prompt)
                    
                    async for chunk in stream_gen:
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
        
        # Reset Logo State
        if hasattr(ui_state, 'logo') and ui_state.logo:
            ui_state.logo.set_state('idle')
        
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
                
                # [NEW] Capture full response for TTS
                ui_state.last_response_text = full_text

                # --- Hallucination Verification (Integration) ---
                if rag_enabled['value'] and 'relevant_chunks' in locals() and relevant_chunks:
                     try:
                         # Run verification in background thread to keep UI responsive
                         # We use the existing 'arbitrator' instance if available
                         if 'arbitrator' in globals() and arbitrator:
                             verification_result = await resource_manager.run_in_thread_future(
                                 arbitrator.verify_hallucination,
                                 full_text,
                                 [c['text'] for c in relevant_chunks],
                                 max_workers=4
                             )
                             
                             v_score = verification_result.get('score', 1.0)
                             
                             if v_score >= 0.8:
                                 # High Confidence
                                 badge = f"\n\n> [!TIP]\n> **Verified ✅**\n> Response checks out against sources. (Score: {v_score:.0%})"
                             elif v_score < 0.6:
                                 # Low Confidence
                                 badge = f"\n\n> [!WARNING]\n> **Uncertain ⚠️**\n> Potential hallucination or weak support from context. (Score: {v_score:.0%})"
                             else:
                                 # Neutral
                                 badge = f"\n\n> [!NOTE]\n> **Plausible ℹ️**\n> Partially supported by context. (Score: {v_score:.0%})"
                                 
                             full_text += badge
                             msg_ui.content = full_text
                             ui_state.safe_update(msg_ui)
                             
                             if v_score < 0.6:
                                 logger.warning(f"[Verification] Flagged response (Score {v_score}): {verification_result.get('unsupported', [])}")
                     except Exception as ve:
                         logger.error(f"[Verification] Check failed: {ve}")
                
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
        """Extracts text from raw bytes using the Advanced Hybrid Extractor."""
        text = ""
        try:
            ext = filename.lower()
            # 1. Check if it's a PDF or Image for universal_extractor
            is_heavy = ext.endswith('.pdf') or any(ext.endswith(img_ext) for img_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'])
            
            if is_heavy and universal_extractor:
                try:
                    chunks, stats = universal_extractor.process(raw_data, filename=filename)
                    if chunks:
                        text = "\n\n".join([c.text for c in chunks])
                        logger.info(f"[Extractor] Extracted {len(text)} chars from {filename}")
                    else:
                        text = f"[No text found in {filename}]"
                except Exception as e:
                    logger.error(f"[Extractor] Failed to extract from {filename}: {e}")
                    text = f"[Error processing file: {e}]"
            else:
                # 2. Standard text/binary handling
                if b'\x00' in raw_data[:1024] and not ext.endswith('.txt'):
                     text = f"[Attached binary file: {filename}]"
                else:
                     text = raw_data.decode('utf-8', errors='replace')
        except Exception as e:
             logger.error(f"[Upload] Extraction failed: {e}")
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
            
            audio_data = await resource_manager.run_in_thread_future(record, max_workers=4)
            
            # Convert to WAV in memory
            ui_state.status_text.text = locale.CHAT_TRANSCRIBING
            ui_state.status_text.classes(Styles.TEXT_WARNING)
            
            wav_buffer = io.BytesIO()
            wav.write(wav_buffer, fs, audio_data)
            wav_buffer.seek(0)
            
            # Send to Backend API
            # Note: start_llm.py endpoint expects data in body
            async with httpx.AsyncClient() as client:
                response = await client.post("http://127.0.0.1:8001/voice/transcribe", content=wav_buffer.read(), timeout=10.0)
            
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

    # Footer (Glass Capsule - Floating)
    # The actual input area is now a floating island, not a full-width bar
    msg_state = {'current': ''}
    
    # Invisible footer container just to hold the floating element
    # Footer (ZenAI Flow Capsule)
    # The actual input area is now a floating island, not a full-width bar
    with ui.footer().classes('bg-transparent border-none p-0 w-full pointer-events-none mb-6 z-50'):
        with ui.column().classes('mx-auto w-full max-w-3xl pointer-events-auto items-center gap-0'):
            # 1. Smart Chips (Context Aware)
            # We map chip clicks to populate the capsule input
            def on_chip_click(text):
                if capsule and capsule.input_element:
                    capsule.input_element.value = text
                    capsule.input_element.run_method('focus')
            
            chips = SmartChips(on_click=on_chip_click)
            
            # 2. Glass Capsule (Cockpit)
            async def on_send_wrapper(text):
                await stream_response(text)
                
            capsule = GlassCapsule(on_send=on_send_wrapper)
            
            # Capture references for external access (e.g., voice transcription)
            ui_state.user_input = capsule.input_element
            handlers['send'] = capsule.handle_send

    # Apply Dark Mode on Initial Load
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

        add_message("system", locale.format('WELCOME_ZENAI', source_msg=source_msg))
    else:
        add_message("system", locale.WELCOME_DEFAULT)
    # Guided Chips (Floating)
    def add_guided_chips():
        """Add context-aware suggestion chips."""
        chips_data = [
            {'label': locale.CHIP_SUMMARIZE, 'icon': 'summarize', 'prompt': 'Summarize this please.'},
            {'label': locale.CHIP_EXPLAIN, 'icon': 'psychology', 'prompt': 'Explain this concept simply.'},
            {'label': locale.CHIP_CODE, 'icon': 'code', 'prompt': 'Write python code for...'},
            {'label': locale.CHIP_ANALYZE, 'icon': 'analytics', 'prompt': 'Analyze this data.'}
        ]
        
        # Floating above footer (Z-index high)
        with ui.row().classes('fixed bottom-[90px] left-0 right-0 justify-center gap-2 z-40 pointer-events-none'):
            for chip in chips_data:
                # Pointer events auto to make clickable
                def chip_click(p=chip['prompt']):
                    ui_state.user_input.value = p
                    # Focus input? NiceGUI focus() not always reliable on mobile
                
                ui.chip(chip['label'], icon=chip['icon'], on_click=chip_click) \
                    .classes('glass bg-white/50 dark:bg-slate-800/50 backdrop-blur-md shadow-sm border border-white/20 hover:bg-white/80 dark:hover:bg-slate-700/80 transition-all cursor-pointer pointer-events-auto') \
                    .props('clickable dense')

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

    # --- Fix 2: pyttsx3 Shutdown Safety ---
    # Monkey-patch to suppress the specific output error on shutdown
    try:
        import pyttsx3.driver
        original_del = pyttsx3.driver.DriverProxy.__del__
        def safe_del(self):
            try:
                original_del(self)
            except:
                pass
        pyttsx3.driver.DriverProxy.__del__ = safe_del
    except:
        pass
        
    app.on_shutdown(lambda: cleanup_resources())

    # --- Unified Startup: Check for Backend ---
    import socket
    import subprocess
    import shutil
    import time
    
    def is_port_open(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    if not is_port_open(8001):
        safe_print(f"\n{EMOJI['rocket']} Backend offline. Initiating Self-Orchestrated Startup...")
        safe_print("    [1/2] Launching Engine (start_llm.py --no-ui)...")
        
        # Spawn backend in background
        subprocess.Popen([sys.executable, 'start_llm.py', '--no-ui'])
        
        # Wait for backend (Splash Logic can go here)
        safe_print("    [2/2] Waiting for Engine API...", end='', flush=True)
        retries = 0
        while not is_port_open(8001) and retries < 45:
            time.sleep(1)
            safe_print(".", end='', flush=True)
            retries += 1
            
        if is_port_open(8001):
            safe_print(f" [OK]\n{EMOJI['check']} Backend Online! Launching UI...")
        else:
            safe_print(f" [TIMEOUT]\n{EMOJI['error']} Error: Backend failed to start in 45s. Check nebula_engine.log")
            # We continue anyway, letting the UI show connection errors rather than crashing hard


    def cleanup_resources():
        """Clean up resources on shutdown to prevent errors."""
        global tts_engine
        if tts_engine:
            try:
                tts_engine.stop()
            except: pass
            
    # --- Fix 3: Robust Port Selection ---
    import socket
    def find_free_port(start_port, max_tries=10):
        for port in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        return None

    # Check if a specific port is requested via environment variable (for testing)
    requested_port = os.environ.get('ZENAI_PORT')
    if requested_port:
        try:
            target_port = int(requested_port)
            logger.info(f"Using requested port: {target_port}")
        except ValueError:
            logger.error(f"Invalid ZENAI_PORT: {requested_port}. Falling back to auto-discovery.")
            target_port = find_free_port(8080)
    else:
        # Check preferred ports
        target_port = find_free_port(8080)

    if not target_port:
         safe_print(f"\n{EMOJI['error']} CRITICAL: No free ports found between 8080-8090! Please close other instances.")
         sys.exit(1)
    
    if target_port != 8080:
        logger.warning(f"Port 8080 in use. Using port {target_port} instead.")
        # Update test port env var if running tests
        if 'NICEGUI_SCREEN_TEST_PORT' in os.environ:
             os.environ['NICEGUI_SCREEN_TEST_PORT'] = str(target_port)

    # Network Access Configuration
    host = '127.0.0.1' # Default localhost only
    if ZENA_CONFIG.get('network_access', False):
        host = '0.0.0.0'
        # Get Local IP to show user
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                safe_print(f"\n📱 Mobile Access Enabled! Connect via: http://{local_ip}:{target_port}")
        except:
            safe_print(f"\n📱 Mobile Access Enabled! Try your LAN IP on port {target_port}")

    # Use saved dark mode preference
    ui.run(title='ZenAI', dark=is_dark_mode(), port=target_port, host=host, reload=False)

if __name__ == "__main__":
    start_app()
