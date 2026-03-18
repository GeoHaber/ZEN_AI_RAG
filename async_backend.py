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

logger = logging.getLogger("AsyncBackend")


class AsyncZenAIBackend:
    """Async HTTP client for the local LLM engine and management hub."""

    def __init__(self):
        self.api_url: str = f"{config.LLM_API_URL}/v1/chat/completions"
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

        client = self.client or httpx.AsyncClient(timeout=60.0)
        own_client = self.client is None
        try:
            async with client.stream("POST", self.api_url, json=payload) as resp:
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
        """Check if the LLM engine is reachable."""
        async with httpx.AsyncClient(timeout=5.0) as c:
            try:
                resp = await c.get(f"{config.LLM_API_URL}/health")
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
