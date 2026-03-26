"""
LLM Backend - Pure async LLM calling without Streamlit dependencies
Provides async/streaming LLM interface for decoupled backend operations

Examples:
    >>> backend = LLMBackend()
    >>> response = asyncio.run(backend.call_llm("OpenAI", "gpt-4", "key", messages))
    >>> # Or use streaming:
    >>> async with backend.stream_llm("OpenAI", "gpt-4", "key", messages) as stream:
    ...     async for chunk in stream:
    ...         print(chunk, end='')
"""

import asyncio
import logging
from typing import List, Dict, Optional, AsyncGenerator

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS — canonical definitions live in llm_adapters.py
# =============================================================================

from llm_adapters import LLMResponse  # noqa: E402


# =============================================================================
# LLM BACKEND (Async, no Streamlit dependencies)
# =============================================================================


class LLMBackend:
    """
    Pure async LLM backend for calling various LLM providers.
    No Streamlit dependencies - suitable for testing, servers, CLIs.

    Supports:
    - Async/await patterns
    - Streaming responses
    - Error recovery
    - Provider abstraction (OpenAI, Claude, Ollama, Local llama-cpp, Gemini)
    """

    def __init__(self, timeout: float = 60.0):
        """
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._providers = {}

    async def call_llm(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Call LLM synchronously and return full response.

        Args:
            provider: Provider name ("OpenAI", "Ollama", "Claude", "Local (llama-cpp)", "Gemini")
            model: Model name
            api_key: API key if required
            messages: List of message dicts with 'role' and 'content'
            prompt: Single prompt string (alt to messages)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt override

        Returns:
            LLMResponse with full text response
        """
        try:
            text = ""
            async for chunk in self.stream_llm(
                provider=provider,
                model=model,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            ):
                text += chunk

            return LLMResponse(
                text=text or "",
                model=model,
                provider=provider,
                success=True,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return LLMResponse(
                text="",
                model=model,
                provider=provider,
                error=str(e),
                success=False,
            )

    async def stream_llm(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response as async generator.

        Args:
            provider: Provider name
            model: Model name
            api_key: API key if required
            messages: List of message dicts
            prompt: Single prompt string
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            system_prompt: System prompt override

        Yields:
            Text chunks as they arrive from the LLM
        """
        # Build request
        if messages is None and prompt is None:
            raise ValueError("Must provide either 'messages' or 'prompt'")

        # Convert messages to prompt if needed
        if prompt is None and messages:
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        # Normalize provider name
        provider_normalized = self._normalize_provider(provider)

        # Get or create adapter
        try:
            from adapter_factory import create_adapter
            from llm_adapters import LLMRequest as AdapterRequest
        except ImportError:
            try:
                from .adapter_factory import create_adapter
                from .llm_adapters import LLMRequest as AdapterRequest
            except ImportError as e:
                logger.error(f"Failed to import adapters: {e}")
                yield f"Error: {e}"
                return

        # Map normalized provider names to adapter names
        provider_to_adapter = {
            "ollama": "Ollama",
            "llama.cpp": "Local (llama-cpp)",
            "local (llama-cpp)": "Local (llama-cpp)",
            "local_llama": "Local (llama-cpp)",
            "openai": "OpenAI",
            "claude": "Anthropic (Claude)",
            "anthropic": "Anthropic (Claude)",
            "anthropic (claude)": "Anthropic (Claude)",
            "gemini": "Google (Gemini)",
            "google": "Google (Gemini)",
            "google (gemini)": "Google (Gemini)",
            "huggingface": "HuggingFace",
        }

        adapter_name = provider_to_adapter.get(provider_normalized, provider)

        try:
            adapter = create_adapter(adapter_name, api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to create adapter for {adapter_name}: {e}")
            yield f"Error: Failed to initialize {adapter_name}: {e}"
            return

        # Create request
        req = AdapterRequest(
            provider=adapter_name,
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,
            system_prompt=system_prompt,
            api_key=api_key,
            stream=True,
        )

        # Call adapter
        try:
            # Validate readiness
            ok = await adapter.validate()
            if not ok:
                yield f"Error: provider {provider} not available or not configured"
                return

            # Stream response
            async for chunk in adapter.query(req):
                if isinstance(chunk, str):
                    yield chunk

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"\nError during streaming: {e}"
        finally:
            # Cleanup
            try:
                await adapter.close()
            except Exception as exc:
                logger.debug("%s", exc)

    def _normalize_provider(self, provider: str) -> str:
        """Normalize provider name to lowercase"""
        return provider.lower() if provider else "openai"

    async def validate_provider(self, provider: str, api_key: Optional[str] = None) -> bool:
        """
        Check if provider is available and ready.

        Args:
            provider: Provider name
            api_key: API key if required

        Returns:
            True if provider can be used, False otherwise
        """
        try:
            from adapter_factory import create_adapter as _create_adapter

            provider_map = {
                "ollama": "OLLAMA",
                "llama.cpp": "LOCAL_LLAMA",
                "local (llama-cpp)": "LOCAL_LLAMA",
                "openai": "OPENAI",
                "claude": "CLAUDE",
                "anthropic (claude)": "CLAUDE",
                "gemini": "GEMINI",
                "google (gemini)": "GEMINI",
            }

            enum_str = provider_map.get(self._normalize_provider(provider), "CUSTOM")

            # Import enum
            try:
                from llm_adapters import LLMProvider as AdapterProvider
            except ImportError:
                from .llm_adapters import LLMProvider as AdapterProvider

            enum_provider = getattr(AdapterProvider, enum_str)
            adapter = _create_adapter(enum_provider, api_key=api_key)
            result = await adapter.validate()
            await adapter.close()
            return result
        except Exception as e:
            logger.debug(f"Provider validation failed: {e}")
            return False


# =============================================================================
# COMPATIBILITY WRAPPER (for existing app.py code)
# =============================================================================

_backend_instance = None


def get_backend() -> LLMBackend:
    """Get or create singleton LLM backend"""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = LLMBackend()
    return _backend_instance


def call_llm(provider: str, model: str, api_key: str, messages: List[Dict]) -> str:
    """
    Synchronous wrapper for backward compatibility with existing code.

    This is called from Streamlit app.py. It runs the async backend
    in a thread to avoid event loop conflicts.

    Args:
        provider: Provider name (like "llama.cpp", "Ollama", "OpenAI", "Claude", "Gemini")
        model: Model name
        api_key: API key
        messages: List of message dicts

    Returns:
        Response text string
    """
    from concurrent.futures import ThreadPoolExecutor

    # Map simple provider names to adapter names
    provider_map = {
        "llama.cpp": "Local (llama-cpp)",
        "local (llama-cpp)": "Local (llama-cpp)",
        "local llama-cpp": "Local (llama-cpp)",
        "ollama": "Ollama",
        "openai": "OpenAI",
        "claude": "Anthropic (Claude)",
        "anthropic": "Anthropic (Claude)",
        "anthropic (claude)": "Anthropic (Claude)",
        "gemini": "Google (Gemini)",
        "google": "Google (Gemini)",
        "google (gemini)": "Google (Gemini)",
        "huggingface": "HuggingFace",
    }

    # Normalize provider name
    provider_normalized = provider.lower().strip()
    provider_full = provider_map.get(provider_normalized, provider)

    backend = get_backend()

    def _run_in_thread():
        """Run async code in a new thread with its own event loop"""

        async def _run():
            response = await backend.call_llm(
                provider=provider_full,
                model=model,
                api_key=api_key,
                messages=messages,
            )
            return response.text if response.success else f"Error: {response.error}"

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_run())
            loop.close()
            return result
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"

    try:
        # Run in executor (thread pool) to avoid event loop conflicts with Streamlit
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_thread)
            result = future.result(timeout=120)  # 2 minute timeout
        return result
    except Exception as e:
        logger.error(f"LLM wrapper failed: {e}")
        return f"Error: {str(e)}"
