"""
Local LLM Wrapper Adapter

Integrates Local_LLM's model discovery (LocalLLMManager) with
FIFOLlamaCppAdapter for in-memory inference.

Flow:
  1. LocalLLMManager discovers GGUF models in C:\\AI\\Models
  2. User selects model (or first balanced/chat model is auto-selected)
  3. FIFOLlamaCppAdapter loads model in-process via llama-cpp-python
  4. Queries go through FIFO buffers (no ports, no HTTP)
"""

from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

# Import Local_LLM manager for model discovery
try:
    try:
        from Local_LLM.Core.services.local_llm_manager import LocalLLMManager
    except Exception:
        from local_llm.local_llm_manager import LocalLLMManager
except Exception:
    LocalLLMManager = None

# Import FIFO adapter (always defined before this module loads)
try:
    from local_adapters import FIFOLlamaCppAdapter, DirectLlamaCppAdapter
except Exception:
    FIFOLlamaCppAdapter = None
    DirectLlamaCppAdapter = None

try:
    from llm_adapters import BaseLLMAdapter, LLMRequest
except Exception:
    BaseLLMAdapter = object
    LLMRequest = None


class LocalLLMWrapperAdapter(BaseLLMAdapter):
    """
    Wrapper adapter combining Local_LLM discovery + FIFO in-memory inference.

    - Uses LocalLLMManager to find available GGUF models
    - Creates FIFOLlamaCppAdapter with selected model path
    - All inference is in-memory (no ports, no HTTP)
    - FIFO buffers provide backpressure and metrics
    """

    def __init__(self, model_name: Optional[str] = None, **kwargs):
        try:
            super().__init__()
        except Exception as exc:
            logger.debug("%s", exc)

        self.manager = None
        self.adapter = None
        self.model_name = model_name
        self._available_models = []

        # Step 1: Use Local_LLM to discover models
        if LocalLLMManager is not None:
            try:
                self.manager = LocalLLMManager()
                status = self.manager.initialize()
                if status and status.models_discovered:
                    self._available_models = self.manager.get_all_cards()
                    logger.info(f"[LocalLLMWrapper] Discovered {len(self._available_models)} models")
                else:
                    logger.warning("[LocalLLMWrapper] No models discovered")
            except Exception as e:
                logger.error(f"[LocalLLMWrapper] Manager init failed: {e}")
        else:
            logger.info("[LocalLLMWrapper] Local_LLM package not available, using direct discovery")

        # Step 2: Select model
        selected_path = self._select_model(model_name)

        # Step 3: Create FIFO adapter with selected model
        if FIFOLlamaCppAdapter is not None:
            try:
                self.adapter = FIFOLlamaCppAdapter(model_path=selected_path)
                if self.adapter._initialized:
                    model_file = selected_path.split("\\")[-1] if selected_path else "auto"
                    logger.info(f"[LocalLLMWrapper] FIFO adapter ready: {model_file} (in-memory, no port)")
                else:
                    logger.warning(
                        f"[LocalLLMWrapper] FIFO adapter created but not initialized: {self.adapter._init_error}"
                    )
            except Exception as e:
                logger.error(f"[LocalLLMWrapper] FIFO adapter creation failed: {e}")
        else:
            logger.warning("[LocalLLMWrapper] FIFOLlamaCppAdapter not available")

    def _select_model(self, model_name: Optional[str] = None) -> Optional[str]:
        """Select a model from discovered models."""
        if not self._available_models:
            return None

        # If user requested specific model
        if model_name:
            for card in self._available_models:
                name = card.get("name", "")
                filename = card.get("filename", "")
                if model_name in name or model_name in filename:
                    path = card.get("path")
                    if path:
                        logger.info(f"[LocalLLMWrapper] Selected requested model: {name}")
                        return path

        # Auto-select: prefer balanced category, then first available
        for card in self._available_models:
            cat = card.get("category", "")
            if cat in ("balanced", "fast"):
                path = card.get("path")
                if path:
                    logger.info(f"[LocalLLMWrapper] Auto-selected: {card.get('name', path)}")
                    return path

        # Fallback: first model
        path = self._available_models[0].get("path")
        if path:
            logger.info(f"[LocalLLMWrapper] Using first available model: {path}")
        return path

    def switch_model(self, new_model_path: str) -> bool:
        """Switch to a different model."""
        if self.adapter and hasattr(self.adapter, "switch_model"):
            return self.adapter.switch_model(new_model_path)
        return False

    async def validate(self) -> bool:
        """Check if adapter is ready for queries."""
        if self.adapter:
            try:
                return await self.adapter.validate()
            except Exception:
                return False
        return False

    async def query(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Query via FIFO in-memory inference (no ports)."""
        if not self.adapter:
            yield "\u274c Local LLM wrapper: FIFO adapter not available"
            if not FIFOLlamaCppAdapter:
                yield "\n\u2192 FIFOLlamaCppAdapter could not be imported"
            yield "\n\u2192 Install: pip install llama-cpp-python"
            return

        try:
            async for chunk in self.adapter.query(request):
                yield chunk
        except Exception as e:
            logger.error(f"[LocalLLMWrapper] Query failed: {e}")
            yield f"\u274c Error: {e}"

    async def query_stream_tokens(self, request) -> AsyncGenerator[str, None]:
        """TRUE token-level streaming — passthrough to FIFO adapter.

        Each yield = one real token from the model, instantly.
        Used by api_server v2 for true SSE streaming.
        """
        if not self.adapter:
            yield "\u274c Local LLM wrapper: FIFO adapter not available"
            return

        if hasattr(self.adapter, "query_stream_tokens"):
            try:
                async for token in self.adapter.query_stream_tokens(request):
                    yield token
            except Exception as e:
                logger.error(f"[LocalLLMWrapper] Token stream failed: {e}")
                yield f"\u274c Error: {e}"
        else:
            # Fallback to batch query
            async for chunk in self.adapter.query(request):
                yield chunk

    async def close(self):
        """Cleanup."""
        if self.adapter:
            try:
                await self.adapter.close()
            except Exception as exc:
                logger.debug("%s", exc)

    def get_available_models(self):
        """Return list of discovered model cards."""
        return self._available_models

    def get_stats(self):
        """Get FIFO buffer statistics from adapter."""
        if self.adapter and hasattr(self.adapter, "get_stats"):
            return self.adapter.get_stats()
        return {}
