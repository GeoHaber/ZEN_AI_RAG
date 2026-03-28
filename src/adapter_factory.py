"""
Adapter Factory - Creates LLM adapter instances

This module provides factory functions to create the correct adapter
based on provider selection. It's the single point of creation for
all LLM adapters, enabling flexibility and testing.

The factory pattern ensures:
- Single place to create adapters (easy to mock in tests)
- Consistent initialization across codebase
- Type safety and validation
- Easy to add new providers
"""

from typing import Dict, Optional, Type
import os
import logging
from llm_adapters import (
    BaseLLMAdapter,
    LocalLlamaAdapter,
    OllamaAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    HuggingFaceAdapter,
    GeminiAdapter,
)

try:
    from adapters.local_llm_wrapper import LocalLLMWrapperAdapter
except Exception:
    LocalLLMWrapperAdapter = None

try:
    import mlx_lm  # noqa: F401
    from adapters.mlx_adapter import MLXAdapter
except Exception:
    MLXAdapter = None

logger = logging.getLogger(__name__)


# Map provider names to adapter classes
def _build_adapter_map() -> Dict[str, Type[BaseLLMAdapter]]:
    m: Dict[str, Type[BaseLLMAdapter]] = {
        "Local (llama-cpp)": LocalLLMWrapperAdapter if LocalLLMWrapperAdapter is not None else LocalLlamaAdapter,
        "Ollama": OllamaAdapter,
        "OpenAI": OpenAIAdapter,
        "Anthropic (Claude)": AnthropicAdapter,
        "HuggingFace": HuggingFaceAdapter,
        "Google (Gemini)": GeminiAdapter,
    }
    if MLXAdapter is not None:
        m["Local (MLX)"] = MLXAdapter
    return m


ADAPTER_MAP: Dict[str, Type[BaseLLMAdapter]] = _build_adapter_map()

# Mapping from internal enum values (LLMProvider.value) to ADAPTER_MAP keys
PROVIDER_ALIAS = {
    "local_llama": "Local (llama-cpp)",
    "local_mlx": "Local (MLX)",
    "ollama": "Ollama",
    "openai": "OpenAI",
    "claude": "Anthropic (Claude)",
    "huggingface": "HuggingFace",
    "gemini": "Google (Gemini)",
    # other enum values may map to custom keys if added
}


def create_adapter(
    provider: str,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
) -> BaseLLMAdapter:
    """
    Factory function to create the correct LLM adapter.

    Validates provider name, handles optional API key, and returns
    an initialized adapter instance ready to use.

    Args:
        provider: Provider name (must match one of ADAPTER_MAP keys)
        api_key: API key if required (will use env var if not provided)
        endpoint: Custom endpoint URL (for local or custom APIs)
        model_name: Model name to use with this adapter
        **kwargs: Additional arguments passed to adapter constructor

    Returns:
        Initialized adapter instance ready for LLM calls

    Raises:
        ValueError: If provider is unknown or required config missing

    Examples:
        # Local model
        adapter = create_adapter("Local (llama-cpp)")

        # Cloud API with key
        adapter = create_adapter("OpenAI", api_key="sk-...")

        # Custom endpoint
        adapter = create_adapter("Ollama", endpoint="http://localhost:11434")
    """

    # Normalize provider name (case-insensitive, trim whitespace)
    # Accept either a string or an enum-like object (e.g. LLMProvider)
    if not isinstance(provider, str):
        provider = getattr(provider, "value", str(provider))
    provider_normalized = provider.strip()

    # Map common enum/string aliases to the ADAPTER_MAP keys
    provider_mapped = PROVIDER_ALIAS.get(provider_normalized, provider_normalized)

    # Validate provider exists
    if provider_mapped not in ADAPTER_MAP:
        available = ", ".join(ADAPTER_MAP.keys())
        raise ValueError(f"Unknown LLM provider: '{provider_normalized}'\nValid options: {available}")

    # Get adapter class
    adapter_class = ADAPTER_MAP[provider_mapped]

    # Build constructor args
    init_args = {}

    # Handle API key (try parameter, then environment variable)
    # Use provider_mapped (the ADAPTER_MAP key) for reliable matching
    ENV_KEY_MAP = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic (Claude)": "ANTHROPIC_API_KEY",
        "HuggingFace": "HUGGINGFACE_API_KEY",
        "Google (Gemini)": "GOOGLE_API_KEY",
    }
    if api_key:
        init_args["api_key"] = api_key
    elif provider_mapped in ENV_KEY_MAP:
        env_key = os.environ.get(ENV_KEY_MAP[provider_mapped])
        if env_key:
            init_args["api_key"] = env_key

    # Handle endpoint
    if endpoint:
        init_args["endpoint"] = endpoint

    # Handle model name
    if model_name:
        init_args["model_name"] = model_name

    # Add any additional kwargs
    init_args.update(kwargs)

    # Create and return adapter
    try:
        adapter = adapter_class(**init_args)
        # If wrapper adapter was selected but its FIFO adapter didn't initialize,
        # fall back directly to FIFOLlamaCppAdapter.
        try:
            if adapter_class is LocalLLMWrapperAdapter:
                fifo_adapter = getattr(adapter, "adapter", None)
                if not fifo_adapter or not getattr(fifo_adapter, "_initialized", False):
                    from local_adapters import FIFOLlamaCppAdapter

                    adapter = FIFOLlamaCppAdapter(model_path=None)
                    logger.info("[Factory] Wrapper FIFO not ready; using FIFOLlamaCppAdapter directly")
        except Exception as e:
            logger.warning(f"[Factory] Fallback check failed: {e}")
            pass
        return adapter
    except TypeError as e:
        raise ValueError(f"Failed to initialize {provider_normalized} adapter: {e}\nArgs passed: {init_args}")


def get_adapter(provider: str, **kwargs) -> BaseLLMAdapter:
    """
    Alias for create_adapter (backward compatibility).

    This function exists to support code that expects 'get_adapter'
    instead of 'create_adapter'. It simply calls create_adapter.

    Args:
        provider: Provider name
        **kwargs: Passed to create_adapter

    Returns:
        Initialized adapter instance
    """
    return create_adapter(provider, **kwargs)


def list_adapters() -> Dict[str, str]:
    """
    List all available adapters with descriptions.

    Useful for UI dropdown lists and help text.

    Returns:
        Dict mapping provider names to descriptions
    """
    out = {
        "Local (llama-cpp)": "Run GGUF models locally using llama.cpp library",
        "Ollama": "Run models via Ollama service (easiest local option)",
        "OpenAI": "Use OpenAI's GPT-4/3.5 models (requires API key)",
        "Anthropic (Claude)": "Use Claude models (requires API key)",
        "HuggingFace": "Use HuggingFace Inference API (requires API key)",
        "Google (Gemini)": "Use Google's Gemini models (requires API key)",
    }
    if MLXAdapter is not None:
        out["Local (MLX)"] = "Run MLX models locally on Apple Silicon (mlx-lm)"
    return out


def validate_provider(provider: str) -> bool:
    """
    Check if a provider name is valid without creating an adapter.

    Args:
        provider: Provider name to validate

    Returns:
        True if provider is valid

    Raises:
        ValueError: If provider is invalid
    """
    if not isinstance(provider, str):
        provider = getattr(provider, "value", str(provider))
    if provider.strip() not in ADAPTER_MAP:
        raise ValueError(f"Unknown provider: {provider}")
    return True


__all__ = [
    "create_adapter",
    "get_adapter",
    "list_adapters",
    "validate_provider",
    "ADAPTER_MAP",
]
