use anyhow::{Result, Context};
use crate::base::{BaseZenHandler};
use crate::config_system::{config};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Namespace for model-related request handling.
#[derive(Debug, Clone)]
pub struct ModelHandler {
}

impl ModelHandler {
    /// Routing for GET requests related to models.
    pub fn handle_get(handler: BaseZenHandler) -> Result<()> {
        // Routing for GET requests related to models.
        let mut path = handler.path;
        if path == "/list".to_string() {
            // try:
            {
                let mut models = config::MODEL_DIR.glob("*.gguf".to_string()).iter().map(|f| f.name).collect::<Vec<_>>();
                handler.send_json_response(200, HashMap::from([("models".to_string(), models)]));
            }
            // except Exception as e:
        } else if path == "/models/popular".to_string() {
            // try:
            {
                let mut models = model_manager::get_popular_models();
                handler.send_json_response(200, models);
            }
            // except Exception as e:
        } else if path.starts_with(&*"/models/search".to_string()) {
            // TODO: import urllib::parse
            let mut query = urllib::parse.parse_qs(urllib::parse.urlparse(path).query).get(&"q".to_string()).cloned().unwrap_or(vec!["".to_string()])[0];
            // try:
            {
                let mut models = model_manager::search_hf_models(query);
                handler.send_json_response(200, models);
            }
            // except Exception as e:
        } else {
            false
        }
        Ok(true)
    }
    /// Routing for POST requests related to models.
    pub fn handle_post(handler: BaseZenHandler) -> Result<()> {
        // Routing for POST requests related to models.
        if handler.path == "/models/download".to_string() {
            let mut params = handler.parse_json_body();
            let mut repo_id = params.get(&"repo_id".to_string()).cloned();
            let mut filename = params.get(&"filename".to_string()).cloned();
            if (!repo_id || !filename) {
                handler.send_json_response(400, HashMap::from([("error".to_string(), "Missing repo_id or filename".to_string())]));
                true
            }
            // try:
            {
                model_manager::download_model_async(repo_id, filename);
                handler.send_json_response(200, HashMap::from([("status".to_string(), "started".to_string()), ("message".to_string(), format!("Downloading {}...", filename))]));
            }
            // except Exception as e:
            true
        }
        Ok(false)
    }
}
