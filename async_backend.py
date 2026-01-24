# -*- coding: utf-8 -*-
"""
async_backend.py - True async HTTP backend for Zena
"""
import httpx
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional
from config_system import config, EMOJI

logger = logging.getLogger(__name__)


class AsyncNebulaBackend:
    """Async HTTP backend using httpx for non-blocking streaming."""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.api_url = f"{config.LLM_API_URL}/v1/chat/completions"
        self.raw_api_url = config.LLM_API_URL
        self.hub_api_url = "http://127.0.0.1:8002"
        logger.info(f"[AsyncBackend] Initialized with API: {self.api_url}")
    
    async def get_models(self) -> list:
        """Fetch available models from Hub API (port 8002)."""
        if not self.client:
             # Just for safety if called outside context, though intended for use within
             async with httpx.AsyncClient() as temp_client:
                 return await self._fetch_models(temp_client)
        return await self._fetch_models(self.client)

    async def _fetch_models(self, client) -> list:
        try:
            response = await client.get(f"{self.hub_api_url}/models/available", timeout=2.0)
            if response.status_code == 200:
                models = response.json()
                if isinstance(models, list):
                    return models
        except Exception as e:
            logger.warning(f"[AsyncHub] API unavailable: {e}")
        return ["qwen2.5-coder.gguf", "llama-3.2-3b.gguf"]

    async def download_model(self, repo_id: str, filename: str) -> bool:
        """Trigger background model download."""
        try:
            # Use existing client or create temporary one with proper cleanup
            if self.client:
                response = await self.client.post(
                    f"{self.hub_api_url}/models/download",
                    json={"repo_id": repo_id, "filename": filename},
                    timeout=5.0
                )
                return response.status_code == 200
            else:
                async with httpx.AsyncClient() as temp_client:
                    response = await temp_client.post(
                        f"{self.hub_api_url}/models/download",
                        json={"repo_id": repo_id, "filename": filename},
                        timeout=5.0
                    )
                    return response.status_code == 200
        except Exception as e:
            logger.error(f"[AsyncHub] Download failed: {e}")
            return False

    async def set_active_model(self, model_name: str) -> bool:
        """Switch the active model."""
        try:
            # Use existing client or create temporary one with proper cleanup
            if self.client:
                response = await self.client.post(
                    f"{self.hub_api_url}/models/load",
                    json={"model": model_name},
                    timeout=30.0
                )
                return response.status_code == 200
            else:
                async with httpx.AsyncClient() as temp_client:
                    response = await temp_client.post(
                        f"{self.hub_api_url}/models/load",
                        json={"model": model_name},
                        timeout=30.0
                    )
                    return response.status_code == 200
        except Exception as e:
            logger.error(f"[AsyncHub] Model switch failed: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry - creates HTTP client."""
        # Increased timeout for large prompts/long responses (5 minutes)
        self.client = httpx.AsyncClient(timeout=300.0)
        logger.debug("[AsyncBackend] HTTP client created")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.debug("[AsyncBackend] HTTP client closed")
    
    async def send_message_async(
        self,
        text: str,
        system_prompt: str = """You are Zena, a helpful AI assistant powered by Qwen2.5-Coder.
You are NOT ChatGPT, NOT GPT-4, and NOT made by OpenAI.
You were created by Alibaba Cloud (Qwen team) and integrated into the ZenAI application.

Your Role: You serve as the coordinator and primary interface for the ZenAI multi-LLM system.

Capabilities:
- Fast local processing for simple queries (your primary role)
- Access to external LLM APIs when enabled in settings (Claude, Gemini, Grok)
- Multi-LLM consensus for complex questions requiring expert validation
- Cost-aware routing (you decide when to escalate to external LLMs)

When External LLMs Are Available:
If the user has enabled external LLM integration and provided API keys, you CAN access:
- Anthropic Claude (claude-3-5-sonnet, claude-3-opus, claude-3-haiku)
- Google Gemini (gemini-pro, gemini-pro-vision)
- xAI Grok (grok-beta)

Your Decision Process:
- Simple questions (greetings, basic facts): Answer directly (fast local response)
- Complex questions (code generation, nuanced advice): Consider external LLM consultation
- When consensus is enabled: Query multiple LLMs and calculate agreement scores

Be helpful, concise, and accurate. If asked about your capabilities, explain that you're a local LLM that coordinates with external LLMs when needed. If asked about your identity, say you are Zena powered by Qwen with multi-LLM orchestration capabilities.""",
        attachment_content: Optional[str] = None,
        cancellation_event: Optional[asyncio.Event] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send message to LLM with true async streaming.

        Args:
            text: User message
            system_prompt: System prompt for LLM
            attachment_content: Optional file attachment content
            cancellation_event: Optional asyncio.Event to cancel streaming

        Yields:
            Response chunks as they arrive (non-blocking)
        """
        # Build message with optional attachment
        user_message = text
        if attachment_content:
            user_message = f"{text}\n\n```\n{attachment_content}\n```"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": True,
            "temperature": 0.7,
            "max_tokens": -1
        }
        
        try:
            if not self.client:
                yield f"{EMOJI['error']} Backend not initialized. Use 'async with backend:'"
                return
            
            logger.info(f"[AsyncBackend] Sending message: {text[:50]}...")
            
            async with self.client.stream('POST', self.api_url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"{EMOJI['error']} Server returned {response.status_code}: {error_text.decode()}"
                    logger.error(f"[AsyncBackend] {error_msg}")
                    yield error_msg
                    return
                
                chunk_count = 0
                async for line in response.aiter_lines():
                    # Check if cancelled
                    if cancellation_event and cancellation_event.is_set():
                        logger.info(f"[AsyncBackend] Stream cancelled by client after {chunk_count} chunks")
                        break

                    if line.startswith('data: '):
                        json_str = line[6:]
                        if json_str.strip() == '[DONE]':
                            logger.info(f"[AsyncBackend] Stream complete: {chunk_count} chunks")
                            break

                        try:
                            data = json.loads(json_str)
                            delta = data['choices'][0]['delta']
                            content = delta.get('content', '')
                            if content:
                                chunk_count += 1
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            logger.debug(f"[AsyncBackend] Skipping malformed chunk: {e}")
                            pass
        
        except httpx.ConnectError:
            error_msg = f"{EMOJI['warning']} **Backend Offline**: Start backend to enable AI responses."
            logger.error("[AsyncBackend] Connection failed - is start_llm.py running?")
            yield error_msg
        
        except httpx.TimeoutException:
            error_msg = f"{EMOJI['error']} Request timed out. Please try again."
            logger.error("[AsyncBackend] Request timeout")
            yield error_msg
        
        except Exception as e:
            logger.error(f"[AsyncBackend] Stream error: {type(e).__name__}: {e}")
            yield f"{EMOJI['error']} Error: {str(e)}"


# Global backend instance
backend = AsyncNebulaBackend()
