"""
LLM Service — Pure Async LLM Calling.

Responsibility: Call LLM providers without UI knowledge.
  - Accept requests in standard format
  - Delegate to adapter based on provider
  - Raise structured exceptions (never silent)
  - Return structured responses

Adapted from RAG_RAT/Core/services/llm_service.py.
"""

from __future__ import annotations

import asyncio
import logging
import time as _time
from typing import Any, AsyncGenerator, Dict, List, Optional

from Core.exceptions import (
    AuthenticationError,
    LLMError,
    ProviderError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for calling LLM providers.

    Pure business logic — no UI dependencies.
    Delegates to adapters for provider-specific calls.
    """

    def __init__(self):
        self._adapter_cache: Dict[str, Any] = {}

    async def call_llm(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        """
        Call an LLM with the provided parameters.

        Args:
            provider: Provider name (e.g. "openai", "local_llama")
            model: Model name or path
            messages: Chat messages in OpenAI format
            api_key: API key if required by provider
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM response text.

        Raises:
            ValidationError, AuthenticationError, ProviderError, LLMError
        """
        self._validate_request(provider, model, messages, api_key)

        try:
            t0 = _time.perf_counter()
            adapter = await self._get_adapter(provider, api_key, model=model)
            t_adapt = _time.perf_counter() - t0
            logger.info(f"⏱ Adapter ready: {t_adapt:.3f}s ({provider})")

            # Build prompt from messages
            system_prompt: Optional[str] = None
            prompt_text = ""
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system_prompt = msg.get("content", "")
                    elif msg.get("role") == "user":
                        prompt_text = msg.get("content", prompt_text)

            # Lazy import to avoid circular deps at module level
            from llm_adapters import LLMRequest, LLMProvider

            request = LLMRequest(
                provider=LLMProvider.LOCAL_LLAMA,
                model=model,
                prompt=prompt_text,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                stream=True,
            )

            t_infer_start = _time.perf_counter()
            chunks: List[str] = []
            async for chunk in adapter.query(request):
                chunks.append(chunk)

            response = "".join(chunks)
            t_total = _time.perf_counter() - t0
            logger.info(
                f"✓ LLM call {provider}/{model} adapt={t_adapt:.2f}s total={t_total:.2f}s {len(response)} chars"
            )
            return response

        except (AuthenticationError, ProviderError, ValidationError):
            raise
        except asyncio.TimeoutError:
            raise LLMError("LLM call timed out after 60 seconds", provider=provider)
        except Exception as exc:
            raise LLMError(
                f"Failed to call {provider} ({model}): {exc}",
                provider=provider,
            )

    async def stream_llm(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response tokens as they arrive.

        Yields:
            Response tokens as strings.
        """
        self._validate_request(provider, model, messages, api_key)

        try:
            adapter = await self._get_adapter(provider, api_key, model=model)
            async for chunk in adapter.stream_llm(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ):
                yield chunk
        except (AuthenticationError, ProviderError, ValidationError):
            raise
        except asyncio.TimeoutError:
            raise LLMError("Streaming timed out", provider=provider)
        except Exception as exc:
            raise LLMError(f"Stream failed: {exc}", provider=provider)

    # ── Private helpers ─────────────────────────────────

    def _validate_request(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        api_key: Optional[str],
    ) -> None:
        if not provider or not provider.strip():
            raise ValidationError("Provider cannot be empty", field="provider")
        if not model or not model.strip():
            raise ValidationError("Model cannot be empty", field="model")
        if not messages:
            raise ValidationError("Messages cannot be empty", field="messages")

    async def _get_adapter(
        self,
        provider: str,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Resolve and cache an adapter for *provider*."""
        cache_key = f"{provider}:{api_key or 'no-key'}"
        if cache_key in self._adapter_cache:
            return self._adapter_cache[cache_key]

        try:
            from adapter_factory import create_adapter

            adapter = create_adapter(
                provider,
                api_key=api_key,
                model_name=kwargs.get("model"),
            )
            self._adapter_cache[cache_key] = adapter
            return adapter
        except ImportError:
            raise ProviderError(
                "adapter_factory not available — install adapter layer",
                provider=provider,
            )
        except Exception as exc:
            raise ProviderError(
                f"Cannot create adapter for {provider}: {exc}",
                provider=provider,
            )
