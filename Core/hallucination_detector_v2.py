"""Thin wrapper — canonical implementation lives in zen_core_libs.rag.hallucination.

Backward-compatible aliases for names used in ZEN_AI_RAG.
"""
from zen_core_libs.rag.hallucination import *  # noqa: F401,F403
from zen_core_libs.rag.hallucination import HallucinationDetector, HallucinationFinding

# Backward-compat aliases used by existing ZEN_AI_RAG code
AdvancedHallucinationDetector = HallucinationDetector
ClaimCheck = HallucinationFinding
