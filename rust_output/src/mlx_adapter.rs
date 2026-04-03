/// MLX Adapter - Run MLX models locally on Apple Silicon.
/// 
/// Text-only: mlx-lm. Vision/VLM (e.g. Qwen3.5-0.8B-MLX-4bit): mlx-vlm for text-only chat (num_images=0).
/// Discovers models under ~/AI/Models/mlx (or MLX_MODELS_DIR).

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static MLX_MODELS_DIR: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub static _MLX_LOAD: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MLX_STREAM_GENERATE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MLX_VLM_LOAD: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MLX_VLM_GENERATE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MLX_VLM_APPLY_CHAT_TEMPLATE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MLX_VLM_LOAD_CONFIG: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _KNOWN_TEXT_ONLY_MLX: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

/// Adapter for MLX models (Apple Silicon).
/// Loads model from a local path; supports streaming via stream_generate.
#[derive(Debug, Clone)]
pub struct MLXAdapter {
    pub model_name: String,
    pub _model_path: Option<String>,
    pub _model: Option<serde_json::Value>,
    pub _tokenizer: Option<serde_json::Value>,
    pub _processor: Option<serde_json::Value>,
    pub _vlm_config: Option<serde_json::Value>,
    pub _is_vlm: bool,
    pub _available_models: discover_mlx_models,
}

impl MLXAdapter {
    pub fn new(model_name: Option<String>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Self {
        Self {
            model_name,
            _model_path: None,
            _model: None,
            _tokenizer: None,
            _processor: None,
            _vlm_config: None,
            _is_vlm: false,
            _available_models: discover_mlx_models(),
        }
    }
    pub fn _resolve_model_path(&mut self) -> () {
        if !self.model_name {
            if self._available_models {
                self._model_path = self._available_models[0]["path".to_string()];
                self.model_name = self._available_models[0]["name".to_string()];
                logger.info(format!("[MLX] Auto-selected: {}", self.model_name));
            }
            return;
        }
        let mut p = PathBuf::from(self.model_name);
        if (p.is_absolute() && p.is_dir()) {
            self._model_path = p.to_string();
            return;
        }
        for m in self._available_models.iter() {
            if (m["name".to_string()] == self.model_name || m["path".to_string()].contains(&self.model_name)) {
                self._model_path = m["path".to_string()];
                return;
            }
        }
        let mut candidate = (MLX_MODELS_DIR / self.model_name);
        if candidate.is_dir() {
            self._model_path = candidate.to_string();
            return;
        }
        logger.warning(format!("[MLX] Model not found: {}", self.model_name));
    }
    pub fn _load_model(&mut self) -> Result<()> {
        if (self._model.is_some() && (self._tokenizer.is_some() || (self._is_vlm && self._processor.is_some()))) {
            return;
        }
        if !self._model_path {
            return Err(anyhow::anyhow!("RuntimeError(f'No MLX model path. Set model_name to a folder under {MLX_MODELS_DIR} or run download_mlx_model.py.')"));
        }
        let mut model_dir = PathBuf::from(self._model_path);
        if _is_vision_or_multimodal_model(model_dir) {
            _ensure_mlx_vlm();
            logger.info(format!("[MLX] Loading VLM (text-only chat) from {}", self._model_path));
            let (self._model, self._processor) = _mlx_vlm_load(self._model_path);
            self._vlm_config = _mlx_vlm_load_config(self._model_path);
            self._is_vlm = true;
            logger.info("[MLX] VLM loaded (use for text chat)".to_string());
            return;
        }
        _ensure_mlx();
        logger.info(format!("[MLX] Loading model from {}", self._model_path));
        // try:
        {
            let (self._model, self._tokenizer) = _mlx_load(self._model_path);
        }
        // except Exception as e:
        Ok(logger.info("[MLX] Model loaded".to_string()))
    }
    /// Build chat prompt from LLMRequest (system_prompt + prompt or messages).
    pub fn _build_prompt(&mut self, request: Box<dyn std::any::Any>) -> Result<String> {
        // Build chat prompt from LLMRequest (system_prompt + prompt or messages).
        let mut messages = /* getattr */ None;
        if (messages && /* /* isinstance(messages, list) */ */ true && self._tokenizer.is_some()) {
            // try:
            {
                let mut prompt = self._tokenizer.apply_chat_template(messages.iter().map(|m| HashMap::from([("role".to_string(), m.get(&"role".to_string()).cloned().unwrap_or("user".to_string())), ("content".to_string(), m.get(&"content".to_string()).cloned().unwrap_or("".to_string()))])).collect::<Vec<_>>(), /* tokenize= */ false, /* add_generation_prompt= */ true);
                prompt
            }
            // except Exception as exc:
        }
        let mut system = (/* getattr */ None || "".to_string());
        let mut user = (/* getattr */ "".to_string() || "".to_string());
        if system {
            format!("<|im_start|>system\n{}<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n", system, user)
        }
        Ok(if user { user } else { "".to_string() })
    }
    /// Run inference and stream response chunks (one yield per stream_generate step).
    pub async fn query(&mut self, request: Box<dyn std::any::Any>) -> Result<AsyncGenerator</* unknown */>> {
        // Run inference and stream response chunks (one yield per stream_generate step).
        // try:
        {
            self._load_model();
        }
        // except RuntimeError as e:
        // except Exception as e:
        let mut prompt = self._build_prompt(request);
        if (!prompt && /* hasattr(request, "prompt".to_string()) */ true) {
            let mut prompt = request.prompt;
        }
        if !prompt {
            /* yield "❌ MLX: empty prompt".to_string() */;
            return;
        }
        let mut temperature = /* getattr */ 0.7_f64;
        let mut max_tokens = /* getattr */ 2048;
        let mut top_p = /* getattr */ 0.9_f64;
        if self._is_vlm {
            let _vlm_generate = || {
                // try:
                {
                    let mut formatted = _mlx_vlm_apply_chat_template(self._processor, self._vlm_config, prompt, /* num_images= */ 0);
                    let mut result = _mlx_vlm_generate(self._model, self._processor, formatted, /* image= */ None, /* max_tokens= */ max_tokens, /* temperature= */ temperature, /* verbose= */ false);
                    if result { /* getattr */ result.to_string() } else { "".to_string() }
                }
                // except Exception as e:
            };
            let mut r#loop = asyncio.get_event_loop();
            let mut text = r#loop.run_in_executor(None, _vlm_generate).await;
            /* yield text */;
            return;
        }
        let mut r#loop = asyncio.get_event_loop();
        let mut queue = asyncio.Queue();
        let mut sentinel = object();
        let _produce = || {
            // try:
            {
                for part in _mlx_stream_generate(self._model, self._tokenizer, prompt, /* max_tokens= */ max_tokens).iter() {
                    let mut text = if /* /* isinstance(part, str) */ */ true { part } else { /* getattr */ part.to_string() };
                    if text {
                        r#loop.call_soon_threadsafe(queue.put_nowait, text);
                    }
                }
            }
            // except Exception as e:
            r#loop.call_soon_threadsafe(queue.put_nowait, sentinel);
        };
        // try:
        {
            r#loop.run_in_executor(None, _produce).await;
            while true {
                let mut chunk = queue.get().await;
                if chunk == sentinel {
                    break;
                }
                /* yield chunk */;
            }
        }
        // except Exception as e:
    }
    /// Stream LLM response (builds LLMRequest and yields from query).
    pub async fn stream_llm(&mut self, model: Option<String>, messages: Option<Vec<HashMap<String, String>>>, temperature: f64, max_tokens: i64, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> AsyncGenerator</* unknown */> {
        // Stream LLM response (builds LLMRequest and yields from query).
        if !messages {
            /* yield "❌ MLX: messages required".to_string() */;
            return;
        }
        // TODO: from llm_adapters import LLMRequest, LLMProvider
        let mut system = "".to_string();
        let mut prompt = "".to_string();
        for m in messages.iter() {
            if m.get(&"role".to_string()).cloned() == "system".to_string() {
                let mut system = m.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            } else if m.get(&"role".to_string()).cloned() == "user".to_string() {
                let mut prompt = m.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            }
        }
        let mut req = LLMRequest(/* provider= */ LLMProvider.LOCAL_LLAMA, /* model= */ (model || self.model_name || "".to_string()), /* prompt= */ prompt, /* system_prompt= */ (system || None), /* temperature= */ temperature, /* max_tokens= */ max_tokens, /* messages= */ messages);
        // async for
        while let Some(chunk) = self.query(req).next().await {
            /* yield chunk */;
        }
    }
    pub async fn validate(&self) -> Result<bool> {
        // try:
        {
            self._load_model();
            if self._is_vlm {
                (self._model.is_some() && self._processor.is_some())
            }
            (self._model.is_some() && self._tokenizer.is_some())
        }
        // except Exception as _e:
    }
    pub async fn close(&mut self) -> () {
        self._model = None;
        self._tokenizer = None;
        self._processor = None;
        self._vlm_config = None;
        self._is_vlm = false;
    }
    pub fn get_available_models(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        self._available_models
    }
}

pub fn _default_mlx_dir() -> PathBuf {
    (((Path.home() / "AI".to_string()) / "Models".to_string()) / "mlx".to_string())
}

pub fn _ensure_mlx() -> Result<()> {
    // global/nonlocal _mlx_load, _mlx_stream_generate
    if _mlx_load.is_some() {
        return;
    }
    // try:
    {
        // TODO: from mlx_lm import load as mlx_load_fn, stream_generate as mlx_stream_generate_fn
        let mut _mlx_load = mlx_load_fn;
        let mut _mlx_stream_generate = mlx_stream_generate_fn;
    }
    // except ImportError as e:
}

pub fn _ensure_mlx_vlm() -> Result<()> {
    // global/nonlocal _mlx_vlm_load, _mlx_vlm_generate, _mlx_vlm_apply_chat_template, _mlx_vlm_load_config
    if _mlx_vlm_load.is_some() {
        return;
    }
    // try:
    {
        // TODO: from mlx_vlm import load as vlm_load_fn, generate as vlm_generate_fn
        // TODO: from mlx_vlm.prompt_utils import apply_chat_template as vlm_apply_chat_template
        // TODO: from mlx_vlm.utils import load_config as vlm_load_config
        let mut _mlx_vlm_load = vlm_load_fn;
        let mut _mlx_vlm_generate = vlm_generate_fn;
        let mut _mlx_vlm_apply_chat_template = vlm_apply_chat_template;
        let mut _mlx_vlm_load_config = vlm_load_config;
    }
    // except ImportError as e:
}

/// true if config indicates a vision/VLM model (mlx_lm load() fails with 'parameters not in model').
pub fn _is_vision_or_multimodal_model(model_dir: PathBuf) -> Result<bool> {
    // true if config indicates a vision/VLM model (mlx_lm load() fails with 'parameters not in model').
    // try:
    {
        let mut resolved = model_dir.canonicalize().unwrap_or_default();
        let mut name_lower = resolved.name.to_lowercase().trim().to_string();
        if _KNOWN_TEXT_ONLY_MLX.contains(&name_lower) {
            false
        }
    }
    // except Exception as exc:
    if _KNOWN_TEXT_ONLY_MLX.contains(&model_dir.name.to_lowercase().trim().to_string()) {
        false
    }
    let mut config_path = (model_dir / "config::json".to_string());
    if !config_path.exists() {
        false
    }
    // try:
    {
        // TODO: import json
        let mut f = File::open(config_path)?;
        {
            let mut config = json::load(f);
        }
        let mut model_type = (config::get(&"model_type".to_string()).cloned() || "".to_string()).to_lowercase();
        let mut arch = (config::get(&"architectures".to_string()).cloned() || vec![]);
        let mut combined = ((model_type + " ".to_string()) + arch.iter().filter(|a| /* /* isinstance(a, str) */ */ true).map(|a| a).collect::<Vec<_>>().join(&" ".to_string())).to_lowercase();
        if (combined.contains(&"vision".to_string()) || combined.contains(&" vl".to_string()) || combined.contains(&"vl ".to_string()) || combined.contains(&"vlm".to_string())) {
            true
        }
        if (config::get(&"vision_tower".to_string()).cloned() || config::get(&"vision_config".to_string()).cloned()) {
            true
        }
        let mut config_str = serde_json::to_string(&config).unwrap();
        if (config_str.contains(&"vision_tower".to_string()) || config_str.contains(&"vision_config".to_string())) {
            true
        }
        false
    }
    // except Exception as _e:
}

/// Check if an MLX model can be used (path exists and has config or weights).
/// Returns (usable: bool, message: str). Use for UI status (e.g. offline vs ready).
pub fn check_mlx_model_usable(model_name: String, models_dir: Option<PathBuf>) -> tuple {
    // Check if an MLX model can be used (path exists and has config or weights).
    // Returns (usable: bool, message: str). Use for UI status (e.g. offline vs ready).
    if (!model_name || !model_name.to_string().trim().to_string()) {
        (false, "No model selected".to_string())
    }
    let mut root = (models_dir || MLX_MODELS_DIR).expanduser().canonicalize().unwrap_or_default();
    if !root.is_dir() {
        (false, format!("MLX dir not found: {}. Set MLX_MODELS_DIR or run download_mlx_model.py.", root))
    }
    for sub in root.iterdir().iter() {
        if !sub.is_dir() {
            continue;
        }
        if (sub.name == model_name || sub.name.contains(&model_name)) {
            if ((sub / "config::json".to_string()).exists() || sub.glob("*.safetensors".to_string()).iter().any(|v| *v)) {
                (true, format!("{} ready", model_name))
            }
            (false, format!("{}: missing config::json or weights", model_name))
        }
    }
    let mut candidate = (root / model_name);
    if candidate.is_dir() {
        if ((candidate / "config::json".to_string()).exists() || candidate.glob("*.safetensors".to_string()).iter().any(|v| *v)) {
            (true, format!("{} ready", model_name))
        }
        (false, format!("{}: missing config::json or weights", model_name))
    }
    (false, format!("Model '{}' not found in {}. Run: python scripts/download_mlx_model.py", model_name, root))
}

/// Scan for MLX model folders (text-only and VLM). VLMs are loaded with mlx-vlm for text-only chat.
/// Known text-only models are listed first. Returns path, name, filename.
pub fn discover_mlx_models(models_dir: Option<PathBuf>) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
    // Scan for MLX model folders (text-only and VLM). VLMs are loaded with mlx-vlm for text-only chat.
    // Known text-only models are listed first. Returns path, name, filename.
    let mut root = (models_dir || MLX_MODELS_DIR).expanduser().canonicalize().unwrap_or_default();
    if !root.is_dir() {
        vec![]
    }
    let mut result = vec![];
    for sub in { let mut v = root.iterdir().clone(); v.sort(); v }.iter() {
        if !sub.is_dir() {
            continue;
        }
        let mut name_lower = sub.name.to_lowercase();
        if (name_lower.contains(&"vl-".to_string()) || name_lower.contains(&"-vl".to_string()) || name_lower.contains(&"vision".to_string()) || name_lower.contains(&"vlm".to_string())) {
            logger.debug("[MLX] Skipping VL-named model: %s".to_string(), sub.name);
            continue;
        }
        let mut has_config = (sub / "config::json".to_string()).exists();
        let mut has_weights = sub.glob("*.safetensors".to_string()).iter().any(|v| *v);
        if (has_config || has_weights) {
            result.push(HashMap::from([("path".to_string(), sub.to_string()), ("name".to_string(), sub.name), ("filename".to_string(), sub.name)]));
        }
    }
    let sort_key = |item| {
        let mut name_lower = item["name".to_string()].to_lowercase();
        (if _KNOWN_TEXT_ONLY_MLX.contains(&name_lower) { 0 } else { 1 }, item["name".to_string()])
    };
    result.sort(/* key= */ sort_key);
    result
}
