"""
Adapter Factory — Creates LLM adapter instances.

Single point of creation for all LLM adapters: enables flexibility,
testability, and consistent initialization.

Adapted from RAG_RAT/adapter_factory.py.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Type

from llm_adapters import (
    BaseLLMAdapter,
    LocalLlamaAdapter,
    OllamaAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    HuggingFaceAdapter,
    GeminiAdapter,
    LLMFactory,
)

logger = logging.getLogger(__name__)

# Try to import the Local_LLM wrapper adapter if available
try:
    from adapters.local_llm_wrapper import LocalLLMWrapperAdapter
except Exception:
    LocalLLMWrapperAdapter = None  # type: ignore[assignment,misc]

# ─── Provider → Adapter mapping ──────────────────────────────

ADAPTER_MAP: Dict[str, Type[BaseLLMAdapter]] = {
    "Local (llama-cpp)": (
        LocalLLMWrapperAdapter
        if LocalLLMWrapperAdapter is not None
        else LocalLlamaAdapter
    ),
    "Ollama": OllamaAdapter,
    "OpenAI": OpenAIAdapter,
    "Anthropic (Claude)": AnthropicAdapter,
    "HuggingFace": HuggingFaceAdapter,
    "Google (Gemini)": GeminiAdapter,
}

PROVIDER_ALIAS: Dict[str, str] = {
    "local_llama": "Local (llama-cpp)",
    "local": "Local (llama-cpp)",
    "ollama": "Ollama",
    "openai": "OpenAI",
    "claude": "Anthropic (Claude)",
    "anthropic": "Anthropic (Claude)",
    "huggingface": "HuggingFace",
    "gemini": "Google (Gemini)",
    "google": "Google (Gemini)",
}


def create_adapter(
    provider: str,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLMAdapter:
    """
    Factory function: create the correct LLM adapter.

    Args:
        provider: Provider name (must match ADAPTER_MAP or PROVIDER_ALIAS)
        api_key: API key if required
        endpoint: Custom endpoint URL
        model_name: Model name / path
        **kwargs: Additional arguments for the adapter constructor

    Returns:
        Initialized adapter instance.

    Raises:
        ValueError: Unknown provider or missing required config.
    """
    # Normalise
    if not isinstance(provider, str):
        provider = getattr(provider, "value", str(provider))

    provider_stripped = provider.strip()

    # Resolve alias
    resolved = PROVIDER_ALIAS.get(provider_stripped.lower(), provider_stripped)
    if resolved not in ADAPTER_MAP:
        # Try original casing
        if provider_stripped in ADAPTER_MAP:
            resolved = provider_stripped
        else:
            available = list(ADAPTER_MAP.keys())
            raise ValueError(
                f"Unknown provider: {provider}. Available: {available}"
            )

    adapter_cls = ADAPTER_MAP[resolved]

    # Resolve API keys from env if not passed
    env_key_map = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic (Claude)": "ANTHROPIC_API_KEY",
        "HuggingFace": "HUGGINGFACE_API_KEY",
        "Google (Gemini)": "GOOGLE_API_KEY",
    }
    if not api_key:
        env_var = env_key_map.get(resolved)
        if env_var:
            api_key = os.getenv(env_var)

    # Build kwargs for constructor
    ctor_kwargs: Dict[str, Any] = {}
    if api_key:
        ctor_kwargs["api_key"] = api_key
    if endpoint:
        ctor_kwargs["endpoint"] = endpoint
    if model_name:
        ctor_kwargs["model_name"] = model_name
    ctor_kwargs.update(kwargs)

    # Different adapters accept different constructor args
    try:
        adapter = adapter_cls(**ctor_kwargs)
    except TypeError:
        # Fallback: omit extra kwargs
        try:
            adapter = adapter_cls(api_key=api_key) if api_key else adapter_cls()
        except TypeError:
            adapter = adapter_cls()

    logger.info(f"Created adapter: {resolved} ({adapter_cls.__name__})")
    return adapter
