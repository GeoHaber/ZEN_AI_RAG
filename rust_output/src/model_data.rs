use anyhow::{Result, Context};

pub static MODEL_INFO: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());
