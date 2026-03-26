# -*- coding: utf-8 -*-
"""
ui/marketplace_panel.py — Model Marketplace UI (Flet)
Displays LLM 'Worth' Cards with Speed, Quality, and RAM metrics.
"""

from __future__ import annotations
import flet as ft
from Core.model_marketplace import CURATED_MODELS, ModelMarketplace
from ui.theme import TH


def _worth_badge(icon: str, label: str, value: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, size=14, color=color),
                ft.Text(
                    f"{label}: {value}",
                    size=11,
                    color=TH.text,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=4,
        ),
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        border_radius=6,
        bgcolor=f"{color}15",
    )


def _llm_card(model: dict, on_download: callable) -> ft.Container:
    """A premium 'Worth' card for an LLM."""

    # Extract worth metrics
    speed = model.get("speed_rating", "⚡ Balanced")
    quality = model.get("quality_rating", "⭐⭐⭐⭐")
    ram = model.get("ram_estimate", "~6 GB")

    # Category badge color
    cat_colors = {
        "coding": ft.Colors.BLUE_400,
        "fast": ft.Colors.GREEN_400,
        "balanced": ft.Colors.ORANGE_400,
        "large": ft.Colors.PURPLE_400,
    }
    cat_color = cat_colors.get(model.get("category", ""), TH.accent)

    return ft.Container(
        content=ft.Column(
            [
                # Title & Category
                ft.Row(
                    [
                        ft.Text(
                            model["name"],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TH.text,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                model.get("category", "general").upper(),
                                size=9,
                                weight=ft.FontWeight.BOLD,
                                color="#ffffff",
                            ),
                            bgcolor=cat_color,
                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                            border_radius=4,
                        ),
                    ]
                ),
                # Description
                ft.Text(
                    model.get("description", ""),
                    size=12,
                    color=TH.dim,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Divider(height=1, color=TH.border),
                # Worth Metrics
                ft.Row(
                    [
                        _worth_badge(
                            ft.Icons.BOLT,
                            "Speed",
                            speed.split()[-1],
                            ft.Colors.AMBER_400,
                        ),
                        _worth_badge(ft.Icons.STAR, "Quality", quality, ft.Colors.YELLOW_600),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        _worth_badge(ft.Icons.MEMORY, "RAM", ram, ft.Colors.CYAN_400),
                        ft.Container(
                            content=ft.Text(
                                f"Size: {model.get('size_gb', 0)}GB",
                                size=10,
                                color=TH.muted,
                            ),
                            padding=ft.padding.only(left=8),
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(expand=True),
                # Action Button
                ft.Button(
                    "Download Model",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    style=ft.ButtonStyle(
                        color="#ffffff",
                        bgcolor={"": TH.accent, "hovered": TH.accent2},
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda _: on_download(model),
                    height=36,
                ),
            ],
            spacing=10,
        ),
        width=280,
        height=260,
        padding=16,
        bgcolor=TH.surface,
        border=ft.border.all(1, TH.border),
        border_radius=12,
        animate=ft.Animation(300, ft.AnimationCurve.DECELERATE),
    )


from src.version_checker import check_library_update


def build_marketplace_panel(page: ft.Page, state: any) -> ft.Container:
    """The main Marketplace panel."""

    def on_check_updates(e):
        # We'll check llama-cpp-python version (mocked version for demo if needed)
        try:
            from llama_cpp import __version__ as cpp_ver
        except ImportError:
            cpp_ver = "0.3.2"

        res = check_library_update(cpp_ver)
        if res["update_available"]:
            msg = f"Update available for llama-cpp-python: {res['latest']} (Current: {res['current']})"
        else:
            msg = "LLM Engine (llama-cpp-python) is up to date."

        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def on_download_click(model):
        repo = model.get("repo", "")
        filename = model.get("file", "")
        if not repo or not filename:
            page.snack_bar = ft.SnackBar(ft.Text("Missing repo/file info for this model."))
            page.snack_bar.open = True
            page.update()
            return

        page.snack_bar = ft.SnackBar(ft.Text(f"Downloading {model['name']} ({model.get('size_gb', '?')}GB)..."))
        page.snack_bar.open = True
        page.update()

        import threading
        def _do_download():
            try:
                mp = ModelMarketplace.get_instance()
                # Download to Config.MODELS_DIR or src/models
                import os
                target_dir = os.environ.get("MODELS_DIR") or str(__import__("pathlib").Path(__file__).parent.parent / "src" / "models")
                result = mp.download_model(repo, filename, target_dir=target_dir)
                if result.get("status") in ("completed", "exists"):
                    page.snack_bar = ft.SnackBar(ft.Text(f"✅ {model['name']} ready! Restart to use it."))
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(f"❌ Download failed: {result.get('error', 'unknown')}"))
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Download error: {e}"))
            page.snack_bar.open = True
            page.update()

        threading.Thread(target=_do_download, daemon=True).start()

    # Create cards for curated models
    cards = [_llm_card(m, on_download_click) for m in CURATED_MODELS]

    # Hardware Status Header
    mp = ModelMarketplace.get_instance()
    hw = mp.hardware
    hw_info = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.DASHBOARD_CUSTOMIZE_OUTLINED, color=TH.accent, size=24),
                ft.Column(
                    [
                        ft.Text(
                            "System Hardware Profile",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f"{hw.cpu_brand} • {hw.ram_gb:.1f}GB RAM • {hw.gpu_name}",
                            size=11,
                            color=TH.dim,
                        ),
                    ],
                    spacing=2,
                ),
                ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=ft.Text(
                        hw.tier_label,
                        size=12,
                        color="#ffffff",
                        weight=ft.FontWeight.W_600,
                    ),
                    bgcolor=f"{TH.accent}dd",
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    border_radius=20,
                ),
            ]
        ),
        padding=20,
        bgcolor=f"{TH.surface}77",
        border_radius=12,
        margin=ft.margin.only(bottom=20),
    )

    grid = ft.Row(
        controls=cards,
        wrap=True,
        spacing=20,
        run_spacing=20,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Model Marketplace",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=TH.text,
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Check for Engine Updates",
                            icon=ft.Icons.SYSTEM_UPDATE_ALT,
                            on_click=on_check_updates,
                        ),
                        ft.TextButton("Refresh Live Data", icon=ft.Icons.REFRESH),
                    ]
                ),
                ft.Text("Curated LLMs optimized for your hardware", size=14, color=TH.dim),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                hw_info,
                grid,
            ],
            expand=True,
        ),
        expand=True,
        padding=24,
    )
