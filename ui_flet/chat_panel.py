# -*- coding: utf-8 -*-
"""
ui_flet/chat_panel.py — Zena RAG Chat Panel
=============================================

Provides the primary chat interface: message list, streaming responses,
RAG source display, typing indicator, and the floating input bar.

Two builders:
- ``build_chat_panel``    — legacy (dict-based state + send_fn callback)
- ``build_chat_panel_v2`` — modern (``AppState`` + ``ConcreteBackend``)
"""

from __future__ import annotations

import logging
from typing import Callable

import flet as ft

from ui_flet.theme import TH, MONO_FONT
from ui_flet.widgets import spacer

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT BUBBLE
# ═══════════════════════════════════════════════════════════════════════════════


def ___chat_bubble_part2_part2(align, bubble_bg, controls):
    """Continue __chat_bubble_part2 logic."""
    if sources:
        source_chips = []
        for src in sources[:5]:
            title = src.get("title", src.get("path", "Source"))
            score = src.get("score", 0)
            source_chips.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=12, color=TH.accent),
                            ft.Text(
                                title[:40],
                                size=10,
                                color=TH.dim,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"{score:.0%}" if score else "",
                                size=9,
                                color=TH.success,
                            ),
                        ],
                        spacing=4,
                    ),
                    bgcolor=TH.bar_bg,
                    border_radius=8,
                    padding=ft.Padding.symmetric(vertical=2, horizontal=6),
                )
            )
        controls.append(ft.Row(source_chips, spacing=4, wrap=True))

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Column(controls, spacing=4),
                    bgcolor=bubble_bg,
                    border_radius=12,
                    padding=ft.Padding.symmetric(vertical=12, horizontal=16),
                    width=680,
                    border=ft.Border.all(1, TH.border),
                )
            ],
            alignment=align,
        ),
    )


def __chat_bubble_part2(content, role, sources):
    """Continue _chat_bubble logic."""
    if role == "user":
        icon, name = "👤", "You"
        bubble_bg = TH.user_bubble
        name_color = TH.accent
        align = ft.MainAxisAlignment.END
    elif role == "system":
        icon, name = "ℹ️", "System"
        bubble_bg = TH.chip
        name_color = TH.muted
        align = ft.MainAxisAlignment.CENTER
    else:
        icon, name = "🤖", "Zena"
        bubble_bg = TH.ai_bubble
        name_color = TH.accent2
        align = ft.MainAxisAlignment.START

    controls: list[ft.Control] = [
        ft.Text(
            f"{icon} {name}",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=name_color,
        ),
        ft.Markdown(
            content,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme=ft.MarkdownCodeTheme.MONOKAI if TH.is_dark() else ft.MarkdownCodeTheme.GITHUB,
            code_style_sheet=ft.MarkdownStyleSheet(
                code_text_style=ft.TextStyle(font_family=MONO_FONT, size=12),
            ),
        ),
    ]

    # Show RAG sources if present
    return ___chat_bubble_part2_part2(align, bubble_bg, controls)


def _chat_bubble(msg: dict) -> ft.Container:
    """Render a single chat message bubble (user, assistant, or system)."""
    role = msg.get("role", "user")
    content = msg.get("content", "")
    sources = msg.get("sources", [])

    return __chat_bubble_part2(content, role, sources)


# ═══════════════════════════════════════════════════════════════════════════════
#  THINKING INDICATOR
# ═══════════════════════════════════════════════════════════════════════════════


def _thinking_indicator() -> ft.Row:
    """Animated thinking indicator shown while Zena generates a response."""
    return ft.Row(
        [
            ft.ProgressRing(width=16, height=16, stroke_width=2, color=TH.accent2),
            ft.Text("Zena is thinking…", size=12, italic=True, color=TH.muted),
        ],
        spacing=8,
        visible=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT HEADER
# ═══════════════════════════════════════════════════════════════════════════════


def _chat_header(rag_stats: ft.Text, on_clear) -> ft.Row:
    """Header row: Zena title + RAG stats + clear button."""
    return ft.Row(
        [
            ft.Text("🤖 Zena", size=20, weight=ft.FontWeight.BOLD, color=TH.accent2),
            ft.Text("— RAG-powered intelligent assistant", size=13, color=TH.muted),
            ft.Container(expand=True),
            rag_stats,
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=TH.muted,
                tooltip="Clear chat history",
                on_click=on_clear,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  INPUT BAR
# ═══════════════════════════════════════════════════════════════════════════════


def _chat_input_bar(
    query_field: ft.TextField,
    on_send,
    on_voice_click=None,
    on_attach_click=None,
) -> ft.Container:
    """Floating input bar with send, voice, and attach buttons."""
    row_controls = []

    if on_attach_click:
        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.ATTACH_FILE,
                icon_color=TH.muted,
                tooltip="Attach file",
                on_click=on_attach_click,
            )
        )

    row_controls.append(query_field)

    if on_voice_click:
        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.MIC_NONE,
                icon_color=TH.muted,
                tooltip="Voice input",
                on_click=on_voice_click,
            )
        )

    row_controls.append(
        ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            bgcolor=TH.accent2,
            tooltip="Send message",
            on_click=on_send,
        )
    )

    return ft.Container(
        content=ft.Row(row_controls, spacing=8),
        bgcolor=TH.surface,
        border=ft.Border.all(1, TH.border),
        border_radius=12,
        padding=ft.Padding.symmetric(vertical=8, horizontal=12),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  WELCOME MESSAGE
# ═══════════════════════════════════════════════════════════════════════════════

_EXAMPLES = [
    ("💡", "Summarise the key findings"),
    ("🔍", "Search for specific topics"),
    ("📊", "Analyse data patterns"),
    ("🧠", "Explain complex concepts"),
]


def _welcome_message(on_chip_click=None) -> ft.Container:
    """Shown when chat history is empty."""
    chips = ft.Row(
        [
            ft.Container(
                content=ft.Row(
                    [ft.Text(icon, size=14), ft.Text(label, size=12, color=TH.dim)],
                    spacing=4,
                ),
                bgcolor=TH.chip,
                border=ft.Border.all(1, TH.border),
                border_radius=20,
                padding=ft.Padding.symmetric(vertical=6, horizontal=12),
                on_click=(lambda e, lbl=label: on_chip_click(lbl)) if on_chip_click else None,
                ink=True if on_chip_click else False,
            )
            for icon, label in _EXAMPLES
        ],
        spacing=8,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("🤖", size=48, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    "Hello! I'm Zena",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=TH.accent2,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Your RAG-powered AI assistant. Ask me anything about your data.",
                    size=14,
                    color=TH.muted,
                    text_align=ft.TextAlign.CENTER,
                ),
                spacer(16),
                ft.Text("Try asking:", size=12, color=TH.dim, text_align=ft.TextAlign.CENTER),
                chips,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=40,
        alignment=ft.Alignment(0, 0),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def _build_chat_panel_part2(history, messages_list, query_field, thinking):
    """Continue build_chat_panel logic."""

    def on_clear(e):
        """Clear the chat history and reset the conversation view."""
        state["chat_history"].clear()
        messages_list.controls = [_welcome_message(on_chip_click=_send_text)]
        page.update()

    # Populate message list
    if history:
        messages_list.controls = [_chat_bubble(m) for m in history]
    else:
        messages_list.controls = [_welcome_message(on_chip_click=_send_text)]

    # RAG stats
    rag_stats = ft.Text("", size=11, color=TH.muted)
    src_name = state.get("rag_source_name", "")
    n_sources = len(state.get("rag_sources", []))
    if src_name:
        rag_stats.value = f"📚 {src_name}"
        if n_sources:
            rag_stats.value += f" · {n_sources} chunks"

    return ft.Column(
        [
            _chat_header(rag_stats, on_clear),
            ft.Divider(color=TH.divider, height=10),
            messages_list,
            thinking,
            _chat_input_bar(query_field, on_send, voice_fn, attach_fn),
        ],
        spacing=8,
        expand=True,
    )


def build_chat_panel(
    page: ft.Page,
    state: dict,
    send_fn: Callable,
    voice_fn: Callable | None = None,
    attach_fn: Callable | None = None,
) -> ft.Column:
    """Build the complete Zena chat panel.

    Parameters
    ----------
    page : ft.Page
        The Flet page instance.
    state : dict
        Shared application state (``page.data["_state"]``).
    send_fn : Callable
        ``async def send_fn(query, page, state, messages_list, thinking)``
    voice_fn : Callable | None
        Optional voice toggle handler.
    attach_fn : Callable | None
        Optional file-attach handler.
    """
    history = state.get("chat_history", [])

    # Message list
    messages_list = ft.ListView(
        controls=[],
        expand=True,
        spacing=10,
        padding=10,
        auto_scroll=True,
    )

    thinking = _thinking_indicator()

    query_field = ft.TextField(
        hint_text="Ask Zena about your data…",
        prefix_icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        border_color=TH.border,
        color=TH.text,
        focused_border_color=TH.accent,
        expand=True,
        autofocus=True,
    )

    def _send_text(text: str):
        """Send a pre-filled message (e.g. from a welcome chip)."""
        query_field.value = text
        on_send(None)

    def on_send(e):
        """Send the current message and clear the input field."""
        page.run_task(send_fn, query_field.value, page, state, messages_list, thinking)
        query_field.value = ""
        page.update()

    query_field.on_submit = on_send

    return _build_chat_panel_part2(history, messages_list, query_field, thinking)


# ═══════════════════════════════════════════════════════════════════════════════
#  V2 BUILDER — works with AppState + ConcreteBackend
# ═══════════════════════════════════════════════════════════════════════════════


def _rag_metadata_card(result) -> ft.Container:
    """Render RAG metadata (mode, confidence, hallucination, stages)."""
    rows = []
    if result.mode:
        rows.append(ft.Text(f"Mode: {result.mode}", size=10, color=TH.dim))
    if result.confidence:
        pct = f"{result.confidence:.0%}"
        rows.append(ft.Text(f"Confidence: {pct}", size=10, color=TH.success))
    if result.hallucination_score:
        h_pct = f"{result.hallucination_score:.0%}"
        color = TH.error_c if result.hallucination_score > 0.5 else TH.warning_c
        rows.append(ft.Text(f"Hallucination risk: {h_pct}", size=10, color=color))
    if result.conflicts:
        rows.append(
            ft.Text(f"⚠ {len(result.conflicts)} conflict(s)", size=10, color=TH.warning_c)
        )
    if result.stages:
        rows.append(
            ft.Text(f"Stages: {' → '.join(result.stages)}", size=10, color=TH.dim)
        )
    if result.latency_ms:
        rows.append(ft.Text(f"Latency: {result.latency_ms:.0f}ms", size=10, color=TH.dim))

    if not rows:
        return ft.Container()
    return ft.Container(
        content=ft.Column(rows, spacing=2),
        bgcolor=TH.bar_bg,
        border_radius=8,
        padding=ft.Padding.symmetric(vertical=6, horizontal=10),
    )


def build_chat_panel_v2(
    page: ft.Page,
    state,
    backend,
) -> ft.Column:
    """Build chat panel using AppState + ConcreteBackend.

    Parameters
    ----------
    page   : Flet page
    state  : ``AppState`` instance
    backend: ``ConcreteBackend`` instance from ``backend_impl``
    """
    messages_list = ft.ListView(
        controls=[],
        expand=True,
        spacing=10,
        padding=10,
        auto_scroll=True,
    )

    thinking = _thinking_indicator()

    query_field = ft.TextField(
        hint_text="Ask Zena about your data…",
        prefix_icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        border_color=TH.border,
        color=TH.text,
        focused_border_color=TH.accent,
        expand=True,
        autofocus=True,
    )

    # Populate existing messages
    history = state.messages or []
    if history:
        messages_list.controls = [_chat_bubble(m) for m in history]
    else:
        def _on_chip_initial(text):
            query_field.value = text
            _on_send(None)
        messages_list.controls = [_welcome_message(on_chip_click=_on_chip_initial)]

    async def _send_message(query: str):
        if not query or not query.strip():
            return
        user_msg = {"role": "user", "content": query}
        state.messages.append(user_msg)
        messages_list.controls.append(_chat_bubble(user_msg))
        thinking.visible = True
        page.update()

        try:
            result = await backend.chat(
                query,
                session_id=state.session_id,
                temperature=state.setting_temperature,
                max_tokens=state.setting_max_tokens,
                rag_enabled=state.rag_enabled,
                rag_mode=state.rag_pipeline_mode,
            )
            ai_msg = {
                "role": "assistant",
                "content": result.answer,
                "sources": result.sources,
            }
            state.messages.append(ai_msg)
            messages_list.controls.append(_chat_bubble(ai_msg))
            meta = _rag_metadata_card(result)
            if meta.content:
                messages_list.controls.append(meta)
        except Exception as exc:
            err_msg = {"role": "system", "content": f"Error: {exc}"}
            messages_list.controls.append(_chat_bubble(err_msg))
        finally:
            thinking.visible = False
            page.update()

    async def _send_council(query: str):
        user_msg = {"role": "user", "content": f"[Council] {query}"}
        state.messages.append(user_msg)
        messages_list.controls.append(_chat_bubble(user_msg))
        thinking.visible = True
        page.update()
        try:
            result = await backend.council_chat(query)
            consensus = result.get("consensus_answer", "No consensus reached.")
            individuals = result.get("individual_responses", [])
            ai_msg = {"role": "assistant", "content": consensus}
            state.messages.append(ai_msg)
            messages_list.controls.append(_chat_bubble(ai_msg))
            if individuals:
                expert_texts = []
                for resp in individuals[:5]:
                    name = resp.get("expert", resp.get("name", "Expert"))
                    answer = resp.get("answer", resp.get("response", ""))[:200]
                    expert_texts.append(f"**{name}:** {answer}")
                detail_msg = {"role": "system", "content": "\n\n".join(expert_texts)}
                messages_list.controls.append(_chat_bubble(detail_msg))
        except Exception as exc:
            err_msg = {"role": "system", "content": f"Council error: {exc}"}
            messages_list.controls.append(_chat_bubble(err_msg))
        finally:
            thinking.visible = False
            page.update()

    def _on_send(e):
        text = query_field.value
        if not text or not text.strip():
            return
        query_field.value = ""
        page.update()
        if state.council_mode:
            page.run_task(_send_council, text)
        else:
            page.run_task(_send_message, text)

    query_field.on_submit = _on_send

    def on_clear(e):
        state.messages.clear()
        def _on_chip_reset(text):
            query_field.value = text
            _on_send(None)
        messages_list.controls = [_welcome_message(on_chip_click=_on_chip_reset)]
        page.update()

    rag_stats = ft.Text("", size=11, color=TH.muted)
    if state.rag_source_name:
        rag_stats.value = f"📚 {state.rag_source_name}"
        n = len(state.rag_sources)
        if n:
            rag_stats.value += f" · {n} chunks"

    mode_chips = ft.Row(
        [
            ft.Container(
                content=ft.Text(
                    f"{'Enhanced' if state.rag_pipeline_mode == 'enhanced' else 'Classic'} RAG",
                    size=10,
                    color=TH.accent if state.rag_enabled else TH.muted,
                ),
                bgcolor=TH.chip,
                border_radius=12,
                padding=ft.Padding.symmetric(vertical=2, horizontal=8),
            ),
            ft.Container(
                content=ft.Text(
                    "Council" if state.council_mode else "Direct",
                    size=10,
                    color=TH.accent2 if state.council_mode else TH.muted,
                ),
                bgcolor=TH.chip,
                border_radius=12,
                padding=ft.Padding.symmetric(vertical=2, horizontal=8),
            ),
        ],
        spacing=4,
    )

    return ft.Column(
        [
            _chat_header(rag_stats, on_clear),
            mode_chips,
            ft.Divider(color=TH.divider, height=10),
            messages_list,
            thinking,
            _chat_input_bar(query_field, _on_send),
        ],
        spacing=8,
        expand=True,
    )
