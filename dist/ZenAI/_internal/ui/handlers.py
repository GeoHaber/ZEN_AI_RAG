import asyncio
import logging
import requests
import io
import random
from nicegui import ui
from config_system import config, EMOJI
from locales import get_locale, L
from state_management import attachment_state, chat_history
from utils import format_message_with_attachment, sanitize_prompt, is_port_active
from zena_mode.profiler import monitor
from ui import Styles, Icons

logger = logging.getLogger("ZenAI.UI.Handlers")

class UIHandlers:
    """Namespace for UI event handlers."""
    
    def __init__(self, ui_state, app_state, rag_system, universal_extractor, conversation_memory, async_backend):
        self.ui_state = ui_state
        self.app_state = app_state
        self.rag_system = rag_system
        self.universal_extractor = universal_extractor
        self.conversation_memory = conversation_memory
        self.async_backend = async_backend
        self.locale = get_locale()

    async def handle_send(self, text: str):
        """Processes the send action from the UI."""
        if not text and not attachment_state.has_attachment():
            return
        
        # Clear input immediately
        self.ui_state.user_input.value = ""
        
        # 1. Handle Attachments
        final_text = text
        if attachment_state.has_attachment():
            try:
                name, content, _ = attachment_state.get()
                if content:
                    final_text = format_message_with_attachment(text, name, content)
                # Clear attachment state
                attachment_state.clear()
                self.ui_state.attachment_preview.text = ""
                self.ui_state.attachment_preview.set_visibility(False)
            except Exception as e:
                logger.error(f"Error processing attachment: {e}")
                ui.notify(f"Processing error: {e}", color='negative')
        
        # 2. Trigger stream
        await self.stream_response(final_text)

    def add_message(self, role: str, content: str):
        """Add a message bubble to the chat log."""
        with self.ui_state.chat_log:
            with ui.row().classes(Styles.CHAT_ROW_USER if role == 'user' else Styles.CHAT_ROW_AI):
                # Zena-style colors
                if role == 'user':
                    color = Styles.CHAT_BUBBLE_USER
                else:
                    color = Styles.CHAT_BUBBLE_AI
                
                align = 'items-end' if role == 'user' else 'items-start'
                
                # Add circular avatar for AI messages
                if role != 'user':
                    ai_initial = 'Z' if config.zena_mode_enabled else 'N'
                    ui.avatar(ai_initial, color='primary', text_color='white').classes(Styles.AVATAR + ' mr-2')
                
                with ui.column().classes(align):
                    ai_name = 'Zena' if config.zena_mode_enabled else self.locale.APP_NAME
                    with ui.row().classes('items-center'):
                        if role == 'assistant_rag':
                             ui.label(self.locale.RAG_LABEL).classes(Styles.LABEL_RAG)
                        ui.label(self.locale.CHAT_YOU if role == 'user' else ai_name).classes(Styles.CHAT_NAME)
                    
                    bubble_color = Styles.CHAT_BUBBLE_RAG if role == 'assistant_rag' else color
                    ui.markdown(content).classes(f'{bubble_color} {Styles.CHAT_BUBBLE_BASE}')
        # Auto-scroll to bottom
        self.ui_state.safe_scroll()

    async def stream_response(self, prompt: str):
        """Stream LLM response to chat UI with conversation memory."""
        if not self.ui_state.is_valid:
            logger.warning("[UI] Client disconnected, skipping stream")
            return

        from zena_mode.dispatcher import FastDispatcher
        
        # --- COUNCIL MODE INTERCEPT ---
        if self.app_state.get('council_mode') and self.app_state['council_mode'].value:
            await self.handle_council_mode(prompt)
            return

        dispatcher = FastDispatcher(self.async_backend, self.rag_system)
        
        # 1. Dispatch
        decision = await dispatcher.dispatch(prompt)
        
        # 2. Handle Direct Responses (Instant)
        if decision['type'] == 'direct':
            logger.info(u"⚡ Fast Dispatch: Direct Response")
            self.add_message('user', prompt) 
            await asyncio.sleep(0.3)
            self.add_message('assistant', decision['content'])
            
            if self.conversation_memory:
                 self.conversation_memory.add_message('user', prompt, self.ui_state.session_id)
                 self.conversation_memory.add_message('assistant', decision['content'], self.ui_state.session_id)
            return

        # 3. Handle Expert Routing
        if decision['type'] == 'expert':
             ui.notify(f"Routing to {decision['expert'].upper()} Expert...", color='accent')

        prompt = sanitize_prompt(prompt)
        self.add_message('user', prompt)
        
        if self.conversation_memory:
            try:
                self.conversation_memory.add_message('user', prompt, self.ui_state.session_id)
            except Exception as e:
                logger.warning(f"[Memory] Failed to save user message: {e}")
        
        try:
            self.ui_state.status_text.text = self.locale.CHAT_THINKING
        except:
            pass
        
        await asyncio.sleep(0.05)
        self.ui_state.safe_scroll()
        
        # Create empty bot message
        msg_row = ui.row().classes(Styles.CHAT_ROW_AI)
        msg_row.move(self.ui_state.chat_log)
        
        with msg_row:
            with ui.column().classes('w-full max-w-3xl'):
                # Get appropriate loading message
                use_rag = self.app_state.get('rag_enabled', False) and self.rag_system and self.rag_system.index
                use_swarm = self.app_state.get('use_cot_swarm') and self.app_state['use_cot_swarm'].value

                if use_swarm:
                    loading_msg = random.choice(self.locale.LOADING_SWARM_THINKING)
                elif use_rag:
                    loading_msg = random.choice(self.locale.LOADING_RAG_THINKING)
                else:
                    loading_msg = random.choice(self.locale.LOADING_THINKING)

                msg_ui = ui.markdown(loading_msg).classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm ' + Styles.LOADING_PULSE + ' w-full')
                sources_ui = ui.column().classes('w-full')

                # Skeleton Container for RAG Search
                rag_skeleton = ui.column().classes('w-full gap-2 mt-2 px-4')
                rag_skeleton.visible = False

                self.ui_state.safe_update(self.ui_state.chat_log)
                self.ui_state.safe_update(self.ui_state.scroll_container)
                await asyncio.sleep(0.05)
                self.ui_state.safe_scroll()

                full_text = ""
                final_prompt = prompt

                if self.conversation_memory:
                    try:
                        final_prompt = self.conversation_memory.build_contextual_prompt(prompt, session_id=self.ui_state.session_id)
                    except: pass

                # RAG Context
                relevant_chunks = []
                if use_rag:
                    try:
                        # Show Skeletons
                        rag_skeleton.visible = True
                        with rag_skeleton:
                             with ui.row().classes('items-center gap-3 animate-pulse'):
                                 ui.skeleton().classes('h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900')
                                 with ui.column().classes('gap-1'):
                                     ui.skeleton().classes('h-3 w-32 rounded bg-gray-200 dark:bg-slate-700')
                                     ui.skeleton().classes('h-3 w-48 rounded bg-gray-100 dark:bg-slate-800')
                             with ui.row().classes('items-center gap-3 animate-pulse'):
                                 ui.skeleton().classes('h-8 w-8 rounded-full bg-purple-100 dark:bg-purple-900')
                                 with ui.column().classes('gap-1'):
                                     ui.skeleton().classes('h-3 w-40 rounded bg-gray-200 dark:bg-slate-700')
                                     ui.skeleton().classes('h-3 w-56 rounded bg-gray-100 dark:bg-slate-800')
                        
                        logger.info(f"[RAG] Searching knowledge base for: '{prompt[:50]}...'")
                        # Use hybrid search for better reliability (Semantic + BM25)
                        # OFFLOAD TO THREAD to prevent blocking event loop (fixes "Connection Lost")
                        # (Now using native async wrapper)
                        if hasattr(self.rag_system, 'hybrid_search_async'):
                            relevant_chunks = await self.rag_system.hybrid_search_async(prompt, k=5, alpha=0.5)
                        else:
                            relevant_chunks = await asyncio.to_thread(self.rag_system.hybrid_search, prompt, k=5, alpha=0.5)
                        logger.info(f"[RAG] Found {len(relevant_chunks)} relevant chunks")
                        
                        # Hide Skeletons immediately after search matches
                        rag_skeleton.visible = False
                        rag_skeleton.clear()
                        
                        if relevant_chunks:
                            for idx, c in enumerate(relevant_chunks):
                                logger.info(f"[RAG] Chunk {idx+1}: {c.get('title', 'Unknown')} (Score: {c.get('fusion_score', 'N/A')})")
                            
                            msg_ui.classes(remove=Styles.CHAT_BUBBLE_AI.split()[0], add=Styles.CHAT_BUBBLE_RAG)
                            full_text = f"{EMOJI['success']} {self.locale.RAG_ANSWERED_FROM_SOURCE + ': ' + str(len(relevant_chunks)) + ' docs'}\n\n"
                            msg_ui.content = full_text
                            
                            context_parts = []
                            for i, c in enumerate(relevant_chunks, 1):
                                 context_parts.append(f"[{i}] Source: {c.get('title', 'Untitled')}\n{c['text']}")
                            
                            context = "\n\n".join(context_parts)
                            final_prompt = f"SOURCES:\n{context}\n\nUSER QUESTION: {prompt}\n\nANSWER:"
                    except Exception as e:
                        logger.error(f"[RAG] Query failed: {e}")
                        rag_skeleton.visible = False
                        rag_skeleton.clear()
        
        try:
            chunk_count = 0
            thinking_active = True
            async def distraction_loop():
                while thinking_active:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    if not thinking_active: break
                    try:
                        if chunk_count == 0:
                            distraction = random.choice(getattr(self.locale, 'LOADING_DISTRACTIONS', self.locale.LOADING_THINKING))
                            msg_ui.content = f"**{distraction}**"
                            self.ui_state.safe_update(msg_ui)
                    except: break
            
            asyncio.create_task(distraction_loop())

            async with self.async_backend:
                async for chunk in self.async_backend.send_message_async(final_prompt, cancellation_event=self.ui_state.cancellation_event):
                    if not self.ui_state.is_valid: break
                    if chunk_count == 0:
                        thinking_active = False
                    chunk_count += 1
                    full_text += chunk
                    msg_ui.content = full_text
                    msg_ui.classes(remove=Styles.LOADING_PULSE)
                    self.ui_state.safe_update(msg_ui)
                    await asyncio.sleep(0.02)

            thinking_active = False 
            
            # Sources disclosure
            if relevant_chunks:
                with sources_ui:
                    with ui.expansion(self.locale.RAG_VIEW_SOURCES, icon=Icons.SOURCE).classes('w-full ' + Styles.CARD_INFO + ' rounded-xl mt-2'):
                        with ui.column().classes('gap-1 p-2'):
                            for i, c in enumerate(relevant_chunks, 1):
                                title = c.get('title', 'Untitled')
                                url = c.get('url', 'N/A')
                                if url.startswith('http'):
                                    ui.link(f"[{i}] {title}", url).classes(Styles.TEXT_ACCENT + ' underline text-sm block')
                                else:
                                    ui.label(f"[{i}] {title}").classes('font-bold text-sm ' + Styles.TEXT_PRIMARY + ' block')
                                    ui.label(f"📍 {url}").classes(Styles.LABEL_XS + ' ml-4 break-all block')
                                from ui import Formatters
                                text_preview = Formatters.preview(c.get('text', ''), 300)
                                ui.label(f'📝 "{text_preview}"').classes(Styles.LABEL_XS + ' italic ml-4 mb-2 border-l-2 border-gray-300 pl-2 block')

            if full_text and self.ui_state.is_valid:
                if self.conversation_memory:
                    try:
                        self.conversation_memory.add_message('assistant', full_text, self.ui_state.session_id)
                    except: pass
        
        except Exception as e:
            logger.error(f"[UI] Stream error: {e}")
            if not full_text: full_text = f"⚠️ Error: {str(e)}"
        
        finally:
            self.ui_state.status_text.text = self.locale.CHAT_READY
            self.ui_state.safe_scroll()

    def extract_text(self, raw_data, filename):
        """Extracts text from raw bytes using the UniversalExtractor."""
        text = ""
        try:
            chunks, stats = self.universal_extractor.process(raw_data, filename=filename, parallel=False)
            if chunks:
                text = "\n\n".join([c.text for c in chunks])
                if stats.ocr_pages > 0:
                    text = f"[Context: OCR Extracted from {filename}]\n\n" + text
            else:
                if b'\x00' not in raw_data[:1024]:
                    text = raw_data.decode('utf-8', errors='replace')
                else:
                    text = f"[File attached: {filename}]"
        except Exception as e:
            logger.warning(f"[Upload] Extraction failed: {e}")
            text = raw_data.decode('utf-8', errors='replace') if b'\x00' not in raw_data[:1024] else f"[Error: {e}]"
        return text

    async def on_upload(self, e):
        """Handle file upload events."""
        try:
            name = getattr(e, 'name', getattr(e, 'filename', 'unknown_file'))
            source = getattr(e, 'content', getattr(e, 'file', None))
            raw_content = b""
            if source:
                if hasattr(source, 'read'):
                    potential = source.read()
                    raw_content = await potential if asyncio.iscoroutine(potential) else potential
                elif isinstance(source, bytes):
                    raw_content = source
                elif hasattr(source, 'file'):
                    inner = source.file
                    if hasattr(inner, 'read'):
                        potential = inner.read()
                        raw_content = await potential if asyncio.iscoroutine(potential) else potential

            if not isinstance(raw_content, bytes):
                raw_content = str(raw_content).encode('utf-8', errors='replace')

            # OFFLOAD TO THREAD (Fixes blocking on upload/OCR)
            content = await asyncio.to_thread(self.extract_text, raw_content, name)
            
            attachment_state.set(name, content, content[:100])
            self.ui_state.attachment_preview.text = f"📎 {name} ({len(content)} chars)"
            self.ui_state.attachment_preview.visible = True
            ui.notify(self.locale.format('NOTIFY_ATTACHED', name=name), color='positive')
        except Exception as ex:
            logger.error(f"[Upload] Error: {ex}")
            ui.notify(str(ex), color='negative')

    async def on_voice_click(self):
        """Handle voice recording trigger."""
        try:
            import sounddevice as sd
            import scipy.io.wavfile as wav
            from feature_detection import is_feature_available, get_feature_detector
        except ImportError:
            ui.notify("Voice dependencies missing", color='negative')
            return

        if not is_feature_available('audio'):
            ui.notify(f"{EMOJI['error']} Voice Recording Unavailable", color='negative')
            return
            
        self.ui_state.status_text.text = self.locale.CHAT_RECORDING
        self.ui_state.status_text.classes(Styles.TEXT_ERROR + ' ' + Styles.LOADING_PULSE)
        
        fs = 16000
        duration = 5 
        
        try:
            def record():
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()
                return recording
            
            audio_data = await asyncio.to_thread(record)
            self.ui_state.status_text.text = self.locale.CHAT_TRANSCRIBING
            self.ui_state.status_text.classes(Styles.TEXT_WARNING)
            
            wav_buffer = io.BytesIO()
            wav.write(wav_buffer, fs, audio_data)
            wav_buffer.seek(0)
            
            # Send to Backend API
            response = await asyncio.to_thread(requests.post, config.get_mgmt_url("/voice/transcribe"), data=wav_buffer.read())
            
            if response.status_code == 200:
                transcription = response.json().get('text', '')
                if transcription:
                    self.ui_state.user_input.value += transcription + " "
                    ui.notify(self.locale.NOTIFY_TRANSCRIBED, color='green')
                else:
                    ui.notify(self.locale.NOTIFY_NO_SPEECH, color='orange')
            else:
                ui.notify(f"Transcription failed: {response.text}", color='red')
                
        except Exception as e:
            ui.notify(f"Voice error: {e}", color='red')
        finally:
            self.ui_state.status_text.text = self.locale.CHAT_READY
            self.ui_state.status_text.classes(remove=Styles.TEXT_ERROR + ' ' + Styles.LOADING_PULSE + ' ' + Styles.TEXT_WARNING)
            
    async def handle_council_mode(self, prompt: str):
        """Handle Council (Swarm) execution flow with UI visualization."""
        prompt = sanitize_prompt(prompt)
        self.add_message('user', prompt)
        
        # UI State: Thinking
        self.ui_state.status_text.text = "COUNCIL SESSION..."
        self.ui_state.status_text.classes(Styles.TEXT_ACCENT + ' ' + Styles.LOADING_PULSE)
        
        msg_row = ui.row().classes(Styles.CHAT_ROW_AI)
        msg_row.move(self.ui_state.chat_log)
        
        with msg_row:
             with ui.column().classes('w-full max-w-3xl'):
                 # Thinking Bubble
                 msg_ui = ui.markdown("**The Council is debating...**").classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm ' + Styles.LOADING_PULSE)
                 
                 debate_ui = ui.column().classes('w-full mt-2')
                 
                 self.ui_state.safe_scroll()
                 
                 # Backend Call
                 try:
                     # Use swarm endpoint
                     payload = {"message": prompt, "mode": "council"}
                     url = config.get_mgmt_url("/api/chat/swarm")
                     
                     # Offload request to avoid blocking UI loop
                     resp = await asyncio.to_thread(requests.post, url, json=payload, timeout=120)
                     
                     if resp.status_code == 200:
                         data = resp.json()
                         final_ans = data.get('consensus_answer', 'No consensus reached.')
                         experts = data.get('individual_responses', [])
                         confidence = data.get('confidence', 0.0)
                         method = data.get('method', 'Unknown')
                         
                         # Update Final Answer
                         msg_ui.content = final_ans
                         msg_ui.classes(remove=Styles.LOADING_PULSE)
                         
                         # Show Debate
                         with debate_ui:
                             with ui.expansion(f"Council Debate ({method.title()}, {confidence:.0%} Agreement)", icon='groups').classes('w-full bg-blue-50 dark:bg-slate-800 rounded-xl border border-blue-100 dark:border-slate-700'):
                                 with ui.column().classes('p-2 gap-2'):
                                     for i, exp in enumerate(experts):
                                         model_name = exp.get('model', f'Expert {i+1}')
                                         exp_conf = exp.get('confidence', 0.0)
                                         with ui.card().classes('w-full p-2 bg-white dark:bg-slate-900'):
                                             with ui.row().classes('items-center justify-between w-full'):
                                                 ui.label(model_name).classes('font-bold text-xs text-blue-600 dark:text-blue-400')
                                                 ui.badge(f"{exp_conf:.0%} conf", color='grey').props('outline dense').classes('text-[10px]')
                                             
                                             ui.markdown(exp.get('content', '')).classes('text-xs text-gray-600 dark:text-gray-300 mt-1')
                     else:
                         msg_ui.content = f"❌ Council Error: {resp.text}"
                         msg_ui.classes(remove=Styles.LOADING_PULSE)

                 except Exception as e:
                     logger.error(f"Council Error: {e}")
                     msg_ui.content = f"❌ System Error: {str(e)}"
                     msg_ui.classes(remove=Styles.LOADING_PULSE)
                 
                 finally:
                     self.ui_state.status_text.text = self.locale.CHAT_READY
                     self.ui_state.status_text.classes(remove=Styles.LOADING_PULSE + ' ' + Styles.TEXT_ACCENT)
                     self.ui_state.safe_scroll()

    async def run_internal_check(self, monkey=False):
        """Run diagnostic tests."""
        self.add_message("system", f"🔍 **{ 'MONKEY MODE' if monkey else 'SELF-TEST' } STARTED**")
        
        def run_command_bg():
            import subprocess
            import sys
            cmd = [sys.executable, "tests/live_diagnostics.py"]
            if monkey: cmd.append("--monkey")
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

        process = await asyncio.to_thread(run_command_bg)
        msg_ui = ui.markdown("⏳ *Running diagnostics...*").classes(Styles.CHAT_BUBBLE_AI + ' p-4 rounded-3xl shadow-sm w-full font-mono text-xs')
        msg_ui.move(self.ui_state.chat_log)
        
        full_output = ""
        while True:
            line = await asyncio.to_thread(process.stdout.readline)
            if not line: break
            full_output += line
            msg_ui.set_content(f"```\n{full_output}\n```")
            self.ui_state.safe_scroll()
        
        self.add_message("system", "✅ **DIAGNOSTICS COMPLETE**")

    async def check_backend_health(self):
        """Periodic background task to update status indicators."""
        import httpx
        while self.ui_state.is_valid:
            try:
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
                            resp = await client.get(config.get_mgmt_url("/startup/progress"), timeout=1.0)
                            if resp.status_code == 200:
                                status_text = f"BOOTING ({resp.json().get('percent', 0)}%)"
                    except: pass
                
                self.ui_state.status_indicator.set_text(status_text)
                self.ui_state.status_indicator.classes(remove=color_remove, add=color_add)
                self.ui_state.status_dot.classes(remove=color_remove, add=color_add)
                
                if 'drawer_status_label' in self.app_state:
                    self.app_state['drawer_status_label'].set_text(status_text)
                    self.app_state['drawer_status_label'].classes(remove=color_remove, add=color_add)
                    self.app_state['drawer_status_dot'].classes(remove=color_remove, add=color_add)
                    
            except Exception as e:
                logger.error(f"[HealthCheck] Error: {e}")
            await asyncio.sleep(2)
