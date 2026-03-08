# -*- coding: utf-8 -*-
"""
ui_flet/sidebar.py — Left Sidebar with Navigation Rail
========================================================

Provides the navigation sidebar: brand header, theme/language controls,
navigation panel buttons, source badge, and footer.
"""

from __future__ import annotations

import flet as ft

from ui_flet.theme import TH, MONO_FONT

APP_VERSION = "2.0.0"

# ── Panel definitions ─────────────────────────────────────────────────────────
PANELS = [
    ("chat", "🤖 Zena Chat", ft.Icons.CHAT_BUBBLE_OUTLINE),
    ("data", "📊 Your Data", ft.Icons.DATASET_OUTLINED),
    ("db", "🗄️ Database", ft.Icons.STORAGE_OUTLINED),
    ("cleanup", "🧹 Cleanup", ft.Icons.CLEANING_SERVICES_OUTLINED),
    ("cache", "💾 Cache", ft.Icons.CACHED_OUTLINED),
    ("eval", "📈 Evaluation", ft.Icons.INSIGHTS_OUTLINED),
    ("dedup", "🗑️ Dedup", ft.Icons.CONTENT_COPY_OUTLINED),
    ("dashboard", "⚖️ Judge", ft.Icons.GAVEL_OUTLINED),
    ("voice", "🎙️ Voice Lab", ft.Icons.MIC_OUTLINED),
]


def _brand_header() -> ft.Container:
    """Brand logo and version."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "ZenAI",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                    color=TH.accent,
                    font_family=MONO_FONT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "RAG ASSISTANT",
                    size=9,
                    color=TH.muted,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"v{APP_VERSION}",
                    size=10,
                    color=TH.muted,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        ),
        padding=ft.Padding.only(top=16, bottom=4),
    )


def _source_badge(source_name: str, source_type: str = "") -> ft.Container:
    """Active-source indicator badge."""
    if not source_name:
        return ft.Container()
    icon_map = {"web": "🌐", "folder": "📁", "email": "📧"}
    prefix = icon_map.get(source_type, "✅")
    display = source_name if len(source_name) <= 28 else "…" + source_name[-25:]
    return ft.Container(
        content=ft.Row(
            [
                ft.Text(prefix, size=14),
                ft.Text(
                    display,
                    size=10,
                    color=TH.accent,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=4,
        ),
        bgcolor=ft.Colors.with_opacity(0.08, TH.success),
        border_radius=8,
        padding=ft.Padding.symmetric(vertical=4, horizontal=8),
    )


def build_nav_rail(state: dict, on_panel_change) -> ft.Column:
    """Build the navigation panel button list."""
    active = state.get("active_panel", "chat")
    buttons = []
    for key, label, icon in PANELS:
        is_active = active == key
        buttons.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            icon,
                            size=18,
                            color=TH.accent if is_active else TH.muted,
                        ),
                        ft.Text(
                            label,
                            size=12,
                            color=TH.text if is_active else TH.muted,
                            weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                        ),
                    ],
                    spacing=8,
                ),
                bgcolor=ft.Colors.with_opacity(0.08, TH.accent) if is_active else ft.Colors.TRANSPARENT,
                border_radius=8,
                padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                on_click=lambda e, k=key: on_panel_change(k),
                ink=True,
            )
        )
    return ft.Column(buttons, spacing=2)


def __build_sidebar_part2_part2():
    """Continue _build_sidebar_part2 logic."""
    if on_settings or on_gallery:
        controls.append(ft.Container(expand=True))
        if on_gallery:
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=18, color=TH.muted),
                            ft.Text("Models", size=12, color=TH.muted),
                        ],
                        spacing=8,
                    ),
                    border_radius=8,
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    on_click=lambda e: on_gallery(),
                    ink=True,
                )
            )
        if on_settings:
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=18, color=TH.muted),
                            ft.Text("Settings", size=12, color=TH.muted),
                        ],
                        spacing=8,
                    ),
                    border_radius=8,
                    padding=ft.Padding.symmetric(vertical=8, horizontal=10),
                    on_click=lambda e: on_settings(),
                    ink=True,
                )
            )

    # Footer
    controls.extend(
        [
            ft.Container(expand=True) if not (on_settings or on_gallery) else ft.Container(),
            ft.Divider(color=TH.divider),
            ft.Text(
                "RAG · Qdrant · Local LLM · Voice",
                size=9,
                color=TH.muted,
                text_align=ft.TextAlign.CENTER,
            ),
        ]
    )

    return ft.Container(
        content=ft.Column(controls, scroll=ft.ScrollMode.AUTO, spacing=6),
        width=280,
        bgcolor=TH.surface,
        border=ft.Border.only(right=ft.BorderSide(1, TH.border)),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )


def _build_sidebar_part2(controls, has_data, source_name, source_type):
    """Continue build_sidebar logic."""
    if source_name:
        controls.append(_source_badge(source_name, source_type))
        controls.append(ft.Divider(color=TH.divider, height=8))

    # Navigation rail (only when data is loaded)
    if has_data:
        controls.append(nav_rail)

    # Settings & Model Gallery buttons
    return __build_sidebar_part2_part2()


def build_sidebar(
    page: ft.Page,
    state: dict,
    theme_icon: ft.Control,
    lang_dd: ft.Control,
    nav_rail: ft.Column,
    on_settings: callable = None,
    on_gallery: callable = None,
) -> ft.Container:
    """Build the complete left sidebar Container."""
    has_data = bool(state.get("rag_content"))

    controls = [
        _brand_header(),
        ft.Row(
            [
                theme_icon,
                ft.Icon(ft.Icons.LANGUAGE, size=16, color=TH.muted),
                lang_dd,
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Divider(color=TH.divider, height=12),
    ]

    # Source badge
    source_name = state.get("rag_source_name", "")
    source_type = state.get("rag_source_type", "")
    return _build_sidebar_part2(controls, has_data, source_name, source_type)


def build_theme_lang_controls(page: ft.Page, rebuild_fn):
    """Build theme toggle icon and language dropdown.

    Parameters
    ----------
    page : ft.Page
        The Flet page.
    rebuild_fn : callable
        Called (synchronously) after theme/lang change to rebuild the UI.

    Returns (theme_icon, lang_dd).
    """
    theme_icon = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE if TH.is_dark() else ft.Icons.DARK_MODE,
        icon_color=TH.accent,
        tooltip="Toggle Light / Dark",
        icon_size=20,
    )

    def on_theme_toggle(e):
        """Toggle the light/dark theme and rebuild the UI."""
        TH.toggle()
        rebuild_fn()

    theme_icon.on_click = on_theme_toggle

    lang_dd = ft.Dropdown(
        value="en",
        width=130,
        dense=True,
        border_color=TH.border,
        color=TH.text,
        options=[
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("ro", "Română"),
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("fr", "Français"),
            ft.dropdown.Option("hu", "Magyar"),
            ft.dropdown.Option("he", "עברית"),
        ],
    )

    def on_lang_change(e):
        """Switch the application language and rebuild the UI."""
        try:
            from ui.locales import set_language

            set_language(e.control.value)
        except ImportError:
            pass  # nosec B110 — optional locales module
        rebuild_fn()

    lang_dd.on_change = on_lang_change

    return theme_icon, lang_dd
