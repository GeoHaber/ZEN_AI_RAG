/// settings::py - Legacy Bridge for config_system
/// Allows old files to 'from settings import ...' without breaking.

use anyhow::{Result, Context};
use crate::config_system::{config, get_settings, is_dark_mode, set_dark_mode, AppConfig, ExternalLLMConfig};

pub const EXTERNALLLMSETTINGS: &str = "ExternalLLMConfig";

pub static __ALL__: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Wrapper for AppConfig that provides a unified settings interface.
#[derive(Debug, Clone)]
pub struct AppSettings {
    pub _config: AppConfig,
    pub external_llm: ExternalLLMSettings,
}

impl AppSettings {
    pub fn new() -> Self {
        Self {
            _config: AppConfig(),
            external_llm: ExternalLLMSettings(),
        }
    }
    pub fn __getattr__(&self, name: String) -> () {
        /* getattr(self._config, name) */ Default::default()
    }
}
