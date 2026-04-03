/// Quick import test to diagnose ZEN_AI_RAG startup issues.

use anyhow::{Result, Context};

pub const PROJECT_ROOT: &str = "Path(file!()).parent";

pub static TESTS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub static FAILED: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());
