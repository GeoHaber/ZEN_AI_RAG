/// ui_flet/persistence::py — Disk persistence for user preferences
/// ================================================================
/// 
/// Saves/loads user settings to ``data/user_settings.json`` so they
/// survive across application restarts.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const ROOT: &str = "Path(file!()).resolve().parent.parent";

pub const SETTINGS_FILE: &str = "ROOT / 'data' / 'user_settings.json";

pub const _PERSISTENT_KEYS: &str = "('onboarded', 'dark_mode', 'council_mode', 'deep_thinking', 'quiet_cot', 'tts_enabled', 'rag_enabled', 'language')";

pub static _SETTINGS_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

/// Load saved settings from disk. Returns empty dict on error.
pub fn load_settings() -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Load saved settings from disk. Returns empty dict on error.
    let _ctx = _settings_lock;
    {
        if !SETTINGS_FILE.exists() {
            HashMap::new()
        }
        // try:
        {
            let mut data = serde_json::from_str(&SETTINGS_FILE.read_to_string())).unwrap();
            data.iter().iter().filter(|(k, v)| _PERSISTENT_KEYS.contains(&k)).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>()
        }
        // except Exception as exc:
    }
}

/// Persist the relevant subset of *state* to disk (atomic write).
pub fn save_settings(state: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Persist the relevant subset of *state* to disk (atomic write).
    let _ctx = _settings_lock;
    {
        // try:
        {
            SETTINGS_FILE.parent().unwrap_or(std::path::Path::new("")).create_dir_all();
            let mut data = _PERSISTENT_KEYS.iter().filter(|k| state::contains(&k)).map(|k| (k, state[&k])).collect::<HashMap<_, _>>();
            let mut content = serde_json::to_string(&data).unwrap();
            let (mut fd, mut tmp_path) = tempfile::mkstemp(/* dir= */ SETTINGS_FILE.parent().unwrap_or(std::path::Path::new("")), /* suffix= */ ".tmp".to_string());
            // try:
            {
                // TODO: import os
                os::write(fd, content.encode("utf-8".to_string()));
                os::close(fd);
                PathBuf::from(tmp_path).replace(SETTINGS_FILE);
            }
            // except Exception as _e:
            logger.info("Settings saved → %s".to_string(), SETTINGS_FILE);
        }
        // except Exception as exc:
    }
}

/// Load from disk and merge into *state* (disk wins).
pub fn apply_settings(state: HashMap<String, Box<dyn std::any::Any>>) -> () {
    // Load from disk and merge into *state* (disk wins).
    let mut saved = load_settings();
    state::extend(saved);
}
