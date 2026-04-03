/// Minimal hub server for tests.
/// 
/// This module provides a small, stable HTTP hub implementation exposing
/// `start_hub` and `stop_hub` so the test-suite and the root shim can import
/// and control the management API without pulling in the full orchestrator.

use anyhow::{Result, Context};
use crate::server::{ThreadingHTTPServer, BaseHTTPRequestHandler};
use std::collections::HashMap;

pub static __ALL__: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// _SimpleHandler class.
#[derive(Debug, Clone)]
pub struct _SimpleHandler {
}

impl _SimpleHandler {
    /// Do options.
    pub fn do_OPTIONS(&self) -> () {
        // Do options.
        self.send_response(200);
        self.send_header("Access-Control-Allow-Origin".to_string(), "http://127.0.0.1:8080".to_string());
        self.send_header("Access-Control-Allow-Methods".to_string(), "GET, POST, OPTIONS".to_string());
        self.send_header("Access-Control-Allow-Headers".to_string(), "Content-Type".to_string());
        self.end_headers();
    }
    /// Do get.
    pub fn do_GET(&mut self) -> Result<()> {
        // Do get.
        if self.path == "/".to_string() {
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "text/plain".to_string());
            self.end_headers();
            self.wfile.write(b"ZenAI Hub Active");
            return;
        }
        if self.path == "/models/available".to_string() {
            // TODO: import json
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "application/json".to_string());
            self.end_headers();
            self.wfile.write(serde_json::to_string(&vec![]).unwrap().as_bytes().to_vec());
            return;
        }
        if self.path.starts_with(&*"/updates/check".to_string()) {
            // TODO: import json
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "application/json".to_string());
            self.end_headers();
            self.wfile.write(serde_json::to_string(&HashMap::new()).unwrap().as_bytes().to_vec());
            return;
        }
        self.send_response(404);
        Ok(self.end_headers())
    }
    pub fn log_message(&self, format: String, args: Vec<Box<dyn std::any::Any>>) -> () {
        return;
    }
}

pub fn _serve_in_thread(server: ThreadingHTTPServer) -> Result<()> {
    // try:
    {
        server::serve_forever();
    }
    // except Exception as _e:
}

/// Start a minimal HTTP hub in a background thread.
/// 
/// Returns the (server, thread) so callers/tests can shut it down.
pub fn start_hub(host: Option<String>, port: Option<i64>) -> Result<(ThreadingHTTPServer, threading::Thread)> {
    // Start a minimal HTTP hub in a background thread.
    // 
    // Returns the (server, thread) so callers/tests can shut it down.
    let mut bind_host = if host.is_some() { host } else { HOST };
    let mut bind_port = if port.is_some() { port } else { PORTS.get(&"MGMT_API".to_string()).cloned().unwrap_or(8002) };
    let mut server = ThreadingHTTPServer((bind_host, bind_port), _SimpleHandler);
    let mut thread = std::thread::spawn(|| {});
    thread.start();
    let mut timeout = 2.0_f64;
    let mut interval = 0.05_f64;
    let mut elapsed = 0.0_f64;
    // TODO: import socket
    let mut bound = false;
    while elapsed < timeout {
        // try:
        {
            let _ctx = socket::create_connection((bind_host, bind_port), /* timeout= */ 0.5_f64);
            {
                let mut bound = true;
                break;
            }
        }
        // except Exception as _e:
    }
    if !bound {
        // try:
        {
            server::shutdown();
            server::server_close();
        }
        // except Exception as _e:
        return Err(anyhow::anyhow!("RuntimeError(f'Hub failed to bind to {bind_host}:{bind_port} within {timeout}s')"));
    }
    println!("HUB_BOUND {}:{}", bind_host, bind_port);
    Ok((server, thread))
}

/// Stop the hub started by `start_hub`.
/// This is safe to call from tests or cleanup hooks.
pub fn stop_hub(server: ThreadingHTTPServer) -> Result<()> {
    // Stop the hub started by `start_hub`.
    // This is safe to call from tests or cleanup hooks.
    // try:
    {
        server::shutdown();
        server::server_close();
    }
    // except Exception as _e:
}

/// Backwards-compatible entry that starts the hub.
/// 
/// The original project exposes a `start_server` entrypoint; keep a thin
/// wrapper so imports remain stable during migration.
pub fn start_server(args: Vec<Box<dyn std::any::Any>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> () {
    // Backwards-compatible entry that starts the hub.
    // 
    // The original project exposes a `start_server` entrypoint; keep a thin
    // wrapper so imports remain stable during migration.
    start_hub(/* *args */, /* ** */ kwargs)
}
