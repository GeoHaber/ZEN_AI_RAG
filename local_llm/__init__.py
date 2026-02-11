"""
local_llm — Local LLM infrastructure management for ZEN_AI_RAG.

Provides integrated llama.cpp detection, GGUF model discovery,
process management, and model card metadata.

Implementation sourced from RAG_RAT/local_llm (the canonical copy) and
kept in-tree to avoid fragile sys.path hacks.
"""

import logging as _logging

_logger = _logging.getLogger(__name__)

# Try the in-tree implementations first (preferred).
# Falls back to RAG_RAT's copy via sys.path only as a last resort.
try:
    from local_llm.llama_cpp_manager import LlamaCppManager, LlamaCppStatus
    from local_llm.model_card import ModelRegistry, ModelCard, ModelCategory
    from local_llm.local_llm_manager import LocalLLMManager, LocalLLMStatus
except ImportError:
    try:
        # Attempt to import from local_llm_backup as secondary fallback
        from local_llm_backup.llama_cpp_manager import LlamaCppManager, LlamaCppStatus
        from local_llm_backup.model_card import ModelRegistry, ModelCard, ModelCategory
        from local_llm_backup.local_llm_manager import LocalLLMManager, LocalLLMStatus
        _logger.info("local_llm: Using local_llm_backup fallback")
    except ImportError as exc:
        _logger.warning(f"local_llm: No implementation available — {exc}")
        # Provide stub placeholders so imports don't crash at module level
        LlamaCppManager = None  # type: ignore[assignment,misc]
        LlamaCppStatus = None  # type: ignore[assignment,misc]
        ModelRegistry = None  # type: ignore[assignment,misc]
        ModelCard = None  # type: ignore[assignment,misc]
        ModelCategory = None  # type: ignore[assignment,misc]
        LocalLLMManager = None  # type: ignore[assignment,misc]
        LocalLLMStatus = None  # type: ignore[assignment,misc]

__all__ = [
    "LlamaCppManager",
    "LlamaCppStatus",
    "ModelRegistry",
    "ModelCard",
    "ModelCategory",
    "LocalLLMManager",
    "LocalLLMStatus",
]
