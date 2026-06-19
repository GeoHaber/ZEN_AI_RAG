# -*- coding: utf-8 -*-
"""
zen_shared_client.py - Client for the shared "Zena" LLM service (SSOT).

WHY THIS EXISTS
===============
On the GeoHab box there must be exactly ONE resident generation LLM (the
shared gemma served by the Zena governor on http://127.0.0.1:8800). The
2026-06-09 outage was caused by TWO gemmas loading at once (this app spawned
its own ``llama-server.exe`` while the shared service was already resident),
pushing RAM to ~97% and taking the box down.

This module is the single place that decides, for the *generation / chat* LLM:

  * whether to PREFER the shared :8800 service (default: yes), and
  * the base URL + auth header to talk to it.

The spawn of a local ``llama-server.exe`` is GATED on this module: if the
shared service is preferred and healthy, the app must NOT start a competing
gemma. See ``zena_mode/server.start_server``.

SCOPE
=====
This only concerns the **chat / generation** LLM (the gemma). Embedding,
reranker and RAG-index models (fastembed / colbert / sentence-transformers)
are NOT the shared gemma and are NOT an OOM risk -- they stay local and are
untouched by this module.

REVERSIBILITY
=============
Everything here is behind env flags, default-ON for the shared path:

  ZENA_PREFER_SHARED_LLM   "1" (default) -> prefer the shared :8800 service.
                           "0"           -> behave like before (local engine).
  ZENA_SHARED_LLM_URL      base URL of the shared service (default
                           http://127.0.0.1:8800).
  ZENA_SHARED_LLM_APP      app name used to register (default "zen_ai_rag").
  ZENA_ALLOW_LOCAL_LLM_SPAWN
                           "1" -> escape hatch: allow spawning a local
                           llama-server even when shared is preferred
                           (offline / dev only -- can re-introduce the OOM).
                           Default unset/"0".
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger("ZenSharedClient")

# ── Defaults ────────────────────────────────────────────────────────────────

_DEFAULT_SHARED_URL = "http://127.0.0.1:8800"
_DEFAULT_APP_NAME = "zen_ai_rag"

# Cache the registration key for the process lifetime so we register once.
_REG_LOCK = threading.Lock()
_REG_KEY: Optional[str] = None
_REG_FAILED_AT: float = 0.0
_REG_RETRY_COOLDOWN = 30.0  # seconds; avoid hammering /zen/register on failure


# ── Flag helpers ────────────────────────────────────────────────────────────

def _truthy(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def prefer_shared() -> bool:
    """True if the shared :8800 service should be the default generation LLM."""
    return _truthy(os.environ.get("ZENA_PREFER_SHARED_LLM"), True)


def allow_local_spawn() -> bool:
    """True only if the operator explicitly opted into a local llama-server.

    This is the escape hatch for offline / dev use. When ``prefer_shared`` is
    True and this is False (the default), the app must NEVER spawn a competing
    gemma.
    """
    return _truthy(os.environ.get("ZENA_ALLOW_LOCAL_LLM_SPAWN"), False)


def shared_base_url() -> str:
    """Base URL of the shared service, e.g. http://127.0.0.1:8800 (no slash)."""
    return os.environ.get("ZENA_SHARED_LLM_URL", _DEFAULT_SHARED_URL).rstrip("/")


def shared_app_name() -> str:
    return os.environ.get("ZENA_SHARED_LLM_APP", _DEFAULT_APP_NAME)


def _shared_host_port() -> tuple[str, int]:
    parsed = urlparse(shared_base_url())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


# ── HTTP plumbing (lazy, dependency-tolerant) ───────────────────────────────

def _get_requests():
    try:
        import requests  # type: ignore

        return requests
    except Exception:  # pragma: no cover - requests is a hard dep in practice
        return None


def is_shared_up(timeout: float = 1.5) -> bool:
    """Cheap liveness probe of the shared service via GET /health.

    Falls back to a raw TCP connect if ``requests`` is unavailable, so the
    spawn gate still works in minimal environments.
    """
    requests = _get_requests()
    base = shared_base_url()
    if requests is not None:
        try:
            resp = requests.get(f"{base}/health", timeout=timeout)
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("[SharedLLM] /health probe failed: %s", exc)
            # Fall through to a TCP check before giving up.
    # TCP fallback: port open is a weak-but-useful signal.
    import socket

    host, port = _shared_host_port()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def wait_for_shared(timeout: float = 60.0, interval: float = 2.0) -> bool:
    """Block until the shared service answers /health, or *timeout* elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_shared_up():
            return True
        time.sleep(interval)
    return is_shared_up()


def should_use_shared() -> bool:
    """The gate: prefer-shared is ON *and* the shared service is reachable."""
    return prefer_shared() and is_shared_up()


# ── Registration / auth ─────────────────────────────────────────────────────

def register(force: bool = False) -> Optional[str]:
    """Register this app with the shared service and cache the returned key.

    Idempotent: returns the cached key on subsequent calls. Returns ``None`` if
    the service is unreachable or registration fails (callers should then treat
    auth as best-effort -- a localhost shared service may not require a key).
    """
    global _REG_KEY, _REG_FAILED_AT

    with _REG_LOCK:
        if _REG_KEY and not force:
            return _REG_KEY
        # Back off after a recent failure to avoid hammering the endpoint.
        if (not force) and (_REG_FAILED_AT > 0) and (
            time.time() - _REG_FAILED_AT < _REG_RETRY_COOLDOWN
        ):
            return None

        requests = _get_requests()
        if requests is None:
            _REG_FAILED_AT = time.time()
            return None

        base = shared_base_url()
        try:
            resp = requests.post(
                f"{base}/zen/register",
                json={"app": shared_app_name()},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                key = data.get("key") or data.get("api_key") or data.get("token")
                if key:
                    _REG_KEY = str(key)
                    _REG_FAILED_AT = 0.0
                    logger.info(
                        "[SharedLLM] Registered '%s' with %s",
                        shared_app_name(),
                        base,
                    )
                    return _REG_KEY
                # Service accepted us but returned no key -> auth not required.
                logger.info(
                    "[SharedLLM] Registered '%s' (no key issued; auth optional)",
                    shared_app_name(),
                )
                _REG_FAILED_AT = 0.0
                return None
            logger.warning(
                "[SharedLLM] register returned HTTP %s", resp.status_code
            )
        except Exception as exc:
            logger.warning("[SharedLLM] register failed: %s", exc)

        _REG_FAILED_AT = time.time()
        return None


def auth_header() -> Dict[str, str]:
    """Authorization header for the shared service (empty dict if no key)."""
    key = _REG_KEY or register()
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


# ── Endpoint resolution for chat/generation clients ─────────────────────────

def chat_base_url() -> str:
    """Base URL the generation/chat clients should use.

    Returns the shared :8800 base when shared is preferred AND up; otherwise
    falls back to the local engine URL from config so offline/dev still works.
    """
    if should_use_shared():
        return shared_base_url()
    # Local fallback -- import lazily to avoid a config import cycle at module load.
    try:
        from config_system import config

        return str(config.LLM_API_URL).rstrip("/")
    except Exception:
        return "http://127.0.0.1:8001"


def chat_completions_url() -> str:
    """Full /v1/chat/completions endpoint for the active generation backend."""
    return f"{chat_base_url()}/v1/chat/completions"


def active_is_shared() -> bool:
    """Convenience: is the active chat backend the shared service?"""
    return should_use_shared()
