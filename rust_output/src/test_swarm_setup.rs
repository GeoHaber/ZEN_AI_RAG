use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const HUB_URL: &str = "http://127.0.0.1:8002";

pub const MODEL_NAME: &str = "tinyllama-1.1b-chat::Q4_K_M.gguf";

pub const SWARM_PORT: i64 = 8005;

/// Test launch.
pub fn test_launch() -> Result<()> {
    // Test launch.
    logger.info(format!("🚀 Launching {} on port {}...", MODEL_NAME, SWARM_PORT));
    // try:
    {
        let mut resp = /* reqwest::post( */format!("{}/swarm/launch", HUB_URL), /* json= */ HashMap::from([("model".to_string(), MODEL_NAME), ("port".to_string(), SWARM_PORT)]), /* timeout= */ 10);
        logger.info(format!("Launch Response: {} {}", resp.status_code, resp.text));
        if resp.status_code != 200 {
            return;
        }
    }
    // except Exception as e:
    logger.info("⏳ Waiting for expert to bind...".to_string());
    let mut url = format!("http://127.0.0.1:{}/health", SWARM_PORT);
    for i in 0..30.iter() {
        // try:
        {
            let mut resp = /* reqwest::get( */&url).cloned().unwrap_or(/* timeout= */ 1);
            if resp.status_code == 200 {
                logger.info("✅ Expert is ONLINE!".to_string());
                logger.info(resp.json());
                return;
            }
        }
        // except Exception as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
        println!("{}", ".".to_string());
    }
    Ok(logger.error("❌ TIMEOUT: Expert did not start.".to_string()))
}
