use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const API_URL: &str = "http://127.0.0.1:8002/api/chat/swarm";

pub const SWARM_LAUNCH_URL: &str = "http://127.0.0.1:8002/swarm/launch";

pub const HEALTH_URL: &str = "http://127.0.0.1:8005/health";

pub static SERVER_PROC: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Start server.
pub fn start_server() -> Result<()> {
    // Start server.
    // global/nonlocal SERVER_PROC
    // TODO: import subprocess
    // TODO: import sys
    logger.info("🔧 Starting Backend Server (headless)...".to_string());
    let mut cmd = vec![sys::executable, "-m".to_string(), "zena_mode.server".to_string()];
    let mut log_file = File::create("server_log.txt".to_string())?;
    let mut SERVER_PROC = subprocess::Popen(cmd, /* cwd= */ ".".to_string(), /* stdout= */ log_file, /* stderr= */ subprocess::STDOUT, /* shell= */ false);
    // TODO: import time
    for i in 0..60.iter() {
        // try:
        {
            if /* reqwest::get( */&"http://127.0.0.1:8002/health".to_string()).cloned().unwrap_or(/* timeout= */ 1).status_code == 200 {
                logger.info("✅ Server Online".to_string());
                true
            }
        }
        // except Exception as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
    }
    Ok(false)
}

/// Launch expert.
pub fn launch_expert() -> Result<()> {
    // Launch expert.
    logger.info("🚀 Launching Expert (TinyLlama)...".to_string());
    // try:
    {
        let mut resp = /* reqwest::post( */SWARM_LAUNCH_URL, /* json= */ HashMap::from([("model".to_string(), "tinyllama-1.1b-chat::Q4_K_M.gguf".to_string()), ("port".to_string(), 8005)]), /* timeout= */ 10);
        logger.info(format!("Launch Response: {} - {}", resp.status_code, resp.text));
        if resp.status_code != 200 {
            false
        }
    }
    // except Exception as e:
    // TODO: import time
    for _ in 0..60.iter() {
        // try:
        {
            if /* reqwest::get( */&HEALTH_URL).cloned().unwrap_or(/* timeout= */ 5).status_code == 200 {
                logger.info("✅ Expert Online".to_string());
                true
            }
        }
        // except Exception as e:
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
        println!("{}", "x".to_string());
    }
    Ok(false)
}

/// Test consensus.
pub fn test_consensus() -> Result<()> {
    // Test consensus.
    if !start_server() {
        logger.error("❌ Failed to start server in time".to_string());
        if SERVER_PROC {
            SERVER_PROC.kill();
        }
        return;
    }
    if !launch_expert() {
        logger.error("❌ Failed to launch expert".to_string());
        if SERVER_PROC {
            SERVER_PROC.kill();
        }
        return;
    }
    logger.info("🧠 Testing Deep Thinking (Council) Mode...".to_string());
    let mut payload = HashMap::from([("message".to_string(), "Who are you? Are you Qwen or TinyLlama?".to_string()), ("mode".to_string(), "council".to_string())]);
    // try:
    {
        let mut resp = /* reqwest::post( */API_URL, /* json= */ payload, /* timeout= */ 60);
        logger.info(format!("Response Status: {}", resp.status_code));
        if resp.status_code == 200 {
            let mut data = resp.json();
            logger.info("✅ Success!".to_string());
            logger.info(format!("Response: {}...", data["response".to_string()][..200]));
            logger.info(format!("Mode: {}", data.get(&"mode".to_string()).cloned()));
            if (data["response".to_string()].contains(&"TinyLlama".to_string()) || data["response".to_string()].contains(&"Qwen".to_string())) {
                logger.info("✅ Models identified in response!".to_string());
            } else {
                logger.warning("⚠️ Could not explicitly identify models in text (might be hidden by consensus)".to_string());
            }
        } else {
            logger.error(format!("❌ Failed: {}", resp.text));
        }
    }
    // except Exception as e:
}
