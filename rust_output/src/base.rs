use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::server::{BaseHTTPRequestHandler};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Base class for Zena AI server handlers, providing common logic and security.
#[derive(Debug, Clone)]
pub struct BaseZenHandler {
}

impl BaseZenHandler {
    /// Standard JSON response helper.
    pub fn send_json_response(&self, status: i64, data: HashMap<String, serde_json::Value>) -> Result<()> {
        // Standard JSON response helper.
        self.send_response(status);
        self.send_header("Content-Type".to_string(), "application/json".to_string());
        self.send_header("Access-Control-Allow-Origin".to_string(), "http://127.0.0.1:8080".to_string());
        self.end_headers();
        Ok(self.wfile.write(serde_json::to_string(&data).unwrap().encode("utf-8".to_string())))
    }
    /// Enforces a global request size limit (Phase 1 security hardening).
    pub fn check_request_size(&mut self) -> Result<bool> {
        // Enforces a global request size limit (Phase 1 security hardening).
        let mut content_length_str = self.headers.get(&"Content-Length".to_string()).cloned();
        if content_length_str.is_none() {
            if self.command == "POST".to_string() {
                self.send_json_response(411, HashMap::from([("error".to_string(), "Content-Length required".to_string())]));
                false
            }
            true
        }
        // try:
        {
            let mut content_length = content_length_str.to_string().parse::<i64>().unwrap_or(0);
        }
        // except ValueError as _e:
        if content_length > config::get(&"MAX_FILE_SIZE".to_string()).cloned().unwrap_or(10485760) {
            self.send_json_response(413, HashMap::from([("error".to_string(), "Request entity too large".to_string())]));
            false
        }
        Ok(true)
    }
    /// Helper to parse JSON from the request body.
    pub fn parse_json_body(&mut self) -> Result<HashMap> {
        // Helper to parse JSON from the request body.
        if !self.check_request_size() {
            HashMap::new()
        }
        // try:
        {
            let mut content_length = self.headers.get(&"Content-Length".to_string()).cloned().unwrap_or(0).to_string().parse::<i64>().unwrap_or(0);
            if content_length == 0 {
                HashMap::new()
            }
            serde_json::from_str(&self.rfile.read(content_length)).unwrap()
        }
        // except Exception as e:
    }
}
