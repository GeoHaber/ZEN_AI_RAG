# -*- coding: utf-8 -*-
"""
ui/source_config.py — Welcome screen + source scanning panels (Flet)
"""

from __future__ import annotations
import asyncio
import logging
import flet as ft

from ui.theme import TH
from ui.state import (
    AppState,
    scan_web as _scan_web_state,
    scan_folder as _scan_folder_state,
    normalize_url,
    is_valid_url,
)

# Fallback: import directly if state's try/except swallowed the import
if _scan_web_state is None:
    try:
        from content_extractor import scan_web as _scan_web_state
    except Exception:
        pass
if _scan_folder_state is None:
    try:
        from content_extractor import scan_folder as _scan_folder_state
    except Exception:
        pass

scan_web = _scan_web_state
scan_folder = _scan_folder_state

logger = logging.getLogger(__name__)


def build_config_panel(page: ft.Page, state: AppState, on_rebuild) -> ft.Container:
    """Unified 'Collect Data for RAG' panel matching RAG_RAT Pro layout."""

    # Header & Intro
    header = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.BOOK_OUTLINED, color=TH.accent, size=24),
                    ft.Text("Collect Data for RAG", size=24, weight="bold", color=TH.text),
                ],
                spacing=10,
            ),
            ft.Text(
                "Select the type of source you want to RAG. Each option has its own input, validation, and max items setting.",
                size=13,
                color=TH.dim,
            ),
        ],
        spacing=8,
    )

    # Source Selection (ChoiceChips)
    source_choices = [
        ("web", "Web", ft.Icons.LANGUAGE),
        ("folder", "Local Files", ft.Icons.FOLDER_OPEN),
        ("email", "Email", ft.Icons.EMAIL_OUTLINED),
        ("social", "Social", ft.Icons.PEOPLE_OUTLINE),
        ("api", "API", ft.Icons.TERMINAL),
    ]

    def on_source_select(e):
        label_text = e.control.label.value if hasattr(e.control.label, "value") else str(e.control.label)
        state.selected_source = label_text.lower().replace(" ", "")
        if "localfiles" in state.selected_source:
            state.selected_source = "folder"
        on_rebuild()

    chips = ft.Row(
        [
            ft.Chip(
                label=ft.Text(label),
                on_click=on_source_select,
                selected=state.selected_source == key,
                leading=ft.Icon(icon, size=16),
                selected_color=TH.accent,
            )
            for key, label, icon in source_choices
        ],
        spacing=15,
    )

    # Specific Config Forms
    config_form = ft.Container(padding=ft.padding.only(top=20))
    source = state.selected_source or "web"  # Default to web

    progress_bar = ft.ProgressBar(visible=False, color=TH.accent, height=2)
    status_text = ft.Text("", size=12, color=TH.dim)

    if source == "web":
        url_field = ft.TextField(
            label="Web Address",
            value=state.last_url or "",
            hint_text="e.g. example.com or https://docs.example.com",
            prefix_icon=ft.Icons.LANGUAGE,
            expand=True,
            border_radius=8,
            border_color=TH.border,
            text_size=14,
        )
        limit_field = ft.TextField(
            label="Max Pages to Read",
            value="10",
            width=120,
            border_radius=8,
            border_color=TH.border,
            text_size=14,
        )

        async def on_start_web(e):
            url = normalize_url(url_field.value)
            if not is_valid_url(url):
                status_text.value = "Invalid URL"
                page.update()
                return
            if scan_web is None:
                status_text.value = "Error: content_extractor not loaded (check imports)"
                page.update()
                return
            state.last_url = url
            progress_bar.visible = True
            status_text.value = "Starting web ingestion..."
            page.update()
            try:
                text, images, sources = await asyncio.to_thread(scan_web, url, max_pages=int(limit_field.value))
                state.rag_content = text
                state.rag_sources = sources
                state.rag_images = images
                state.rag_source_name = url
                status_text.value = f"Success: {len(sources)} pages indexed."
                on_rebuild()
            except Exception as ex:
                logger.exception("Web ingestion failed")
                status_text.value = f"Error: {ex}"
            progress_bar.visible = False
            page.update()

        config_form.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LANGUAGE, color=TH.accent, size=20),
                        ft.Text("Web Source", size=18, weight="bold"),
                    ]
                ),
                ft.Text(
                    "Enter a web address and press START. The URL will be validated automatically.",
                    size=12,
                    color=TH.dim,
                ),
                url_field,
                ft.Row([limit_field, ft.Container(expand=True)]),
                ft.Button(
                    "▶ START Web RAG",
                    bgcolor=TH.accent,
                    color="white",
                    on_click=on_start_web,
                    height=40,
                ),
            ],
            spacing=15,
        )

    elif source == "folder":
        path_field = ft.TextField(
            label="Directory Path",
            hint_text="C:\\Documents\\Data",
            prefix_icon=ft.Icons.FOLDER_OPEN,
            expand=True,
            border_radius=8,
            border_color=TH.border,
            text_size=14,
        )

        async def on_start_folder(e):
            path = path_field.value
            if scan_folder is None:
                status_text.value = "Error: content_extractor not loaded (check imports)"
                page.update()
                return
            progress_bar.visible = True
            page.update()
            try:
                text, images, sources = await asyncio.to_thread(scan_folder, path)
                state.rag_content = text
                state.rag_sources = sources
                state.rag_images = images
                state.rag_source_name = path
                on_rebuild()
            except Exception as ex:
                logger.exception("Folder ingestion failed")
                status_text.value = f"Error: {ex}"
            progress_bar.visible = False
            page.update()

        config_form.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FOLDER_OPEN, color=TH.accent, size=20),
                        ft.Text("Local Files", size=18, weight="bold"),
                    ]
                ),
                ft.Text(
                    "Point to a folder on your computer to index its contents.",
                    size=12,
                    color=TH.dim,
                ),
                path_field,
                ft.Button(
                    "▶ START Local RAG",
                    bgcolor=TH.accent,
                    color="white",
                    on_click=on_start_folder,
                    height=40,
                ),
            ],
            spacing=15,
        )

    elif source == "email":
        state.selected_email_subsource = getattr(state, "selected_email_subsource", "online")

        def on_email_subsource_select(e):
            label_text = e.control.label.value if hasattr(e.control.label, "value") else str(e.control.label)
            state.selected_email_subsource = "online" if "Online" in label_text else "local"
            on_rebuild()

        email_forms = {
            "online": ft.Column(
                [
                    ft.TextField(label="IMAP Server", value="imap.gmail.com"),
                    ft.TextField(label="Email Address", hint_text="user@gmail.com"),
                    ft.TextField(label="App Password", password=True, can_reveal_password=True),
                    ft.Button("Connect & Scan", bgcolor=TH.accent, color="white"),
                ],
                spacing=10,
            ),
            "local": ft.Column(
                [
                    ft.TextField(label="Path to .eml or .mbox", hint_text="C:\\MailArchives"),
                    ft.Button("Scan Local Mail", bgcolor=TH.accent, color="white"),
                ],
                spacing=10,
            ),
        }

        email_selector = ft.Row(
            [
                ft.Chip(
                    label=ft.Text("Online (IMAP)"),
                    on_click=on_email_subsource_select,
                    selected=state.selected_email_subsource == "online",
                    selected_color=TH.accent,
                ),
                ft.Chip(
                    label=ft.Text("Local Files"),
                    on_click=on_email_subsource_select,
                    selected=state.selected_email_subsource == "local",
                    selected_color=TH.accent,
                ),
            ],
            spacing=10,
        )

        config_form.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.EMAIL_OUTLINED, color=TH.accent, size=20),
                        ft.Text("Email Source", size=18, weight="bold"),
                    ]
                ),
                ft.Text(
                    "Connect to Gmail, Outlook or scan local .eml/.mbox files.",
                    size=12,
                    color=TH.dim,
                ),
                email_selector,
                email_forms[state.selected_email_subsource],
            ],
            spacing=15,
        )

    elif source == "social":
        platform_dd = ft.Dropdown(
            label="Platform",
            options=[
                ft.dropdown.Option("WhatsApp"),
                ft.dropdown.Option("Telegram"),
                ft.dropdown.Option("Discord"),
            ],
            width=150,
        )
        config_form.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=TH.accent, size=20),
                        ft.Text("Social Media Source", size=18, weight="bold"),
                    ]
                ),
                ft.Text(
                    "Scan exported chat logs or connect via Live API.",
                    size=12,
                    color=TH.dim,
                ),
                ft.Row([platform_dd, ft.TextField(label="Export Path", expand=True)]),
                ft.Button("▶ Start Social Scan", bgcolor=TH.accent, color="white"),
            ],
            spacing=15,
        )

    elif source == "api":
        config_form.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.TERMINAL, color=TH.accent, size=20),
                        ft.Text("API Integration", size=18, weight="bold"),
                    ]
                ),
                ft.Text(
                    "Connect to a REST API or Database to fetch data.",
                    size=12,
                    color=TH.dim,
                ),
                ft.TextField(label="Endpoint URL", hint_text="https://api.myapp.com/v1/data"),
                ft.TextField(label="Bearer Token / API Key", password=True),
                ft.Button("Fetch & Index", bgcolor=TH.accent, color="white"),
            ],
            spacing=15,
        )

    return ft.Container(
        content=ft.Column(
            [
                header,
                ft.Divider(height=1, color=TH.divider),
                ft.Text("Source Type", size=14, weight="bold"),
                chips,
                ft.Container(height=10),
                config_form,
                progress_bar,
                status_text,
                ft.Container(height=40),  # Footer spacer
                ft.Row(
                    [
                        ft.Text(
                            f"ZEN_RAG v{state.app_version} — Your data stays on your computer • Privacy-focused • Open source",
                            size=10,
                            color=TH.muted,
                        )
                    ],
                    alignment="center",
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        padding=ft.padding.only(left=30, right=30, top=20),
    )


def build_welcome(*args, **kwargs):  # Compatibility wrapper
    return build_config_panel(*args, **kwargs)


def build_source_panel(*args, **kwargs):  # Compatibility wrapper
    return build_config_panel(*args, **kwargs)
