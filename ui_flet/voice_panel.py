# -*- coding: utf-8 -*-
"""
ui_flet/voice_panel.py — Voice Controls & Diagnostics
=======================================================

Voice recording, TTS playback, microphone diagnostics.
Uses the backend voice WebSocket on port 8006 and TTS API on port 8002.
"""

from __future__ import annotations

import logging

import flet as ft

from ui_flet.theme import TH
from ui_flet.widgets import glass_card, section_title, spacer

logger = logging.getLogger(__name__)


def build_voice_controls(
    page: ft.Page,
    state: dict,
    on_voice_toggle=None,
) -> ft.Container:
    """Compact voice control bar for the chat footer area."""
    recording = state.get("voice_recording", False)

    mic_btn = ft.IconButton(
        icon=ft.Icons.MIC_OFF if not recording else ft.Icons.MIC,
        icon_color=TH.error_c if recording else TH.muted,
        tooltip="Toggle voice recording",
        on_click=on_voice_toggle,
    )

    rec_indicator = ft.Row(
        [
            ft.Container(
                bgcolor=TH.error_c,
                border_radius=6,
                width=12,
                height=12,
            ),
            ft.Text("REC", size=10, color=TH.error_c, weight=ft.FontWeight.BOLD),
        ],
        spacing=4,
        visible=recording,
    )

    return ft.Container(
        content=ft.Row([mic_btn, rec_indicator], spacing=4),
    )


def __build_voice_lab_panel_part2_part2(client, resp):
    """Continue _build_voice_lab_panel_part2 logic."""

    async def on_check_devices(e):
        """Enumerate audio devices and display results."""
        status_text.value = "🔍 Checking audio devices…"
        page.update()
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get("http://127.0.0.1:8002/api/devices", timeout=10)
                if resp.status_code == 200:
                    devices = resp.json()
                    result_text.value = (
                        "\n".join(
                            f"  {d.get('name', '?')} ({'input' if d.get('input') else 'output'})"
                            for d in devices.get("devices", [])
                        )
                        or "No devices found"
                    )
                    status_text.value = f"✅ Found {len(devices.get('devices', []))} devices"
                    status_text.color = TH.success
                else:
                    status_text.value = "❌ Could not list devices"
                    status_text.color = TH.error_c
        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
            status_text.color = TH.error_c
        page.update()

    return ft.Column(
        [
            section_title("Voice Lab", "🎙️"),
            ft.Text("Test voice recording, TTS, and audio devices.", size=12, color=TH.muted),
            spacer(12),
            # Recording section
            glass_card(
                ft.Column(
                    [
                        ft.Text("🎤 Speech-to-Text", size=14, weight=ft.FontWeight.BOLD, color=TH.text),
                        ft.Row(
                            [
                                duration_field,
                                ft.Button(
                                    "🎙️ Record",
                                    on_click=lambda e: page.run_task(on_record, e),
                                    bgcolor=TH.error_c,
                                    color=ft.Colors.WHITE,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            spacer(8),
            # TTS section
            glass_card(
                ft.Column(
                    [
                        ft.Text("🔊 Text-to-Speech", size=14, weight=ft.FontWeight.BOLD, color=TH.text),
                        ft.Button(
                            "🔊 Test TTS",
                            on_click=lambda e: page.run_task(on_tts_test, e),
                            bgcolor=TH.accent,
                            color=ft.Colors.WHITE,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            spacer(8),
            # Device info
            glass_card(
                ft.Column(
                    [
                        ft.Text("🎧 Audio Devices", size=14, weight=ft.FontWeight.BOLD, color=TH.text),
                        ft.Button(
                            "🔍 Check Devices",
                            on_click=lambda e: page.run_task(on_check_devices, e),
                            bgcolor=TH.accent2,
                            color=ft.Colors.WHITE,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            spacer(12),
            # Status & results
            status_text,
            result_text,
        ],
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


def _build_voice_lab_panel_part2(duration_field, result_text, status_text):
    """Continue build_voice_lab_panel logic."""

    async def on_record(e):
        """Toggle audio recording and process the result."""
        status_text.value = "🎙️ Recording…"
        status_text.color = TH.error_c
        page.update()

        try:
            duration = int(duration_field.value or "5")
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://127.0.0.1:8002/api/stt",
                    json={"duration": duration},
                    timeout=duration + 30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    transcription = data.get("text", "")
                    result_text.value = f"Transcription: {transcription}"
                    status_text.value = "✅ Recording complete"
                    status_text.color = TH.success
                else:
                    status_text.value = f"❌ STT failed: {resp.status_code}"
                    status_text.color = TH.error_c
        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
            status_text.color = TH.error_c
        page.update()

    async def on_tts_test(e):
        """Generate and play a text-to-speech sample."""
        status_text.value = "🔊 Generating speech…"
        page.update()
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://127.0.0.1:8002/api/tts",
                    json={"text": "Hello! I am Zena, your AI assistant."},
                    timeout=30,
                )
                if resp.status_code == 200:
                    status_text.value = "✅ TTS playback complete"
                    status_text.color = TH.success
                else:
                    status_text.value = f"❌ TTS failed: {resp.status_code}"
                    status_text.color = TH.error_c
        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
            status_text.color = TH.error_c
        page.update()

    # Mic diagnostics
    return __build_voice_lab_panel_part2_part2(client, resp)


def build_voice_lab_panel(page: ft.Page, state: dict) -> ft.Column:
    """Full voice lab panel with recording, playback, and diagnostics."""
    status_text = ft.Text("Ready", size=12, color=TH.dim)
    result_text = ft.Text("", size=12, color=TH.text, selectable=True)

    # Recording controls
    duration_field = ft.TextField(
        label="Duration (s)",
        value="5",
        width=100,
        border_color=TH.border,
        color=TH.text,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    return _build_voice_lab_panel_part2(duration_field, result_text, status_text)
