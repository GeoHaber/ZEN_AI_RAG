"""
LLM Adapters - Unified interface for multiple LLM providers.

Supports:
  - Local: llama.cpp, Ollama
  - Cloud: OpenAI, Anthropic Claude, HuggingFace, Google Gemini, Cohere
  - Custom: Any OpenAI-compatible API

Author: RAG_RAT Team
Version: 1.0.0-beta
"""

import os
import json
import httpx
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""

    LOCAL_LLAMA = "local_llama"
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"
    COHERE = "cohere"
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
    endpoint: Optional[str] = None  # For custom endpoints


@dataclass
class LLMResponse:
    """Unified LLM response format."""

    text: str
    provider: Any = None  # LLMProvider enum or str
    model: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None
    success: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class BaseLLMAdapter:
    """Base class for LLM adapters.  Supports ``async with`` for safe cleanup."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv(f"{self.__class__.__name__}_API_KEY")
        self.client = httpx.AsyncClient(timeout=120)

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query the LLM and yield response tokens."""
        raise NotImplementedError

    async def validate(self) -> bool:
        """Validate the adapter is working."""
        raise NotImplementedError

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def calculate_cost(self, tokens_used: int, is_input: bool = False) -> float:
        """Calculate cost for API-based providers."""
        return 0.0  # Override in subclasses


class LocalLlamaAdapter(BaseLLMAdapter):
    """Adapter for local in-memory llama.cpp inference (NO PORT 8001)."""

    def __init__(self, endpoint: str = None):
        """Initialize with in-memory FIFO llama-cpp-python adapter"""
        super().__init__()
        self.adapter = None

        # Use FIFO-based in-memory adapter (no ports, no HTTP)
        try:
            from local_adapters import FIFOLlamaCppAdapter

            self.adapter = FIFOLlamaCppAdapter()
            logger.info("[LLM] FIFO in-memory llama.cpp initialized (no port)")
        except (ImportError, Exception) as e:
            logger.warning(f"[LLM] FIFO llama.cpp not available: {e}")
            self.adapter = None

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query in-memory llama.cpp (no HTTP port)."""
        if not self.adapter:
            yield "❌ Error: In-memory llama.cpp not available. Install: pip install llama-cpp-python"
            return

        # Use in-memory inference
        try:
            async for chunk in self.adapter.query(request):
                yield chunk
        except Exception as e:
            logger.error(f"[LLM] In-memory query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Check if in-memory llama.cpp is ready."""
        if not self.adapter:
            logger.warning("[LLM] In-memory llama.cpp not available. Install: pip install llama-cpp-python")
            return False

        try:
            ready = await self.adapter.validate()
            if ready:
                logger.info("[LLM] ✓ In-memory llama.cpp is ready")
            else:
                logger.warning("[LLM] In-memory llama.cpp validation failed")
            return ready
        except Exception as e:
            logger.error(f"[LLM] Validation failed: {e}")
            return False


class OllamaAdapter(BaseLLMAdapter):
    """Adapter for Ollama local LLM server."""

    def __init__(self, endpoint: str = "http://localhost:11434"):
        super().__init__()
        self.endpoint = endpoint

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query Ollama with streaming."""
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
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    logger.error(f"Ollama error: {error}")
                    yield f"❌ Error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("response"):
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self.client.get(f"{self.endpoint}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama validation failed: {e}")
            return False


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API."""

    ENDPOINT = "https://api.openai.com/v1"
    PRICING = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.api_key:
            raise ValueError("OpenAI API key required (OPENAI_API_KEY)")

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query OpenAI with streaming."""
        url = f"{self.ENDPOINT}/chat/completions"

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    logger.error(f"OpenAI error: {error}")
                    yield f"❌ OpenAI Error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get("choices"):
                                chunk = data["choices"][0].get("delta", {}).get("content", "")
                                if chunk:
                                    yield chunk
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"OpenAI query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Validate OpenAI API key."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            response = await self.client.get(
                f"{self.ENDPOINT}/models",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI validation failed: {e}")
            return False

    def calculate_cost(self, tokens_used: int, model: str = "gpt-3.5-turbo", is_input: bool = False) -> float:
        """Calculate OpenAI API cost."""
        base = "input" if is_input else "output"
        price_per_1k = self.PRICING.get(model, {}).get(base, 0)
        return (tokens_used / 1000) * price_per_1k


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude API."""

    ENDPOINT = "https://api.anthropic.com/v1"
    PRICING = {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.api_key:
            raise ValueError("Anthropic API key required (CLAUDE_API_KEY)")

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query Claude with streaming."""
        url = f"{self.ENDPOINT}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": request.system_prompt or "",
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    logger.error(f"Claude error: {error}")
                    yield f"❌ Claude Error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Claude query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Validate Anthropic API key."""
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            response = await self.client.get(
                f"{self.ENDPOINT}/models",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Anthropic validation failed: {e}")
            return False

    def calculate_cost(self, tokens_used: int, model: str = "claude-3-haiku", is_input: bool = False) -> float:
        """Calculate Claude API cost."""
        base = "input" if is_input else "output"
        price_per_1k = self.PRICING.get(model, {}).get(base, 0)
        return (tokens_used / 1000) * price_per_1k


class HuggingFaceAdapter(BaseLLMAdapter):
    """Adapter for HuggingFace Inference API."""

    ENDPOINT = "https://api-inference.huggingface.co"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.api_key:
            raise ValueError("HuggingFace API key required (HUGGINGFACE_API_KEY)")

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query HuggingFace with streaming."""
        url = f"{self.ENDPOINT}/models/{request.model}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "inputs": request.prompt,
            "parameters": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_new_tokens": request.max_tokens,
            },
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    logger.error(f"HuggingFace error: {error}")
                    yield f"❌ HuggingFace Error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if isinstance(data, list):
                                for item in data:
                                    if item.get("token", {}).get("text"):
                                        yield item["token"]["text"]
                            elif data.get("token", {}).get("text"):
                                yield data["token"]["text"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"HuggingFace query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Validate HuggingFace API key."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            response = await self.client.get(
                f"{self.ENDPOINT}/models",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"HuggingFace validation failed: {e}")
            return False


class GeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini API."""

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.api_key:
            raise ValueError("Google Gemini API key required (GEMINI_API_KEY)")

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query Gemini with streaming."""
        url = f"{self.ENDPOINT}/models/{request.model}:streamGenerateContent"

        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "topP": request.top_p,
                "maxOutputTokens": request.max_tokens,
            },
        }

        params = {"key": self.api_key}

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                params=params,
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    logger.error(f"Gemini error: {error}")
                    yield f"❌ Gemini Error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("candidates"):
                                for candidate in data["candidates"]:
                                    if candidate.get("content", {}).get("parts"):
                                        for part in candidate["content"]["parts"]:
                                            if part.get("text"):
                                                yield part["text"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Gemini query error: {e}")
            yield f"❌ Error: {str(e)}"

    async def validate(self) -> bool:
        """Validate Gemini API key."""
        try:
            params = {"key": self.api_key}
            response = await self.client.get(
                f"{self.ENDPOINT}/models",
                params=params,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}")
            return False


# ---------------------------------------------------------------------------
# Backwards-compatible factory accessor expected by some tests/modules
# ---------------------------------------------------------------------------
try:
    # Prefer the central adapter factory if available
    from adapter_factory import create_adapter as create_adapter
except Exception:

    def create_adapter(
        provider,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        """Compatibility shim: create adapter from provider enum."""
        _ADAPTER_MAP = {
            LLMProvider.LOCAL_LLAMA: LocalLlamaAdapter,
            LLMProvider.OLLAMA: OllamaAdapter,
            LLMProvider.OPENAI: OpenAIAdapter,
            LLMProvider.CLAUDE: AnthropicAdapter,
            LLMProvider.HUGGINGFACE: HuggingFaceAdapter,
            LLMProvider.GEMINI: GeminiAdapter,
        }
        if isinstance(provider, LLMProvider) and provider in _ADAPTER_MAP:
            cls = _ADAPTER_MAP[provider]
            if provider in (LLMProvider.LOCAL_LLAMA, LLMProvider.OLLAMA):
                return cls(endpoint)
            return cls(api_key)
        raise ValueError(f"Unknown provider: {provider}")
