/// Predefined prompts for real-case medical scenarios.
/// Used by run_queries_report::py to drive RAG + optional LLM.

use anyhow::{Result, Context};

pub static MEDICAL_PROMPTS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static PROMPT_IDS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());
