# -*- coding: utf-8 -*-
"""
ui_flet/model_panel.py — Model Gallery & Manager
==================================================

Model gallery dialog for viewing, swapping, downloading, and managing
LLM models. Communicates with backend via HTTP on port 8002.
"""

from __future__ import annotations

import logging

import flet as ft

from ui_flet.theme import TH
from ui_flet.widgets import badge, snack, spacer

logger = logging.getLogger(__name__)

# ── Static model info (fallback when backend unavailable) ────────────────────
MODEL_INFO = {
    "qwen2.5-coder-7b": {
        "name": "Qwen 2.5 Coder 7B",
        "icon": "🧑‍💻",
        "desc": "Excellent for code generation",
        "size": "4.7 GB",
        "tags": ["code", "fast"],
        "quality": "⭐⭐⭐⭐",
    },
    "llama-3.2-3b": {
        "name": "Llama 3.2 3B",
        "icon": "🦙",
        "desc": "Meta's lightweight model",
        "size": "2.0 GB",
        "tags": ["general", "fast"],
        "quality": "⭐⭐⭐",
    },
    "phi-3-mini": {
        "name": "Phi-3 Mini",
        "icon": "🔬",
        "desc": "Microsoft's efficient model",
        "size": "2.3 GB",
        "tags": ["general", "efficient"],
        "quality": "⭐⭐⭐",
    },
    "mistral-7b": {
        "name": "Mistral 7B",
        "icon": "🌊",
        "desc": "Mistral AI's flagship",
        "size": "4.1 GB",
        "tags": ["general", "quality"],
        "quality": "⭐⭐⭐⭐",
    },
    "deepseek-coder-6.7b": {
        "name": "DeepSeek Coder 6.7B",
        "icon": "🐳",
        "desc": "Strong code model",
        "size": "3.8 GB",
        "tags": ["code", "quality"],
        "quality": "⭐⭐⭐⭐",
    },
    "codellama-7b": {
        "name": "CodeLlama 7B",
        "icon": "🦙",
        "desc": "Meta's code-focused model",
        "size": "3.8 GB",
        "tags": ["code"],
        "quality": "⭐⭐⭐",
    },
}


def _model_card(
    key: str,
    info: dict,
    is_active: bool,
    on_swap,
) -> ft.Container:
    """Render a single model card."""
    tag_chips = ft.Row(
        [badge(t, color=TH.accent if t == "code" else TH.text) for t in info.get("tags", [])],
        spacing=4,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(info.get("icon", "🤖"), size=32, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    info.get("name", key),
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=TH.accent if is_active else TH.text,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(info.get("size", ""), size=11, color=TH.muted, text_align=ft.TextAlign.CENTER),
                ft.Text(info.get("desc", ""), size=11, color=TH.dim, text_align=ft.TextAlign.CENTER),
                tag_chips,
                ft.Divider(color=TH.divider, height=8),
                ft.Button(
                    "Active" if is_active else "Swap",
                    on_click=lambda e, k=key: on_swap(k),
                    bgcolor=TH.success if is_active else TH.accent,
                    color=ft.Colors.WHITE,
                    disabled=is_active,
                    width=100,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        bgcolor=TH.card,
        border=ft.Border.all(2, TH.accent if is_active else TH.border),
        border_radius=14,
        padding=16,
        width=200,
        shadow=ft.BoxShadow(blur_radius=6, color=TH.shadow),
    )


def __build_model_gallery_part2_part2(file_field, repo_field):
    """Continue _build_model_gallery_part2 logic."""

    def on_close(e):
        """Close the model gallery dialog."""
        page.close(dlg)

    dlg = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Text("🤖 Council of LLMs", size=20, weight=ft.FontWeight.BOLD, color=TH.accent),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_color=TH.muted, on_click=on_close),
            ]
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Select a model to swap or download a new one", size=12, color=TH.muted),
                    spacer(8),
                    grid,
                    ft.Divider(color=TH.divider, height=20),
                    ft.Text("⬇️ Custom Download", size=14, weight=ft.FontWeight.BOLD, color=TH.accent2),
                    ft.Row([repo_field, file_field], spacing=8),
                    ft.Button(
                        "Download",
                        on_click=lambda e: page.run_task(on_download, e),
                        icon=ft.Icons.DOWNLOAD,
                        bgcolor=TH.accent2,
                        color=ft.Colors.WHITE,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=8,
            ),
            width=750,
            height=500,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=16),
    )
    return dlg


def _build_model_gallery_part2(client, grid, resp):
    """Continue build_model_gallery logic."""
    repo_field = ft.TextField(
        label="HuggingFace Repo",
        hint_text="TheBloke/Mistral-7B-GGUF",
        border_color=TH.border,
        color=TH.text,
        expand=True,
    )
    file_field = ft.TextField(
        label="Filename",
        hint_text="mistral-7b.Q4_K_M.gguf",
        border_color=TH.border,
        color=TH.text,
        expand=True,
    )

    async def on_download(e):
        """Start downloading a custom model from HuggingFace."""
        repo = repo_field.value.strip()
        fname = file_field.value.strip()
        if not repo or not fname:
            snack(page, "Enter repo and filename", TH.error_c)
            return
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://127.0.0.1:8002/models/download",
                    json={"repo_id": repo, "filename": fname},
                    timeout=300,
                )
                if resp.status_code == 200:
                    snack(page, f"✅ Download started: {fname}")
                else:
                    snack(page, f"❌ Download failed: {resp.text}", TH.error_c)
        except Exception as exc:
            snack(page, f"❌ Download error: {exc}", TH.error_c)

    return __build_model_gallery_part2_part2(file_field, repo_field)


def build_model_gallery(
    page: ft.Page,
    state: dict,
) -> ft.AlertDialog:
    """Build the model gallery dialog with swap and download controls."""
    active_model = state.get("active_model", "")

    async def on_swap(model_key):
        """Request a model swap via the management API."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://127.0.0.1:8002/swap",
                    json={"model": model_key},
                    timeout=30,
                )
                if resp.status_code == 200:
                    state["active_model"] = model_key
                    snack(page, f"✅ Swapped to {model_key}")
                else:
                    snack(page, f"❌ Swap failed: {resp.text}", TH.error_c)
        except Exception as exc:
            snack(page, f"❌ Swap error: {exc}", TH.error_c)

    # Build model grid
    cards = []
    for key, info in MODEL_INFO.items():
        is_active = key in active_model
        cards.append(_model_card(key, info, is_active, lambda k: page.run_task(on_swap, k)))

    grid = ft.Row(cards, wrap=True, spacing=12, run_spacing=12, alignment=ft.MainAxisAlignment.CENTER)

    # Download section
    return _build_model_gallery_part2(client, grid, resp)
