/// Thin wrapper — canonical implementation lives in zen_core_libs.rag.hallucination.
/// 
/// Backward-compatible aliases for names used in ZEN_AI_RAG.

use anyhow::{Result, Context};

pub const ADVANCEDHALLUCINATIONDETECTOR: &str = "HallucinationDetector";

pub const CLAIMCHECK: &str = "HallucinationFinding";
