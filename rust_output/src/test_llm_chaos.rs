use anyhow::{Result, Context};
use crate::config_system::{config};
use std::collections::HashMap;
use tokio;

/// Explicitly verify 'Iron-Clad' resilience of the LLM Engine.
#[derive(Debug, Clone)]
pub struct TestLLMChaos {
}

impl TestLLMChaos {
    /// Flood the engine with 50 concurrent requests.
    pub async fn test_concurrency_flood(&self) -> Result<()> {
        // Flood the engine with 50 concurrent requests.
        if !config::BIN_DIR.exists() {
            pytest.skip("No engine binary found".to_string());
        }
        let send_request = |session, i| {
            // Send request.
            // try:
            {
                let mut payload = HashMap::from([("prompt".to_string(), format!("Test request {}", i)), ("n_predict".to_string(), 10)]);
                let mut resp = session.post(format!("http://127.0.0.1:{}/completion", config::llm_port), /* json= */ payload, /* timeout= */ 5);
                {
                    resp.status
                }
            }
            // except Exception as e:
        };
        let mut session = aiohttp.ClientSession();
        {
            let mut tasks = 0..50.iter().map(|i| send_request(session, i)).collect::<Vec<_>>();
            let mut results = asyncio.gather(/* *tasks */).await;
            let mut crashes = results.iter().filter(|r| (/* /* isinstance(r, str) */ */ true && r.contains(&"Connection refused".to_string()))).map(|r| r).collect::<Vec<_>>();
            assert!(crashes.len() == 0, "Engine crashed under load: {}", crashes[..3]);
        }
    }
    /// Send a massive 1MB payload to stress the tokenizer.
    pub async fn test_tokenizer_stress(&self) -> Result<()> {
        // Send a massive 1MB payload to stress the tokenizer.
        let mut garbage = random.choices((string.ascii_letters + string.punctuation), /* k= */ (1024 * 1024)).join(&"".to_string());
        let mut payload = HashMap::from([("prompt".to_string(), garbage), ("n_predict".to_string(), 1)]);
        let mut session = aiohttp.ClientSession();
        {
            // try:
            {
                let mut resp = session.post(format!("http://127.0.0.1:{}/completion", config::llm_port), /* json= */ payload, /* timeout= */ 10);
                {
                    assert!(vec![200, 400, 413, 500].contains(&resp.status), "Unexpected status: {}", resp.status);
                }
            }
            // except Exception as e:
        }
    }
    /// Identify Llama Server process, KILL IT, and verify it comes back.
    pub fn test_recovery_logic(&self) -> () {
        // Identify Llama Server process, KILL IT, and verify it comes back.
        // TODO: import time
        // TODO: from utils import is_port_active
        assert!(is_port_active(config::llm_port), "Engine not running at start of test");
        let mut target_pid = None;
        for p in psutil.process_iter(vec!["pid".to_string(), "name".to_string(), "cmdline".to_string()]).iter() {
            if !p.info["name".to_string()].to_lowercase().contains(&"llama-server".to_string()) {
                continue;
            }
            let mut target_pid = p.info["pid".to_string()];
            break;
        }
        if !target_pid {
            pytest.skip("Could not find llama-server process to kill".to_string());
        }
        println!("\n💀 KILLING PID {} FOR SCIENCE...", target_pid);
        psutil.Process(target_pid).kill();
        let mut recovered = false;
        for _ in 0..15.iter() {
            std::thread::sleep(std::time::Duration::from_secs_f64(1));
            if is_port_active(config::llm_port) {
                let mut recovered = true;
                break;
            }
        }
        assert!(recovered, "Orchestrator FAILED to restart the engine after crash!");
        println!("{}", "\n✅ Engine successfully resurrected! 🧟".to_string());
    }
}
