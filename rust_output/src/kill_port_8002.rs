use anyhow::{Result, Context};

pub const PORT: i64 = 8002;

pub static KILLED: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());
