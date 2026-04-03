use anyhow::{Result, Context};
use crate::base::{BaseZenHandler};
use crate::config_system::{config};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Namespace for static file serving.
#[derive(Debug, Clone)]
pub struct StaticHandler {
}

impl StaticHandler {
    /// Routing for GET requests related to static files.
    pub fn handle_get(handler: BaseZenHandler) -> Result<()> {
        // Routing for GET requests related to static files.
        let mut path = handler.path;
        if path.contains(&"..".to_string()) {
            handler.send_json_response(403, HashMap::from([("error".to_string(), "Forbidden".to_string())]));
            true
        }
        if (path.starts_with(&*"/static/".to_string()) || path.starts_with(&*"/assets/".to_string())) {
            // try:
            {
                let mut rel_path = path.trim_start_matches(|c: char| "/".to_string().contains(c)).to_string();
                let mut file_path = (config::BASE_DIR / rel_path);
                if (file_path.exists() && file_path.is_file()) {
                    let (mut content_type, _) = mimetypes.guess_type(file_path.to_string());
                    handler.send_response(200);
                    handler.send_header("Content-Type".to_string(), (content_type || "application/octet-stream".to_string()));
                    handler.end_headers();
                    let mut f = File::open(file_path)?;
                    {
                        handler.wfile.write(f.read());
                    }
                    true
                }
            }
            // except Exception as e:
        }
        Ok(false)
    }
}
