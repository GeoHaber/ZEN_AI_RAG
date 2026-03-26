"""Gateways panel — Telegram / WhatsApp bot toggles."""

from __future__ import annotations

import flet as ft

from ui_flet.theme import TH


def build_gateways_panel(page: ft.Page, state, backend=None) -> ft.Container:
    """Panel for starting/stopping Telegram & WhatsApp gateways."""
    tg_status = ft.Text("Stopped", size=12, color=TH.dim)
    wa_status = ft.Text("Stopped", size=12, color=TH.dim)
    log_view = ft.ListView(controls=[], expand=True, spacing=4, auto_scroll=True)

    def _log(msg: str):
        log_view.controls.append(ft.Text(msg, size=11, color=TH.dim))
        if len(log_view.controls) > 200:
            log_view.controls = log_view.controls[-100:]
        page.update()

    async def _toggle_telegram(e):
        enabled = e.control.value
        if hasattr(state, "telegram_enabled"):
            state.telegram_enabled = enabled
        if enabled:
            tg_status.value = "Starting…"
            tg_status.color = TH.accent
            page.update()
            try:
                if backend and hasattr(backend, "start_gateways"):
                    await backend.start_gateways(telegram=True, whatsapp=False)
                tg_status.value = "Running"
                _log("Telegram gateway started")
            except Exception as exc:
                tg_status.value = f"Error: {exc}"
                tg_status.color = TH.error_c if hasattr(TH, "error_c") else "#ff4444"
                _log(f"Telegram error: {exc}")
        else:
            tg_status.value = "Stopped"
            tg_status.color = TH.dim
            _log("Telegram gateway stopped")
        page.update()

    async def _toggle_whatsapp(e):
        enabled = e.control.value
        if hasattr(state, "whatsapp_enabled"):
            state.whatsapp_enabled = enabled
        if enabled:
            wa_status.value = "Starting…"
            wa_status.color = TH.accent
            page.update()
            try:
                if backend and hasattr(backend, "start_gateways"):
                    await backend.start_gateways(telegram=False, whatsapp=True)
                wa_status.value = "Running"
                _log("WhatsApp gateway started")
            except Exception as exc:
                wa_status.value = f"Error: {exc}"
                wa_status.color = TH.error_c if hasattr(TH, "error_c") else "#ff4444"
                _log(f"WhatsApp error: {exc}")
        else:
            wa_status.value = "Stopped"
            wa_status.color = TH.dim
            _log("WhatsApp gateway stopped")
        page.update()

    tg_switch = ft.Switch(
        label="Telegram Bot",
        value=getattr(state, "telegram_enabled", False),
        on_change=_toggle_telegram,
    )
    wa_switch = ft.Switch(
        label="WhatsApp Bot",
        value=getattr(state, "whatsapp_enabled", False),
        on_change=_toggle_whatsapp,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Gateways", size=16, weight=ft.FontWeight.W_600, color=TH.text),
                ft.Text("Connect Zena to messaging platforms.", size=12, color=TH.dim),
                ft.Container(height=12),
                ft.Row([tg_switch, tg_status], spacing=12),
                ft.Row([wa_switch, wa_status], spacing=12),
                ft.Divider(color=TH.divider, height=16),
                ft.Text("Gateway Log", size=13, weight=ft.FontWeight.W_500, color=TH.text),
                log_view,
            ],
            expand=True,
            spacing=8,
        ),
        expand=True,
        padding=20,
    )
