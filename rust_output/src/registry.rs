/// ui/registry::py - Centralized UI Interaction Registry
/// Defines the IDs for all interactive elements to prevent dead links
/// and enable automatic chaos/monkey testing.

use anyhow::{Result, Context};

pub static UI_METADATA: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static MONKEY_TARGETS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

/// UI_IDS class.
#[derive(Debug, Clone)]
pub struct UI_IDS {
}
