/// Local Adapters — In-memory LLM inference via FIFO buffers + llama-cpp-python.
/// 
/// Architecture:
/// AdaptiveFIFOBuffer      — Semaphore-synced adaptive buffer with backpressure
/// FIFOLlamaCppAdapter     — Core adapter: model loading, singleton, streaming inference
/// MockLLMAdapter          — Deterministic mock for testing
/// RealisticMockLLMAdapter — Streaming mock with delays
/// 
/// Data flow:
/// RAG_RAT query -> FIFOLlamaCppAdapter.query_stream_tokens()
/// -> asyncio.Queue bridge (thread -> async)
/// -> llama_cpp.Llama.create_chat_completion(stream=true)
/// -> each token instant-pushed to Queue -> yield to caller
/// 
/// No HTTP, no ports, no network. Pure in-memory FIFO buffers.
/// 
/// Diagnostics:
/// Crash diagnostics are handled EXTERNALLY by InferenceGuard (inference_guard::py).
/// This module does NOT import psutil or do its own memory monitoring.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const LLAMA_CPP_INSTALL_HINT: &str = "";

pub static _STOP_TOKENS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub const DIRECTLLAMACPPADAPTER: &str = "FIFOLlamaCppAdapter";

/// Message priority levels for LLM requests.
#[derive(Debug, Clone)]
pub struct MessagePriority {
}

/// Standardized message for FIFO buffer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FIFOMessage {
    pub content: Box<dyn std::any::Any>,
    pub message_type: String,
    pub priority: MessagePriority,
    pub timestamp: f64,
    pub source: String,
    pub metadata: HashMap<String, Box<dyn std::any::Any>>,
}

impl FIFOMessage {
    pub fn __lt__(&mut self, other: String) -> () {
        if self.priority.value != other.priority.value {
            self.priority.value > other.priority.value
        }
        self.timestamp < other.timestamp
    }
}

/// Adaptive FIFO buffer with semaphore-based producer/consumer sync.
/// 
/// Features:
/// - Adaptive sizing (grows under load, shrinks when idle)
/// - Backpressure (blocks producers when full)
/// - Priority queue support
/// - Built-in metrics
#[derive(Debug, Clone)]
pub struct AdaptiveFIFOBuffer {
    pub min_size: String,
    pub initial_size: String,
    pub max_size: String,
    pub current_max_size: String,
    pub enable_backpressure: String,
    pub buffer_name: String,
    pub _queue: Deque<FIFOMessage>,
    pub _priority_queue: Vec<FIFOMessage>,
    pub _empty_semaphore: String /* asyncio.Semaphore */,
    pub _full_semaphore: String /* asyncio.Semaphore */,
    pub _lock: String /* asyncio.Lock */,
    pub _metrics: HashMap<String, serde_json::Value>,
}

impl AdaptiveFIFOBuffer {
    pub fn new(min_size: i64, initial_size: i64, max_size: i64, enable_backpressure: bool, buffer_name: String) -> Self {
        Self {
            min_size,
            initial_size,
            max_size,
            current_max_size: initial_size,
            enable_backpressure,
            buffer_name,
            _queue: Default::default(),
            _priority_queue: Vec::new(),
            _empty_semaphore: asyncio.Semaphore(self.current_max_size),
            _full_semaphore: asyncio.Semaphore(0),
            _lock: asyncio.Lock(),
            _metrics: HashMap::from([("total_added".to_string(), 0), ("total_retrieved".to_string(), 0), ("times_grew".to_string(), 0), ("times_shrunk".to_string(), 0), ("peak_size".to_string(), 0), ("backpressure_events".to_string(), 0)]),
        }
    }
    /// Add message with automatic backpressure.
    pub async fn add_message(&mut self, content: Box<dyn std::any::Any>, message_type: String, priority: MessagePriority, source: String, metadata: Option<HashMap>, timeout: Option<f64>) -> Result<bool> {
        // Add message with automatic backpressure.
        let mut message = FIFOMessage(/* content= */ content, /* message_type= */ message_type, /* priority= */ priority, /* source= */ source, /* metadata= */ (metadata || HashMap::new()));
        // try:
        {
            if self.enable_backpressure {
                _wait_with_timeout(self._empty_semaphore.acquire(), (timeout || 30.0_f64)).await;
            }
            let _ctx = self._lock;
            {
                self._check_and_adapt_size();
                if priority == MessagePriority.NORMAL {
                    self._queue.push(message);
                } else {
                    self._priority_queue.push(message);
                    self._priority_queue.sort();
                }
                self._metrics["total_added".to_string()] += 1;
                self._metrics["peak_size".to_string()] = self._metrics["peak_size".to_string()].max(self.size());
            }
            self._full_semaphore.release();
            true
        }
        // except asyncio.TimeoutError as _e:
    }
    /// Get next message from buffer.
    pub async fn get_message(&mut self, timeout: Option<f64>) -> Result<Option<FIFOMessage>> {
        // Get next message from buffer.
        // try:
        {
            if self.enable_backpressure {
                _wait_with_timeout(self._full_semaphore.acquire(), (timeout || 5.0_f64)).await;
            }
            let _ctx = self._lock;
            {
                let mut message = None;
                if self._priority_queue {
                    let mut message = self._priority_queue.remove(&0);
                } else if self._queue {
                    let mut message = self._queue.popleft();
                }
                if message {
                    self._metrics["total_retrieved".to_string()] += 1;
                    if self.enable_backpressure {
                        self._empty_semaphore.release();
                    }
                    self._check_and_adapt_size();
                }
                message
            }
        }
        // except asyncio.TimeoutError as _e:
    }
    /// Adapt buffer size based on demand.
    pub fn _check_and_adapt_size(&mut self) -> () {
        // Adapt buffer size based on demand.
        let mut current_size = self.size();
        if self.current_max_size == 0 {
            return;
        }
        let mut fill_percent = ((current_size / self.current_max_size) * 100);
        if (fill_percent > 80 && self.current_max_size < self.max_size) {
            let mut new_size = (self.current_max_size * 1.5_f64).to_string().parse::<i64>().unwrap_or(0).min(self.max_size);
            let mut additional = (new_size - self.current_max_size);
            for _ in 0..additional.iter() {
                self._empty_semaphore.release();
            }
            self.current_max_size = new_size;
            self._metrics["times_grew".to_string()] += 1;
            logger.debug(format!("[{}] Grew to {}", self.buffer_name, new_size));
        }
        if (fill_percent < 10 && self.current_max_size > self.initial_size) {
            let mut new_size = (self.current_max_size * 0.8_f64).to_string().parse::<i64>().unwrap_or(0).max(self.initial_size);
            self.current_max_size = new_size;
            self._metrics["times_shrunk".to_string()] += 1;
        }
    }
    pub fn size(&self) -> i64 {
        (self._queue.len() + self._priority_queue.len())
    }
    pub fn stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("current_size".to_string(), self.size()), ("max_size".to_string(), self.current_max_size), ("fill_percent".to_string(), if self.current_max_size > 0 { ((self.size() / self.current_max_size) * 100) } else { 0 })])
    }
}

/// In-memory LLM adapter using FIFO buffers + llama-cpp-python.
/// 
/// - Model loaded once via llama_cpp.Llama (singleton, in-process)
/// - TRUE token streaming via asyncio.Queue bridge (thread -> async)
/// - FIFO buffers for request tracking / metrics
/// - NO inline diagnostics — InferenceGuard handles that externally
#[derive(Debug, Clone)]
pub struct FIFOLlamaCppAdapter {
    pub _shared_model_path: Option<String>,
}

impl FIFOLlamaCppAdapter {
    pub fn new(model_path: Option<String>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Self {
        Self {
            _shared_model_path: None,
        }
    }
    /// Discover GGUF models: Local_LLM registry -> manual search.
    pub fn _find_gguf_model(&self) -> Result<Option<PathBuf>> {
        // Discover GGUF models: Local_LLM registry -> manual search.
        // try:
        {
            // TODO: from Local_LLM.Core.services.local_llm_manager import LocalLLMManager
            let mut manager = LocalLLMManager();
            let mut status = manager.initialize();
            if (status && status.models_discovered) {
                let mut cards = manager.get_all_cards();
                if cards {
                    for card in cards.iter() {
                        let mut cat = card.get(&"category".to_string()).cloned().unwrap_or("".to_string());
                        if ("balanced".to_string(), "fast".to_string()).contains(&cat) {
                            let mut path = card.get(&"path".to_string()).cloned();
                            if (path && PathBuf::from(path).exists()) {
                                logger.info(format!("[FIFOLlama] Selected: {}", path));
                                PathBuf::from(path)
                            }
                        }
                    }
                    let mut path = cards[0].get(&"path".to_string()).cloned();
                    if (path && PathBuf::from(path).exists()) {
                        logger.info(format!("[FIFOLlama] Using first model: {}", path));
                        PathBuf::from(path)
                    }
                }
            }
        }
        // except Exception as e:
        let mut home = Path.home();
        let mut ai_models = ((home / "AI".to_string()) / "Models".to_string()).canonicalize().unwrap_or_default();
        let mut config_models_dir = None;
        // try:
        {
            // TODO: from config_enhanced import Config
            let mut config_models_dir = Config.MODELS_DIR;
        }
        // except Exception as _e:
        if os::name == "nt".to_string() {
            let mut default_primary = std::env::var(&"MODELS_DIR".to_string()).unwrap_or_default().cloned().unwrap_or("C:\\AI\\Models".to_string());
            let mut candidates = vec![PathBuf::from(default_primary), PathBuf::from("C:\\AI\\Models".to_string()), ai_models, (home / "models".to_string()).canonicalize().unwrap_or_default(), PathBuf::from("./models".to_string()).canonicalize().unwrap_or_default()];
        } else {
            let mut default_primary = std::env::var(&"MODELS_DIR".to_string()).unwrap_or_default().cloned().unwrap_or(ai_models.to_string());
            let mut candidates = vec![PathBuf::from(default_primary).expanduser().canonicalize().unwrap_or_default(), ai_models, (home / "models".to_string()).canonicalize().unwrap_or_default(), (((home / ".local".to_string()) / "share".to_string()) / "models".to_string()).canonicalize().unwrap_or_default(), PathBuf::from("./models".to_string()).canonicalize().unwrap_or_default()];
        }
        if (config_models_dir && !candidates.contains(&config_models_dir)) {
            candidates.insert(0, config_models_dir);
        }
        let mut seen = HashSet::new();
        let mut all_ggufs = vec![];
        for d in candidates.iter() {
            // try:
            {
                let mut d = d.canonicalize().unwrap_or_default();
            }
            // except (OSError, RuntimeError) as _e:
            if (seen.contains(&d) || !d.exists()) {
                continue;
            }
            seen.insert(d);
            all_ggufs.extend(d.glob("*.gguf".to_string()));
            all_ggufs.extend(d.glob("*/*.gguf".to_string()));
        }
        if all_ggufs {
            let mut best = all_ggufs.min(/* key= */ |p| p.stat().st_size);
            logger.info(format!("[FIFOLlama] Found model: {}", best));
            best
        }
        Ok(None)
    }
    /// Load model into memory (singleton — one model shared across adapters).
    pub fn _setup_llm(&mut self) -> Result<()> {
        // Load model into memory (singleton — one model shared across adapters).
        if !LLAMA_CPP_AVAILABLE {
            self._init_error = "llama-cpp-python not installed".to_string();
            return;
        }
        let mut model_path = self.model_path;
        if !model_path {
            let mut found = self._find_gguf_model();
            if found {
                let mut model_path = found.to_string();
            }
        }
        if !model_path {
            self._init_error = "No GGUF model found".to_string();
            logger.error(format!("[FIFOLlama] {}", self._init_error));
            return;
        }
        let mut p = PathBuf::from(model_path);
        if !p.exists() {
            self._init_error = format!("Model file not found: {}", model_path);
            logger.error(format!("[FIFOLlama] {}", self._init_error));
            return;
        }
        let _ctx = FIFOLlamaCppAdapter._shared_lock;
        {
            if (FIFOLlamaCppAdapter._shared_llm.is_some() && FIFOLlamaCppAdapter._shared_model_path == p.to_string()) {
                logger.info(format!("[FIFOLlama] Reusing loaded model: {}", p.name));
                self._initialized = true;
                self.model_path = p.to_string();
                return;
            }
            let mut n_gpu = _get_n_gpu_layers();
            let mut to_try = if n_gpu != 0 { vec![0, n_gpu] } else { vec![0] };
            let mut last_error = None;
            for (attempt, gpu_layers) in to_try.iter().enumerate().iter() {
                if attempt > 0 {
                    logger.info("[FIFOLlama] Retrying with n_gpu_layers=%s".to_string(), gpu_layers);
                } else {
                    logger.info(format!("[FIFOLlama] Loading: {} ({:.1} GB), n_gpu_layers={}", p.name, (p.stat().st_size / (1024).pow(3 as u32)), gpu_layers));
                }
                // try:
                {
                    let mut llm = Llama(/* model_path= */ p.to_string(), /* n_gpu_layers= */ gpu_layers, /* n_ctx= */ 4096, /* n_threads= */ None, /* verbose= */ false);
                    FIFOLlamaCppAdapter._shared_llm = llm;
                    FIFOLlamaCppAdapter._shared_model_path = p.to_string();
                    self.model_path = p.to_string();
                    self._initialized = true;
                    logger.info("[FIFOLlama] Model loaded (in-memory, no port)".to_string());
                    break;
                }
                // except Exception as e:
            }
        }
    }
    /// Switch to a different model (unloads current, loads new).
    pub fn switch_model(&mut self, new_model_path: String) -> Result<bool> {
        // Switch to a different model (unloads current, loads new).
        if !LLAMA_CPP_AVAILABLE {
            false
        }
        let mut p = PathBuf::from(new_model_path);
        if !p.exists() {
            logger.error(format!("[FIFOLlama] Model not found: {}", new_model_path));
            false
        }
        let _ctx = FIFOLlamaCppAdapter._shared_lock;
        {
            if FIFOLlamaCppAdapter._shared_llm.is_some() {
                logger.info("[FIFOLlama] Unloading current model...".to_string());
                drop(FIFOLlamaCppAdapter._shared_llm);
                FIFOLlamaCppAdapter._shared_llm = None;
                FIFOLlamaCppAdapter._shared_model_path = None;
            }
            let mut n_gpu = _get_n_gpu_layers();
            for gpu_layers in if n_gpu != 0 { vec![n_gpu, 0] } else { vec![0] }.iter() {
                // try:
                {
                    logger.info(format!("[FIFOLlama] Loading: {} (n_gpu_layers={})", p.name, gpu_layers));
                    let mut llm = Llama(/* model_path= */ p.to_string(), /* n_gpu_layers= */ gpu_layers, /* n_ctx= */ 4096, /* n_threads= */ None, /* verbose= */ false);
                    FIFOLlamaCppAdapter._shared_llm = llm;
                    FIFOLlamaCppAdapter._shared_model_path = p.to_string();
                    self.model_path = p.to_string();
                    self._initialized = true;
                    self._init_error = None;
                    logger.info(format!("[FIFOLlama] Switched to {}", p.name));
                    true
                }
                // except Exception as e:
            }
            false
        }
    }
    /// TRUE token-level streaming via asyncio.Queue bridge.
    /// 
    /// This is the SINGLE streaming path. No batch variant.
    /// 
    /// Thread: llama_cpp.create_chat_completion(stream=true)
    /// -> each token -> queue.put_nowait via call_soon_threadsafe
    /// Async:  await queue.get() -> yield token
    pub async fn _stream_tokens(&self, prompt: String, params: HashMap<String, Box<dyn std::any::Any>>) -> Result<AsyncGenerator</* unknown */>> {
        // TRUE token-level streaming via asyncio.Queue bridge.
        // 
        // This is the SINGLE streaming path. No batch variant.
        // 
        // Thread: llama_cpp.create_chat_completion(stream=true)
        // -> each token -> queue.put_nowait via call_soon_threadsafe
        // Async:  await queue.get() -> yield token
        let mut llm = FIFOLlamaCppAdapter._shared_llm;
        if !llm {
            return Err(anyhow::anyhow!("RuntimeError('Model not loaded')"));
        }
        let mut messages = params.get(&"messages".to_string()).cloned();
        if !messages {
            let mut messages = vec![];
            let mut system_prompt = params.get(&"system_prompt".to_string()).cloned();
            if system_prompt {
                messages.push(HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)]));
            }
            messages.push(HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)]));
        }
        let mut temperature = params.get(&"temperature".to_string()).cloned().unwrap_or(0.7_f64);
        let mut top_p = params.get(&"top_p".to_string()).cloned().unwrap_or(0.9_f64);
        let mut max_tokens = params.get(&"max_tokens".to_string()).cloned().unwrap_or(2048);
        let mut grammar = params.get(&"grammar".to_string()).cloned();
        let mut response_format = params.get(&"response_format".to_string()).cloned();
        let mut seed = params.get(&"seed".to_string()).cloned();
        let mut logprobs = params.get(&"logprobs".to_string()).cloned();
        let mut top_logprobs = params.get(&"top_logprobs".to_string()).cloned();
        let mut logit_bias = params.get(&"logit_bias".to_string()).cloned();
        let mut top_k = params.get(&"top_k".to_string()).cloned();
        let mut min_p = params.get(&"min_p".to_string()).cloned();
        let mut repeat_penalty = params.get(&"repeat_penalty".to_string()).cloned();
        let mut frequency_penalty = params.get(&"frequency_penalty".to_string()).cloned();
        let mut presence_penalty = params.get(&"presence_penalty".to_string()).cloned();
        let mut tools = params.get(&"tools".to_string()).cloned();
        let mut tool_choice = params.get(&"tool_choice".to_string()).cloned();
        let mut _SENTINEL = object();
        let mut queue = asyncio.Queue();
        let mut r#loop = asyncio.get_running_loop();
        let _produce = || {
            // Thread: push each token to the async queue immediately.
            // 
            // No psutil, no diagnostics — InferenceGuard handles that
            // from the caller side.
            let mut accumulated = "".to_string();
            // try:
            {
                let mut call_kwargs = /* dict(/* messages= */ messages, /* temperature= */ temperature, /* top_p= */ top_p, /* max_tokens= */ max_tokens, /* stream= */ true, /* stop= */ _STOP_TOKENS) */ HashMap::new();
                if seed.is_some() {
                    call_kwargs["seed".to_string()] = seed;
                }
                if logprobs {
                    call_kwargs["logprobs".to_string()] = true;
                    if top_logprobs {
                        call_kwargs["top_logprobs".to_string()] = top_logprobs;
                    }
                }
                if logit_bias {
                    call_kwargs["logit_bias".to_string()] = logit_bias;
                }
                if top_k.is_some() {
                    call_kwargs["top_k".to_string()] = top_k;
                }
                if min_p.is_some() {
                    call_kwargs["min_p".to_string()] = min_p;
                }
                if repeat_penalty.is_some() {
                    call_kwargs["repeat_penalty".to_string()] = repeat_penalty;
                }
                if frequency_penalty {
                    call_kwargs["frequency_penalty".to_string()] = frequency_penalty;
                }
                if presence_penalty {
                    call_kwargs["presence_penalty".to_string()] = presence_penalty;
                }
                if grammar {
                    // try:
                    {
                        // TODO: from llama_cpp import LlamaGrammar
                        call_kwargs["grammar".to_string()] = LlamaGrammar.from_string(grammar);
                    }
                    // except Exception as e:
                }
                if response_format {
                    call_kwargs["response_format".to_string()] = response_format;
                }
                if tools {
                    call_kwargs["tools".to_string()] = tools;
                }
                if tool_choice.is_some() {
                    call_kwargs["tool_choice".to_string()] = tool_choice;
                }
                let mut completion = llm.create_chat_completion(/* ** */ call_kwargs);
                for chunk in completion.iter() {
                    if (chunk.contains(&"choices".to_string()) && chunk["choices".to_string()]) {
                        let mut delta = chunk["choices".to_string()][0].get(&"delta".to_string()).cloned().unwrap_or(HashMap::new());
                        let mut content = delta.get(&"content".to_string()).cloned();
                        if content {
                            accumulated += content;
                            if (accumulated.len() > 400 && accumulated[..-200].contains(&accumulated[-200..])) {
                                logger.warning("[FIFOLlama] Loop detected, stopping".to_string());
                                break;
                            }
                            r#loop.call_soon_threadsafe(queue.put_nowait, content);
                        }
                    }
                }
            }
            // except Exception as e:
            // finally:
                r#loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL);
        };
        r#loop.run_in_executor(None, _produce);
        while true {
            let mut item = queue.get().await;
            if item == _SENTINEL {
                break;
            }
            /* yield item */;
        }
    }
    /// Stream individual tokens as they're generated.
    /// 
    /// Each yield = one token from the model, the instant it's produced.
    /// Used by api_server for true SSE streaming.
    pub async fn query_stream_tokens(&mut self, request: String) -> AsyncGenerator</* unknown */> {
        // Stream individual tokens as they're generated.
        // 
        // Each yield = one token from the model, the instant it's produced.
        // Used by api_server for true SSE streaming.
        if !LLAMA_CPP_AVAILABLE {
            /* yield "❌ llama-cpp-python not installed".to_string() */;
            return;
        }
        if (!self._initialized || FIFOLlamaCppAdapter._shared_llm.is_none()) {
            let mut error = (self._init_error || "Model not loaded".to_string());
            /* yield format!("❌ Local LLM not ready: {}", error) */;
            return;
        }
        let mut prompt = /* getattr */ request.to_string();
        let mut params = HashMap::from([("system_prompt".to_string(), /* getattr */ None), ("temperature".to_string(), /* getattr */ 0.7_f64), ("top_p".to_string(), /* getattr */ 0.9_f64), ("max_tokens".to_string(), /* getattr */ 2048), ("grammar".to_string(), /* getattr */ None), ("response_format".to_string(), /* getattr */ None), ("seed".to_string(), /* getattr */ None), ("logprobs".to_string(), /* getattr */ None), ("top_logprobs".to_string(), /* getattr */ None), ("logit_bias".to_string(), /* getattr */ None), ("top_k".to_string(), /* getattr */ None), ("min_p".to_string(), /* getattr */ None), ("repeat_penalty".to_string(), /* getattr */ None), ("frequency_penalty".to_string(), /* getattr */ 0.0_f64), ("presence_penalty".to_string(), /* getattr */ 0.0_f64), ("tools".to_string(), /* getattr */ None), ("tool_choice".to_string(), /* getattr */ None)]);
        let mut messages = /* getattr */ None;
        if messages {
            params["messages".to_string()] = messages;
        }
        let mut model_name = if self.model_path { PathBuf::from(self.model_path).file_stem().unwrap_or_default().to_str().unwrap_or("") } else { "unknown".to_string() };
        logger.info(format!("[FIFOLlama] Token-stream -> {}: {}...", model_name, prompt[..80]));
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut token_count = 0;
        let mut first_token_at = None;
        // async for
        while let Some(token) = self._stream_tokens(prompt, /* ** */ params).next().await {
            if first_token_at.is_none() {
                let mut first_token_at = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            }
            token_count += 1;
            /* yield token */;
        }
        let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
        let mut ttft = if first_token_at { (first_token_at - start) } else { elapsed };
        let mut tps = if elapsed > 0 { (token_count / elapsed) } else { 0 };
        logger.info(format!("[FIFOLlama] Done {:.2}s  TTFT={:.3}s  {} tok  {:.1} tok/s", elapsed, ttft, token_count, tps));
    }
    /// Query the LLM — collects streamed tokens into a single response.
    /// 
    /// Uses _stream_tokens internally (single streaming path).
    /// Post-processes to strip leaked conversation markers.
    pub async fn query(&mut self, request: String) -> Result<AsyncGenerator</* unknown */>> {
        // Query the LLM — collects streamed tokens into a single response.
        // 
        // Uses _stream_tokens internally (single streaming path).
        // Post-processes to strip leaked conversation markers.
        if !LLAMA_CPP_AVAILABLE {
            /* yield "❌ llama-cpp-python not installed. Install: pip install llama-cpp-python".to_string() */;
            return;
        }
        if (!self._initialized || FIFOLlamaCppAdapter._shared_llm.is_none()) {
            let mut error = (self._init_error || "Model not loaded".to_string());
            /* yield format!("❌ Local LLM not ready: {}", error) */;
            return;
        }
        // try:
        {
            let mut prompt = /* getattr */ request.to_string();
            let mut params = HashMap::from([("system_prompt".to_string(), /* getattr */ None), ("temperature".to_string(), /* getattr */ 0.7_f64), ("top_p".to_string(), /* getattr */ 0.9_f64), ("max_tokens".to_string(), /* getattr */ 2048)]);
            let mut messages = /* getattr */ None;
            if messages {
                params["messages".to_string()] = messages;
            }
            let mut model_name = if self.model_path { PathBuf::from(self.model_path).file_stem().unwrap_or_default().to_str().unwrap_or("") } else { "unknown".to_string() };
            logger.info(format!("[FIFOLlama] Query to {}: {}...", model_name, prompt[..80]));
            self.request_buffer.add_message(/* content= */ prompt, /* message_type= */ "llm_request".to_string(), /* priority= */ MessagePriority.NORMAL, /* source= */ "RAG_RAT".to_string(), /* metadata= */ params, /* timeout= */ 5.0_f64).await;
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut chunks = vec![];
            // async for
            while let Some(token) = self._stream_tokens(prompt, /* ** */ params).next().await {
                chunks.push(token);
            }
            let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
            let mut total_text = chunks.join(&"".to_string());
            for marker in _STOP_TOKENS.iter() {
                if total_text.contains(&marker) {
                    let mut total_text = total_text[..total_text.iter().position(|v| *v == marker).unwrap()].trim_end().to_string();
                    break;
                }
            }
            self.response_buffer.add_message(/* content= */ total_text, /* message_type= */ "llm_response".to_string(), /* source= */ model_name, /* metadata= */ HashMap::from([("latency".to_string(), elapsed), ("chunks".to_string(), chunks.len())])).await;
            logger.info(format!("[FIFOLlama] Completed in {:.2}s ({} chunks, {} chars)", elapsed, chunks.len(), total_text.len()));
            /* yield total_text */;
        }
        // except Exception as e:
    }
    /// Check if model is loaded and ready.
    pub async fn validate(&self) -> bool {
        // Check if model is loaded and ready.
        ((LLAMA_CPP_AVAILABLE && self._initialized && FIFOLlamaCppAdapter._shared_llm.is_some()) != 0)
    }
    /// Cleanup (model stays loaded for reuse).
    pub async fn close(&self) -> () {
        // Cleanup (model stays loaded for reuse).
        return;
    }
    /// Get FIFO buffer statistics.
    pub fn get_stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Get FIFO buffer statistics.
        HashMap::from([("request_buffer".to_string(), self.request_buffer.stats()), ("response_buffer".to_string(), self.response_buffer.stats()), ("model_loaded".to_string(), self._initialized), ("model_path".to_string(), self.model_path)])
    }
}

/// Deterministic mock adapter for testing UI flows without a real LLM.
#[derive(Debug, Clone)]
pub struct MockLLMAdapter {
    pub closed: bool,
}

impl MockLLMAdapter {
    pub fn new(kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Self {
        Self {
            closed: false,
        }
    }
    pub async fn validate(&self) -> bool {
        true
    }
    pub async fn query(&self, request: String) -> () {
        let mut prompt = /* getattr */ "".to_string();
        let mut base = format!("MOCK_ANSWER: concise answer for prompt -> {}", prompt[..120]);
        for i in (0..base::len()).step_by(40 as usize).iter() {
            /* yield base[i..(i + 40)] */;
            asyncio.sleep(0).await;
        }
    }
    pub async fn close(&mut self) -> () {
        self.closed = true;
    }
}

/// Realistic mock that streams token-like chunks with delays.
#[derive(Debug, Clone)]
pub struct RealisticMockLLMAdapter {
    pub token_delay: String,
    pub closed: bool,
}

impl RealisticMockLLMAdapter {
    pub fn new() -> Self {
        Self {
            token_delay: token_delay,
            closed: false,
        }
    }
    pub async fn validate(&self) -> bool {
        true
    }
    pub async fn close(&mut self) -> () {
        self.closed = true;
    }
    pub async fn query(&mut self, request: String) -> AsyncGenerator</* unknown */> {
        let mut prompt = /* getattr */ "".to_string();
        let mut base = format!("Answer: summary({} chars) - This is a realistic mock streaming response that emits tokens one by one.", prompt.len());
        let mut tokens = vec![];
        let mut cur = vec![];
        for ch in base::iter() {
            cur.push(ch);
            if (ch.isspace() || ",.;!-".to_string().contains(&ch)) {
                tokens.push(cur.join(&"".to_string()));
                let mut cur = vec![];
            }
        }
        if cur {
            tokens.push(cur.join(&"".to_string()));
        }
        for tok in tokens.iter() {
            asyncio.sleep(self.token_delay).await;
            /* yield tok */;
        }
    }
}

/// Number of layers to offload to GPU. -1 = all, 0 = CPU-only. Read from env or config.
pub fn _get_n_gpu_layers() -> Result<i64> {
    // Number of layers to offload to GPU. -1 = all, 0 = CPU-only. Read from env or config.
    // try:
    {
        let mut val = (std::env::var(&"GPU_LAYERS".to_string()).unwrap_or_default().cloned() || std::env::var(&"LLM_GPU_LAYERS".to_string()).unwrap_or_default().cloned());
        if val.is_some() {
            val.to_string().parse::<i64>().unwrap_or(0)
        }
    }
    // except (ValueError, TypeError) as _e:
    // try:
    {
        // TODO: from Core.config import GPU_LAYERS
        GPU_LAYERS.to_string().parse::<i64>().unwrap_or(0)
    }
    // except Exception as exc:
    Ok(-1)
}

/// Wait for coroutine with timeout. Uses asyncio.wait() to avoid 'Timeout should be
/// used inside a task' when run under Streamlit/nest_asyncio or non-task contexts.
pub async fn _wait_with_timeout(coro: String, timeout_sec: f64) -> Result<()> {
    // Wait for coroutine with timeout. Uses asyncio.wait() to avoid 'Timeout should be
    // used inside a task' when run under Streamlit/nest_asyncio or non-task contexts.
    if (timeout_sec.is_none() || timeout_sec <= 0) {
        coro.await
    }
    let mut task = asyncio.ensure_future(coro);
    // try:
    {
        let (mut done, mut pending) = asyncio.wait(vec![task], /* timeout= */ timeout_sec, /* return_when= */ asyncio.FIRST_COMPLETED).await;
        if pending {
            task.cancel();
            // try:
            {
                task.await;
            }
            // except asyncio.CancelledError as exc:
            return Err(anyhow::anyhow!("asyncio.TimeoutError()"));
        }
        task.result()
    }
    // except asyncio.CancelledError as _e:
}
