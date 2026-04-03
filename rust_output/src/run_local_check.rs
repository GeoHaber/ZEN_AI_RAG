use anyhow::{Result, Context};
use crate::server::{BaseHTTPRequestHandler, HTTPServer};

pub static SRV: std::sync::LazyLock<HTTPServer> = std::sync::LazyLock::new(|| Default::default());

/// SimpleExpert class.
#[derive(Debug, Clone)]
pub struct SimpleExpert {
}

impl SimpleExpert {
    /// Do get.
    pub fn do_GET(&mut self) -> Result<()> {
        // Do get.
        if self.path == "/health".to_string() {
            self.send_response(200);
            self.end_headers();
            self.wfile.write(b"{"status":"ok"}");
        } else {
            self.send_response(404);
            self.end_headers();
        }
    }
    pub fn log_message(&self, a: Vec<Box<dyn std::any::Any>>) -> () {
        // pass
    }
}
