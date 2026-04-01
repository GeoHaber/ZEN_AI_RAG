"""Thin wrapper — canonical implementation lives in zen_core_libs.rag.query_router.

Backward-compatible alias for names used in ZEN_AI_RAG.
"""
from zen_core_libs.rag.query_router import *  # noqa: F401,F403
from zen_core_libs.rag.query_router import RoutingResult

# Backward-compat alias used by existing ZEN_AI_RAG code
RoutingDecision = RoutingResult
