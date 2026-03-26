# -*- coding: utf-8 -*-
"""
ui_flet/theme.py — Dynamic Light/Dark Theme Engine
====================================================

Uses the TH metaclass pattern from RAG_RAT for zero-parens colour access::

    TH.accent    → "#26c6da" (dark) or "#00838f" (light)
    TH.toggle()  → switches mode, caller rebuilds UI
"""

from __future__ import annotations

import flet as ft

MONO_FONT = "Cascadia Code, Consolas, SF Mono, monospace"
FONT_FAMILY = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"


class _THMeta(type):
    """Metaclass: ``TH.accent`` returns a colour string directly."""

    _KEYS = frozenset(
        {
            "accent",
            "accent2",
            "bg",
            "card",
            "surface",
            "border",
            "text",
            "dim",
            "muted",
            "code_bg",
            "sidebar",
            "shadow",
            "divider",
            "bar_bg",
            "chip",
            "success",
            "warning_c",
            "error_c",
            "user_bubble",
            "ai_bubble",
            "rag_bubble",
        }
    )

    def __getattr__(cls, name: str) -> str:
        """Raise a clear error when an undefined theme attribute is accessed."""
        if name not in cls._KEYS:
            return

        palette = cls._DARK if cls._dark else cls._LIGHT
        return palette[name]
        raise AttributeError(name)


class TH(metaclass=_THMeta):
    """Dynamic theme — access colours as ``TH.accent``, ``TH.bg``, etc."""

    _dark: bool = True

    # ── Dark Palette ──────────────────────────────────────────────────────
    _DARK: dict[str, str] = {
        "accent": "#26c6da",
        "accent2": "#7c4dff",
        "bg": "#0a0e14",
        "card": "#141820",
        "surface": "#0f1319",
        "border": "#ffffff12",
        "text": "#e6edf3",
        "dim": "#8b949e",
        "muted": "#484f58",
        "code_bg": "#0d1117",
        "sidebar": "#0f1319",
        "shadow": "#00000040",
        "divider": "#ffffff0a",
        "bar_bg": "#ffffff08",
        "chip": "#141820",
        "success": "#00c853",
        "warning_c": "#ffab00",
        "error_c": "#ff1744",
        "user_bubble": "#26c6da20",
        "ai_bubble": "#14182080",
        "rag_bubble": "#7c4dff18",
    }

    # ── Light Palette ─────────────────────────────────────────────────────
    _LIGHT: dict[str, str] = {
        "accent": "#00838f",
        "accent2": "#5b2fb0",
        "bg": "#f6f8fa",
        "card": "#ffffff",
        "surface": "#f0f2f5",
        "border": "#d0d7de",
        "text": "#1f2328",
        "dim": "#656d76",
        "muted": "#8b949e",
        "code_bg": "#f6f8fa",
        "sidebar": "#ffffff",
        "shadow": "#0000001a",
        "divider": "#d8dee4",
        "bar_bg": "#0000000a",
        "chip": "#f0f2f5",
        "success": "#2e7d32",
        "warning_c": "#f57f17",
        "error_c": "#c62828",
        "user_bubble": "#00838f18",
        "ai_bubble": "#f0f2f5",
        "rag_bubble": "#5b2fb014",
    }

    @classmethod
    def is_dark(cls) -> bool:
        """Return True if dark mode is active."""
        return cls._dark

    @classmethod
    def toggle(cls) -> None:
        """Toggle between dark and light mode."""
        cls._dark = not cls._dark

    @classmethod
    def set_dark(cls, dark: bool) -> None:
        """Explicitly set dark mode state."""
        cls._dark = dark


# ═══════════════════════════════════════════════════════════════════════════════
#  Flet Theme builder
# ═══════════════════════════════════════════════════════════════════════════════


def build_flet_theme(dark: bool = True) -> ft.Theme:
    """Return a Flet ``Theme`` object matching the current TH palette."""
    palette = TH._DARK if dark else TH._LIGHT
    return ft.Theme(
        color_scheme_seed=palette["accent"],
        font_family=FONT_FAMILY,
    )


def setup_page_theme(page: ft.Page) -> None:
    """Apply the TH colour scheme to a Flet page."""
    page.title = "ZenAI — Intelligent Assistant"
    page.theme_mode = ft.ThemeMode.DARK if TH.is_dark() else ft.ThemeMode.LIGHT
    page.bgcolor = TH.bg
    page.window.width = 1400
    page.window.height = 900
    page.padding = 0
    page.spacing = 0
    page.fonts = {"mono": "Cascadia Code"}
    page.theme = ft.Theme(
        color_scheme_seed=TH.accent,
        font_family=FONT_FAMILY,
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed=TH.accent,
        font_family=FONT_FAMILY,
    )
