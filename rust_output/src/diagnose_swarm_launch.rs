use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const SWARM_LAUNCH_URL: &str = "http://127.0.0.1:8002/swarm/launch";

pub const HEALTH_URL: &str = "http://127.0.0.1:8005/health";

pub const MODEL_NAME: &str = "tinyllama-1.1b-chat::Q4_K_M.gguf";

/// Check server health.
pub fn check_server_health() -> Result<()> {
    // Check server health.
    for _ in 0..15.iter() {
        // try:
        {
            let mut resp = /* reqwest::get( */&"http://127.0.0.1:8002/health".to_string()).cloned().unwrap_or(/* timeout= */ 2);
            if resp.status_code == 200 {
                true
            }
        }
        // except Exception as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(2));
        logger.info("   ... waiting for Main Server (8002) ...".to_string());
    }
    Ok(false)
}

/// Diagnose launch.
pub fn diagnose_launch() -> Result<()> {
    // Diagnose launch.
    logger.info("🔍 DIAGNOSING SWARM LAUNCH...".to_string());
    if !check_server_health() {
        logger.error("❌ Main Orchestrator (Port 8002) is OFFLINE. Cannot proceed.".to_string());
        logger.info("👉 Run 'python -m zena_mode.server' in another terminal first.".to_string());
        return;
    }
    logger.info("✅ Main Orchestrator is ONLINE.".to_string());
    logger.info(format!("🚀 Sending Launch Request for {} on Port 8005...", MODEL_NAME));
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    // try:
    {
        let mut resp = /* reqwest::post( */SWARM_LAUNCH_URL, /* json= */ HashMap::from([("model".to_string(), MODEL_NAME), ("port".to_string(), 8005)]), /* timeout= */ 15);
        logger.info(format!("📥 Response ({}): {}", resp.status_code, resp.text));
        if resp.status_code != 200 {
            logger.error("❌ Launch API refused command.".to_string());
            return;
        }
    }
    // except Exception as e:
    logger.info("⏳ Waiting for Port 8005 to bind...".to_string());
    for i in 0..30.iter() {
        // try:
        {
            let mut r = /* reqwest::get( */&HEALTH_URL).cloned().unwrap_or(/* timeout= */ 1);
            if r.status_code == 200 {
                let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
                logger.info(format!("✅ EXPERT IS ONLINE! (Took {:.2}s)", elapsed));
                return;
            } else {
                logger.warning(format!("⚠️ Port active but returned {}", r.status_code));
            }
        }
        // except requests.exceptions::ConnectionError as _e:
        // except requests.exceptions::ReadTimeout as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
        if (i % 5) == 0 {
            logger.info(format!("   ... waiting {}s", i));
        }
    }
    Ok(logger.error("❌ Timed out waiting for Expert Health Check.".to_string()))
}
