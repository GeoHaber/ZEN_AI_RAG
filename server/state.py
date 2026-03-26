"""
Server State — ResponseCache, ServerState, SwapTracker.

Extracted from api_server.py.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("api_server")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Error token prefix — tokens starting with this are model errors
_ERROR_PREFIX = "\u274c"


# =========================================================================
# Response Cache (LRU)
# =========================================================================


class ResponseCache:
    """Thread-safe LRU response cache.

    Key:   SHA-256 of messages + temperature + max_tokens
    Value: (text, char_count, created_at)
    """

    def __init__(self, max_size: int = 200):
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, messages: List[dict], temperature: float, max_tokens: int) -> str:
        raw = json.dumps(messages, sort_keys=True) + f"|{temperature}|{max_tokens}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, messages: List[dict], temperature: float, max_tokens: int) -> Optional[str]:
        key = self._make_key(messages, temperature, max_tokens)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            text, _, _ = self._cache[key]
            return text
        self._misses += 1
        return None

    def put(self, messages: List[dict], temperature: float, max_tokens: int, text: str):
        """Cache response — skip error tokens (❌ prefix)."""
        if text.startswith(_ERROR_PREFIX):
            return
        key = self._make_key(messages, temperature, max_tokens)
        self._cache[key] = (text, len(text), time.time())
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total else "0%",
        }

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# =========================================================================
# Server State — focused: adapter + concurrency + cache
# =========================================================================


class ServerState:
    """Holds the adapter, concurrency semaphore, and response cache."""

    def __init__(
        self,
        provider: str = "Local (llama-cpp)",
        cache_size: int = 200,
        **adapter_kwargs,
    ):
        self.provider = provider
        self.adapter = None
        self.adapter_kwargs = adapter_kwargs
        self.model_id = "local-gguf"
        self.model_name = "Local GGUF Model"
        self.ready = False
        self.start_time = time.time()

        self.request_count = 0
        self.cache_served = 0
        self.total_tokens_approx = 0
        self.last_request_time = time.time()

        self.inference_semaphore = asyncio.Semaphore(1)
        self.cache = ResponseCache(max_size=cache_size)

        # LoRA tracking
        self.active_lora: Optional[str] = None
        self.lora_scale: float = 1.0

        # State save/load directory
        self._states_dir = _PROJECT_ROOT / "state_cache"
        self._states_dir.mkdir(exist_ok=True)

    def initialize(self):
        """Create the adapter (loads model into memory)."""
        from adapter_factory import create_adapter

        logger.info(f"Initializing adapter: {self.provider}")
        try:
            self.adapter = create_adapter(self.provider, **self.adapter_kwargs)
            inner = getattr(self.adapter, "adapter", self.adapter)
            model_path = getattr(inner, "model_path", None)

            if model_path:
                p = Path(model_path)
                self.model_id = p.stem
                self.model_name = p.stem.replace("-", " ").replace("_", " ").title()
                logger.info(f"Model loaded: {p.name}")
            else:
                logger.info("Adapter created (model path not exposed)")

            self.ready = True
            return True
        except Exception as e:
            logger.error(f"Adapter init failed: {e}")
            self.ready = False
            return False

    def record_request(self, tokens: int):
        """Record a served request."""
        self.request_count += 1
        self.total_tokens_approx += tokens
        self.last_request_time = time.time()

    def get_inner_adapter(self):
        """Get the innermost adapter (FIFOLlamaCppAdapter)."""
        return getattr(self.adapter, "adapter", self.adapter)

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models in OpenAI format."""
        models = [
            {
                "id": self.model_id,
                "object": "model",
                "created": int(self.start_time),
                "owned_by": "local",
                "permission": [],
                "root": self.model_id,
                "parent": None,
            }
        ]

        wrapper = self.adapter
        if hasattr(wrapper, "get_available_models"):
            for card in wrapper.get_available_models():
                mid = card.get("name", card.get("filename", "unknown"))
                if mid == self.model_id:
                    continue
                models.append(
                    {
                        "id": mid,
                        "object": "model",
                        "created": int(self.start_time),
                        "owned_by": "local",
                        "permission": [],
                        "root": mid,
                        "parent": None,
                    }
                )

        return models


# =========================================================================
# Swap Cost Tracker
# =========================================================================


class SwapTracker:
    """Track model hot-swap events with timing and cost metrics."""

    def __init__(self, max_events: int = 100):
        self._events: deque = deque(maxlen=max_events)
        self._total_swaps: int = 0
        self._total_downtime_ms: float = 0.0

    def record(
        self,
        from_model: str,
        to_model: str,
        swap_time_ms: float,
        trigger: str = "manual",
    ):
        self._events.append(
            {
                "from_model": from_model,
                "to_model": to_model,
                "swap_time_ms": round(swap_time_ms, 1),
                "trigger": trigger,
                "timestamp": time.time(),
                "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self._total_swaps += 1
        self._total_downtime_ms += swap_time_ms

    def history(self, last_n: int = 20) -> List[Dict[str, Any]]:
        events = list(self._events)
        events.reverse()
        return events[:last_n]

    def stats(self) -> Dict[str, Any]:
        if not self._events:
            return {
                "total_swaps": 0,
                "total_downtime_ms": 0.0,
                "avg_swap_ms": 0.0,
                "fastest_swap_ms": 0.0,
                "slowest_swap_ms": 0.0,
                "last_swap": None,
            }
        times = [e["swap_time_ms"] for e in self._events]
        last = self._events[-1]
        return {
            "total_swaps": self._total_swaps,
            "total_downtime_ms": round(self._total_downtime_ms, 1),
            "avg_swap_ms": round(self._total_downtime_ms / self._total_swaps, 1),
            "fastest_swap_ms": round(min(times), 1),
            "slowest_swap_ms": round(max(times), 1),
            "last_swap": {
                "from": last["from_model"],
                "to": last["to_model"],
                "ms": last["swap_time_ms"],
                "trigger": last["trigger"],
                "when": last["timestamp_iso"],
            },
        }

    def estimate_swap_cost_ms(self) -> float:
        if not self._events:
            return 0.0
        recent = list(self._events)[-10:]
        return round(sum(e["swap_time_ms"] for e in recent) / len(recent), 1)
