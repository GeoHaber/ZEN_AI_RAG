use anyhow::{Result, Context};
use crate::config_system::{config, EMOJI};
use crate::profiler::{monitor};
use crate::state_management::{attachment_state, chat_history};
use crate::utils::{format_message_with_attachment, sanitize_prompt, is_port_active};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Namespace for UI event handlers.
#[derive(Debug, Clone)]
pub struct UIHandlers {
    pub ui_state: String,
    pub app_state: String,
    pub rag_system: String,
    pub universal_extractor: String,
    pub conversation_memory: String,
    pub async_backend: String,
    pub enhanced_rag_service: Option<serde_json::Value>,
    pub locale: get_locale,
}

impl UIHandlers {
    /// Initialize instance.
    pub fn new(ui_state: String, app_state: String, rag_system: String, universal_extractor: String, conversation_memory: String, async_backend: String) -> Self {
        Self {
            ui_state,
            app_state,
            rag_system,
            universal_extractor,
            conversation_memory,
            async_backend,
            enhanced_rag_service: None,
            locale: get_locale(),
        }
    }
    /// Initialize EnhancedRAGService with bridge functions to LocalRAG + LLM API.
    pub fn _init_enhanced_rag_service(&mut self) -> Result<()> {
        // Initialize EnhancedRAGService with bridge functions to LocalRAG + LLM API.
        // try:
        {
            // TODO: from Core.services.enhanced_rag_service import EnhancedRAGService
            if self.rag_system.is_none() {
                return;
            }
            let retrieve_fn = |query, top_k| {
                if /* hasattr(self.rag_system, "hybrid_search".to_string()) */ true {
                    self.rag_system.hybrid_search(query, /* k= */ top_k, /* alpha= */ 0.5_f64)
                }
                if /* hasattr(self.rag_system, "search".to_string()) */ true {
                    self.rag_system.search(query, /* k= */ top_k)
                }
                vec![]
            };
            let generate_fn = |query, chunks| {
                // try:
                {
                    let mut context = chunks[..8].iter().enumerate().iter().map(|(i, c)| format!("[{}] {}\n{}", i, c.get(&"title".to_string()).cloned().unwrap_or("Untitled".to_string()), c.get(&"text".to_string()).cloned().unwrap_or("".to_string()))).collect::<Vec<_>>().join(&"\n\n".to_string());
                    let mut user_prompt = format!("SOURCES:\n{}\n\nUSER QUESTION: {}\n\nANSWER:", context, query);
                    let mut payload = HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are ZenAI, a helpful assistant.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), user_prompt)])]), ("stream".to_string(), false), ("temperature".to_string(), 0.5_f64), ("max_tokens".to_string(), 1024)]);
                    let mut response = /* reqwest::post( */format!("{}/v1/chat/completions", config::LLM_API_URL), /* json= */ payload, /* timeout= */ 60);
                    response.raise_for_status();
                    let mut data = response.json();
                    data.get(&"choices".to_string()).cloned().unwrap_or(vec![HashMap::new()])[0].get(&"message".to_string()).cloned().unwrap_or(HashMap::new()).get(&"content".to_string()).cloned().unwrap_or("".to_string())
                }
                // except Exception as e:
            };
            let llm_fn = |prompt| {
                // try:
                {
                    let mut payload = HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are ZenAI, a helpful assistant.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)])]), ("stream".to_string(), false), ("temperature".to_string(), 0.4_f64), ("max_tokens".to_string(), 512)]);
                    let mut response = /* reqwest::post( */format!("{}/v1/chat/completions", config::LLM_API_URL), /* json= */ payload, /* timeout= */ 60);
                    response.raise_for_status();
                    let mut data = response.json();
                    data.get(&"choices".to_string()).cloned().unwrap_or(vec![HashMap::new()])[0].get(&"message".to_string()).cloned().unwrap_or(HashMap::new()).get(&"content".to_string()).cloned().unwrap_or("".to_string())
                }
                // except Exception as e:
            };
            let embed_fn = |text| {
                // try:
                {
                    if /* hasattr(self.rag_system, "_embed_mgr".to_string()) */ true {
                        let mut vec = self.rag_system._embed_mgr.encode_single(text, /* normalize= */ true);
                        if /* hasattr(vec, "tolist".to_string()) */ true { vec.tolist() } else { vec }
                    }
                }
                // except Exception as _e:
                vec![]
            };
            let search_by_embedding_fn = |embedding, top_k| {
                // try:
                {
                    if !/* getattr */ None {
                        vec![]
                    }
                    let mut hits = self.rag_system.qdrant.query_points(/* collection_name= */ self.rag_system.collection_name, /* query= */ embedding, /* limit= */ top_k).points;
                    hits.iter().map(|h| HashMap::from([("text".to_string(), h.payload.get(&"text".to_string()).cloned().unwrap_or("".to_string())), ("url".to_string(), h.payload.get(&"url".to_string()).cloned().unwrap_or("".to_string())), ("title".to_string(), h.payload.get(&"title".to_string()).cloned().unwrap_or("Untitled".to_string())), ("score".to_string(), h.score), ("metadata".to_string(), h.payload.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))])).collect::<Vec<_>>()
                }
                // except Exception as e:
            };
            let mut service = EnhancedRAGService();
            service.initialize(/* retrieve_fn= */ retrieve_fn, /* generate_fn= */ generate_fn, /* llm_fn= */ llm_fn, /* embed_fn= */ embed_fn, /* search_by_embedding_fn= */ search_by_embedding_fn);
            self.enhanced_rag_service = service;
            logger.info("[EnhancedRAG] UI service initialized".to_string());
        }
        // except Exception as e:
    }
    /// Processes the send action from the UI.
    pub async fn handle_send(&mut self, text: String) -> Result<()> {
        // Processes the send action from the UI.
        if (!text && !attachment_state.has_attachment()) {
            return;
        }
        self.ui_state::user_input.value = "".to_string();
        let mut final_text = text;
        if attachment_state.has_attachment() {
            // try:
            {
                let (mut name, mut content, _) = attachment_state.get();
                if content {
                    let mut final_text = format_message_with_attachment(text, name, content);
                }
                attachment_state.clear();
                self.ui_state::attachment_preview.text = "".to_string();
                self.ui_state::attachment_preview.set_visibility(false);
            }
            // except Exception as e:
        }
        Ok(self.stream_response(final_text).await)
    }
    /// Add a message bubble to the chat log.
    /// 
    /// Args:
    /// role: 'user', 'assistant', 'assistant_rag', or 'system'
    /// content: Message text
    /// enable_tts: Enable "Read Response" button for assistant messages
    pub fn add_message(&mut self, role: String, content: String, enable_tts: bool) -> Result<()> {
        // Add a message bubble to the chat log.
        // 
        // Args:
        // role: 'user', 'assistant', 'assistant_rag', or 'system'
        // content: Message text
        // enable_tts: Enable "Read Response" button for assistant messages
        let _ctx = self.ui_state::chat_log;
        let _ctx = ui.row().classes(if role == "user".to_string() { Styles.CHAT_ROW_USER } else { Styles.CHAT_ROW_AI });
        {
            if role == "user".to_string() {
                let mut color = Styles.CHAT_BUBBLE_USER;
            } else {
                let mut color = Styles.CHAT_BUBBLE_AI;
            }
            let mut align = if role == "user".to_string() { "items-end".to_string() } else { "items-start".to_string() };
            if role != "user".to_string() {
                let mut ai_initial = if config::zena_mode_enabled { "Z".to_string() } else { "N".to_string() };
                ui.avatar(ai_initial, /* color= */ "primary".to_string(), /* text_color= */ "white".to_string()).classes((Styles.AVATAR + " mr-2".to_string()));
            }
            let _ctx = ui.column().classes(align);
            {
                let mut ai_name = if config::zena_mode_enabled { "Zena".to_string() } else { self.locale.APP_NAME };
                let _ctx = ui.row().classes("items-center".to_string());
                {
                    if role == "assistant_rag".to_string() {
                        ui.label(self.locale.RAG_LABEL).classes(Styles.LABEL_RAG);
                    }
                    ui.label(if role == "user".to_string() { self.locale.CHAT_YOU } else { ai_name }).classes(Styles.CHAT_NAME);
                }
                let mut bubble_color = if role == "assistant_rag".to_string() { Styles.CHAT_BUBBLE_RAG } else { color };
                ui.markdown(content).classes(format!("{} {}", bubble_color, Styles.CHAT_BUBBLE_BASE));
                if (("assistant".to_string(), "assistant_rag".to_string()).contains(&role) && enable_tts) {
                    let on_read_click = |text_to_read| {
                        // Generate and play TTS for message.
                        // try:
                        {
                            // TODO: import httpx
                            read_btn.enabled = false;
                            read_btn.props("loading".to_string());
                            let mut client = httpx.AsyncClient();
                            {
                                let mut response = client.post("http://localhost:8001/voice/speak".to_string(), /* json= */ HashMap::from([("text".to_string(), text_to_read)])).await;
                                if response.status_code == 200 {
                                    let mut data = response.json();
                                    if (data.get(&"success".to_string()).cloned() && data.get(&"audio_url".to_string()).cloned()) {
                                        let mut audio_html = format!("\n                                        <audio controls autoplay style=\"width: 100%; max-width: 300px; margin: 8px 0;\">\n                                            <source src=\"{}\" type=\"audio/wav\">\n                                            Your browser does not support the audio element.\n                                        </audio>\n                                        ", data["audio_url".to_string()]);
                                        ui.html(audio_html);
                                        ui.notify("🔊 Playing response...".to_string(), /* type= */ "positive".to_string());
                                    } else {
                                        ui.notify(format!("TTS failed: {}", data.get(&"error".to_string()).cloned().unwrap_or("Unknown error".to_string())), /* type= */ "negative".to_string());
                                    }
                                } else {
                                    ui.notify("TTS service unavailable".to_string(), /* type= */ "warning".to_string());
                                }
                            }
                        }
                        // except Exception as e:
                        // finally:
                            read_btn.enabled = true;
                            read_btn.props(/* remove= */ "loading".to_string());
                    };
                    let _ctx = ui.row().classes("items-center gap-1 mt-2".to_string());
                    {
                        let mut read_btn = ui.button(/* icon= */ "volume_up".to_string(), /* on_click= */ || on_read_click(content)).props("flat dense small".to_string()).classes("text-sm text-blue-500 hover:text-blue-700".to_string());
                        read_btn.tooltip = "Read response aloud".to_string();
                        ui.label("Read".to_string()).classes("text-xs text-gray-500".to_string());
                    }
                }
            }
        }
        Ok(self.ui_state::safe_scroll())
    }
    /// Continue stream_response logic.
    pub async fn _stream_response_continued(&mut self, final_prompt: String, full_text: String, msg_ui: String, relevant_chunks: String, sources_ui: String, precomputed_answer: String, rag_metadata: String) -> Result<()> {
        // Continue stream_response logic.
        // try:
        {
            let mut chunk_count = 0;
            let mut thinking_active = true;
            let distraction_loop = || {
                // Distraction loop.
                while thinking_active {
                    asyncio.sleep(random.uniform(2.0_f64, 4.0_f64)).await;
                    if !thinking_active {
                        break;
                    }
                    // try:
                    {
                        if chunk_count == 0 {
                            let mut distraction = random.choice(/* getattr */ self.locale.LOADING_THINKING);
                            msg_ui.content = format!("**{}**", distraction);
                            self.ui_state::safe_update(msg_ui);
                        }
                    }
                    // except Exception as _e:
                }
            };
            asyncio.create_task(distraction_loop());
            if precomputed_answer.is_some() {
                let mut thinking_active = false;
                full_text += precomputed_answer;
                msg_ui.content = full_text;
                msg_ui.classes(/* remove= */ Styles.LOADING_PULSE);
                self.ui_state::safe_update(msg_ui);
            } else {
                let _ctx = self.async_backend;
                {
                    // async for
                    while let Some(chunk) = self.async_backend::send_message_async(final_prompt, /* cancellation_event= */ self.ui_state::cancellation_event).next().await {
                        if !self.ui_state::is_valid {
                            break;
                        }
                        if chunk_count == 0 {
                            let mut thinking_active = false;
                        }
                        chunk_count += 1;
                        full_text += chunk;
                        msg_ui.content = full_text;
                        msg_ui.classes(/* remove= */ Styles.LOADING_PULSE);
                        self.ui_state::safe_update(msg_ui);
                        asyncio.sleep(0.02_f64).await;
                    }
                }
            }
            let mut thinking_active = false;
            if rag_metadata {
                let _ctx = sources_ui;
                let _ctx = ui.card().classes(("w-full rounded-xl mt-2 p-2 ".to_string() + Styles.CARD_INFO));
                {
                    let mut routing = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"routing".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut intent = if /* /* isinstance(routing, dict) */ */ true { routing::get(&"intent".to_string()).cloned().unwrap_or("-".to_string()) } else { "-".to_string() };
                    let mut stages = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"stages".to_string()).cloned().unwrap_or(vec![]) } else { vec![] };
                    let mut latency = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"latency_ms".to_string()).cloned().unwrap_or("-".to_string()) } else { "-".to_string() };
                    let mut mode = if /* /* isinstance(routing, dict) */ */ true { routing::get(&"mode".to_string()).cloned().unwrap_or(self.app_state.get(&"rag_pipeline_mode".to_string()).cloned().unwrap_or("classic".to_string())) } else { self.app_state.get(&"rag_pipeline_mode".to_string()).cloned().unwrap_or("classic".to_string()) };
                    ui.label("RAG Pipeline".to_string()).classes(("text-xs font-semibold ".to_string() + Styles.TEXT_PRIMARY));
                    ui.label(format!("Mode: {}", mode)).classes(Styles.LABEL_XS);
                    ui.label(format!("Intent: {}", intent)).classes(Styles.LABEL_XS);
                    ui.label(format!("Stages: {}", if stages { stages.join(&", ".to_string()) } else { "-".to_string() })).classes(Styles.LABEL_XS);
                    ui.label(format!("Latency: {} ms", latency)).classes(Styles.LABEL_XS);
                    let mut hallucination = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"hallucination".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut confidence = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"confidence".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut conflicts = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"conflicts".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut follow_ups = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"follow_up_questions".to_string()).cloned().unwrap_or(vec![]) } else { vec![] };
                    let mut crag_info = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"crag".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut flare_info = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"flare".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut graph_info = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"graph_rag".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    let mut dedup_info = if /* /* isinstance(rag_metadata, dict) */ */ true { rag_metadata.get(&"dedup".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
                    if confidence {
                        let mut score = confidence.get(&"score".to_string()).cloned().unwrap_or("-".to_string());
                        let mut risk = confidence.get(&"risk_level".to_string()).cloned().unwrap_or("-".to_string());
                        ui.label(format!("Confidence: {} ({})", score, risk)).classes(Styles.LABEL_XS);
                    }
                    if hallucination {
                        let mut h_status = if hallucination.get(&"is_clean".to_string()).cloned() { "Clean".to_string() } else { format!("Prob: {}", hallucination.get(&"probability".to_string()).cloned().unwrap_or("-".to_string())) };
                        ui.label(format!("Hallucination: {}", h_status)).classes(Styles.LABEL_XS);
                    }
                    if (conflicts && conflicts.get(&"has_conflicts".to_string()).cloned()) {
                        ui.label(format!("Conflicts: {} detected", conflicts.get(&"count".to_string()).cloned().unwrap_or(0))).classes((Styles.LABEL_XS + " text-orange-500".to_string()));
                    }
                    if crag_info {
                        ui.label(format!("CRAG: grade={}, corrections={}", crag_info.get(&"grade".to_string()).cloned().unwrap_or("-".to_string()), crag_info.get(&"corrections".to_string()).cloned().unwrap_or(0))).classes(Styles.LABEL_XS);
                    }
                    if flare_info {
                        ui.label(format!("FLARE: {} iters, {} sub-queries", flare_info.get(&"iterations".to_string()).cloned().unwrap_or(0), flare_info.get(&"sub_queries".to_string()).cloned().unwrap_or(vec![]).len())).classes(Styles.LABEL_XS);
                    }
                    if graph_info {
                        ui.label(format!("GraphRAG: {}, {} communities", graph_info.get(&"strategy".to_string()).cloned().unwrap_or("-".to_string()), graph_info.get(&"communities_used".to_string()).cloned().unwrap_or(0))).classes(Styles.LABEL_XS);
                    }
                    if dedup_info {
                        ui.label(format!("Dedup: removed {}, conflicts {}", dedup_info.get(&"removed".to_string()).cloned().unwrap_or(0), dedup_info.get(&"conflicts".to_string()).cloned().unwrap_or(0))).classes(Styles.LABEL_XS);
                    }
                    if follow_ups {
                        ui.label("Follow-ups:".to_string()).classes(("text-xs font-semibold mt-1 ".to_string() + Styles.TEXT_PRIMARY));
                        for fq in follow_ups[..3].iter() {
                            ui.label(format!("  {}", fq)).classes(Styles.LABEL_XS);
                        }
                    }
                    if self.app_state.contains(&"rag_last_mode_label".to_string()) {
                        self.app_state["rag_last_mode_label".to_string()].text = format!("Mode: {}", mode);
                        self.app_state["rag_last_intent_label".to_string()].text = format!("Intent: {}", intent);
                        self.app_state["rag_last_stages_label".to_string()].text = format!("Stages: {}", if stages { stages.join(&", ".to_string()) } else { "-".to_string() });
                        self.app_state["rag_last_latency_label".to_string()].text = format!("Latency: {} ms", latency);
                    }
                    if self.app_state.contains(&"rag_last_confidence_label".to_string()) {
                        if confidence {
                            self.app_state["rag_last_confidence_label".to_string()].text = format!("Confidence: {} ({})", confidence.get(&"score".to_string()).cloned().unwrap_or("-".to_string()), confidence.get(&"risk_level".to_string()).cloned().unwrap_or("-".to_string()));
                        }
                        if hallucination {
                            let mut h_text = if hallucination.get(&"is_clean".to_string()).cloned() { "Clean".to_string() } else { format!("Prob: {}", hallucination.get(&"probability".to_string()).cloned().unwrap_or("-".to_string())) };
                            self.app_state["rag_last_hallucination_label".to_string()].text = format!("Hallucination: {}", h_text);
                        }
                    }
                }
            }
            if relevant_chunks {
                let _ctx = sources_ui;
                let _ctx = ui.expansion(self.locale.RAG_VIEW_SOURCES, /* icon= */ Icons.SOURCE).classes((("w-full ".to_string() + Styles.CARD_INFO) + " rounded-xl mt-2".to_string()));
                let _ctx = ui.column().classes("gap-1 p-2".to_string());
                {
                    for (i, c) in relevant_chunks.iter().enumerate().iter() {
                        let mut title = c.get(&"title".to_string()).cloned().unwrap_or("Untitled".to_string());
                        let mut url = c.get(&"url".to_string()).cloned().unwrap_or("N/A".to_string());
                        if url.starts_with(&*"http".to_string()) {
                            ui.link(format!("[{}] {}", i, title), url).classes((Styles.TEXT_ACCENT + " underline text-sm block".to_string()));
                        } else {
                            ui.label(format!("[{}] {}", i, title)).classes((("font-bold text-sm ".to_string() + Styles.TEXT_PRIMARY) + " block".to_string()));
                            ui.label(format!("📍 {}", url)).classes((Styles.LABEL_XS + " ml-4 break-all block".to_string()));
                        }
                        // TODO: from ui import Formatters
                        let mut text_preview = Formatters.preview(c.get(&"text".to_string()).cloned().unwrap_or("".to_string()), 300);
                        ui.label(format!("📝 \"{}\"", text_preview)).classes((Styles.LABEL_XS + " italic ml-4 mb-2 border-l-2 border-gray-300 pl-2 block".to_string()));
                    }
                }
            }
            if (full_text && self.ui_state::is_valid) {
                if self.conversation_memory {
                    // try:
                    {
                        self.conversation_memory::add_message("assistant".to_string(), full_text, self.ui_state::session_id);
                    }
                    // except Exception as _e:
                }
            }
        }
        // except Exception as e:
        // finally:
            self.ui_state::status_text.text = self.locale.CHAT_READY;
            Ok(self.ui_state::safe_scroll())
    }
    /// Stream LLM response to chat UI with conversation memory.
    pub async fn stream_response(&mut self, prompt: String) -> Result<()> {
        // Stream LLM response to chat UI with conversation memory.
        if !self.ui_state::is_valid {
            logger.warning("[UI] Client disconnected, skipping stream".to_string());
            return;
        }
        // TODO: from zena_mode.dispatcher import FastDispatcher
        if (self.app_state.get(&"council_mode".to_string()).cloned() && self.app_state["council_mode".to_string()].value) {
            self.handle_council_mode(prompt).await;
            return;
        }
        let mut dispatcher = FastDispatcher(self.async_backend, self.rag_system);
        let mut decision = dispatcher::dis/* mock::patch(prompt) */.await;
        if decision["type".to_string()] == "direct".to_string() {
            logger.info("⚡ Fast Dispatch: Direct Response".to_string());
            self.add_message("user".to_string(), prompt);
            asyncio.sleep(0.3_f64).await;
            self.add_message("assistant".to_string(), decision["content".to_string()]);
            if self.conversation_memory {
                self.conversation_memory::add_message("user".to_string(), prompt, self.ui_state::session_id);
                self.conversation_memory::add_message("assistant".to_string(), decision["content".to_string()], self.ui_state::session_id);
            }
            return;
        }
        if decision["type".to_string()] == "expert".to_string() {
            ui.notify(format!("Routing to {} Expert...", decision["expert".to_string()].to_uppercase()), /* color= */ "accent".to_string());
        }
        let mut prompt = sanitize_prompt(prompt);
        self.add_message("user".to_string(), prompt);
        if self.conversation_memory {
            // try:
            {
                self.conversation_memory::add_message("user".to_string(), prompt, self.ui_state::session_id);
            }
            // except Exception as e:
        }
        // try:
        {
            self.ui_state::status_text.text = self.locale.CHAT_THINKING;
        }
        // except Exception as _e:
        asyncio.sleep(0.05_f64).await;
        self.ui_state::safe_scroll();
        let mut msg_row = ui.row().classes(Styles.CHAT_ROW_AI);
        msg_row.move(self.ui_state::chat_log);
        let _ctx = msg_row;
        let _ctx = ui.column().classes("w-full max-w-3xl".to_string());
        {
            let mut rag_flag = self.app_state.get(&"rag_enabled".to_string()).cloned().unwrap_or(false);
            let mut rag_sys = self.rag_system.is_some();
            let mut rag_idx = (/* hasattr(self.rag_system, "index".to_string()) */ true && self.rag_system.index);
            logger.info(format!("[UI-DEBUG] RAG Flags: Enabled={}, Sys={}, Index={}", rag_flag, rag_sys, (rag_idx != 0)));
            let mut use_rag = (rag_flag && rag_sys && rag_idx);
            if use_rag {
                let mut words = prompt.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
                let mut is_short = words.len() < 4;
                let mut keywords = vec!["search".to_string(), "find".to_string(), "lookup".to_string(), "what is".to_string(), "who is".to_string(), "define".to_string(), "summary".to_string(), "analyze".to_string()];
                let mut has_keyword = keywords.iter().map(|k| prompt.to_lowercase().contains(&k)).collect::<Vec<_>>().iter().any(|v| *v);
                if (is_short && !has_keyword) {
                    logger.info(format!("[RAG] Skipped (Smart Mode): Prompt '{}' is too short/conversational.", prompt));
                    let mut use_rag = false;
                }
            }
            let mut use_swarm = (self.app_state.get(&"use_cot_swarm".to_string()).cloned() && self.app_state["use_cot_swarm".to_string()].value);
            if use_swarm {
                let mut loading_msg = random.choice(self.locale.LOADING_SWARM_THINKING);
            } else if use_rag {
                let mut loading_msg = random.choice(self.locale.LOADING_RAG_THINKING);
            } else {
                let mut loading_msg = random.choice(self.locale.LOADING_THINKING);
            }
            let mut msg_ui = ui.markdown(loading_msg).classes((((Styles.CHAT_BUBBLE_AI + " p-4 rounded-3xl shadow-sm ".to_string()) + Styles.LOADING_PULSE) + " w-full".to_string()));
            let mut sources_ui = ui.column().classes("w-full".to_string());
            let mut rag_skeleton = ui.column().classes("w-full gap-2 mt-2 px-4".to_string());
            rag_skeleton.visible = false;
            self.ui_state::safe_update(self.ui_state::chat_log);
            self.ui_state::safe_update(self.ui_state::scroll_container);
            asyncio.sleep(0.05_f64).await;
            self.ui_state::safe_scroll();
            let mut full_text = "".to_string();
            let mut final_prompt = prompt;
            let mut precomputed_answer = None;
            let mut rag_metadata = None;
            if self.conversation_memory {
                // try:
                {
                    let mut final_prompt = self.conversation_memory::build_contextual_prompt(prompt, /* session_id= */ self.ui_state::session_id);
                }
                // except Exception as _e:
            }
            let mut relevant_chunks = vec![];
            if use_rag {
                // try:
                {
                    let mut rag_query_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                    rag_skeleton.visible = true;
                    let _ctx = rag_skeleton;
                    {
                        let _ctx = ui.row().classes("items-center gap-3 animate-pulse".to_string());
                        {
                            ui.skeleton().classes("h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900".to_string());
                            let _ctx = ui.column().classes("gap-1".to_string());
                            {
                                ui.skeleton().classes("h-3 w-32 rounded bg-gray-200 dark:bg-slate-700".to_string());
                                ui.skeleton().classes("h-3 w-48 rounded bg-gray-100 dark:bg-slate-800".to_string());
                            }
                        }
                        let _ctx = ui.row().classes("items-center gap-3 animate-pulse".to_string());
                        {
                            ui.skeleton().classes("h-8 w-8 rounded-full bg-purple-100 dark:bg-purple-900".to_string());
                            let _ctx = ui.column().classes("gap-1".to_string());
                            {
                                ui.skeleton().classes("h-3 w-40 rounded bg-gray-200 dark:bg-slate-700".to_string());
                                ui.skeleton().classes("h-3 w-56 rounded bg-gray-100 dark:bg-slate-800".to_string());
                            }
                        }
                    }
                    let mut pipeline_mode = self.app_state.get(&"rag_pipeline_mode".to_string()).cloned().unwrap_or("classic".to_string());
                    if (pipeline_mode == "enhanced".to_string() && self.enhanced_rag_service::is_some()) {
                        logger.info(format!("[RAG][Enhanced] Querying enhanced pipeline for: '{}...'", prompt[..50]));
                        let mut enhanced_result = asyncio.to_thread(self.enhanced_rag_service::query, prompt, 5).await;
                        let mut relevant_chunks = (enhanced_result.get(&"sources".to_string()).cloned().unwrap_or(vec![]) || vec![]);
                        let mut rag_metadata = (enhanced_result.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()) || HashMap::new());
                        let mut answer = (enhanced_result.get(&"answer".to_string()).cloned() || "".to_string()).trim().to_string();
                        logger.info(format!("[RAG][Enhanced] Sources: {}", relevant_chunks.len()));
                        if answer {
                            let mut precomputed_answer = answer;
                        }
                        if /* /* isinstance(rag_metadata, dict) */ */ true {
                            let mut routing = rag_metadata.get(&"routing".to_string()).cloned().unwrap_or(HashMap::new());
                            if !/* /* isinstance(routing, dict) */ */ true {
                                let mut routing = HashMap::new();
                            }
                            routing["mode".to_string()] = "enhanced".to_string();
                            rag_metadata["routing".to_string()] = routing;
                            if !rag_metadata.contains(&"latency_ms".to_string()) {
                                rag_metadata["latency_ms".to_string()] = ((((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - rag_query_start) * 1000) as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
                            }
                        }
                    } else {
                        logger.info(format!("[RAG] Searching knowledge base for: '{}...'", prompt[..50]));
                        if /* hasattr(self.rag_system, "hybrid_search_async".to_string()) */ true {
                            let mut relevant_chunks = self.rag_system.hybrid_search_async(prompt, /* k= */ 5, /* alpha= */ 0.5_f64).await;
                        } else {
                            let mut relevant_chunks = asyncio.to_thread(self.rag_system.hybrid_search, prompt, /* k= */ 5, /* alpha= */ 0.5_f64).await;
                        }
                        logger.info(format!("[RAG] Found {} relevant chunks", relevant_chunks.len()));
                        let mut rag_metadata = HashMap::from([("routing".to_string(), HashMap::from([("intent".to_string(), "classic".to_string()), ("mode".to_string(), "classic".to_string())])), ("stages".to_string(), vec!["hybrid_search".to_string(), "context_prompt".to_string(), "stream_generate".to_string()]), ("latency_ms".to_string(), ((((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - rag_query_start) * 1000) as f64) * 10f64.powi(2)).round() / 10f64.powi(2))]);
                    }
                    rag_skeleton.visible = false;
                    rag_skeleton.clear();
                    if relevant_chunks {
                        for (idx, c) in relevant_chunks.iter().enumerate().iter() {
                            logger.info(format!("[RAG] Chunk {}: {} (Score: {})", (idx + 1), c.get(&"title".to_string()).cloned().unwrap_or("Unknown".to_string()), c.get(&"fusion_score".to_string()).cloned().unwrap_or("N/A".to_string())));
                        }
                        msg_ui.classes(/* remove= */ Styles.CHAT_BUBBLE_AI.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>()[0], /* add= */ Styles.CHAT_BUBBLE_RAG);
                        let mut full_text = format!("{} {}\n\n", EMOJI["success".to_string()], (((self.locale.RAG_ANSWERED_FROM_SOURCE + ": ".to_string()) + relevant_chunks.len().to_string()) + " docs".to_string()));
                        msg_ui.content = full_text;
                        if precomputed_answer.is_none() {
                            let mut context_parts = vec![];
                            for (i, c) in relevant_chunks.iter().enumerate().iter() {
                                context_parts.push(format!("[{}] Source: {}\n{}", i, c.get(&"title".to_string()).cloned().unwrap_or("Untitled".to_string()), c["text".to_string()]));
                            }
                            let mut context = context_parts.join(&"\n\n".to_string());
                            let mut final_prompt = format!("SOURCES:\n{}\n\nUSER QUESTION: {}\n\nANSWER:", context, prompt);
                        }
                    }
                }
                // except Exception as e:
            }
        }
        Ok(self._stream_response_continued(final_prompt, full_text, msg_ui, relevant_chunks, sources_ui, /* precomputed_answer= */ precomputed_answer, /* rag_metadata= */ rag_metadata).await)
    }
    /// Extracts text from raw bytes using the UniversalExtractor.
    pub fn extract_text(&mut self, raw_data: String, filename: String) -> Result<()> {
        // Extracts text from raw bytes using the UniversalExtractor.
        let mut text = "".to_string();
        // try:
        {
            let (mut chunks, mut stats) = self.universal_extractor::process(raw_data, /* filename= */ filename, /* parallel= */ false);
            if chunks {
                let mut text = chunks.iter().map(|c| c.text).collect::<Vec<_>>().join(&"\n\n".to_string());
                if stats.ocr_pages > 0 {
                    let mut text = (format!("[Context: OCR Extracted from {}]\n\n", filename) + text);
                }
            } else if !raw_data[..1024].contains(&b" ") {
                let mut text = raw_data.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
            } else {
                let mut text = format!("[File attached: {}]", filename);
            }
        }
        // except Exception as e:
        Ok(text)
    }
    /// Handle file upload events.
    pub async fn on_upload(&mut self, e: String) -> Result<()> {
        // Handle file upload events.
        // try:
        {
            let mut name = /* getattr */ /* getattr */ "unknown_file".to_string();
            let mut source = /* getattr */ /* getattr */ None;
            let mut raw_content = b"";
            if source {
                if /* hasattr(source, "read".to_string()) */ true {
                    let mut potential = source.read();
                    let mut raw_content = if asyncio.iscoroutine(potential) { potential.await } else { potential };
                } else if /* /* isinstance(source, bytes) */ */ true {
                    let mut raw_content = source;
                } else if /* hasattr(source, "file".to_string()) */ true {
                    let mut inner = source.file;
                    if /* hasattr(inner, "read".to_string()) */ true {
                        let mut potential = inner.read();
                        let mut raw_content = if asyncio.iscoroutine(potential) { potential.await } else { potential };
                    }
                }
            }
            if !/* /* isinstance(raw_content, bytes) */ */ true {
                let mut raw_content = raw_content.to_string().encode("utf-8".to_string(), /* errors= */ "replace".to_string());
            }
            let mut content = asyncio.to_thread(self.extract_text, raw_content, name).await;
            attachment_state.set(name, content, content[..100]);
            self.ui_state::attachment_preview.text = format!("📎 {} ({} chars)", name, content.len());
            self.ui_state::attachment_preview.visible = true;
            ui.notify(format!(self.locale, "NOTIFY_ATTACHED".to_string(), /* name= */ name), /* color= */ "positive".to_string());
        }
        // except Exception as ex:
    }
    /// Direct Event Listener: Receives voice text directly from Client JS.
    /// Bypasses DOM inputs for maximum reliability.
    pub async fn handle_voice_data(&mut self, e: String) -> Result<()> {
        // Direct Event Listener: Receives voice text directly from Client JS.
        // Bypasses DOM inputs for maximum reliability.
        // try:
        {
            let mut text = e.args;
            if /* /* isinstance(text, dict) */ */ true {
                let mut text = text.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            }
            if !text {
                return;
            }
            logger.info(format!("[VoiceEvent] Received: '{}'", text));
            let mut current = (self.ui_state::user_input.value || "".to_string());
            self.ui_state::user_input.value = (current + text);
            self.ui_state::user_input.update();
        }
        // except Exception as ex:
    }
    /// Toggle voice streaming (Client-Side).
    pub async fn on_voice_click(&self) -> () {
        // Toggle voice streaming (Client-Side).
        let mut js_code = "\n        // 1. Ensure Global State Exists\n        if (typeof window.voiceGlobals === 'undefined') {\n            window.voiceGlobals = {\n                socket: null,\n                recorder: null,\n                stream: null,\n                context: null,\n                isRecording: false\n            };\n        }\n\n        // 2. Define the Toggle Function (DEBUG MODE)\n        window.toggleVoiceStream = async function() {\n            const btn = document.getElementById('ui-btn-voice');\n            const G = window.voiceGlobals;\n            \n            console.log(\"[Voice] Clicked. Current recording state:\", G.isRecording);\n            \n            if (G.isRecording) {\n                // STOP LOGIC...\n                try {\n                    console.log(\"[Voice] Cleanup started...\");\n                    if (G.socket) { G.socket::close(); G.socket = null; }\n                    if (G.stream) { G.stream.getTracks().forEach(t => t.stop()); G.stream = null; }\n                    if (G.context) { G.context.close(); G.context = null; }\n                    G.isRecording = false;\n                    if(btn) btn.classList.remove('text-red-500', 'animate-pulse');\n                    console.log(\"[Voice] Stopped fully.\");\n                } catch(e) { console.error(\"Stop Error:\", e); }\n                \n            } else {\n                // START LOGIC\n                try {\n                    console.log(\"[Voice] Requesting Mic...\");\n                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });\n                    G.stream = stream;\n                    console.log(\"[Voice] Mic OK\");\n                    \n                    const AudioContext = window.AudioContext || window.webkitAudioContext;\n                    const audioContext = new AudioContext();\n                    await audioContext.resume();\n                    G.context = audioContext;\n                    console.log(\"[Voice] AudioContext OK. State:\", audioContext.state);\n                    \n                    const source = audioContext.createMediaStreamSource(stream);\n                    const processor = audioContext.createScriptProcessor(4096, 1, 1);\n                    \n                    console.log(\"[Voice] Connecting WebSocket...\");\n                    const socket = new WebSocket('ws://127.0.0.1:8006');\n                    G.socket = socket;\n                    \n                    socket::onopen = () => {\n                        console.log('✅ Voice WS Connected (onopen fired)');\n                        source.connect(processor);\n                        processor.connect(audioContext.destination);\n                        \n                        G.isRecording = true;\n                        if(btn) btn.classList.add('text-red-500', 'animate-pulse');\n                        \n                        // TEST EMIT immediately to prove channel works\n                        try {\n                            if(window.emitEvent) window.emitEvent('voice_data', '[DEBUG] Handshake');\n                            else if(typeof emitEvent === 'function') emitEvent('voice_data', '[DEBUG] Handshake');\n                            else console.warn(\"❌ emitEvent not found in onopen\");\n                        } catch(e) { console.error(\"Emit fail:\", e); }\n                    };\n                    \n                    processor.onaudioprocess = (e) => {\n                         // Only send if OPEN (1)\n                        if (socket::readyState === 1) {\n                            const data = e.inputBuffer.getChannelData(0);\n                            const ratio = audioContext.sampleRate / 16000;\n                            const len = Math.floor(data.length / ratio);\n                            const pcm = new Int16Array(len);\n                            for(let i=0; i<len; i++) {\n                                let s = Math.max(-1, Math.min(1, data[Math.floor(i*ratio)]));\n                                pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;\n                            }\n                            socket::send(pcm.buffer);\n                        }\n                    };\n                    \n                    socket::onmessage = (event) => {\n                        console.log(\"[Voice] Raw Message:\", event.data);\n                        try {\n                            const data = JSON.parse(event.data);\n                            if (data.text) {\n                                console.log(\"🗣️ TX:\", data.text);\n                                \n                                if (window.emitEvent) window.emitEvent('voice_data', data.text);\n                                else if (typeof emitEvent === 'function') emitEvent('voice_data', data.text);\n                                else console.error(\"CRITICAL: emitEvent missing during receive\");\n                            }\n                        } catch(e) { console.error(\"Parse Error:\", e); }\n                    };\n                    \n                    socket::onerror = (e) => {\n                        console.error(\"❌ WS Error:\", e);\n                        alert(\"WebSocket Failure. See Console.\");\n                    };\n                    \n                    socket::onclose = (e) => {\n                        console.warn(\"⚠️ WS Closed:\", e.code, e.reason);\n                        G.isRecording = false;\n                        if(btn) btn.classList.remove('text-red-500', 'animate-pulse');\n                    };\n                    \n               } catch (err) {\n                    console.error(\"Setup Error:\", err);\n                    alert(\"Setup Error: \" + err.message);\n               }\n            }\n        };\n        \n        // 3. Execute\n        window.toggleVoiceStream();\n        ".to_string();
        ui.run_javascript(js_code);
    }
    /// Handle Council (Swarm) execution flow with UI visualization.
    pub async fn handle_council_mode(&mut self, prompt: String) -> Result<()> {
        // Handle Council (Swarm) execution flow with UI visualization.
        let mut prompt = sanitize_prompt(prompt);
        self.add_message("user".to_string(), prompt);
        self.ui_state::status_text.text = "COUNCIL SESSION...".to_string();
        self.ui_state::status_text.classes(((Styles.TEXT_ACCENT + " ".to_string()) + Styles.LOADING_PULSE));
        let mut msg_row = ui.row().classes(Styles.CHAT_ROW_AI);
        msg_row.move(self.ui_state::chat_log);
        let _ctx = msg_row;
        {
            let _ctx = ui.column().classes("w-full max-w-3xl".to_string());
            {
                let mut msg_ui = ui.markdown("**The Council is debating...**".to_string()).classes(((Styles.CHAT_BUBBLE_AI + " p-4 rounded-3xl shadow-sm ".to_string()) + Styles.LOADING_PULSE));
                let mut debate_ui = ui.column().classes("w-full mt-2".to_string());
                self.ui_state::safe_scroll();
                // try:
                {
                    let mut payload = HashMap::from([("message".to_string(), prompt), ("mode".to_string(), "council".to_string())]);
                    let mut url = config::get_mgmt_url("/api/chat/swarm".to_string());
                    let mut resp = asyncio.to_thread(requests.post, url, /* json= */ payload, /* timeout= */ 120).await;
                    if resp.status_code == 200 {
                        let mut data = resp.json();
                        let mut final_ans = data.get(&"consensus_answer".to_string()).cloned().unwrap_or("No consensus reached.".to_string());
                        let mut experts = data.get(&"individual_responses".to_string()).cloned().unwrap_or(vec![]);
                        let mut confidence = data.get(&"confidence".to_string()).cloned().unwrap_or(0.0_f64);
                        let mut method = data.get(&"method".to_string()).cloned().unwrap_or("Unknown".to_string());
                        msg_ui.content = final_ans;
                        msg_ui.classes(/* remove= */ Styles.LOADING_PULSE);
                        let _ctx = debate_ui;
                        let _ctx = ui.expansion(format!("Council Debate ({}, {:.0%} Agreement)", /* title */ method.to_string(), confidence), /* icon= */ "groups".to_string()).classes("w-full bg-blue-50 dark:bg-slate-800 rounded-xl border border-blue-100 dark:border-slate-700".to_string());
                        let _ctx = ui.column().classes("p-2 gap-2".to_string());
                        {
                            for (i, exp) in experts.iter().enumerate().iter() {
                                let mut model_name = exp.get(&"model".to_string()).cloned().unwrap_or(format!("Expert {}", (i + 1)));
                                let mut exp_conf = exp.get(&"confidence".to_string()).cloned().unwrap_or(0.0_f64);
                                let _ctx = ui.card().classes("w-full p-2 bg-white dark:bg-slate-900".to_string());
                                let _ctx = ui.row().classes("items-center justify-between w-full".to_string());
                                {
                                    ui.label(model_name).classes("font-bold text-xs text-blue-600 dark:text-blue-400".to_string());
                                    ui.badge(format!("{:.0%} conf", exp_conf), /* color= */ "grey".to_string()).props("outline dense".to_string()).classes("text-[10px]".to_string());
                                    ui.markdown(exp.get(&"content".to_string()).cloned().unwrap_or("".to_string())).classes("text-xs text-gray-600 dark:text-gray-300 mt-1".to_string());
                                }
                            }
                        }
                    } else {
                        msg_ui.content = format!("❌ Council Error: {}", resp.text);
                        msg_ui.classes(/* remove= */ Styles.LOADING_PULSE);
                    }
                }
                // except Exception as e:
                // finally:
                    self.ui_state::status_text.text = self.locale.CHAT_READY;
                    self.ui_state::status_text.classes(/* remove= */ ((Styles.LOADING_PULSE + " ".to_string()) + Styles.TEXT_ACCENT));
                    self.ui_state::safe_scroll();
            }
        }
    }
    /// Run diagnostic tests.
    pub async fn run_internal_check(&mut self, monkey: String) -> Result<()> {
        // Run diagnostic tests.
        self.add_message("system".to_string(), format!("🔍 **{} STARTED**", if monkey { "MONKEY MODE".to_string() } else { "SELF-TEST".to_string() }));
        let run_command_bg = || {
            // Run command bg.
            // TODO: import subprocess
            // TODO: import sys
            let mut cmd = vec![sys::executable, "tests/live_diagnostics::py".to_string()];
            if monkey {
                cmd.push("--monkey".to_string());
            }
            subprocess::Popen(cmd, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ true, /* bufsize= */ 1, /* universal_newlines= */ true, /* shell= */ false)
        };
        let mut process = asyncio.to_thread(run_command_bg).await;
        let mut msg_ui = ui.markdown("⏳ *Running diagnostics...*".to_string()).classes((Styles.CHAT_BUBBLE_AI + " p-4 rounded-3xl shadow-sm w-full font-mono text-xs".to_string()));
        msg_ui.move(self.ui_state::chat_log);
        let mut full_output = "".to_string();
        while true {
            let mut line = asyncio.to_thread(process.stdout.readline).await;
            if !line {
                break;
            }
            full_output += line;
            msg_ui.set_content(format!("```\n{}\n```", full_output));
            self.ui_state::safe_scroll();
        }
        Ok(self.add_message("system".to_string(), "✅ **DIAGNOSTICS COMPLETE**".to_string()))
    }
    /// Periodic background task to update status indicators.
    pub async fn check_backend_health(&mut self) -> Result<()> {
        // Periodic background task to update status indicators.
        // TODO: import httpx
        while self.ui_state::is_valid {
            // try:
            {
                let mut llm_online = asyncio.to_thread(is_port_active, 8001).await;
                let mut hub_online = asyncio.to_thread(is_port_active, 8002).await;
                let mut status_text = "OFFLINE".to_string();
                let mut color_add = "text-red-500".to_string();
                let mut color_remove = "text-green-500 text-orange-500".to_string();
                if llm_online {
                    let mut status_text = "ONLINE".to_string();
                    let mut color_add = "text-green-500".to_string();
                    let mut color_remove = "text-red-500 text-orange-500".to_string();
                } else if hub_online {
                    let mut status_text = "BOOTING".to_string();
                    let mut color_add = "text-orange-500".to_string();
                    let mut color_remove = "text-green-500 text-red-500".to_string();
                    // try:
                    {
                        let mut client = httpx.AsyncClient();
                        {
                            let mut resp = client.get(&config::get_mgmt_url("/startup/progress".to_string())).cloned().unwrap_or(/* timeout= */ 1.0_f64).await;
                            if resp.status_code == 200 {
                                let mut status_text = format!("BOOTING ({}%)", resp.json().get(&"percent".to_string()).cloned().unwrap_or(0));
                            }
                        }
                    }
                    // except Exception as _e:
                }
                self.ui_state::status_indicator.set_text(status_text);
                self.ui_state::status_indicator.classes(/* remove= */ color_remove, /* add= */ color_add);
                self.ui_state::status_dot.classes(/* remove= */ color_remove, /* add= */ color_add);
                if self.app_state.contains(&"drawer_status_label".to_string()) {
                    self.app_state["drawer_status_label".to_string()].set_text(status_text);
                    self.app_state["drawer_status_label".to_string()].classes(/* remove= */ color_remove, /* add= */ color_add);
                    self.app_state["drawer_status_dot".to_string()].classes(/* remove= */ color_remove, /* add= */ color_add);
                }
            }
            // except Exception as e:
            asyncio.sleep(2).await;
        }
    }
}
