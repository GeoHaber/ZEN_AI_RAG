"""
Local Adapters — In-memory LLM inference via FIFO buffers + llama-cpp-python.

Architecture:
  AdaptiveFIFOBuffer      — Semaphore-synced adaptive buffer with backpressure
  FIFOLlamaCppAdapter     — Core adapter: model loading, singleton, streaming inference
  MockLLMAdapter          — Deterministic mock for testing
  RealisticMockLLMAdapter — Streaming mock with delays

Data flow:
  RAG_RAT query -> FIFOLlamaCppAdapter.query_stream_tokens()
    -> asyncio.Queue bridge (thread -> async)
      -> llama_cpp.Llama.create_chat_completion(stream=True)
        -> each token instant-pushed to Queue -> yield to caller

No HTTP, no ports, no network. Pure in-memory FIFO buffers.

Diagnostics:
  Crash diagnostics are handled EXTERNALLY by InferenceGuard (inference_guard.py).
  This module does NOT import psutil or do its own memory monitoring.
"""

import asyncio
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLMRequest import
# ---------------------------------------------------------------------------
try:
    from llm_adapters import LLMRequest, LLMProvider
except Exception:
    try:
        from .llm_adapters import LLMRequest, LLMProvider
    except Exception:
        LLMRequest = None
        LLMProvider = None

# ---------------------------------------------------------------------------
# llama-cpp-python availability
# ---------------------------------------------------------------------------
LLAMA_CPP_INSTALL_HINT = ""
try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
    logger.info("[local_adapters] llama-cpp-python available")
    # Patch LlamaModel.close so __del__ does not raise when sampler is missing (known bug on teardown)
    try:
        import llama_cpp._internals as _internals

        if hasattr(_internals, "LlamaModel"):
            _orig_close = getattr(_internals.LlamaModel, "close", None)
            if callable(_orig_close):

                def _safe_close(self):
                    try:
                        if getattr(self, "sampler", None) is not None:
                            _orig_close(self)
                    except Exception as exc:
                        logger.debug("%s", exc)

                _internals.LlamaModel.close = _safe_close
    except Exception as exc:
        logger.debug("%s", exc)
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None
    # Build a helpful diagnostic message
    _hints = []
    _hints.append("[local_adapters] llama-cpp-python NOT available.")
    _hints.append("  To install, run:  python scripts/install_llama_cpp.py")
    _hints.append("  Alternative:      Use Ollama (https://ollama.com) as LLM provider")
    LLAMA_CPP_INSTALL_HINT = "\n".join(_hints)
    logger.warning(LLAMA_CPP_INSTALL_HINT)
except Exception as e:
    LLAMA_CPP_AVAILABLE = False
    Llama = None
    logger.warning(f"[local_adapters] llama-cpp-python import error: {e}")
    logger.warning("  To fix, run:  python scripts/install_llama_cpp.py")
    LLAMA_CPP_INSTALL_HINT = f"llama-cpp-python import error: {e}"


def _get_n_gpu_layers() -> int:
    """Number of layers to offload to GPU. -1 = all, 0 = CPU-only. Read from env or config."""
    try:
        val = os.environ.get("GPU_LAYERS") or os.environ.get("LLM_GPU_LAYERS")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    try:
        from Core.config import GPU_LAYERS

        return int(GPU_LAYERS)
    except Exception as exc:
        logger.debug("%s", exc)
    return -1


# =========================================================================
# ADAPTIVE FIFO BUFFER
# =========================================================================


class MessagePriority(Enum):
    """Message priority levels for LLM requests."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class FIFOMessage:
    """Standardized message for FIFO buffer."""

    content: Any
    message_type: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.timestamp < other.timestamp


async def _wait_with_timeout(coro, timeout_sec: float):
    """Wait for coroutine with timeout. Uses asyncio.wait() to avoid 'Timeout should be
    used inside a task' when run under Streamlit/nest_asyncio or non-task contexts.
    """
    if timeout_sec is None or timeout_sec <= 0:
        return await coro
    task = asyncio.ensure_future(coro)
    try:
        done, pending = await asyncio.wait([task], timeout=timeout_sec, return_when=asyncio.FIRST_COMPLETED)
        if pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError as exc:
                logger.debug("%s", exc)
            raise asyncio.TimeoutError()
        return task.result()
    except asyncio.CancelledError:
        task.cancel()
        raise


class AdaptiveFIFOBuffer:
    """Adaptive FIFO buffer with semaphore-based producer/consumer sync.

    Features:
    - Adaptive sizing (grows under load, shrinks when idle)
    - Backpressure (blocks producers when full)
    - Priority queue support
    - Built-in metrics
    """

    def __init__(
        self,
        min_size: int = 5,
        initial_size: int = 50,
        max_size: int = 500,
        enable_backpressure: bool = True,
        buffer_name: str = "buffer",
    ):
        self.min_size = min_size
        self.initial_size = initial_size
        self.max_size = max_size
        self.current_max_size = initial_size
        self.enable_backpressure = enable_backpressure
        self.buffer_name = buffer_name

        self._queue: Deque[FIFOMessage] = deque(maxlen=None)
        self._priority_queue: List[FIFOMessage] = []

        self._empty_semaphore = asyncio.Semaphore(self.current_max_size)
        self._full_semaphore = asyncio.Semaphore(0)
        self._lock = asyncio.Lock()

        self._metrics = {
            "total_added": 0,
            "total_retrieved": 0,
            "times_grew": 0,
            "times_shrunk": 0,
            "peak_size": 0,
            "backpressure_events": 0,
        }

    async def add_message(
        self,
        content: Any,
        message_type: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        source: str = "",
        metadata: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Add message with automatic backpressure."""
        message = FIFOMessage(
            content=content,
            message_type=message_type,
            priority=priority,
            source=source,
            metadata=metadata or {},
        )

        try:
            if self.enable_backpressure:
                await _wait_with_timeout(
                    self._empty_semaphore.acquire(),
                    timeout or 30.0,
                )

            async with self._lock:
                self._check_and_adapt_size()
                if priority == MessagePriority.NORMAL:
                    self._queue.append(message)
                else:
                    self._priority_queue.append(message)
                    self._priority_queue.sort()
                self._metrics["total_added"] += 1
                self._metrics["peak_size"] = max(self._metrics["peak_size"], self.size())

            self._full_semaphore.release()
            return True

        except asyncio.TimeoutError:
            self._metrics["backpressure_events"] += 1
            logger.warning(f"[{self.buffer_name}] Backpressure timeout")
            return False

    async def get_message(self, timeout: Optional[float] = None) -> Optional[FIFOMessage]:
        """Get next message from buffer."""
        try:
            if self.enable_backpressure:
                await _wait_with_timeout(
                    self._full_semaphore.acquire(),
                    timeout or 5.0,
                )

            async with self._lock:
                message = None
                if self._priority_queue:
                    message = self._priority_queue.pop(0)
                elif self._queue:
                    message = self._queue.popleft()

                if message:
                    self._metrics["total_retrieved"] += 1
                    if self.enable_backpressure:
                        self._empty_semaphore.release()
                    self._check_and_adapt_size()
                return message

        except asyncio.TimeoutError:
            return None

    def _check_and_adapt_size(self):
        """Adapt buffer size based on demand."""
        current_size = self.size()
        if self.current_max_size == 0:
            return
        fill_percent = (current_size / self.current_max_size) * 100

        if fill_percent > 80 and self.current_max_size < self.max_size:
            new_size = min(int(self.current_max_size * 1.5), self.max_size)
            additional = new_size - self.current_max_size
            for _ in range(additional):
                self._empty_semaphore.release()
            self.current_max_size = new_size
            self._metrics["times_grew"] += 1
            logger.debug(f"[{self.buffer_name}] Grew to {new_size}")

        if fill_percent < 10 and self.current_max_size > self.initial_size:
            new_size = max(int(self.current_max_size * 0.8), self.initial_size)
            self.current_max_size = new_size
            self._metrics["times_shrunk"] += 1

    def size(self) -> int:
        return len(self._queue) + len(self._priority_queue)

    def stats(self) -> Dict[str, Any]:
        return {
            "current_size": self.size(),
            "max_size": self.current_max_size,
            "fill_percent": (self.size() / self.current_max_size * 100 if self.current_max_size > 0 else 0),
            **self._metrics,
        }


# =========================================================================
# STOP TOKENS — shared between all inference paths
# =========================================================================

_STOP_TOKENS = [
    "[/INST]",
    "</s>",
    "<|im_end|>",
    "<|eot_id|>",
    "User question:",
    "\nUser:",
    "\n[INST]",
]


# =========================================================================
# FIFO-BASED LLM ADAPTER
# =========================================================================


class FIFOLlamaCppAdapter:
    """In-memory LLM adapter using FIFO buffers + llama-cpp-python.

    - Model loaded once via llama_cpp.Llama (singleton, in-process)
    - TRUE token streaming via asyncio.Queue bridge (thread -> async)
    - FIFO buffers for request tracking / metrics
    - NO inline diagnostics — InferenceGuard handles that externally
    """

    # Singleton model instance
    _shared_llm = None
    _shared_model_path: Optional[str] = None
    _shared_lock = threading.Lock()

    def __init__(self, model_path: Optional[str] = None, **kwargs):
        self.model_path = model_path
        self._initialized = False
        self._init_error = None

        # FIFO buffers (per-instance for isolation)
        self.request_buffer = AdaptiveFIFOBuffer(
            min_size=2,
            initial_size=10,
            max_size=50,
            enable_backpressure=True,
            buffer_name="llm_requests",
        )
        self.response_buffer = AdaptiveFIFOBuffer(
            min_size=2,
            initial_size=20,
            max_size=100,
            enable_backpressure=False,
            buffer_name="llm_responses",
        )

        if LLAMA_CPP_AVAILABLE:
            try:
                self._setup_llm()
            except Exception as e:
                self._init_error = str(e)
                logger.error(f"[FIFOLlama] Init error: {e}")

    # -- Model discovery & loading ------------------------------------------

    def _find_gguf_model(self) -> Optional[Path]:
        """Discover GGUF models: Local_LLM registry -> manual search."""
        try:
            from Local_LLM.Core.services.local_llm_manager import LocalLLMManager

            manager = LocalLLMManager()
            status = manager.initialize()
            if status and status.models_discovered:
                cards = manager.get_all_cards()
                if cards:
                    # Prefer balanced/fast
                    for card in cards:
                        cat = card.get("category", "")
                        if cat in ("balanced", "fast"):
                            path = card.get("path")
                            if path and Path(path).exists():
                                logger.info(f"[FIFOLlama] Selected: {path}")
                                return Path(path)
                    # Fallback: first available
                    path = cards[0].get("path")
                    if path and Path(path).exists():
                        logger.info(f"[FIFOLlama] Using first model: {path}")
                        return Path(path)
        except Exception as e:
            logger.debug(f"[FIFOLlama] Local_LLM discovery failed: {e}")

        # Manual search: platform-aware defaults + always include ~/AI/Models
        home = Path.home()
        ai_models = (home / "AI" / "Models").resolve()

        # Include Config.MODELS_DIR (src/models/) so bundled models are found
        config_models_dir = None
        try:
            from config_enhanced import Config
            config_models_dir = Config.MODELS_DIR
        except Exception:
            pass

        if os.name == "nt":
            default_primary = os.environ.get("MODELS_DIR", "C:\\AI\\Models")
            candidates = [
                Path(default_primary),
                Path("C:\\AI\\Models"),
                ai_models,
                (home / "models").resolve(),
                Path("./models").resolve(),
            ]
        else:
            default_primary = os.environ.get("MODELS_DIR", str(ai_models))
            candidates = [
                Path(default_primary).expanduser().resolve(),
                ai_models,
                (home / "models").resolve(),
                (home / ".local" / "share" / "models").resolve(),
                Path("./models").resolve(),
            ]
        if config_models_dir and config_models_dir not in candidates:
            candidates.insert(0, config_models_dir)
        seen = set()
        all_ggufs: List[Path] = []
        for d in candidates:
            try:
                d = d.resolve()
            except (OSError, RuntimeError):
                continue
            if d in seen or not d.exists():
                continue
            seen.add(d)
            all_ggufs.extend(d.glob("*.gguf"))
            all_ggufs.extend(d.glob("*/*.gguf"))
        # Prefer smallest across all dirs (most likely to load without OOM when no model is set)
        if all_ggufs:
            best = min(all_ggufs, key=lambda p: p.stat().st_size)
            logger.info(f"[FIFOLlama] Found model: {best}")
            return best
        return None

    def _setup_llm(self):
        """Load model into memory (singleton — one model shared across adapters)."""
        if not LLAMA_CPP_AVAILABLE:
            self._init_error = "llama-cpp-python not installed"
            return

        model_path = self.model_path
        if not model_path:
            found = self._find_gguf_model()
            if found:
                model_path = str(found)

        if not model_path:
            self._init_error = "No GGUF model found"
            logger.error(f"[FIFOLlama] {self._init_error}")
            return

        p = Path(model_path)
        if not p.exists():
            self._init_error = f"Model file not found: {model_path}"
            logger.error(f"[FIFOLlama] {self._init_error}")
            return

        with FIFOLlamaCppAdapter._shared_lock:
            if FIFOLlamaCppAdapter._shared_llm is not None and FIFOLlamaCppAdapter._shared_model_path == str(p):
                logger.info(f"[FIFOLlama] Reusing loaded model: {p.name}")
                self._initialized = True
                self.model_path = str(p)
                return

            n_gpu = _get_n_gpu_layers()
            # Try CPU-first (0) then GPU if requested — avoids Metal/GPU load failures on many setups
            to_try = [0, n_gpu] if n_gpu != 0 else [0]
            last_error = None
            for attempt, gpu_layers in enumerate(to_try):
                if attempt > 0:
                    logger.info("[FIFOLlama] Retrying with n_gpu_layers=%s", gpu_layers)
                else:
                    logger.info(
                        f"[FIFOLlama] Loading: {p.name} "
                        f"({p.stat().st_size / (1024**3):.1f} GB), n_gpu_layers={gpu_layers}"
                    )
                try:
                    llm = Llama(
                        model_path=str(p),
                        n_gpu_layers=gpu_layers,
                        n_ctx=4096,
                        n_threads=None,
                        verbose=False,
                    )
                    FIFOLlamaCppAdapter._shared_llm = llm
                    FIFOLlamaCppAdapter._shared_model_path = str(p)
                    self.model_path = str(p)
                    self._initialized = True
                    logger.info("[FIFOLlama] Model loaded (in-memory, no port)")
                    break
                except Exception as e:
                    last_error = e
                    err = str(e).strip()
                    if attempt < len(to_try) - 1:
                        logger.warning(
                            "[FIFOLlama] Load failed (n_gpu_layers=%s), trying next: %s",
                            gpu_layers,
                            err,
                        )
                        continue
                    self._init_error = f"Failed to load model: {e}"
                    if "load model from file" in err.lower() or "failed to load" in err.lower():
                        self._init_error += " Upgrade llama-cpp-python or use Python 3.11/3.12 if on 3.14."
                    logger.error(f"[FIFOLlama] {self._init_error}")
                    logger.info(
                        "[FIFOLlama] A follow-up 'Exception ignored... deallocator' or 'LlamaModel' ... 'sampler' "
                        "is a known llama-cpp-python cleanup bug after a failed load; safe to ignore."
                    )

    def switch_model(self, new_model_path: str) -> bool:
        """Switch to a different model (unloads current, loads new)."""
        if not LLAMA_CPP_AVAILABLE:
            return False

        p = Path(new_model_path)
        if not p.exists():
            logger.error(f"[FIFOLlama] Model not found: {new_model_path}")
            return False

        with FIFOLlamaCppAdapter._shared_lock:
            if FIFOLlamaCppAdapter._shared_llm is not None:
                logger.info("[FIFOLlama] Unloading current model...")
                del FIFOLlamaCppAdapter._shared_llm
                FIFOLlamaCppAdapter._shared_llm = None
                FIFOLlamaCppAdapter._shared_model_path = None

            n_gpu = _get_n_gpu_layers()
            for gpu_layers in [n_gpu, 0] if n_gpu != 0 else [0]:
                try:
                    logger.info(f"[FIFOLlama] Loading: {p.name} (n_gpu_layers={gpu_layers})")
                    llm = Llama(
                        model_path=str(p),
                        n_gpu_layers=gpu_layers,
                        n_ctx=4096,
                        n_threads=None,
                        verbose=False,
                    )
                    FIFOLlamaCppAdapter._shared_llm = llm
                    FIFOLlamaCppAdapter._shared_model_path = str(p)
                    self.model_path = str(p)
                    self._initialized = True
                    self._init_error = None
                    logger.info(f"[FIFOLlama] Switched to {p.name}")
                    return True
                except Exception as e:
                    if gpu_layers != 0:
                        logger.warning("[FIFOLlama] Switch failed, retrying with CPU-only: %s", e)
                        continue
                    self._init_error = str(e)
                    self._initialized = False
                    logger.error(f"[FIFOLlama] Switch failed: {e}")
                    return False
            return False

    # -- Streaming inference ------------------------------------------------

    async def _stream_tokens(self, prompt: str, **params) -> AsyncGenerator[str, None]:
        """TRUE token-level streaming via asyncio.Queue bridge.

        This is the SINGLE streaming path. No batch variant.

        Thread: llama_cpp.create_chat_completion(stream=True)
                -> each token -> queue.put_nowait via call_soon_threadsafe
        Async:  await queue.get() -> yield token
        """
        llm = FIFOLlamaCppAdapter._shared_llm
        if not llm:
            raise RuntimeError("Model not loaded")

        # Build messages: use full array if provided, else construct from prompt
        messages = params.get("messages")
        if not messages:
            messages = []
            system_prompt = params.get("system_prompt")
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        temperature = params.get("temperature", 0.7)
        top_p = params.get("top_p", 0.9)
        max_tokens = params.get("max_tokens", 2048)
        grammar = params.get("grammar")
        response_format = params.get("response_format")
        # v3.2 — additional sampler params
        seed = params.get("seed")
        logprobs = params.get("logprobs")
        top_logprobs = params.get("top_logprobs")
        logit_bias = params.get("logit_bias")
        top_k = params.get("top_k")
        min_p = params.get("min_p")
        repeat_penalty = params.get("repeat_penalty")
        frequency_penalty = params.get("frequency_penalty")
        presence_penalty = params.get("presence_penalty")
        # v3.3 — tool calling
        tools = params.get("tools")
        tool_choice = params.get("tool_choice")

        _SENTINEL = object()
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _produce():
            """Thread: push each token to the async queue immediately.

            No psutil, no diagnostics — InferenceGuard handles that
            from the caller side.
            """
            accumulated = ""
            try:
                # Build kwargs — only include grammar/response_format if set
                call_kwargs = dict(
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stream=True,
                    stop=_STOP_TOKENS,
                )
                # v3.2 — optional sampler params (only include if set)
                if seed is not None:
                    call_kwargs["seed"] = seed
                if logprobs:
                    call_kwargs["logprobs"] = True
                    if top_logprobs:
                        call_kwargs["top_logprobs"] = top_logprobs
                if logit_bias:
                    call_kwargs["logit_bias"] = logit_bias
                if top_k is not None:
                    call_kwargs["top_k"] = top_k
                if min_p is not None:
                    call_kwargs["min_p"] = min_p
                if repeat_penalty is not None:
                    call_kwargs["repeat_penalty"] = repeat_penalty
                if frequency_penalty:
                    call_kwargs["frequency_penalty"] = frequency_penalty
                if presence_penalty:
                    call_kwargs["presence_penalty"] = presence_penalty
                if grammar:
                    try:
                        from llama_cpp import LlamaGrammar

                        call_kwargs["grammar"] = LlamaGrammar.from_string(grammar)
                    except Exception as e:
                        logger.warning(f"[FIFOLlama] Grammar parse failed: {e}")
                if response_format:
                    call_kwargs["response_format"] = response_format
                # v3.3 — tool calling
                if tools:
                    call_kwargs["tools"] = tools
                if tool_choice is not None:
                    call_kwargs["tool_choice"] = tool_choice

                completion = llm.create_chat_completion(**call_kwargs)
                for chunk in completion:
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            accumulated += content
                            # Loop detection
                            if len(accumulated) > 400 and accumulated[-200:] in accumulated[:-200]:
                                logger.warning("[FIFOLlama] Loop detected, stopping")
                                break
                            loop.call_soon_threadsafe(queue.put_nowait, content)
            except Exception as e:
                logger.error(f"[FIFOLlama] Inference thread crash: {e}")
                loop.call_soon_threadsafe(queue.put_nowait, f"\u274c Inference error: {e}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

        loop.run_in_executor(None, _produce)

        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            yield item

    # -- Public API (adapter interface) -------------------------------------

    async def query_stream_tokens(self, request) -> AsyncGenerator[str, None]:
        """Stream individual tokens as they're generated.

        Each yield = one token from the model, the instant it's produced.
        Used by api_server for true SSE streaming.
        """
        if not LLAMA_CPP_AVAILABLE:
            yield "\u274c llama-cpp-python not installed"
            return

        if not self._initialized or FIFOLlamaCppAdapter._shared_llm is None:
            error = self._init_error or "Model not loaded"
            yield f"\u274c Local LLM not ready: {error}"
            return

        prompt = getattr(request, "prompt", str(request))
        params = {
            "system_prompt": getattr(request, "system_prompt", None),
            "temperature": getattr(request, "temperature", 0.7),
            "top_p": getattr(request, "top_p", 0.9),
            "max_tokens": getattr(request, "max_tokens", 2048),
            "grammar": getattr(request, "grammar", None),
            "response_format": getattr(request, "response_format", None),
            # v3.2 — additional sampler params
            "seed": getattr(request, "seed", None),
            "logprobs": getattr(request, "logprobs", None),
            "top_logprobs": getattr(request, "top_logprobs", None),
            "logit_bias": getattr(request, "logit_bias", None),
            "top_k": getattr(request, "top_k", None),
            "min_p": getattr(request, "min_p", None),
            "repeat_penalty": getattr(request, "repeat_penalty", None),
            "frequency_penalty": getattr(request, "frequency_penalty", 0.0),
            "presence_penalty": getattr(request, "presence_penalty", 0.0),
            # v3.3 — tool calling
            "tools": getattr(request, "tools", None),
            "tool_choice": getattr(request, "tool_choice", None),
        }

        # Multi-turn: pass full message array if available
        messages = getattr(request, "messages", None)
        if messages:
            params["messages"] = messages

        model_name = Path(self.model_path).stem if self.model_path else "unknown"
        logger.info(f"[FIFOLlama] Token-stream -> {model_name}: {prompt[:80]}...")

        start = time.time()
        token_count = 0
        first_token_at = None

        async for token in self._stream_tokens(prompt, **params):
            if first_token_at is None:
                first_token_at = time.time()
            token_count += 1
            yield token

        elapsed = time.time() - start
        ttft = (first_token_at - start) if first_token_at else elapsed
        tps = token_count / elapsed if elapsed > 0 else 0
        logger.info(f"[FIFOLlama] Done {elapsed:.2f}s  TTFT={ttft:.3f}s  {token_count} tok  {tps:.1f} tok/s")

    async def query(self, request) -> AsyncGenerator[str, None]:
        """Query the LLM — collects streamed tokens into a single response.

        Uses _stream_tokens internally (single streaming path).
        Post-processes to strip leaked conversation markers.
        """
        if not LLAMA_CPP_AVAILABLE:
            yield "\u274c llama-cpp-python not installed. Install: pip install llama-cpp-python"
            return

        if not self._initialized or FIFOLlamaCppAdapter._shared_llm is None:
            error = self._init_error or "Model not loaded"
            yield f"\u274c Local LLM not ready: {error}"
            return

        try:
            prompt = getattr(request, "prompt", str(request))
            params = {
                "system_prompt": getattr(request, "system_prompt", None),
                "temperature": getattr(request, "temperature", 0.7),
                "top_p": getattr(request, "top_p", 0.9),
                "max_tokens": getattr(request, "max_tokens", 2048),
            }

            # Multi-turn support
            messages = getattr(request, "messages", None)
            if messages:
                params["messages"] = messages

            model_name = Path(self.model_path).stem if self.model_path else "unknown"
            logger.info(f"[FIFOLlama] Query to {model_name}: {prompt[:80]}...")

            # Track in FIFO for metrics
            await self.request_buffer.add_message(
                content=prompt,
                message_type="llm_request",
                priority=MessagePriority.NORMAL,
                source="RAG_RAT",
                metadata=params,
                timeout=5.0,
            )

            start_time = time.time()
            chunks = []

            async for token in self._stream_tokens(prompt, **params):
                chunks.append(token)

            elapsed = time.time() - start_time
            total_text = "".join(chunks)

            # Post-process: strip leaked conversation markers
            for marker in _STOP_TOKENS:
                if marker in total_text:
                    total_text = total_text[: total_text.index(marker)].rstrip()
                    break

            # Track in FIFO for metrics
            await self.response_buffer.add_message(
                content=total_text,
                message_type="llm_response",
                source=model_name,
                metadata={"latency": elapsed, "chunks": len(chunks)},
            )

            logger.info(f"[FIFOLlama] Completed in {elapsed:.2f}s ({len(chunks)} chunks, {len(total_text)} chars)")

            yield total_text

        except Exception as e:
            logger.error(f"[FIFOLlama] Query error: {e}")
            yield f"\u274c Error: {str(e)}"

    async def validate(self) -> bool:
        """Check if model is loaded and ready."""
        return bool(LLAMA_CPP_AVAILABLE and self._initialized and FIFOLlamaCppAdapter._shared_llm is not None)

    async def close(self):
        """Cleanup (model stays loaded for reuse)."""
        return

    def get_stats(self) -> Dict[str, Any]:
        """Get FIFO buffer statistics."""
        return {
            "request_buffer": self.request_buffer.stats(),
            "response_buffer": self.response_buffer.stats(),
            "model_loaded": self._initialized,
            "model_path": self.model_path,
        }


# =========================================================================
# ALIASES & WRAPPER IMPORT
# =========================================================================

DirectLlamaCppAdapter = FIFOLlamaCppAdapter

try:
    from adapters.local_llm_wrapper import LocalLLMWrapperAdapter

    InMemoryLlamaCppAdapter = LocalLLMWrapperAdapter
    _USING_WRAPPER = True
    logger.info("[local_adapters] Using Local_LLM wrapper adapter")
except Exception:
    InMemoryLlamaCppAdapter = FIFOLlamaCppAdapter
    _USING_WRAPPER = False
    logger.info("[local_adapters] Wrapper not available; using FIFOLlamaCppAdapter")


# =========================================================================
# MOCK ADAPTERS (testing)
# =========================================================================


class MockLLMAdapter:
    """Deterministic mock adapter for testing UI flows without a real LLM."""

    def __init__(self, **kwargs):
        self.closed = False

    async def validate(self) -> bool:
        return True

    async def query(self, request):
        prompt = getattr(request, "prompt", "")
        base = f"MOCK_ANSWER: concise answer for prompt -> {prompt[:120]}"
        for i in range(0, len(base), 40):
            yield base[i : i + 40]
            await asyncio.sleep(0)

    async def close(self):
        self.closed = True


class RealisticMockLLMAdapter:
    """Realistic mock that streams token-like chunks with delays."""

    def __init__(self, *, token_delay: float = 0.03):
        self.token_delay = token_delay
        self.closed = False

    async def validate(self) -> bool:
        return True

    async def close(self) -> None:
        self.closed = True

    async def query(self, request) -> AsyncGenerator[str, None]:
        prompt = getattr(request, "prompt", "")
        base = (
            f"Answer: summary({len(prompt)} chars) - "
            "This is a realistic mock streaming response that emits tokens one by one."
        )
        tokens = []
        cur = []
        for ch in base:
            cur.append(ch)
            if ch.isspace() or ch in ",.;!-":
                tokens.append("".join(cur))
                cur = []
        if cur:
            tokens.append("".join(cur))

        for tok in tokens:
            await asyncio.sleep(self.token_delay)
            yield tok
