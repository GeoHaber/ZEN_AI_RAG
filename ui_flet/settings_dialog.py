# -*- coding: utf-8 -*-
"""
ui_flet/settings_dialog.py — Settings Panel (8 categories)
============================================================

Full settings panel with Language, Appearance, AI Model, External LLMs,
Voice, RAG, Chat, and System configuration sections.
"""

from __future__ import annotations

import logging

import flet as ft

from ui_flet.theme import TH
from ui_flet.persistence import save_settings

logger = logging.getLogger(__name__)


def _settings_section(title: str, icon: str, controls: list[ft.Control]) -> ft.ExpansionTile:
    """Wrap controls in a themed ExpansionTile."""
    return ft.ExpansionTile(
        title=ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=TH.text),
        leading=ft.Icon(icon, color=TH.accent, size=20),
        controls=[
            ft.Container(
                content=ft.Column(controls, spacing=10),
                padding=ft.Padding.symmetric(vertical=8, horizontal=16),
            )
        ],
        initially_expanded=False,
    )


def ___build_settings_dialog_part2_part2_part2(chat_section, system_section):
    """Continue __build_settings_dialog_part2_part2 logic."""

    def on_close(e):
        """Close the settings dialog without saving."""
        page.close(dlg)

    def on_save_click(e):
        """Persist widget values to state and save to disk."""
        state["council_mode"] = council_switch.value
        state["deep_thinking"] = deep_switch.value
        state["quiet_cot"] = quiet_cot_switch.value
        state["tts_enabled"] = tts_switch.value
        state["rag_enabled"] = rag_switch.value
        state["dark_mode"] = dark_switch.value
        state["language"] = lang_dd.value
        save_settings(state)
        if on_save:
            on_save()
        page.close(dlg)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.SETTINGS, color=TH.accent),
                ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD, color=TH.text),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_color=TH.muted, on_click=on_close),
            ]
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    lang_section,
                    appearance_section,
                    model_section,
                    external_section,
                    voice_section,
                    rag_section,
                    chat_section,
                    system_section,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=4,
            ),
            width=600,
            height=500,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=on_close),
            ft.Button("Save", on_click=on_save_click, bgcolor=TH.accent, color=ft.Colors.WHITE),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=16),
    )
    return dlg


def __build_settings_dialog_part2_part2(chat_controls, rag_section, rag_switch, tts_switch, voice_section):
    """Continue _build_settings_dialog_part2 logic."""
    chat_section = _settings_section("Chat", ft.Icons.CHAT_OUTLINED, chat_controls)

    # ── 8. System ────────────────────────────────────────────────────────
    system_controls = [
        ft.TextField(
            label="API Port",
            value=str(getattr(config, "mgmt_port", 8002)) if config else "8002",
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.TextField(
            label="Models Directory",
            value=str(getattr(config, "MODEL_DIR", str(Path(__file__).resolve().parent.parent / "models"))) if config else str(Path(__file__).resolve().parent.parent / "models"),
            border_color=TH.border,
            color=TH.text,
        ),
        ft.Switch(label="Check for Updates", value=True),
        ft.Switch(label="Auto-Start Backend", value=True),
        ft.Dropdown(
            label="Log Level",
            value="INFO",
            width=160,
            border_color=TH.border,
            color=TH.text,
            options=[ft.dropdown.Option(lv) for lv in ["DEBUG", "INFO", "WARNING", "ERROR"]],
        ),
    ]
    system_section = _settings_section("System", ft.Icons.SETTINGS_OUTLINED, system_controls)

    # ── Dialog ────────────────────────────────────────────────────────────
    return ___build_settings_dialog_part2_part2_part2(chat_section, system_section)


def _build_settings_dialog_part2(
    appearance_section,
    config,
    council_switch,
    dark_switch,
    deep_switch,
    external_section,
    lang_dd,
    lang_section,
    model_section,
    quiet_cot_switch,
):
    """Continue build_settings_dialog logic."""
    tts_switch = ft.Switch(label="Text-to-Speech Enabled", value=state.get("tts_enabled", False))
    voice_controls = [
        tts_switch,
        ft.Slider(min=0.5, max=2.0, value=1.0, divisions=15, label="Voice Speed: {value}x"),
        ft.Switch(label="Auto-Speak Responses", value=False),
        ft.TextField(
            label="Recording Duration (s)",
            value="5",
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
    ]
    voice_section = _settings_section("Voice", ft.Icons.RECORD_VOICE_OVER_OUTLINED, voice_controls)

    # ── 6. RAG ───────────────────────────────────────────────────────────
    rag_switch = ft.Switch(label="RAG Enabled", value=state.get("rag_enabled", True))
    rag_controls = [
        rag_switch,
        ft.TextField(
            label="Chunk Size",
            value=str(getattr(config, "rag", None) and config.rag.chunk_size or 500),
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.TextField(
            label="Similarity Threshold",
            value="0.95",
            width=140,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.TextField(
            label="Max Results",
            value="10",
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.Switch(label="Auto-Index on Scan", value=True),
    ]
    rag_section = _settings_section("RAG Pipeline", ft.Icons.LIBRARY_BOOKS_OUTLINED, rag_controls)

    # ── 7. Chat ──────────────────────────────────────────────────────────
    chat_controls = [
        ft.Switch(label="Show Timestamps", value=False),
        ft.Switch(label="Auto-Scroll", value=True),
        ft.Switch(label="Stream Responses", value=True),
        ft.Switch(label="Show Token Count", value=False),
        ft.Switch(label="Save Conversations", value=True),
        ft.TextField(
            label="History Days",
            value="30",
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
    ]
    return __build_settings_dialog_part2_part2(chat_controls, rag_section, rag_switch, tts_switch, voice_section)


def _build_settings_dialog_part2(
    appearance_section, config, council_switch, dark_switch, lang_dd, lang_section, model_controls
):
    """Continue build_settings_dialog logic."""
    deep_switch = ft.Switch(label="Deep Thinking (CoT)", value=state.get("deep_thinking", False))
    quiet_cot_switch = ft.Switch(label="Quiet CoT", value=state.get("quiet_cot", False))
    model_controls.extend([council_switch, deep_switch, quiet_cot_switch])
    model_section = _settings_section("AI Model", ft.Icons.SMART_TOY_OUTLINED, model_controls)

    # ── 4. External LLMs ────────────────────────────────────────────────
    external_controls = [
        ft.Switch(label="Enable External LLMs", value=False),
        ft.TextField(
            label="Anthropic API Key",
            hint_text="sk-ant-…",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            border_color=TH.border,
            color=TH.text,
        ),
        ft.TextField(
            label="Google API Key",
            hint_text="AIza…",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            border_color=TH.border,
            color=TH.text,
        ),
        ft.TextField(
            label="Grok API Key",
            hint_text="xai-…",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            border_color=TH.border,
            color=TH.text,
        ),
    ]
    external_section = _settings_section("External LLMs", ft.Icons.CLOUD_OUTLINED, external_controls)

    # ── 5. Voice ─────────────────────────────────────────────────────────
    return _build_settings_dialog_part2(
        appearance_section,
        config,
        council_switch,
        dark_switch,
        deep_switch,
        external_section,
        lang_dd,
        lang_section,
        model_section,
        quiet_cot_switch,
    )


def _build_settings_dialog_part2(config, dark_switch, lang_dd, lang_section):
    """Continue build_settings_dialog logic."""
    appearance_section = _settings_section(
        "Appearance",
        ft.Icons.PALETTE_OUTLINED,
        [
            dark_switch,
            ft.Text("Toggle between dark and light themes", size=11, color=TH.muted),
        ],
    )

    # ── 3. AI Model ──────────────────────────────────────────────────────
    model_controls = [
        ft.TextField(
            label="Default Model",
            value=getattr(config, "default_model", "model.gguf") if config else "model.gguf",
            border_color=TH.border,
            color=TH.text,
        ),
        ft.TextField(
            label="Temperature",
            value="0.7",
            width=120,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.TextField(
            label="Max Tokens",
            value="2048",
            width=140,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        ft.TextField(
            label="Context Window",
            value=str(getattr(config, "context_size", 4096)) if config else "4096",
            width=140,
            border_color=TH.border,
            color=TH.text,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
    ]
    council_switch = ft.Switch(label="Council / Swarm Mode", value=state.get("council_mode", False))
    return _build_settings_dialog_part2(
        appearance_section, config, council_switch, dark_switch, lang_dd, lang_section, model_controls
    )


def build_settings_dialog(
    page: ft.Page,
    state: dict,
    on_save=None,
    on_theme_toggle=None,
    on_language_change=None,
) -> ft.AlertDialog:
    """Build the 8-category settings dialog.

    Parameters
    ----------
    page : ft.Page
        The Flet page.
    state : dict
        Shared application state.
    on_save : callable
        Called when user clicks Save.
    on_theme_toggle : callable
        Called when dark mode is toggled.
    on_language_change : callable
        Called with new language code.
    """
    try:
        from config_system import config
    except ImportError:
        config = None

    # ── 1. Language ───────────────────────────────────────────────────────
    lang_dd = ft.Dropdown(
        label="UI Language",
        value="en",
        width=200,
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
        on_change=lambda e: on_language_change(e.control.value) if on_language_change else None,
    )
    lang_section = _settings_section(
        "Language",
        ft.Icons.TRANSLATE,
        [
            lang_dd,
            ft.Text("Choose the interface language", size=11, color=TH.muted),
        ],
    )

    # ── 2. Appearance ────────────────────────────────────────────────────
    dark_switch = ft.Switch(
        label="Dark Mode",
        value=TH.is_dark(),
        on_change=lambda e: on_theme_toggle() if on_theme_toggle else None,
    )
    return _build_settings_dialog_part2(config, dark_switch, lang_dd, lang_section)
