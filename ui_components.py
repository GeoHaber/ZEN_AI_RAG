from nicegui import ui
import logging
import asyncio
import requests
import subprocess
from utils import normalize_input
import time

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
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        if (document.body.classList.contains('body--dark')) {
                            document.documentElement.classList.add('dark');
                        } else {
                            document.documentElement.classList.remove('dark');
                        }
                    }
                });
            });
            
            // Start observing after load
            document.addEventListener('DOMContentLoaded', () => {
                observer.observe(document.body, { attributes: true });
                // Initial check
                if (document.body.classList.contains('body--dark')) {
                    document.documentElement.classList.add('dark');
                }
            });
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
            /* Dark Menu */
            .body--dark .q-menu { 
                background: #1e293b !important; 
                color: #f1f5f9 !important; 
                border: 1px solid #334155; 
            }
            .body--dark .q-item { color: #f1f5f9 !important; }
            .body--dark .q-item--active { background: #334155 !important; color: #60a5fa !important; }

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
        </style>
    ''')

def setup_common_dialogs(backend, app_state):
    """
    Creates reusable dialogs (Model Download, Llama Update).
    Returns a dict referencing them: {'model': dialog, 'llama': dialog}
    """
    dialogs = {}

    # --- Model Download Dialog ---
    with ui.dialog() as model_dialog, ui.card().classes('p-6 w-96 bg-white dark:bg-slate-800 shadow-2xl'):
        ui.label('Download New Model').classes('text-xl font-bold mb-4 text-gray-900 dark:text-white')
        
        repo_input = ui.input('HuggingFace Repo ID', placeholder='e.g. Qwen/Qwen2.5-7B-Instruct-GGUF').classes('w-full mb-3 text-gray-900 dark:text-white').props('outlined input-class="text-gray-900 dark:text-white"')
        file_input = ui.input('GGUF Filename', placeholder='e.g. qwen2.5-7b-instruct-q4_k_m.gguf').classes('w-full mb-4 text-gray-900 dark:text-white').props('outlined input-class="text-gray-900 dark:text-white"')
        
        async def run_smart_download():
            repo = repo_input.value.strip()
            filename = normalize_input(file_input.value, 'filename')
            
            if not repo or not filename:
                ui.notify("Please enter Repo ID and Filename", color='warning')
                return
            
            model_dialog.close()
            ui.notify(f"Starting background download for {filename}...", color='info')
            
            try:
                response = await asyncio.to_thread(
                    requests.post,
                    "http://127.0.0.1:8002/models/download",
                    json={"repo_id": repo, "filename": filename},
                    timeout=5
                )
                if response.status_code == 200:
                        ui.notify(f"✅ Download started! Status: {response.json().get('status')}", color='positive')
                        backend.get_models() 
                        # Update model_select if available
                        if 'model_select' in app_state and app_state['model_select']:
                             app_state['model_select'].options = backend.get_models()
                             app_state['model_select'].update() 
                else:
                        ui.notify(f"❌ Download failed: {response.text}", color='negative')
            except Exception as e:
                ui.notify(f"❌ Error: {e}", color='negative')

        ui.button('Download', on_click=run_smart_download).props('color=primary').classes('w-full')
        ui.button('Cancel', on_click=model_dialog.close).props('flat').classes('w-full mt-2')

    dialogs['model'] = model_dialog

    # --- Llama Update Dialog ---
    with ui.dialog() as llama_dialog, ui.card().classes('p-6 w-96 bg-white dark:bg-slate-800 shadow-2xl'):
            ui.label('Update Engine').classes('text-xl font-bold mb-4 text-gray-900 dark:text-white')
            llama_info = ui.label("Loading...").classes('mb-4 text-gray-700 dark:text-slate-300')
            
            async def run_update():
                llama_dialog.close()
                ui.notify("Update requires manual download currently. Opening GitHub...", color='info')
                await asyncio.to_thread(lambda: subprocess.Popen(["explorer", "https://github.com/ggerganov/llama.cpp/releases/latest"]))

            ui.button('Get Update (GitHub)', on_click=run_update).props('color=primary').classes('w-full')
            ui.button('Cancel', on_click=llama_dialog.close).props('flat').classes('w-full mt-2')

            # We need to expose llama_info so checking function can update it.
            llama_dialog.info_label = llama_info

    dialogs['llama'] = llama_dialog
    
    return dialogs
    



def setup_drawer(backend, async_backend, rag_system, config, dialogs, ZENA_MODE, EMOJI, app_state):
    # Retrieve dialogs
    model_dialog = dialogs.get('model')
    llama_dialog = dialogs.get('llama')
    # Use info_label if available
    llama_info = getattr(llama_dialog, 'info_label', None) if llama_dialog else None

    # --- LEFT SIDEBAR (Drawer) - Light Theme ---
    # Fix: Use explicit background classes. NiceDrawer doesn't support bind_prop for 'dark' easily.
    # We rely on the global 'dark' class on body to trigger 'dark:bg-gray-900'.
    with ui.left_drawer(value=True).classes('bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 p-5 shadow-lg text-gray-900 dark:text-gray-100').props('width=260 bordered') as drawer:
        # Logo Area with Circular Avatar (Zena Style)
        with ui.row().classes('items-center gap-3 mb-6'):
            # Circular avatar
            ui.avatar('Z' if ZENA_MODE else 'N', color='primary', text_color='white').classes('text-xl')
            # Dynamic branding
            app_name = 'Zena' if ZENA_MODE else 'Nebula AI'
            ui.label(app_name).classes('text-2xl font-bold text-blue-600')
        
        # 1. Model Manager Section
        ui.label('MODEL MANAGER').classes('text-sm font-bold mb-3 text-primary')
        
        # Model Selector with change notification
        current_models = backend.get_models()
        
        async def on_model_change(e):
            """Show popup when model changes."""
            new_model = e.value
            if new_model:
                # Show loading notification
                ui.notify(f"🔄 Loading model: {new_model}...", color='info', position='top', timeout=2000)
                
                # Call Hub API to switch model (if endpoint exists)
                try:
                    response = await asyncio.to_thread(
                        requests.post,
                        "http://127.0.0.1:8002/models/load",
                        json={"model": new_model},
                        timeout=30
                    )
                    if response.status_code == 200:
                        ui.notify(f"✅ Model ready: {new_model}", color='positive', position='top', timeout=3000)
                    else:
                        # API might not have /load endpoint, just confirm selection
                        ui.notify(f"✅ Active model set: {new_model}", color='positive', position='top', timeout=3000)
                except Exception:
                    # If no API endpoint, just confirm the UI selection
                    ui.notify(f"✅ Active model: {new_model}", color='positive', position='top', timeout=3000)
        
        model_select = ui.select(current_models, value=current_models[0] if current_models else None, label="Active Model", on_change=on_model_change).classes('w-full mb-3 text-gray-900 dark:text-white').props('outlined input-class="text-gray-900 dark:text-white" popup-content-class="text-gray-900 dark:text-white bg-white dark:bg-slate-800"')
        app_state['model_select'] = model_select
        
        with ui.expansion('Download New Model', icon='download').classes('w-full mb-4 bg-blue-50 dark:bg-slate-800'):
            with ui.column().classes('w-full gap-2 p-3'):
                # Popular Model Presets
                ui.label('Quick Downloads').classes('text-xs font-bold text-gray-600 dark:text-gray-300')
                
                popular_models = [
                    ("Qwen 2.5 Coder 7B", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "~5GB RAM"),
                    ("Llama 3.2 3B", "lmstudio-community/Llama-3.2-3B-Instruct-GGUF", "Llama-3.2-3B-Instruct-Q4_K_M.gguf", "~3GB RAM"),
                    ("Phi-3 Mini", "microsoft/Phi-3-mini-4k-instruct-gguf", "Phi-3-mini-4k-instruct-q4.gguf", "~2GB RAM"),
                ]
                
                for name, repo, filename, ram in popular_models:
                    with ui.row().classes('w-full items-center gap-2'):
                        ui.label(f"{name}").classes('text-sm flex-grow text-gray-800 dark:text-gray-200')
                        ui.label(ram).classes('text-xs text-gray-500')
                        
                        async def download_preset(r=repo, f=filename, n=name):
                            ui.notify(f"Starting download: {n}...", color='info')
                            try:
                                response = await asyncio.to_thread(
                                    requests.post,
                                    "http://127.0.0.1:8002/models/download",
                                    json={"repo_id": r, "filename": f},
                                    timeout=5
                                )
                                if response.status_code == 200:
                                    ui.notify(f"{n} download started!", color='positive')
                                    model_select.options = backend.get_models()
                                    model_select.update()
                                else:
                                    ui.notify(f"Download failed: {response.text}", color='negative')
                            except Exception as e:
                                ui.notify(f"Download error: {e}", color='negative')
                        
                        ui.button(icon='download', on_click=download_preset).props('flat dense round').classes('text-blue-500')
                
                ui.separator().classes('my-2')
                
                # Custom Download (Dialog Trigger)
                ui.label('Custom Download').classes('text-xs font-bold text-gray-600 dark:text-gray-300')
                if model_dialog:
                     ui.button('Download New Model', icon='cloud_download', on_click=lambda: model_dialog.open()).props('flat dense').classes('bg-blue-600 text-white w-full mt-1')

        # 2. AI Engine Mode Section
        ui.label('AI ENGINE MODE').classes('text-sm font-bold mt-4 mb-2 text-primary')
        with ui.column().classes('w-full gap-1'):
             use_cot = ui.switch('CoT Swarm (Experts)', value=False).classes('text-sm')
             ui.label('Parallel Consensus Arbitrage').classes('text-[10px] text-gray-500 italic ml-10 -mt-2 mb-2')
             app_state['use_cot_swarm'] = use_cot

        # 3. System Section
        ui.label('SYSTEM').classes('text-xs font-bold text-gray-800 mb-2')
        with ui.column().classes('w-full gap-2'):
            # llama.cpp Version with Download Option
            async def check_llama_version():
                try:
                    # Check local version from binary
                    result = await asyncio.to_thread(
                        subprocess.run,
                        ["_bin/llama-server.exe", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    local_version = result.stdout.strip() if result.returncode == 0 else "Unknown"
                    
                    # Check GitHub for latest release
                    response = await asyncio.to_thread(
                        requests.get,
                        "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest",
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        latest = response.json().get("tag_name", "Unknown")
                        download_url = f"https://github.com/ggerganov/llama.cpp/releases/tag/{latest}"
                        
                        if local_version != latest and latest != "Unknown":
                            # Newer version available!
                            if llama_info:
                                llama_info.text = f"Local: {local_version}\\nLatest: {latest}"
                            if llama_dialog:
                                llama_dialog.open()
                            logger.info(f"[Version] Update available: {local_version} → {latest}")
                            logger.info(f"[Version] Download: {download_url}")
                        else:
                            ui.notify(f'✅ Up to date! Version: {local_version}', color='positive')
                    else:
                        ui.notify(f'Version: {local_version}', color='info')
                        
                except Exception as e:
                    logger.error(f"[Version] Check failed: {e}")
                    ui.notify(f"Version check failed: {e}", color='warning')
            
            # System Buttons - Dark Mode Adaptive
            btn_classes = 'w-full bg-gray-100 dark:bg-slate-800 text-left text-gray-900 dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-slate-700'
            ui.button('Check llama.cpp Version', icon='info', on_click=check_llama_version).classes(btn_classes).props('flat align=left')
            
            # Real Benchmark
            async def run_benchmark():
                try:
                    ui.notify('🏃 Running benchmark... (this will take ~30 seconds)', color='info', position='top')
                    
                    # Simple benchmark: measure tokens/sec
                    test_prompt = "Write a short story about a robot learning to code."
                    start_time = time.time()
                    token_count = 0
                    
                    async with async_backend:
                        async for chunk in async_backend.send_message_async(test_prompt):
                            token_count += len(chunk.split())
                    
                    elapsed = time.time() - start_time
                    tokens_per_sec = token_count / elapsed if elapsed > 0 else 0
                    
                    # Display results
                    result_msg = f"""✅ Benchmark Complete!
                    
📊 Performance: {tokens_per_sec:.1f} tokens/sec
📝 Generated: {token_count} tokens
⏱️ Time: {elapsed:.1f} seconds"""
                    
                    ui.notify(result_msg, color='positive', position='top', multi_line=True, timeout=10000)
                    logger.info(f"[Benchmark] {tokens_per_sec:.1f} tok/s, {token_count} tokens in {elapsed:.1f}s")
                    
                except Exception as e:
                    logger.error(f"[Benchmark] Error: {e}")
                    ui.notify(f'❌ Benchmark failed: {str(e)}', color='negative', position='top')
            
            # Real Diagnostics
            async def run_diagnostics():
                try:
                    ui.notify('Running diagnostics...', color='info')
                    
                    checks = []
                    
                    # Check LLM backend
                    try:
                        llm_url = config.get('LLM_API_URL', "http://127.0.0.1:8001") if isinstance(config, dict) else (getattr(config, 'LLM_API_URL', "http://127.0.0.1:8001"))

                        response = await asyncio.to_thread(
                            requests.get,
                            f"{llm_url}/v1/models",
                            timeout=2
                        )
                        logger.info(f"[Diagnostics] LLM check: status={response.status_code}")
                        if response.status_code == 200:
                            checks.append(f'✅ LLM Backend: Online')
                        else:
                            checks.append(f'❌ LLM Backend: Error {response.status_code}')
                    except Exception as e:
                        logger.error(f"[Diagnostics] LLM check failed: {e}")
                        checks.append(f'❌ LLM Backend: Offline ({str(e)[:30]}...)')
                    
                    # Check RAG system
                    if rag_system and rag_system.index:
                        checks.append(f'{EMOJI.get("success", "✅")} RAG: {rag_system.index.ntotal} vectors')
                    else:
                        checks.append(f'{EMOJI.get("warning", "⚠️")} RAG: Not initialized')
                    
                    # Check memory
                    import psutil
                    mem = psutil.virtual_memory()
                    checks.append(f'{EMOJI.get("info", "ℹ️")} Memory: {mem.percent}% used')
                    
                    # Show results
                    result = '\\n'.join(checks)
                    ui.notify(result, color='info', multi_line=True)
                    logger.info(f"[Diagnostics]\\n{result}")
                    
                except Exception as e:
                    logger.error(f"[Diagnostics] Error: {e}")
                    ui.notify(f'Diagnostics failed: {e}', color='negative')
            
            ui.button('Run Benchmark', icon='speed', on_click=run_benchmark).classes(btn_classes).props('flat align=left')
            ui.button('Diagnostics', icon='bug_report', on_click=run_diagnostics).classes(btn_classes).props('flat align=left')
            
    return drawer
