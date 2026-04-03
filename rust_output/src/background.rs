use anyhow::{Result, Context};
use crate::auto_updater::{check_for_updates, get_local_version, ModelScout};
use crate::config_system::{config};
use crate::gateway_telegram::{run_gateway};
use crate::gateway_whatsapp::{run_whatsapp_gateway};
use crate::utils::{is_port_active};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Start the backend orchestrator if it's not already running.
pub fn start_backend_server() -> Result<()> {
    // Start the backend orchestrator if it's not already running.
    let mut mgmt_port = config::mgmt_port;
    if is_port_active(mgmt_port) {
        logger.info(format!("[Background] Backend Hub already active on port {}", mgmt_port));
        return;
    }
    logger.info(format!("[Background] Starting Backend Orchestrator on port {}...", mgmt_port));
    let mut cmd = vec![sys::executable, "-m".to_string(), "zena_mode.server".to_string(), "--no-ui".to_string(), "--guard-bypass".to_string()];
    // try:
    {
        subprocess::Popen(cmd, /* cwd= */ config::BASE_DIR.to_string(), /* creationflags= */ if os::name == "nt".to_string() { subprocess::CREATE_NEW_CONSOLE } else { 0 }, /* shell= */ false);
        logger.info("[Background] Backend launch command issued.".to_string());
        std::thread::sleep(std::time::Duration::from_secs_f64(2));
        if !is_port_active(mgmt_port) {
            logger.warning("[Background] Backend port still closed after simple launch.".to_string());
        }
    }
    // except Exception as e:
}

/// Launch backend services and messaging gateways.
pub fn start_background_gateways() -> () {
    // Launch backend services and messaging gateways.
    if config::system.auto_start_backend {
        std::thread::spawn(|| {});
    }
    let mut zena_config = config::get(&"zena_mode".to_string()).cloned().unwrap_or(HashMap::new());
    if zena_config.get(&"telegram_token".to_string()).cloned() {
        std::thread::spawn(|| {});
    }
    if zena_config.get(&"whatsapp_whitelist".to_string()).cloned() {
        std::thread::spawn(|| {});
    }
}

/// Perform background auto-update and model scout checks.
pub async fn run_system_checks() -> () {
    // Perform background auto-update and model scout checks.
    let mut zena_config = config::get(&"zena_mode".to_string()).cloned().unwrap_or(HashMap::new());
    if zena_config.get(&"auto_update_enabled".to_string()).cloned().unwrap_or(true) {
        let mut local_tag = get_local_version().await;
        let mut update_info = check_for_updates(/* current_tag= */ local_tag);
        if update_info {
            ui.notify(format!("💎 Shiny new update available: {}!", update_info["tag".to_string()]), /* color= */ "info".to_string(), /* position= */ "bottom-right".to_string());
        }
        let mut scout = ModelScout();
        let mut coding_models = scout.find_shiny_models("coding".to_string());
        if coding_models {
            logger.info(format!("[ModelScout] Found {} shiny models on HF.", coding_models.len()));
        }
    }
}
