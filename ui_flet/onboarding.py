# -*- coding: utf-8 -*-
"""
ui_flet/onboarding.py — First-run onboarding wizard
=====================================================

3-step tutorial dialog shown on first launch.
"""

from __future__ import annotations

import flet as ft

from ui_flet.theme import TH

_STEPS = [
    (
        "Choose Your Source",
        "Paste a website URL, pick a local folder, or connect your email to scan.",
        ft.Icons.LANGUAGE,
    ),
    ("Scan & Index", "Hit Scan — we'll extract, chunk, embed, and index your data locally.", ft.Icons.SEARCH),
    ("Ask Zena", "Chat with your data using RAG-powered intelligent answers.", ft.Icons.CHAT_BUBBLE_OUTLINE),
]


def _show_onboarding_part2(desc_text, icon_ctrl, step_idx, step_ind, title_text):
    """Continue show_onboarding logic."""

    def on_next(e):
        """Advance to the next onboarding step."""
        if step_idx[0] >= len(_STEPS) - 1:
            page.close(dlg)
            return
        step_idx[0] += 1
        _update()

    def on_back(e):
        """Return to the previous onboarding step."""
        if step_idx[0] <= 0:
            return

        step_idx[0] -= 1
        _update()

    back_btn = ft.TextButton("← Back", on_click=on_back, visible=False)
    next_btn = ft.Button(
        "Next →",
        on_click=on_next,
        bgcolor=TH.accent,
        color=ft.Colors.WHITE,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "🧠 Welcome to ZenAI",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=TH.accent,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row([icon_ctrl], alignment=ft.MainAxisAlignment.CENTER),
                    title_text,
                    desc_text,
                    step_ind,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=420,
            height=220,
        ),
        actions=[back_btn, next_btn],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=16),
    )

    page.open(dlg)


def show_onboarding(page: ft.Page) -> None:
    """Display the 3-step onboarding wizard dialog."""
    step_idx = [0]

    title_text = ft.Text(
        _STEPS[0][0],
        size=20,
        weight=ft.FontWeight.BOLD,
        color=TH.accent,
    )
    desc_text = ft.Text(_STEPS[0][1], size=14, color=TH.dim)
    icon_ctrl = ft.Icon(_STEPS[0][2], size=48, color=TH.accent)
    step_ind = ft.Text(f"1 / {len(_STEPS)}", size=12, color=TH.muted)

    def _update():
        """Refresh the onboarding step content and button states."""
        t, d, ic = _STEPS[step_idx[0]]
        title_text.value = t
        desc_text.value = d
        icon_ctrl.name = ic
        step_ind.value = f"{step_idx[0] + 1} / {len(_STEPS)}"
        back_btn.visible = step_idx[0] > 0
        next_btn.text = "Got it!" if step_idx[0] >= len(_STEPS) - 1 else "Next →"
        page.update()

    _show_onboarding_part2(desc_text, icon_ctrl, step_idx, step_ind, title_text)
