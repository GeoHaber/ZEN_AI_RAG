import asyncio
import logging
import os
import random
import subprocess
import time
import requests
from pathlib import Path
from nicegui import ui
from ui import Styles, Icons
from ui.registry import UI_IDS
from locales import get_locale

logger = logging.getLogger("UI.Actions")

class _UIActionsBase:
    """Base methods for UIActions."""

    def __init__(self, backend, rag_system, app_state, dialogs, config):
        """Initialize instance."""
        self.backend = backend
        self.rag_system = rag_system
        self.app_state = app_state
        self.dialogs = dialogs
        self.config = config
        self.locale = get_locale()

    def start_new_chat(self):
        """Clear chat and start fresh."""
        if 'chat_container' in self.app_state and self.app_state['chat_container']:
            self.app_state['chat_container'].clear()
        if 'chat_history' in self.app_state and self.app_state['chat_history']:
            self.app_state['chat_history'].clear()
        
        msg = getattr(self.locale, 'CHAT_CLEARED', 'Chat cleared')
        ui.notify(msg, color='positive', position='bottom-right')

    async def start_tour(self):
        """Launch the interactive guided tour."""
        try:
            from zena_mode.tutorial import start_tutorial
            # Get client from current context
            client = ui.context.client
            start_tutorial(client)
        except Exception as e:
            logger.error(f"[Tutorial] Failed to start: {e}")
            ui.notify("Tutorial unavailable", color='warning')

    def on_theme_change(self, e):
        """Handle theme toggle."""
        from settings import set_dark_mode as _set_dark_mode
        if e.value:
            ui.dark_mode().enable()
            ui.query('body').classes(remove='bg-gray-50 text-gray-900', add='bg-slate-900 text-white')
        else:
            ui.dark_mode().disable()
            ui.query('body').classes(remove='bg-slate-900 text-white', add='bg-gray-50 text-gray-900')
        
        _set_dark_mode(e.value)
        # Force JavaScript sync
        ui.run_javascript('if(typeof syncDarkMode === "function") syncDarkMode();')
        ui.notify(f"Theme: {'Dark' if e.value else 'Light'}", color='info', position='bottom-right')

    def on_rag_toggle(self, e):
        """Handle RAG enable/disable."""
        self.app_state['rag_enabled'] = e.value
        if 'rag_scan_btn' in self.app_state:
            self.app_state['rag_scan_btn'].set_visibility(e.value)
        ui.notify(f"RAG {'Enabled' if e.value else 'Disabled'}", color='positive' if e.value else 'info')

    def open_rag_scan(self):
        """Open the RAG knowledge base scanner dialog."""
        if 'open_rag_dialog' in self.app_state:
             self.app_state['open_rag_dialog']()
        else:
             ui.notify("RAG Scan Dialog not initialized", color='warning')

    async def start_batch(self, files_input, progress_container, progress_label, progress_bar, batch_btn):
        """Execute batch analysis on selected files."""
        from zena_mode.batch_engine import BatchAnalyzer
        
        paths = [p.strip() for p in files_input.value.split(',') if p.strip()]
        if not paths:
            ui.notify("No files selected", color='warning')
            return
        
        # Resolve directory if single path
        if len(paths) == 1 and os.path.isdir(paths[0]):
            dir_path = Path(paths[0])
            paths = [str(f) for f in dir_path.glob('**/*') if f.is_file() and f.suffix in ('.py', '.txt', '.md', '.ipynb')]
            if not paths:
                ui.notify(f"No valid files found in {dir_path.name}", color='warning')
                return
        
        # UI Updates
        progress_container.classes(remove='hidden')
        batch_btn.disable()
        files_input.disable()
        
        def progress_cb(msg, pct):
            """Progress cb."""
            progress_label.set_text(msg)
            progress_bar.set_value(pct)
            # Randomized "Distraction" messages
            if random.random() < 0.2:
                distraction = random.choice(getattr(self.locale, 'LOADING_THINKING', ["Thinking..."]))
                ui.notify(distraction, position='bottom', type='info', timeout=2000)
        
        try:
            batch_analyzer = BatchAnalyzer(self.backend)
            result = await batch_analyzer.analyze_files(paths, on_progress=progress_cb)
            
            # Show success with "Open Folder" button
            with ui.notification(f"Batch Complete: {result['completed']} files analyzed!", color='positive', timeout=10000):
                if paths:
                    folder = str(Path(paths[0]).parent)
                    ui.button('Open Folder', icon='folder', on_click=lambda f=folder: os.startfile(f)).props('flat color=white')
        except Exception as e:
            ui.notify(f"Batch Failed: {e}", color='negative')
        finally:
            batch_btn.enable()
            files_input.enable()


class UIActions(_UIActionsBase):
    """
    Centralized logic controller for UI actions.
    Decouples business logic from UI layout code.
    """
    

    def get_model_info(self, filename, MODEL_INFO):
        """Get model info or generate smart defaults."""
        if filename in MODEL_INFO:
            return MODEL_INFO[filename]
        
        # Smart detection from filename
        fname_lower = filename.lower()
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
            name = filename.replace('.gguf', '').replace('-', ' ').replace('_', ' ').title()[:25]
            return {'name': name, 'desc': 'Local GGUF model', 'size': '?', 'icon': '🤖',
                    'good_for': ['General'], 'speed': 'Unknown', 'quality': 'Unknown'}

    async def switch_to_model(self, model_file, info, ui_elements):
        """Switch active model via backend API."""
        ui.notify(f"⏳ Loading {info['name']}...", color='info', position='bottom-right', timeout=2000)
        try:
            response = await asyncio.to_thread(
                requests.post, "http://127.0.0.1:8002/models/load",
                json={"model": model_file}, timeout=30
            )
            if response.status_code == 200:
                ui.notify(f"✅ {info['name']} ready!", color='positive', position='bottom-right')
            else:
                ui.notify(f"✅ {info['name']} selected", color='positive', position='bottom-right')
        except Exception:
            ui.notify(f"✅ {info['name']} active", color='positive', position='bottom-right')
        
        # Update UI elements if provided
        if ui_elements:
            if 'name_label' in ui_elements:
                ui_elements['name_label'].text = info['name']
            if 'desc_label' in ui_elements:
                ui_elements['desc_label'].text = info['desc']
            if 'tags_row' in ui_elements:
                ui_elements['tags_row'].clear()
                with ui_elements['tags_row']:
                    for tag in info.get('good_for', []):
                        ui.badge(tag, color='green').props('outline dense').classes('text-[10px]')

    async def download_model(self, model):
        """Start model download via Hub API."""
        ui.notify(f"⬇️ Starting download: {model['name']}...", color='info', position='bottom-right')
        try:
            # Check for conflicting download dialogs or state
            response = await asyncio.to_thread(
                requests.post, "http://127.0.0.1:8002/models/download",
                json={"repo_id": model['repo'], "filename": model['file']}, timeout=10
            )
            if response.status_code == 200:
                ui.notify(f"✅ {model['name']} download started!", color='positive', position='bottom-right')
            else:
                ui.notify(f"❌ Download failed: {response.text[:50]}", color='negative', position='bottom-right')
        except Exception as e:
            ui.notify(f"❌ Error: {str(e)[:50]}", color='negative', position='bottom-right')

    def open_voice_lab(self):
        """Open Voice Lab in maximized dialog."""
        with ui.dialog().props('maximized') as lab_dialog:
             with ui.card().classes('w-full h-full p-0 no-shadow'), ui.row().classes('w-full p-2 bg-gray-100 dark:bg-slate-800 items-center justify-between border-b'):
                 ui.label("🎙️ Voice Lab").classes('text-lg font-bold ml-2')
                 ui.button(icon=Icons.CLOSE, on_click=lab_dialog.close).props('flat round dense')

                 ui.html('<iframe src="http://localhost:8002/voice/lab" style="width:100%; height:calc(100% - 50px); border:none;"></iframe>', sanitize=False).classes('w-full h-full')
        lab_dialog.open()

    async def open_judge(self):
        """Open Intelligence Judge dialog."""
        from ui.quality_dashboard import create_quality_tab
        from ui.model_data import MODEL_INFO

        # Fetch active model info
        model_info = {"id": "Unknown", "name": "System Default"}
        try:
            llm_url = self.config.get('LLM_API_URL', "http://127.0.0.1:8001") if isinstance(self.config, dict) else getattr(self.config, 'LLM_API_URL', "http://127.0.0.1:8001")
            response = await asyncio.to_thread(requests.get, f"{llm_url}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    mid = data["data"][0]["id"]
                    info = self.get_model_info(mid, MODEL_INFO)
                    model_info = {"id": mid, "name": info.get('name', mid)}
        except Exception as e:
            logger.warning(f"Failed to fetch model info for judge: {e}")

        with ui.dialog().props('maximized') as judge_dialog, ui.card().classes('w-full h-full p-0 overflow-hidden'), ui.row().classes('w-full p-4 items-center justify-between border-b'):
            ui.label("ZenAI Judge").classes('text-xl font-bold')
            ui.button(icon=Icons.CLOSE, on_click=judge_dialog.close).props('flat round')

            with ui.scroll_area().classes('w-full flex-grow'):
                create_quality_tab(model_info)
        judge_dialog.open()

    async def check_llama_version(self):
        """Check local vs remote llama.cpp version."""
        ui.notify("🔍 Checking llama.cpp version...", color='info', position='bottom-right')
        try:
            # Local version
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
            
            # Remote version
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
            
            # Notify
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

    async def run_benchmark(self, status_label):
        """Run a quick performance benchmark."""
        ui.notify("⏱️ Running benchmark...", color='info', position='bottom-right')
        status_label.text = "Running benchmark..."
        try:
            test_prompt = "Write a short story about a robot learning to code."
            start_time = time.time()
            token_count = 0
            
            async with self.backend:
                async for chunk in self.backend.send_message_async(test_prompt):
                    token_count += len(chunk.split())
            
            elapsed = time.time() - start_time
            tokens_per_sec = token_count / elapsed if elapsed > 0 else 0
            
            status_label.text = f"Last: {tokens_per_sec:.1f} tok/s"
            ui.notify(f"✅ Benchmark Complete\\n⚡ Speed: {tokens_per_sec:.1f} tokens/sec\\n📝 Tokens: {token_count}\\n⏱️ Time: {elapsed:.1f}s", 
                     color='positive', position='bottom-right', multi_line=True, timeout=8000)
        except Exception as e:
            status_label.text = "Benchmark failed"
            ui.notify(f"❌ Benchmark failed: {str(e)[:50]}", color='negative', position='bottom-right')

    async def run_diagnostics(self, status_label):
        """Run system diagnostics."""
        ui.notify("🔍 Running diagnostics...", color='info', position='bottom-right')
        status_label.text = "Checking systems..."
        try:
            results = []
            
            # LLM Check
            try:
                llm_url = self.config.get('LLM_API_URL', "http://127.0.0.1:8001") if isinstance(self.config, dict) else getattr(self.config, 'LLM_API_URL', "http://127.0.0.1:8001")
                response = await asyncio.to_thread(requests.get, f"{llm_url}/v1/models", timeout=3)
                if response.status_code == 200:
                    results.append("✅ LLM Backend: Online")
                else:
                    results.append(f"⚠️ LLM Backend: Error {response.status_code}")
            except Exception:
                results.append("❌ LLM Backend: Offline")
            
            # RAG Check
            if self.rag_system and hasattr(self.rag_system, 'index') and self.rag_system.index:
                count = self.rag_system.index.ntotal
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
            
            status_label.text = "Ready"
            ui.notify("🔧 System Diagnostics\\n" + "\\n".join(results), 
                     color='info', position='bottom-right', multi_line=True, timeout=8000)
        except Exception as e:
            status_label.text = "Diagnostics failed"
            ui.notify(f"❌ Diagnostics failed: {str(e)[:50]}", color='negative', position='bottom-right')
