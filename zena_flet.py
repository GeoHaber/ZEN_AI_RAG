#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zena_flet.py — Flet Desktop/Web GUI for ZEN_AI_RAG
====================================================

Launch with::

    python zena_flet.py                 # native desktop window
    flet run zena_flet.py               # same, via flet CLI
    flet run --web zena_flet.py         # opens in browser

Features:
  - Native Material 3 desktop app (Flutter engine)
  - Light / Dark mode toggle with persistent state
  - Multi-language support (EN, ES, FR, RO, HU, HE)
  - First-run onboarding stepper
  - Web URL + local folder + email scanning with progress
  - Zena RAG chat panel (async Q&A with streaming)
  - Data inspector, DB contents, document library
  - KB cleanup, cache dashboard, evaluation, dedup
  - Model gallery, settings dialog, intelligence judge
  - Voice lab with STT/TTS testing
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import flet as ft

# ── Ensure project root is importable ────────────────────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── UI Flet package ──────────────────────────────────────────────────────────
from ui_flet.theme import TH, setup_page_theme  # noqa: E402
from ui_flet.state import get_state  # noqa: E402
from ui_flet.persistence import apply_settings, save_settings  # noqa: E402
from ui_flet.sidebar import (  # noqa: E402
    build_sidebar,
    build_nav_rail,
    build_theme_lang_controls,
)
from ui_flet.chat_panel import build_chat_panel  # noqa: E402
from ui_flet.rag_panel import (  # noqa: E402
    build_source_config_panel,
    build_data_inspector_panel,
    build_db_contents_panel,
    build_cleanup_panel,
    build_cache_panel,
    build_eval_panel,
    build_dedup_panel,
)
from ui_flet.settings_dialog import build_settings_dialog  # noqa: E402
from ui_flet.model_panel import build_model_gallery  # noqa: E402
from ui_flet.onboarding import show_onboarding  # noqa: E402
from ui_flet.dashboard_panel import build_quality_dashboard  # noqa: E402
from ui_flet.voice_panel import build_voice_lab_panel  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  BACKEND HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Cached RAG singleton ─────────────────────────────────────────────────────
_rag_instance = None


def _get_rag() -> object:
    """Return a cached LocalRAG instance (created once, reused)."""
    global _rag_instance  # noqa: PLW0603
    if _rag_instance is None:
        from zena_mode.rag_pipeline import LocalRAG

        _rag_instance = LocalRAG()
    return _rag_instance


def ___chat_send_part2_part2(m):
    """Continue __chat_send_part2 logic."""
    messages_list.controls = [_chat_bubble(m) for m in state["chat_history"]]
    thinking.visible = False
    page.update()


def __chat_send_part2(m):
    """Continue _chat_send logic."""
    page.update()

    try:
        answer = ""
        sources = []

        # Try RAG search first
        if state.get("rag_enabled") and state.get("rag_content"):
            try:
                rag = _get_rag()
                loop = asyncio.get_running_loop()
                context, results = await loop.run_in_executor(None, lambda: rag.hybrid_search(query.strip(), top_k=5))
                sources = results if isinstance(results, list) else []
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)
                context = ""
        else:
            context = ""

        # Generate LLM answer — stream token-by-token
        try:
            import httpx

            system_msg = "You are ZenAI, a helpful assistant."
            if context:
                system_msg = (
                    "You are ZenAI, a helpful RAG assistant. "
                    "Answer based on the provided context.\n\n"
                    f"CONTEXT:\n{context[:8000]}"
                )

            payload = {
                "model": "model.gguf",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": query.strip()},
                ],
                "stream": True,
                "max_tokens": 2048 if context else 512,
            }

            # Add a placeholder assistant bubble for streaming
            state["chat_history"].append(
                {
                    "role": "assistant",
                    "content": "",
                    "sources": sources,
                }
            )
            bubble_idx = len(state["chat_history"]) - 1

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    "http://127.0.0.1:8001/v1/chat/completions",
                    json=payload,
                ) as resp:
                    if resp.status_code == 200:
                        import json as _json

                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = _json.loads(data_str)
                                delta = chunk["choices"][0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    answer += token
                                    state["chat_history"][bubble_idx]["content"] = answer
                                    messages_list.controls = [_chat_bubble(m) for m in state["chat_history"]]
                                    page.update()
                            except (KeyError, _json.JSONDecodeError):
                                continue
                    else:
                        answer = f"Backend error: {resp.status_code}"
                        state["chat_history"][bubble_idx]["content"] = answer

        except Exception as exc:
            logger.warning("LLM streaming failed, trying non-stream fallback: %s", exc)
            # Fallback: non-streaming via the ASGI server
            try:
                import httpx

                payload_fb = {
                    "message": query.strip(),
                    "mode": "council"
                    if state.get("council_mode")
                    else "deep_thinking"
                    if state.get("deep_thinking")
                    else "fast",
                }
                if context:
                    payload_fb["context"] = context[:8000]
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "http://127.0.0.1:8002/api/chat",
                        json=payload_fb,
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        answer = resp.json().get("response", "")
                    else:
                        answer = f"Backend error: {resp.status_code}"
            except Exception as exc2:
                if context:
                    answer = f"**Context found:**\n\n{context[:2000]}\n\n*(LLM unavailable — showing raw context)*"
                else:
                    answer = f"Error: Could not reach backend — {exc2}"

            # Update the placeholder bubble
            if state["chat_history"] and state["chat_history"][-1]["role"] == "assistant":
                state["chat_history"][-1]["content"] = answer
                state["chat_history"][-1]["sources"] = sources
            else:
                state["chat_history"].append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

    except Exception as exc:
        state["chat_history"].append(
            {
                "role": "assistant",
                "content": f"❌ Error: {exc}",
            }
        )
        logger.error("Chat error: %s", exc)

    ___chat_send_part2_part2(m)


async def _chat_send(query: str, page: ft.Page, state: dict, messages_list: ft.ListView, thinking: ft.Row) -> None:
    """Send a chat message: query RAG → stream answer → update UI."""
    if not query or not query.strip():
        return

    # Add user message
    state["chat_history"].append({"role": "user", "content": query.strip()})
    from ui_flet.chat_panel import _chat_bubble

    messages_list.controls = [_chat_bubble(m) for m in state["chat_history"]]
    thinking.visible = True
    __chat_send_part2(m)


async def _check_backend_health(page: ft.Page, state: dict) -> None:
    """Periodically check backend health."""
    while True:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Check ASGI server
                try:
                    resp = await client.get("http://127.0.0.1:8002/health", timeout=3)
                    state["backend_online"] = resp.status_code == 200
                except Exception:
                    state["backend_online"] = False

                # Check LLM server
                try:
                    resp = await client.get("http://127.0.0.1:8001/v1/models", timeout=3)
                    state["llm_online"] = resp.status_code == 200
                except Exception:
                    state["llm_online"] = False
        except Exception:
            state["backend_online"] = False
            state["llm_online"] = False

        await asyncio.sleep(10)


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL MAP
# ═══════════════════════════════════════════════════════════════════════════════

_PANEL_MAP = {
    "chat": lambda page, state: build_chat_panel(page, state, _chat_send),
    "data": build_data_inspector_panel,
    "db": build_db_contents_panel,
    "cleanup": build_cleanup_panel,
    "cache": build_cache_panel,
    "eval": build_eval_panel,
    "dedup": build_dedup_panel,
    "dashboard": build_quality_dashboard,
    "voice": build_voice_lab_panel,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  REBUILD / LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════


def _rebuild_app(page: ft.Page, state: dict, main_content: ft.Column) -> None:
    """Rebuild the sidebar + main content for the current panel."""

    def show_panel(key: str):
        """Switch the active panel and rebuild the app layout."""
        state["active_panel"] = key
        _rebuild_app(page, state, main_content)

    nav_rail = build_nav_rail(state, show_panel)

    def _on_full_rebuild():
        """Called by theme/lang controls to rebuild the entire page."""
        setup_page_theme(page)
        _rebuild_app(page, state, main_content)

    theme_icon, lang_dd = build_theme_lang_controls(page, _on_full_rebuild)

    def open_settings():
        """Open the settings dialog with theme-toggle support."""
        dlg = build_settings_dialog(
            page,
            state,
            on_theme_toggle=lambda: (TH.toggle(), _rebuild_app(page, state, main_content)),
        )
        page.open(dlg)

    def open_gallery():
        """Open the model gallery dialog."""
        dlg = build_model_gallery(page, state)
        page.open(dlg)

    sidebar = build_sidebar(
        page,
        state,
        theme_icon,
        lang_dd,
        nav_rail,
        on_settings=open_settings,
        on_gallery=open_gallery,
    )

    # Main content area
    main_content.controls.clear()
    has_data = bool(state.get("rag_content"))

    if not has_data:

        def on_scan_done():
            """Handle scan completion: switch to chat panel and rebuild."""
            state["active_panel"] = "chat"
            _rebuild_app(page, state, main_content)

        main_content.controls.append(build_source_config_panel(page, state, on_scan_done))
    else:
        active = state.get("active_panel", "chat")
        builder = _PANEL_MAP.get(active, _PANEL_MAP["chat"])
        main_content.controls.append(ft.Container(content=builder(page, state), padding=30, expand=True))

    page.controls.clear()
    page.add(ft.Row([sidebar, main_content], expand=True, spacing=0))


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════


async def main(page: ft.Page) -> None:
    """Main Flet application entry point."""
    state = get_state(page)

    # ── Restore persisted settings from disk ──────────────────────────────
    apply_settings(state)

    # Apply persisted dark mode preference
    if state.get("dark_mode") and not TH.is_dark():
        TH.toggle()
    elif not state.get("dark_mode") and TH.is_dark():
        TH.toggle()

    setup_page_theme(page)

    main_content = ft.Column([], expand=True, scroll=ft.ScrollMode.AUTO)

    _rebuild_app(page, state, main_content)

    # Start background health check (only once per session)
    if not state.get("_health_started"):
        state["_health_started"] = True
        page.run_task(_check_backend_health, page, state)

    # Show onboarding on first run and persist completion
    if not state.get("onboarded"):
        state["onboarded"] = True
        save_settings(state)
        show_onboarding(page)


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ft.app(target=main)
