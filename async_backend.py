# -*- coding: utf-8 -*-
"""
async_backend.py - Async HTTP backend for ZenAI

Provides AsyncZenAIBackend for streaming chat completions and model management
via the local llama-server (OpenAI-compatible API) and the ZenAI Hub API.
"""

import logging
from typing import AsyncGenerator, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from config_system import config

try:
    import zen_shared_client as _shared
except Exception:  # pragma: no cover - module always present in-tree
    _shared = None  # type: ignore[assignment]

logger = logging.getLogger("AsyncBackend")


def _resolve_chat_url() -> str:
    """Endpoint for chat completions.

    Prefers the shared Zena :8800 service (SSOT) when available, so this app
    never needs its own resident gemma. Falls back to the local engine URL.
    """
    if _shared is not None:
        try:
            return _shared.chat_completions_url()
        except Exception:
            pass
    return f"{config.LLM_API_URL}/v1/chat/completions"


def _chat_headers() -> dict:
    """Auth header for the shared service (empty when talking to the local engine)."""
    if _shared is not None:
        try:
            if _shared.active_is_shared():
                return _shared.auth_header()
        except Exception:
            pass
    return {}


class AsyncZenAIBackend:
    """Async HTTP client for the local LLM engine and management hub."""

    def __init__(self):
        # Resolve lazily-at-construction so the env flags / service liveness at
        # the time the backend is built decide the endpoint. Re-resolved per
        # request below to survive the shared service coming up after boot.
        self.api_url: str = _resolve_chat_url()
        self.hub_url: str = config.HUB_API_URL
        self.client: Optional["httpx.AsyncClient"] = None
        logger.info(f"[AsyncBackend] Initialized with API: {self.api_url}")

    # --- Context manager for connection pooling ---

    async def __aenter__(self):
        if httpx is None:
            raise ImportError("httpx is required for AsyncZenAIBackend (pip install httpx)")
        self.client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, *exc):
        if self.client:
            await self.client.aclose()
            self.client = None

    # --- Chat streaming ---

    async def send_message_async(
        self,
        message: str,
        system_prompt: str = "You are ZenAI, a helpful assistant.",
        context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions from the LLM engine."""
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": message})

        payload = {
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Re-resolve per request: the shared :8800 service may have come up
        # (or the flag changed) after this backend was constructed.
        url = _resolve_chat_url()
        headers = _chat_headers()

        client = self.client or httpx.AsyncClient(timeout=60.0)
        own_client = self.client is None
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        finally:
            if own_client:
                await client.aclose()

    # --- Health ---

    async def check_health(self) -> dict:
        """Check if the active generation backend is reachable.

        Targets the shared :8800 service when it is the active backend,
        otherwise the local engine.
        """
        base = config.LLM_API_URL
        if _shared is not None:
            try:
                if _shared.active_is_shared():
                    base = _shared.shared_base_url()
            except Exception:
                pass
        async with httpx.AsyncClient(timeout=5.0) as c:
            try:
                resp = await c.get(f"{base}/health")
                return {"status": "ok", "code": resp.status_code}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    # --- Model management ---

    async def get_models(self) -> List[str]:
        """Fetch available models from the hub."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                resp = await c.get(f"{self.hub_url}/models/available", timeout=2.0)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        # Fallback list
        return [config.default_model]

    async def download_model(self, repo_id: str, filename: str) -> bool:
        """Request the hub to download a model."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.post(
                    f"{self.hub_url}/models/download",
                    json={"repo_id": repo_id, "filename": filename},
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def set_active_model(self, model_name: str) -> bool:
        """Tell the hub to switch the active model."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.post(
                    f"{self.hub_url}/models/set",
                    json={"model": model_name},
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception:
            return False


# Module-level singleton used by gateway_telegram / gateway_whatsapp
backend = AsyncZenAIBackend()
