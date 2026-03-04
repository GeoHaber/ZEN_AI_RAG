# -*- coding: utf-8 -*-
"""
ui_flet/widgets.py — Shared reusable Flet widgets
===================================================

Provides glassmorphism cards, metric tiles, section headers,
bar charts, badges, and other building blocks used across panels.
"""

from __future__ import annotations

import flet as ft

from ui_flet.theme import TH, MONO_FONT


# ═══════════════════════════════════════════════════════════════════════════════
#  GLASS CARD
# ═══════════════════════════════════════════════════════════════════════════════

def glass_card(
    content: ft.Control,
    padding: int = 20,
    expand: bool = False,
    **kwargs,
) -> ft.Container:
    """Glassmorphism-style card with subtle border and shadow."""
    return ft.Container(
        content=content,
        bgcolor=TH.card,
        border=ft.Border.all(1, TH.border),
        border_radius=16,
        padding=padding,
        expand=expand,
        shadow=ft.BoxShadow(blur_radius=8, color=TH.shadow),
        **kwargs,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  METRIC TILE
# ═══════════════════════════════════════════════════════════════════════════════

def metric_tile(
    icon: str,
    value: str | int | float,
    label: str,
    color: str | None = None,
) -> ft.Container:
    """Compact icon + value + label tile for dashboards."""
    color = color or TH.accent
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(icon, size=24, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    str(value),
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                    font_family=MONO_FONT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    label,
                    size=10,
                    color=TH.dim,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        bgcolor=TH.card,
        border=ft.Border.all(1, TH.border),
        border_radius=14,
        padding=ft.Padding.symmetric(vertical=14, horizontal=10),
        expand=True,
        shadow=ft.BoxShadow(blur_radius=6, color=TH.shadow),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION TITLE
# ═══════════════════════════════════════════════════════════════════════════════

def section_title(text: str, icon: str = "") -> ft.Text:
    """Bold accent-coloured section header with optional emoji."""
    display = f"{icon}  {text}" if icon else text
    return ft.Text(
        display,
        size=15,
        weight=ft.FontWeight.BOLD,
        color=TH.accent,
        font_family=MONO_FONT,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  BAR ROW
# ═══════════════════════════════════════════════════════════════════════════════

def bar_row(label: str, count: int, max_count: int, color: str) -> ft.Row:
    """Horizontal bar chart row for data visualisations."""
    pct = count / max(max_count, 1)
    return ft.Row(
        [
            ft.Text(
                label,
                size=12,
                width=200,
                font_family=MONO_FONT,
                color=TH.dim,
                no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Container(
                content=ft.Container(
                    bgcolor=color,
                    border_radius=4,
                    width=max(4, pct * 350),
                    height=14,
                ),
                bgcolor=TH.bar_bg,
                border_radius=4,
                width=350,
                height=14,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
            ft.Text(
                str(count),
                size=12,
                weight=ft.FontWeight.BOLD,
                font_family=MONO_FONT,
                width=50,
                color=TH.text,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  BADGE
# ═══════════════════════════════════════════════════════════════════════════════

def badge(
    text: str,
    color: str | None = None,
    bg_color: str | None = None,
) -> ft.Container:
    """Pill-shaped badge for tags and status indicators."""
    color = color or TH.text
    bg_color = bg_color or TH.chip
    return ft.Container(
        content=ft.Text(text, size=10, color=color, weight=ft.FontWeight.BOLD),
        bgcolor=bg_color,
        border_radius=12,
        padding=ft.Padding.symmetric(vertical=2, horizontal=8),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  ADDITIONAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def themed_text_field(
    label: str = "",
    hint_text: str = "",
    prefix_icon: str | None = None,
    **kwargs,
) -> ft.TextField:
    """Pre-themed TextField matching ZenAI design."""
    return ft.TextField(
        label=label,
        hint_text=hint_text,
        prefix_icon=prefix_icon,
        border_color=TH.border,
        color=TH.text,
        focused_border_color=TH.accent,
        **kwargs,
    )


def num_field(label: str, value: str = "50", width: int = 100) -> ft.TextField:
    """Compact numeric input field."""
    return ft.TextField(
        label=label,
        value=value,
        width=width,
        border_color=TH.border,
        color=TH.text,
        keyboard_type=ft.KeyboardType.NUMBER,
    )


def snack(page: ft.Page, message: str, color: str | None = None) -> None:
    """Show a transient snackbar notification."""
    bar = ft.SnackBar(content=ft.Text(message), open=True)
    if color:
        bar.bgcolor = color
    page.overlay.append(bar)
    page.update()


def accent_button(
    text: str,
    on_click=None,
    icon: str | None = None,
    color: str | None = None,
    width: int = 260,
) -> ft.ElevatedButton:
    """Primary action button with accent styling."""
    return ft.ElevatedButton(
        text=text,
        on_click=on_click,
        icon=icon,
        bgcolor=color or TH.accent,
        color=ft.Colors.WHITE,
        width=width,
        height=42,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )


def spacer(height: int = 8) -> ft.Container:
    """Vertical spacer."""
    return ft.Container(height=height)
