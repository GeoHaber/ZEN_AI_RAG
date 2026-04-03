/// One-shot X-Ray audit of ZEN_AI_RAG connectivity.

use anyhow::{Result, Context};

pub static R: std::sync::LazyLock<analyze_connections> = std::sync::LazyLock::new(|| Default::default());

pub static D: std::sync::LazyLock<detect_dead_functions> = std::sync::LazyLock::new(|| Default::default());
