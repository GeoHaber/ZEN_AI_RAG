
"""
Bridge to the central Local_LLM library.
This allows ZEN_AI_RAG to use the single source of truth in Documents/_Python/Local_LLM.
"""
import sys
import os
from pathlib import Path

# Calculate path to Documents/_Python/Local_LLM
# Current file is in: ZEN_AI_RAG/local_llm/__init__.py
# We need to go up to _Python, then down to Local_LLM
CURRENT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CURRENT_DIR.parent
PYTHON_ROOT = PROJECT_ROOT.parent.parent # Documents/_Python

LOCAL_LLM_PATH = PYTHON_ROOT / "Local_LLM"

if str(LOCAL_LLM_PATH) not in sys.path:
    # Prepend to ensure we load the real one, not this bridge (circular check)
    sys.path.insert(0, str(LOCAL_LLM_PATH))

# Now we can import from the actual package
# The actual package starts with Core so we import what ZEN_AI_RAG expects from Core.services
try:
    from Core.services import (
        LocalLLMManager, 
        LocalLLMStatus, 
        LlamaCppManager,
        ModelRegistry,
        # Re-export types if needed
        ModelCard,
        ModelCategory
    )
except ImportError as e:
    # If the path hack didn't work or file structure is different
    raise ImportError(f"Could not import Local_LLM from {LOCAL_LLM_PATH}. Error: {e}")

# Re-export for ZEN_AI_RAG compatibility
__all__ = [
    "LocalLLMManager", 
    "LocalLLMStatus", 
    "LlamaCppManager",
    "ModelRegistry",
    "ModelCard",
    "ModelCategory"
]
