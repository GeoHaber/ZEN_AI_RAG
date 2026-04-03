/// ui_flet/state::py — Centralised application state
/// ==================================================
/// 
/// Provides **AppState** (framework-agnostic mutable bag) used by ``app::py``
/// and the legacy ``get_state()`` helper for ``zena_flet::py``.
/// 
/// No framework imports here — both NiceGUI and Flet can depend on this.

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static DEFAULT_STATE: std::sync::LazyLock<HashMap<String, Box<dyn std::any::Any>>> = std::sync::LazyLock::new(|| HashMap::new());

/// Observable, dict-backed application state.
/// 
/// Access attributes naturally::
/// 
/// state = AppState()
/// state::dark_mode = true
/// print(state::rag_content)
/// 
/// Subscribe to changes::
/// 
/// state::subscribe(lambda: rebuild_ui())
#[derive(Debug, Clone)]
pub struct AppState {
    pub _DEFAULTS: HashMap<String, Box<dyn std::any::Any>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            _DEFAULTS: HashMap::new(),
        }
    }
    pub fn __getattr__(&self, name: String) -> Result<Box<dyn std::any::Any>> {
        let mut data = object.__getattribute__(self, "_data".to_string());
        if data.contains(&name) {
            data[&name]
        }
        return Err(anyhow::anyhow!("AttributeError(f\"AppState has no attribute '{name}'\")"));
    }
    pub fn __setattr__(&self, name: String, value: Box<dyn std::any::Any>) -> () {
        let mut data = object.__getattribute__(self, "_data".to_string());
        data[name] = value;
    }
    pub fn subscribe(&self, callback: Box<dyn Fn(serde_json::Value)>) -> () {
        self._subscribers.push(callback);
    }
    pub fn notify(&self) -> Result<()> {
        for cb in self._subscribers.iter() {
            // try:
            {
                cb();
            }
            // except Exception as _e:
        }
    }
    pub fn has_data(&self) -> bool {
        ((self.rag_content || self.rag_sources) != 0)
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        copy::deepcopy(self._data)
    }
}

/// Return the per-page state dict, initialising if needed.
pub fn get_state(page: String) -> HashMap<String, Box<dyn std::any::Any>> {
    // Return the per-page state dict, initialising if needed.
    if (!/* hasattr(page, "data".to_string()) */ true || page.data.is_none()) {
        page.data = HashMap::new();
    }
    if !page.data.contains(&"_state".to_string()) {
        page.data["_state".to_string()] = copy::deepcopy(DEFAULT_STATE);
    }
    page.data["_state".to_string()]
}

/// Build an LLM config dict from current state.
pub fn get_llm_config(state: AppState) -> HashMap<String, Box<dyn std::any::Any>> {
    // Build an LLM config dict from current state.
    HashMap::from([("provider".to_string(), state::provider), ("model".to_string(), state::model), ("api_key".to_string(), state::api_key), ("temperature".to_string(), state::setting_temperature), ("max_tokens".to_string(), state::setting_max_tokens), ("streaming".to_string(), state::setting_streaming)])
}

/// Return names of configured LLM providers.
pub fn get_available_providers() -> Result<Vec<String>> {
    // Return names of configured LLM providers.
    let mut providers = vec!["Local".to_string()];
    // try:
    {
        // TODO: import os
        if std::env::var(&"OPENAI_API_KEY".to_string()).unwrap_or_default().cloned() {
            providers.push("OpenAI".to_string());
        }
        if std::env::var(&"ANTHROPIC_API_KEY".to_string()).unwrap_or_default().cloned() {
            providers.push("Anthropic".to_string());
        }
    }
    // except Exception as _e:
    Ok(providers)
}
