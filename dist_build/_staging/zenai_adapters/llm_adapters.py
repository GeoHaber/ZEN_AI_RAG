"""
LLM Adapters — Unified interface for multiple LLM providers.

Supports:
  - Local: llama.cpp (in-process via llama-cpp-python)
  - Cloud: OpenAI, Anthropic Claude, HuggingFace, Google Gemini
  - Custom: Any OpenAI-compatible API

Adapted from RAG_RAT/llm_adapters.py — the proven multi-provider adapter layer.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional HTTP client — only needed for cloud providers
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class LLMProvider(Enum):
    """Supported LLM providers."""
    LOCAL_LLAMA = "local_llama"
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"
    CUSTOM = "custom"


@dataclass
class LLMRequest:
    """Unified LLM request format."""
    provider: Any  # LLMProvider enum or str
    model: str
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    system_prompt: Optional[str] = None
    api_key: Optional[str] = None
    stream: bool = True
    endpoint: Optional[str] = None


@dataclass
class LLMResponse:
    """Unified LLM response format."""
    text: str
    provider: Any = None
    model: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None
    success: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ─── Base Adapter ────────────────────────────────────────

class BaseLLMAdapter:
    """Base class for LLM adapters."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        if httpx is not None:
            self.client = httpx.AsyncClient(timeout=120)

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query the LLM and yield response tokens."""
        raise NotImplementedError
        yield  # make it a generator  # noqa: E501

    async def validate(self) -> bool:
        """Validate the adapter is working."""
        raise NotImplementedError

    async def close(self):
        """Close HTTP client."""
        if self.client is not None:
            await self.client.aclose()


# ─── Local llama.cpp Adapter ────────────────────────────

class LocalLlamaAdapter(BaseLLMAdapter):
    """Adapter for local llama.cpp (in-memory, no HTTP port)."""

    def __init__(self, endpoint: Optional[str] = None):
        super().__init__()
        self.adapter = None
        self._endpoint = endpoint or "http://127.0.0.1:8001"

        # Try in-memory FIFO adapter first
        try:
            from local_adapters import FIFOLlamaCppAdapter
            self.adapter = FIFOLlamaCppAdapter()
            logger.info("[LLM] FIFO in-memory llama.cpp initialized")
        except (ImportError, Exception) as exc:
            logger.debug(f"[LLM] FIFO adapter not available: {exc}")

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.adapter:
            try:
                async for chunk in self.adapter.query(request):
                    yield chunk
                return
            except Exception as exc:
                logger.error(f"[LLM] In-memory query error: {exc}")
                yield f"Error: {exc}"
                return

        # Fallback: call llama-server HTTP API
        if self.client is None:
            yield "Error: httpx not installed"
            return
        url = f"{self._endpoint}/v1/chat/completions"
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        try:
            async with self.client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    error = await resp.aread()
                    yield f"Error: {resp.status_code} - {error.decode()}"
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        if self.adapter:
            try:
                return await self.adapter.validate()
            except Exception:
                return False
        if self.client is None:
            return False
        try:
            resp = await self.client.get(f"{self._endpoint}/health")
            return resp.status_code == 200
        except Exception:
            return False


# ─── Ollama Adapter ──────────────────────────────────────

class OllamaAdapter(BaseLLMAdapter):
    """Adapter for Ollama local LLM server."""

    def __init__(self, endpoint: str = "http://localhost:11434"):
        super().__init__()
        self.endpoint = endpoint

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.client is None:
            yield "Error: httpx not installed"
            return
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True,
            "num_predict": request.max_tokens,
        }
        try:
            async with self.client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    yield f"Error: {resp.status_code}"
                    return
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("response"):
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        if self.client is None:
            return False
        try:
            resp = await self.client.get(f"{self.endpoint}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False


# ─── OpenAI Adapter ──────────────────────────────────────

class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(api_key=key)
        self.endpoint = "https://api.openai.com/v1"

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.client is None:
            yield "Error: httpx not installed"
            return
        url = f"{self.endpoint}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key or request.api_key}",
            "Content-Type": "application/json",
        }
        messages: List[Dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error = await resp.aread()
                    yield f"Error: {resp.status_code} - {error.decode()}"
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        if not self.api_key or self.client is None:
            return False
        try:
            resp = await self.client.get(
                f"{self.endpoint}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return resp.status_code == 200
        except Exception:
            return False


# ─── Anthropic (Claude) Adapter ──────────────────────────

class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(api_key=key)
        self.endpoint = "https://api.anthropic.com/v1"

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.client is None:
            yield "Error: httpx not installed"
            return
        url = f"{self.endpoint}/messages"
        headers = {
            "x-api-key": self.api_key or request.api_key or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": True,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error = await resp.aread()
                    yield f"Error: {resp.status_code} - {error.decode()}"
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        return bool(self.api_key)


# ─── HuggingFace Adapter ────────────────────────────────

class HuggingFaceAdapter(BaseLLMAdapter):
    """Adapter for HuggingFace Inference API."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        super().__init__(api_key=key)
        self.endpoint = "https://api-inference.huggingface.co/models"

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.client is None:
            yield "Error: httpx not installed"
            return
        url = f"{self.endpoint}/{request.model}"
        headers = {"Authorization": f"Bearer {self.api_key or request.api_key}"}
        payload = {
            "inputs": request.prompt,
            "parameters": {
                "temperature": request.temperature,
                "max_new_tokens": request.max_tokens,
            },
        }
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    yield data[0].get("generated_text", "")
                else:
                    yield str(data)
            else:
                yield f"Error: {resp.status_code} - {resp.text}"
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        return bool(self.api_key)


# ─── Google Gemini Adapter ───────────────────────────────

class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        super().__init__(api_key=key)
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta"

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        if self.client is None:
            yield "Error: httpx not installed"
            return
        model = request.model or "gemini-pro"
        url = f"{self.endpoint}/models/{model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key or request.api_key}
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        try:
            resp = await self.client.post(url, json=payload, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield text
            else:
                yield f"Error: {resp.status_code} - {resp.text}"
        except Exception as exc:
            yield f"Error: {exc}"

    async def validate(self) -> bool:
        return bool(self.api_key)


# ─── Factory ────────────────────────────────────────────

class LLMFactory:
    """Factory for creating LLM adapters."""

    _registry: Dict[str, type] = {
        "local_llama": LocalLlamaAdapter,
        "ollama": OllamaAdapter,
        "openai": OpenAIAdapter,
        "claude": AnthropicAdapter,
        "huggingface": HuggingFaceAdapter,
        "gemini": GeminiAdapter,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseLLMAdapter:
        """Create an adapter for *provider*."""
        key = provider.lower().replace(" ", "_").replace("-", "_")
        # Resolve common aliases
        aliases = {
            "local": "local_llama",
            "local_(llama_cpp)": "local_llama",
            "anthropic": "claude",
            "anthropic_(claude)": "claude",
            "google_(gemini)": "gemini",
            "google": "gemini",
        }
        key = aliases.get(key, key)

        adapter_cls = cls._registry.get(key)
        if adapter_cls is None:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._registry.keys())}"
            )

        if key in ("openai", "claude", "huggingface", "gemini"):
            return adapter_cls(api_key=api_key)
        return adapter_cls(**kwargs)
