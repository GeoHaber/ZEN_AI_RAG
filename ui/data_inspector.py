# -*- coding: utf-8 -*-
"""
ui/data_inspector.py — Data status bar, Your Data tab, Analytics tab (Flet)
"""

from __future__ import annotations
import logging
import flet as ft

from ui.i18n import _
from ui.theme import TH
from ui.state import AppState, services

logger = logging.getLogger(__name__)


def build_data_status_bar(page: ft.Page, state: AppState, on_rebuild) -> ft.Container:
    n_sources = len(state.rag_sources)
    n_msgs = len(state.messages)
    name = state.rag_source_name or "—"
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=TH.success),
                ft.Text(
                    name,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=TH.text,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    expand=True,
                ),
                ft.Container(width=16),
                _metric_chip(str(n_sources), _("metric.sources")),
                _metric_chip(str(n_msgs), _("metric.questions_asked")),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=TH.card,
        border=ft.border.all(1, TH.border),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )


def _metric_chip(value: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Text(value, size=12, weight=ft.FontWeight.BOLD, color=TH.accent),
                ft.Text(label, size=10, color=TH.dim),
            ],
            spacing=4,
        ),
        bgcolor=TH.chip,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
    )


def build_data_tab(state: AppState) -> ft.Container:
    sources = state.rag_sources
    if not sources:
        return ft.Container(
            content=ft.Text(
                _("data_tab.no_content"),
                size=13,
                color=TH.dim,
                text_align=ft.TextAlign.CENTER,
            ),
            expand=True,
            padding=40,
        )

    rows = []
    for i, src in enumerate(sources):
        title = src.get("title", src.get("url", src.get("path", f"Source {i + 1}")))
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DESCRIPTION, size=14, color=TH.dim),
                        ft.Text(str(title)[:60], size=12, color=TH.text, expand=True),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                border=ft.border.only(bottom=ft.BorderSide(1, TH.divider)),
            )
        )

    return ft.Container(
        content=ft.ListView(controls=rows, expand=True, spacing=0),
        expand=True,
        padding=16,
    )


def build_analytics_tab(state: AppState) -> ft.Container:
    n_sources = len(state.rag_sources)
    n_msgs = len(state.messages)
    n_user = len([m for m in state.messages if m.get("role") == "user"])
    n_ai = n_msgs - n_user
    content_len = len(state.rag_content) if state.rag_content else 0

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    _("analytics_tab.title"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=TH.text,
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        _stat_card("Sources", str(n_sources), ft.Icons.LANGUAGE),
                        _stat_card("Messages", str(n_msgs), ft.Icons.CHAT),
                        _stat_card("Content", f"{content_len:,} chars", ft.Icons.ARTICLE),
                    ],
                    spacing=12,
                    wrap=True,
                ),
                ft.Container(height=16),
                ft.Row(
                    [
                        _stat_card("User Qs", str(n_user), ft.Icons.PERSON),
                        _stat_card("AI Answers", str(n_ai), ft.Icons.SMART_TOY),
                    ],
                    spacing=12,
                    wrap=True,
                ),
            ]
        ),
        expand=True,
        padding=20,
    )


def _stat_card(label: str, value: str, icon) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, size=24, color=TH.accent),
                ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=TH.text),
                ft.Text(label, size=11, color=TH.dim),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        width=120,
        padding=16,
        bgcolor=TH.card,
        border=ft.border.all(1, TH.border),
        border_radius=10,
    )


def build_db_panel(page: ft.Page, state: AppState) -> ft.Container:
    """Database contents panel."""
    info_text = ft.Text("Loading...", size=12, color=TH.dim)
    results = ft.ListView(controls=[], expand=True, spacing=4)

    async def _load():
        try:
            rag = services.rag_integration
            if not rag:
                info_text.value = "RAG not available"
                page.update()
                return
            stats = rag.get_stats()
            chunks = stats.get("chunks", 0)
            info_text.value = f"Total chunks: {chunks}"

            if hasattr(rag, "list_indexed_sources"):
                indexed = rag.list_indexed_sources()
                for doc in indexed or []:
                    name = doc.get("name") or doc.get("title") or "?"
                    results.controls.append(ft.Text(f"  {name}", size=11, color=TH.text))
        except Exception as exc:
            info_text.value = f"Error: {exc}"
        page.update()

    page.run_task(_load)

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Database", size=16, weight=ft.FontWeight.W_600, color=TH.text),
                info_text,
                ft.Divider(color=TH.divider, height=8),
                results,
            ],
            expand=True,
        ),
        expand=True,
        padding=20,
    )


def build_cleanup_panel(page: ft.Page, state: AppState) -> ft.Container:
    status_text = ft.Text("", size=12, color=TH.dim)
    results = ft.ListView(controls=[], expand=True, spacing=4)

    async def on_run(e):
        status_text.value = "Scanning..."
        results.controls.clear()
        page.update()
        try:
            rag = services.rag_integration
            if not rag:
                status_text.value = "RAG not available"
                page.update()
                return
            docs = rag.list_documents()
            seen, conflicts = {}, []
            for doc in docs:
                src = doc.get("path", "")
                if src in seen:
                    conflicts.append(src)
                else:
                    seen[src] = doc
            if conflicts:
                status_text.value = f"Found {len(conflicts)} conflicts"
                for c in conflicts:
                    results.controls.append(ft.Text(f"  Duplicate: {c}", size=11, color=TH.warning_c))
            else:
                status_text.value = "No conflicts found"
        except Exception as exc:
            status_text.value = f"Error: {exc}"
        page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Cleanup", size=16, weight=ft.FontWeight.W_600, color=TH.text),
                ft.Button(
                    "Run Cleanup Scan",
                    on_click=on_run,
                    bgcolor=TH.accent2,
                    color="#ffffff",
                ),
                status_text,
                ft.Divider(color=TH.divider, height=8),
                results,
            ],
            expand=True,
            spacing=8,
        ),
        expand=True,
        padding=20,
    )


def build_cache_panel(page: ft.Page, state: AppState) -> ft.Container:
    info = ft.Text("Loading...", size=12, color=TH.dim)

    async def _load():
        try:
            from Core.semantic_cache import SemanticCache

            cache = SemanticCache()
            stats = cache.get_stats() if hasattr(cache, "get_stats") else {}
            hits = stats.get("hits", 0)
            misses = stats.get("misses", 0)
            total = hits + misses
            rate = (hits / total * 100) if total > 0 else 0
            info.value = f"Hits: {hits} | Misses: {misses} | Rate: {rate:.1f}%"
        except Exception:
            info.value = "Semantic cache not available"
        page.update()

    page.run_task(_load)
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Cache Dashboard",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=TH.text,
                ),
                ft.Container(height=12),
                info,
            ],
            spacing=8,
        ),
        expand=True,
        padding=20,
    )


def build_eval_panel(page: ft.Page, state: AppState) -> ft.Container:
    n_turns = len([m for m in state.messages if m.get("role") == "assistant"])
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Evaluation", size=16, weight=ft.FontWeight.W_600, color=TH.text),
                ft.Container(height=12),
                ft.Row(
                    [
                        _stat_card("Answers", str(n_turns), ft.Icons.QUESTION_ANSWER),
                        _stat_card("Messages", str(len(state.messages)), ft.Icons.CHAT),
                    ],
                    spacing=12,
                ),
            ],
            spacing=8,
        ),
        expand=True,
        padding=20,
    )


def build_dedup_panel(page: ft.Page, state: AppState) -> ft.Container:
    status_text = ft.Text("", size=12, color=TH.dim)
    results = ft.ListView(controls=[], expand=True, spacing=4)

    async def on_run(e):
        status_text.value = "Scanning..."
        results.controls.clear()
        page.update()
        try:
            rag = services.rag_integration
            if not rag:
                status_text.value = "RAG not available"
                page.update()
                return
            docs = rag.list_documents()
            seen, dupes = {}, []
            for doc in docs:
                name = doc.get("name", doc.get("path", ""))
                if name in seen:
                    dupes.append(name)
                else:
                    seen[name] = doc
            if dupes:
                status_text.value = f"Found {len(dupes)} duplicates"
                for d in dupes:
                    results.controls.append(ft.Text(f"  {d}", size=11, color=TH.warning_c))
            else:
                status_text.value = "No duplicates found"
        except Exception as exc:
            status_text.value = f"Error: {exc}"
        page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Deduplication", size=16, weight=ft.FontWeight.W_600, color=TH.text),
                ft.Button(
                    "Check for Duplicates",
                    on_click=on_run,
                    bgcolor=TH.accent2,
                    color="#ffffff",
                ),
                status_text,
                ft.Divider(color=TH.divider, height=8),
                results,
            ],
            expand=True,
            spacing=8,
        ),
        expand=True,
        padding=20,
    )
