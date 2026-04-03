use anyhow::{Result, Context};
use crate::server::{BaseHTTPRequestHandler, HTTPServer};
use std::collections::HashMap;

pub const ROOT: &str = "Path(file!()).parent.parent";

pub const _FQN_SRV: &str = "zena_mode.server";

/// _SimpleExpertHandler class.
#[derive(Debug, Clone)]
pub struct _SimpleExpertHandler {
}

impl _SimpleExpertHandler {
    /// Do get.
    pub fn do_GET(&mut self) -> Result<()> {
        // Do get.
        if self.path == "/health".to_string() {
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "application/json".to_string());
            self.end_headers();
            self.wfile.write(b"{"status":"ok"}");
        } else {
            self.send_response(404);
            self.end_headers();
        }
    }
    pub fn log_message(&self, format: String, args: Vec<Box<dyn std::any::Any>>) -> () {
        return;
    }
}

/// _HubHandler class.
#[derive(Debug, Clone)]
pub struct _HubHandler {
    pub servers: HashMap<i64, HTTPServer>,
}

impl _HubHandler {
    /// Do post.
    pub fn do_POST(&mut self) -> Result<()> {
        // Do post.
        if self.path == "/swarm/scale".to_string() {
            let mut length = self.headers.get(&"Content-Length".to_string()).cloned().unwrap_or(0).to_string().parse::<i64>().unwrap_or(0);
            let mut body = self.rfile.read(length);
            // try:
            {
                let mut data = serde_json::from_str(&body).unwrap();
                let mut count = data.get(&"count".to_string()).cloned().unwrap_or(0).to_string().parse::<i64>().unwrap_or(0);
            }
            // except Exception as _e:
            let mut started = vec![];
            let mut base = 8005;
            for i in 0..count.iter() {
                let mut port = (base + i);
                if _HubHandler.servers.contains(&port) {
                    started.push(port);
                    continue;
                }
                let mut server = HTTPServer(("127.0.0.1".to_string(), port), _SimpleExpertHandler);
                let mut t = std::thread::spawn(|| {});
                t.start();
                _HubHandler.servers[port] = server;
                started.push(port);
            }
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "application/json".to_string());
            self.end_headers();
            let mut resp = HashMap::from([("status".to_string(), "scaled".to_string()), ("ports".to_string(), started)]);
            self.wfile.write(serde_json::to_string(&resp).unwrap().encode("utf-8".to_string()));
        } else {
            self.send_response(404);
            self.end_headers();
        }
    }
    /// Do get.
    pub fn do_GET(&mut self) -> Result<()> {
        // Do get.
        if self.path == "/swarm/list".to_string() {
            let mut ports = _HubHandler.servers.keys().into_iter().collect::<Vec<_>>();
            self.send_response(200);
            self.send_header("Content-Type".to_string(), "application/json".to_string());
            self.end_headers();
            self.wfile.write(serde_json::to_string(&HashMap::from([("ports".to_string(), ports)])).unwrap().encode("utf-8".to_string()));
        } else {
            self.send_response(404);
            self.end_headers();
        }
    }
    pub fn log_message(&self, format: String, args: Vec<Box<dyn std::any::Any>>) -> () {
        return;
    }
}

/// Fixture to mock LLM API responses (8001).
pub fn mock_llm_api() -> () {
    // Fixture to mock LLM API responses (8001).
    let mut respx_mock = respx.mock(/* base_url= */ "http://127.0.0.1:8001".to_string(), /* assert_all_called= */ false);
    {
        respx_mock.get(&"/health".to_string()).cloned().mock(/* return_value= */ httpx.Response(200, /* json= */ HashMap::from([("status".to_string(), "ok".to_string())])));
        let mut stream_content = vec!["data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}\n\n".to_string(), "data: {\"choices\": [{\"delta\": {\"content\": \" world!\"}}]}\n\n".to_string(), "data: [DONE]\n\n".to_string()];
        respx_mock.post("/v1/chat/completions".to_string()).mock(/* return_value= */ httpx.Response(200, /* content= */ stream_content.join(&"".to_string())));
        /* yield respx_mock */;
    }
}

/// Fixture to mock Hub API responses (8002).
pub fn mock_hub_api() -> () {
    // Fixture to mock Hub API responses (8002).
    let mut respx_mock = respx.mock(/* base_url= */ "http://127.0.0.1:8002".to_string(), /* assert_all_called= */ false);
    {
        respx_mock.get(&"/models/available".to_string()).cloned().mock(/* return_value= */ httpx.Response(200, /* json= */ vec!["mock-model-1.gguf".to_string(), "mock-model-2.gguf".to_string()]));
        respx_mock.post("/models/load".to_string()).mock(/* return_value= */ httpx.Response(200, /* json= */ HashMap::from([("status".to_string(), "loaded".to_string())])));
        respx_mock.post("/models/download".to_string()).mock(/* return_value= */ httpx.Response(200, /* json= */ HashMap::from([("status".to_string(), "started".to_string())])));
        /* yield respx_mock */;
    }
}

/// Start a lightweight Hub on 127.0.0.1:8002 that can scale experts for integration tests.
pub fn hub_server() -> Result<()> {
    // Start a lightweight Hub on 127.0.0.1:8002 that can scale experts for integration tests.
    // try:
    {
        // TODO: from config_system import config
        config::swarm_enabled = true;
        config::swarm_size = 7;
        config::SWARM_ENABLED = true;
        config::SWARM_SIZE = 7;
    }
    // except Exception as _e:
    let mut hub = HTTPServer(("127.0.0.1".to_string(), 8002), _HubHandler);
    let mut th = std::thread::spawn(|| {});
    th.start();
    /* yield */;
    // try:
    {
        hub.shutdown();
    }
    // except Exception as _e:
    for srv in _HubHandler.servers.values().into_iter().collect::<Vec<_>>().iter() {
        // try:
        {
            srv.shutdown();
        }
        // except Exception as _e:
    }
}

/// Create an instance of the default event loop for the session.
pub fn event_loop() -> () {
    // Create an instance of the default event loop for the session.
    let mut r#loop = asyncio.new_event_loop();
    /* yield r#loop */;
    r#loop.close();
}
