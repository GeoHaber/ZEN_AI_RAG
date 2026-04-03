/// Thin wrapper — canonical implementation lives in zen_core_libs.rag.query_router.
/// 
/// Backward-compatible alias for names used in ZEN_AI_RAG.

use anyhow::{Result, Context};
use crate::query_router::{RoutingResult};
use crate::query_router::{};

pub const ROUTINGDECISION: &str = "RoutingResult";
