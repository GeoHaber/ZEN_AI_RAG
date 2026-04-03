use anyhow::{Result, Context};

pub static EXAMPLES: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());
