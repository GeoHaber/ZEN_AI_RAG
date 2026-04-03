use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::server::{ThreadingHTTPServer, ZenAIOrchestrator};
use std::collections::HashMap;

/// Verify that the 10MB request size limit is enforced.
pub fn test_request_size_limit() -> Result<()> {
    // Verify that the 10MB request size limit is enforced.
    let mut test_port = 9010;
    let run_server = || {
        // Run server.
        // try:
        {
            let mut server = ThreadingHTTPServer(("127.0.0.1".to_string(), test_port), ZenAIOrchestrator);
            server::serve_forever();
        }
        // except Exception as _e:
    };
    let mut t = std::thread::spawn(|| {});
    t.start();
    std::thread::sleep(std::time::Duration::from_secs_f64(1));
    let mut limit = config::MAX_FILE_SIZE;
    let mut large_data = ("x".to_string() * (limit + 1024));
    // try:
    {
        let mut url = format!("http://127.0.0.1:{}/api/chat", test_port);
        let mut resp = /* reqwest::post( */url, /* data= */ serde_json::to_string(&HashMap::from([("message".to_string(), large_data)])).unwrap(), /* timeout= */ 5);
        assert!(resp.status_code == 413, "Expected 413 for large payload, got {}", resp.status_code);
    }
    // except (requests.exceptions::ConnectionError, requests.exceptions::ChunkedEncodingError) as _e:
    // finally:
        // pass
}

/// Verify that the server rejects non-local binds if possible to test.
pub fn test_local_only_bind() -> Result<()> {
    // Verify that the server rejects non-local binds if possible to test.
    let mut url = format!("http://127.0.0.1:{}/startup/progress", config::mgmt_port);
    // try:
    {
        let mut resp = /* reqwest::get( */&url).cloned().unwrap_or(/* timeout= */ 1);
        assert!(vec![200, 404].contains(&resp.status_code));
    }
    // except requests.exceptions::ConnectionError as _e:
}

/// Verify that malformed JSON doesn't crash the orchestrator.
pub fn test_invalid_json_handling() -> Result<()> {
    // Verify that malformed JSON doesn't crash the orchestrator.
    let mut test_port = 9011;
    let run_server = || {
        // Run server.
        // try:
        {
            let mut server = ThreadingHTTPServer(("127.0.0.1".to_string(), test_port), ZenAIOrchestrator);
            server::serve_forever();
        }
        // except Exception as _e:
    };
    let mut t = std::thread::spawn(|| {});
    t.start();
    std::thread::sleep(std::time::Duration::from_secs_f64(1));
    let mut url = format!("http://127.0.0.1:{}/api/chat", test_port);
    let mut resp = /* reqwest::post( */url, /* data= */ "{invalid json...".to_string(), /* headers= */ HashMap::from([("Content-Type".to_string(), "application/json".to_string())]), /* timeout= */ 30);
    assert!(resp.status_code != 500);
}
