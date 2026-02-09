"""
local_llm - Local LLM infrastructure management for ZEN_AI_RAG.

Unified llama.cpp detection, model discovery, and process management.
Ported from RAG_RAT's proven local_llm module (verified working).

Provides:
- LlamaCppManager: Engine lifecycle & health monitoring
- ModelRegistry: GGUF discovery and metadata
- LocalLLMManager: High-level orchestration (main entry point)
"""

from .llama_cpp_manager import LlamaCppManager, LlamaCppStatus
from .model_card import ModelRegistry, ModelCard, ModelCategory
from .local_llm_manager import LocalLLMManager, LocalLLMStatus

__all__ = [
    "LlamaCppManager",
    "LlamaCppStatus",
    "ModelRegistry",
    "ModelCard",
    "ModelCategory",
    "LocalLLMManager",
    "LocalLLMStatus",
]
