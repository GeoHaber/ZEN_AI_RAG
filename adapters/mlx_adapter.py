"""
MLX Adapter - Run MLX models locally on Apple Silicon.

Text-only: mlx-lm. Vision/VLM (e.g. Qwen3.5-0.8B-MLX-4bit): mlx-vlm for text-only chat (num_images=0).
Discovers models under ~/AI/Models/mlx (or MLX_MODELS_DIR).
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Any, Dict

logger = logging.getLogger(__name__)


# Default directory for MLX models (same base as GGUF, with /mlx)
def _default_mlx_dir() -> Path:
    return Path.home() / "AI" / "Models" / "mlx"


MLX_MODELS_DIR = Path(os.getenv("MLX_MODELS_DIR", str(_default_mlx_dir())))

# Lazy imports so the app runs without mlx installed
_mlx_load = None
_mlx_stream_generate = None
_mlx_vlm_load = None
_mlx_vlm_generate = None
_mlx_vlm_apply_chat_template = None
_mlx_vlm_load_config = None


def _ensure_mlx():
    global _mlx_load, _mlx_stream_generate
    if _mlx_load is not None:
        return
    try:
        from mlx_lm import (
            load as mlx_load_fn,
            stream_generate as mlx_stream_generate_fn,
        )

        _mlx_load = mlx_load_fn
        _mlx_stream_generate = mlx_stream_generate_fn
    except ImportError as e:
        raise RuntimeError(
            "mlx and mlx-lm are required for the MLX adapter. Install with: pip install mlx mlx-lm"
        ) from e


def _ensure_mlx_vlm():
    global _mlx_vlm_load, _mlx_vlm_generate, _mlx_vlm_apply_chat_template, _mlx_vlm_load_config
    if _mlx_vlm_load is not None:
        return
    try:
        from mlx_vlm import load as vlm_load_fn, generate as vlm_generate_fn
        from mlx_vlm.prompt_utils import apply_chat_template as vlm_apply_chat_template
        from mlx_vlm.utils import load_config as vlm_load_config

        _mlx_vlm_load = vlm_load_fn
        _mlx_vlm_generate = vlm_generate_fn
        _mlx_vlm_apply_chat_template = vlm_apply_chat_template
        _mlx_vlm_load_config = vlm_load_config
    except ImportError as e:
        raise RuntimeError("mlx-vlm is required for vision/VLM models. Install with: pip install mlx-vlm") from e


# Known text-only MLX model folder names (load with mlx_lm). Preferred when ordering.
# Qwen3 branch: mlx-community/Qwen3-* and Qwen/Qwen3-*-MLX-* (folder = repo last segment).
_KNOWN_TEXT_ONLY_MLX = frozenset(
    {
        "qwen3-4b-4bit",
        "qwen3-1.7b-4bit",
        "qwen3-0.6b-base-4bit",
        "qwen3-4b-4bit-dwq",
        "qwen3-4b-mlx-4bit",
        "qwen2.5-1.5b-instruct-4bit",
    }
)


def _is_vision_or_multimodal_model(model_dir: Path) -> bool:
    """True if config indicates a vision/VLM model (mlx_lm load() fails with 'parameters not in model')."""
    # Never treat known text-only models as vision (some share configs that mention vision_tower)
    try:
        resolved = model_dir.resolve()
        name_lower = resolved.name.lower().strip()
        if name_lower in _KNOWN_TEXT_ONLY_MLX:
            return False
    except Exception as exc:
        logger.debug("%s", exc)
    if model_dir.name.lower().strip() in _KNOWN_TEXT_ONLY_MLX:
        return False
    config_path = model_dir / "config.json"
    if not config_path.exists():
        return False
    try:
        import json

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        model_type = (config.get("model_type") or "").lower()
        arch = config.get("architectures") or []
        combined = (model_type + " " + " ".join(a for a in arch if isinstance(a, str))).lower()
        if "vision" in combined or " vl" in combined or "vl " in combined or "vlm" in combined:
            return True
        if config.get("vision_tower") or config.get("vision_config"):
            return True
        config_str = json.dumps(config)
        if "vision_tower" in config_str or "vision_config" in config_str:
            return True
        return False
    except Exception:
        return False


def check_mlx_model_usable(model_name: str, models_dir: Optional[Path] = None) -> tuple:
    """
    Check if an MLX model can be used (path exists and has config or weights).
    Returns (usable: bool, message: str). Use for UI status (e.g. offline vs ready).
    """
    if not model_name or not str(model_name).strip():
        return False, "No model selected"
    root = (models_dir or MLX_MODELS_DIR).expanduser().resolve()
    if not root.is_dir():
        return (
            False,
            f"MLX dir not found: {root}. Set MLX_MODELS_DIR or run download_mlx_model.py.",
        )
    # Resolve path: by name in discovered list, or root / model_name
    for sub in root.iterdir():
        if not sub.is_dir():
            continue
        if sub.name == model_name or model_name in sub.name:
            if (sub / "config.json").exists() or any(sub.glob("*.safetensors")):
                return True, f"{model_name} ready"
            return False, f"{model_name}: missing config.json or weights"
    candidate = root / model_name
    if candidate.is_dir():
        if (candidate / "config.json").exists() or any(candidate.glob("*.safetensors")):
            return True, f"{model_name} ready"
        return False, f"{model_name}: missing config.json or weights"
    return (
        False,
        f"Model '{model_name}' not found in {root}. Run: python scripts/download_mlx_model.py",
    )


def discover_mlx_models(models_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Scan for MLX model folders (text-only and VLM). VLMs are loaded with mlx-vlm for text-only chat.
    Known text-only models are listed first. Returns path, name, filename.
    """
    root = (models_dir or MLX_MODELS_DIR).expanduser().resolve()
    if not root.is_dir():
        return []
    result = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        # Skip only explicitly VL-named repos (e.g. Qwen2-VL-*); keep Qwen3.5-0.8B-MLX-4bit (VLM via mlx-vlm)
        name_lower = sub.name.lower()
        if "vl-" in name_lower or "-vl" in name_lower or "vision" in name_lower or "vlm" in name_lower:
            logger.debug("[MLX] Skipping VL-named model: %s", sub.name)
            continue
        has_config = (sub / "config.json").exists()
        has_weights = any(sub.glob("*.safetensors"))
        if has_config or has_weights:
            result.append({"path": str(sub), "name": sub.name, "filename": sub.name})

    # Prefer known text-only first, then others (e.g. Qwen3.5-0.8B-MLX-4bit)
    def sort_key(item: Dict[str, Any]) -> tuple:
        name_lower = item["name"].lower()
        return (0 if name_lower in _KNOWN_TEXT_ONLY_MLX else 1, item["name"])

    result.sort(key=sort_key)
    return result


try:
    from llm_adapters import BaseLLMAdapter, LLMRequest
except Exception:
    BaseLLMAdapter = object
    LLMRequest = None


class MLXAdapter(BaseLLMAdapter):
    """
    Adapter for MLX models (Apple Silicon).
    Loads model from a local path; supports streaming via stream_generate.
    """

    def __init__(self, model_name: Optional[str] = None, **kwargs):
        try:
            super().__init__()
        except Exception as exc:
            logger.debug("%s", exc)
        self.model_name = model_name
        self._model_path: Optional[str] = None
        self._model = None
        self._tokenizer = None
        self._processor = None
        self._vlm_config = None
        self._is_vlm = False
        self._available_models = discover_mlx_models()
        self._resolve_model_path()

    def _resolve_model_path(self) -> None:
        if not self.model_name:
            # Auto-select first discovered model
            if self._available_models:
                self._model_path = self._available_models[0]["path"]
                self.model_name = self._available_models[0]["name"]
                logger.info(f"[MLX] Auto-selected: {self.model_name}")
            return
        # Check if it's already an absolute path
        p = Path(self.model_name)
        if p.is_absolute() and p.is_dir():
            self._model_path = str(p)
            return
        # Match by folder name
        for m in self._available_models:
            if m["name"] == self.model_name or self.model_name in m["path"]:
                self._model_path = m["path"]
                return
        # Treat as relative to MLX_MODELS_DIR
        candidate = MLX_MODELS_DIR / self.model_name
        if candidate.is_dir():
            self._model_path = str(candidate)
            return
        logger.warning(f"[MLX] Model not found: {self.model_name}")

    def _load_model(self) -> None:
        if self._model is not None and (self._tokenizer is not None or (self._is_vlm and self._processor is not None)):
            return
        if not self._model_path:
            raise RuntimeError(
                f"No MLX model path. Set model_name to a folder under {MLX_MODELS_DIR} or run download_mlx_model.py."
            )
        model_dir = Path(self._model_path)
        if _is_vision_or_multimodal_model(model_dir):
            # Load with mlx-vlm for text-only chat (num_images=0)
            _ensure_mlx_vlm()
            logger.info(f"[MLX] Loading VLM (text-only chat) from {self._model_path}")
            self._model, self._processor = _mlx_vlm_load(self._model_path)
            self._vlm_config = _mlx_vlm_load_config(self._model_path)
            self._is_vlm = True
            logger.info("[MLX] VLM loaded (use for text chat)")
            return
        _ensure_mlx()
        logger.info(f"[MLX] Loading model from {self._model_path}")
        try:
            self._model, self._tokenizer = _mlx_load(self._model_path)
        except Exception as e:
            err_str = str(e).lower()
            if model_dir.name.lower() in _KNOWN_TEXT_ONLY_MLX:
                raise
            if "vision_tower" in err_str or "parameters not in model" in err_str:
                raise RuntimeError(
                    "This model has vision weights; use a VLM-capable path or install mlx-vlm: pip install mlx-vlm"
                ) from e
            raise
        logger.info("[MLX] Model loaded")

    def _build_prompt(self, request: Any) -> str:
        """Build chat prompt from LLMRequest (system_prompt + prompt or messages)."""
        # If we have tokenizer and message list, use chat template
        messages = getattr(request, "messages", None)
        if messages and isinstance(messages, list) and self._tokenizer is not None:
            try:
                prompt = self._tokenizer.apply_chat_template(
                    [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                return prompt
            except Exception as exc:
                logger.debug("%s", exc)
        # Fallback: system + user (Qwen-style)
        system = getattr(request, "system_prompt", None) or ""
        user = getattr(request, "prompt", "") or ""
        if system:
            return (
                f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
            )
        return user if user else ""

    async def query(self, request: Any) -> AsyncGenerator[str, None]:
        """Run inference and stream response chunks (one yield per stream_generate step)."""
        try:
            self._load_model()
        except RuntimeError as e:
            yield f"\u274c MLX: {e}"
            return
        except Exception as e:
            logger.exception("[MLX] Load failed")
            yield f"\u274c MLX load error: {e}"
            return

        prompt = self._build_prompt(request)
        if not prompt and hasattr(request, "prompt"):
            prompt = request.prompt
        if not prompt:
            yield "\u274c MLX: empty prompt"
            return

        temperature = getattr(request, "temperature", 0.7)
        max_tokens = getattr(request, "max_tokens", 2048)
        top_p = getattr(request, "top_p", 0.9)

        if self._is_vlm:
            # VLM path: text-only chat via mlx-vlm (num_images=0)
            def _vlm_generate():
                try:
                    formatted = _mlx_vlm_apply_chat_template(self._processor, self._vlm_config, prompt, num_images=0)
                    result = _mlx_vlm_generate(
                        self._model,
                        self._processor,
                        formatted,
                        image=None,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        verbose=False,
                    )
                    return getattr(result, "text", str(result)) if result else ""
                except Exception as e:
                    return f"\u274c Error: {e}"

            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, _vlm_generate)
            yield text
            return

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _produce():
            try:
                # Only pass params that mlx_lm stream_generate forwards (temp/top_p can cause "unexpected keyword argument 'temp'" in generate_step)
                for part in _mlx_stream_generate(
                    self._model,
                    self._tokenizer,
                    prompt,
                    max_tokens=max_tokens,
                ):
                    text = part if isinstance(part, str) else getattr(part, "text", str(part))
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"\u274c Error: {e}")
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        try:
            await loop.run_in_executor(None, _produce)
            while True:
                chunk = await queue.get()
                if chunk is sentinel:
                    break
                yield chunk
        except Exception as e:
            logger.exception("[MLX] Query failed")
            yield f"\u274c MLX error: {e}"

    async def stream_llm(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response (builds LLMRequest and yields from query)."""
        if not messages:
            yield "\u274c MLX: messages required"
            return
        from llm_adapters import LLMRequest, LLMProvider

        system = ""
        prompt = ""
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            elif m.get("role") == "user":
                prompt = m.get("content", "")
        req = LLMRequest(
            provider=LLMProvider.LOCAL_LLAMA,
            model=model or self.model_name or "",
            prompt=prompt,
            system_prompt=system or None,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
        async for chunk in self.query(req):
            yield chunk

    async def validate(self) -> bool:
        try:
            self._load_model()
            if self._is_vlm:
                return self._model is not None and self._processor is not None
            return self._model is not None and self._tokenizer is not None
        except Exception:
            return False

    async def close(self) -> None:
        self._model = None
        self._tokenizer = None
        self._processor = None
        self._vlm_config = None
        self._is_vlm = False

    def get_available_models(self) -> List[Dict[str, Any]]:
        return self._available_models
