# -*- coding: utf-8 -*-
"""
async_backend.py - True async HTTP backend for ZenAI
"""
import httpx
import json
import logging
from typing import AsyncGenerator, Optional
import time
import asyncio
from config_system import config, EMOJI
from zena_mode.profiler import monitor

logger = logging.getLogger(__name__)


class AsyncZenAIBackend:
    """Async HTTP backend using httpx for non-blocking streaming."""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.api_url = f"http://{config.host}:{config.llm_port}/v1/chat/completions"
        self.raw_api_url = f"http://{config.host}:{config.llm_port}"
        self.hub_api_url = f"http://{config.host}:{config.mgmt_port}"
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
            logger.warning(f"[ZenAIHub] API unavailable: {e}")
        return ["qwen2.5-coder-7b-instruct-q4_k_m.gguf", "llama-3.2-3b.gguf"]

    def get_models_sync(self) -> list:
        """Synchronous version of get_models for UI initialization."""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.hub_api_url}/models/available", timeout=1.0)
                if response.status_code == 200:
                    models = response.json()
                    if isinstance(models, list):
                        return models
        except Exception:
            pass
        return ["qwen2.5-coder-7b-instruct-q4_k_m.gguf", "llama-3.2-3b.gguf"]

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
            logger.error(f"[ZenAIHub] Download failed: {e}")
            return False

    async def set_active_model(self, model_name: str) -> bool:
        """Switch the active model."""
        try:
            # Use existing client or create temporary one with proper cleanup
            if self.client:
                response = await self.client.post(
                    f"{self.hub_api_url}/swap",
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
            logger.error(f"[ZenAIHub] Model switch failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Verify LLM API is online and responding."""
        try:
            if self.client:
                response = await self.client.get(f"{self.raw_api_url}/health", timeout=2.0)
                return response.status_code == 200
            else:
                async with httpx.AsyncClient() as temp_client:
                    response = await temp_client.get(f"{self.raw_api_url}/health", timeout=2.0)
                    return response.status_code == 200
        except Exception:
            return False

    async def scale_swarm(self, count: int) -> bool:
        """Dynamically scale the expert swarm via Hub API."""
        try:
            logger.info(f"[AsyncHub] Scaling swarm to {count} experts...")
            if self.client:
                response = await self.client.post(
                    f"{self.hub_api_url}/swarm/scale",
                    json={"count": count},
                    timeout=10.0
                )
                return response.status_code == 200
            else:
                async with httpx.AsyncClient() as temp_client:
                    response = await temp_client.post(
                        f"{self.hub_api_url}/swarm/scale",
                        json={"count": count},
                        timeout=10.0
                    )
                    return response.status_code == 200
        except Exception as e:
            logger.error(f"[AsyncHub] Swarm scaling failed: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry - creates HTTP client with connection pooling."""
        # Connection pooling for better performance under load
        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0
        )
        # Increased timeout for large prompts/long responses (5 minutes)
        self.client = httpx.AsyncClient(timeout=300.0, limits=limits)
        logger.debug("[AsyncBackend] HTTP client created with connection pooling")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.debug("[AsyncBackend] HTTP client closed")
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize input to prevent server crashes/400s."""
        if not text: return ""
        # Remove null bytes which cause C++ server hangs
        text = text.replace("\x00", "")
        # Remove non-characters (e.g. \uffff)
        text = text.replace("\uffff", "").replace("\ufffe", "")
        # Ensure valid UTF-8, ignore errors if necessary (though strings are unicode in Py3)
        return text

    async def send_message_async(
        self, 
        text: str, 
        system_prompt: str = """You are ZenAI, a helpful AI assistant powered by Qwen2.5-Coder.
You are NOT ChatGPT, NOT GPT-4, and NOT made by OpenAI.
You were created by Alibaba Cloud (Qwen team) and integrated into the ZenAI application.
Be helpful, concise, and accurate. If asked about your identity, say you are ZenAI powered by Qwen.""",
        attachment_content: Optional[str] = None,
        cancellation_event: Optional[asyncio.Event] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send message to LLM with stable requests-based streaming.
        """
        import requests
        
        # Sanitize inputs
        text = self._sanitize_input(text)
        system_prompt = self._sanitize_input(system_prompt)
        if attachment_content:
            attachment_content = self._sanitize_input(attachment_content)
        
        user_message = text
        if attachment_content:
            user_message = f"{text}\n\n```\n{attachment_content}\n```"
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        try:
            logger.info(f"[AsyncBackend] Sending stable requests POST to: {self.api_url}")
            
            # Run the synchronous requests call in a thread
            def perform_request():
                session = requests.Session()
                return session.post(self.api_url, json=payload, stream=True, timeout=30.0)

            response = await asyncio.to_thread(perform_request)

            if response.status_code != 200:
                error_text = response.text
                error_msg = f"{EMOJI['error']} Server returned {response.status_code}: {error_text}"
                logger.error(f"[AsyncBackend] Stable Request Failed! Status: {response.status_code}")
                yield error_msg
                return

            chunk_count = 0
            first_token_time = None
            start_request_time = time.time()

            # Iterate over the stream in the thread to avoid blocking the event loop
            # But we can iterate over lines directly if we are careful
            for line in response.iter_lines():
                if cancellation_event and cancellation_event.is_set():
                    logger.info("[AsyncBackend] Request cancelled by user")
                    break
                
                if line:
                    line_str = line.decode('utf-8', errors='replace')
                    if line_str.startswith('data: '):
                        json_str = line_str[6:]
                        if json_str.strip() == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(json_str)
                            delta = data['choices'][0]['delta']
                            content = delta.get('content', '')
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    ttft_ms = (first_token_time - start_request_time) * 1000
                                    monitor.add_metric('llm_ttft', ttft_ms)
                                    
                                chunk_count += 1
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            
            total_generation_time = time.time() - (first_token_time or start_request_time)
            logger.info(f"[AsyncBackend] Stable Stream complete: {chunk_count} chunks in {total_generation_time:.1f}s")

        except Exception as e:
            logger.error(f"[AsyncBackend] Stable Stream error: {type(e).__name__}: {e}")
            yield f"{EMOJI['error']} Error: {str(e)}"
        
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
backend = AsyncZenAIBackend()
# Backwards-compatibility alias expected by tests
AsyncBackend = AsyncZenAIBackend
