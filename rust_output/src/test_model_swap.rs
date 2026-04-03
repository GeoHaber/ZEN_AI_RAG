use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const HUB_URL: &str = "http://127.0.0.1:8002";

pub const MODEL_NAME: &str = "qwen2.5-1.5b-instruct-q4_k_m.gguf";

/// Test swap.
pub fn test_swap() -> Result<()> {
    // Test swap.
    logger.info(format!("🔄 Triggering Swap to {}...", MODEL_NAME));
    // try:
    {
        let mut resp = /* reqwest::post( */format!("{}/swap", HUB_URL), /* json= */ HashMap::from([("model".to_string(), MODEL_NAME)]), /* timeout= */ 5);
        logger.info(format!("Response: {} {}", resp.status_code, resp.text));
    }
    // except Exception as e:
    logger.info("⏳ Waiting for restart...".to_string());
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) < 60 {
        // try:
        {
            let mut resp = /* reqwest::get( */&format!("{}/health", HUB_URL)).cloned().unwrap_or(/* timeout= */ 1);
            if resp.status_code == 200 {
                let mut data = resp.json();
                if data.get(&"llm_online".to_string()).cloned() {
                    logger.info(format!("✅ Server is BACK ONLINE! (Time: {:.1}s)", (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start)));
                    return;
                } else {
                    logger.info("Hub online, LLM booting...".to_string());
                }
            } else {
                logger.info(format!("Hub Status: {}", resp.status_code));
            }
        }
        // except requests.exceptions::ConnectionError as _e:
        // except Exception as e:
        std::thread::sleep(std::time::Duration::from_secs_f64(2));
    }
    Ok(logger.error("❌ TIMEOUT: Server did not return within 60s.".to_string()))
}
