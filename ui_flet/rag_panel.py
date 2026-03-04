# -*- coding: utf-8 -*-
"""
ui_flet/rag_panel.py — RAG Source Configuration & Data Inspector
=================================================================

Three-tab source scanner (Web / Folder / Email) with progress tracking,
plus a data inspector panel showing indexed sources, chunks, and images.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

import flet as ft

from ui_flet.theme import TH, MONO_FONT
from ui_flet.widgets import (
    glass_card, metric_tile, section_title, themed_text_field, num_field, accent_button, snack, spacer,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path("data")
_SCAN_RESULTS_FILE = _DATA_DIR / "scan_results.json"


# ═══════════════════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def _persist_scan_results(state: dict) -> None:
    """Save scan results to JSON for resume / coordination."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "source_name": state.get("rag_source_name", ""),
        "source_type": state.get("rag_source_type", ""),
        "content_chars": len(state.get("rag_content", "")),
        "source_count": len(state.get("rag_sources", [])),
        "image_count": len(state.get("rag_images", [])),
        "sources": state.get("rag_sources", []),
        "content_preview": state.get("rag_content", "")[:2000],
    }
    history: list = []
    if _SCAN_RESULTS_FILE.exists():
        try:
            existing = json.loads(_SCAN_RESULTS_FILE.read_text("utf-8"))
            history = existing if isinstance(existing, list) else [existing]
        except Exception:
            logger.debug("[RAG] Could not read previous scan results")
    history.append(payload)
    history = history[-50:]
    _SCAN_RESULTS_FILE.write_text(
        json.dumps(history, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PROGRESS HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_progress() -> dict:
    """Create progress widgets for scan operations."""
    return {
        "bar": ft.ProgressBar(width=500, color=TH.accent, bgcolor=TH.card,
                              value=0, visible=False),
        "label": ft.Text("", size=12, color=TH.dim),
        "detail": ft.Text("", size=10, color=TH.muted, font_family=MONO_FONT),
    }


def _progress_column(progress: dict) -> ft.Column:
    """Layout for progress bar + label + detail."""
    return ft.Column(
        [
            ft.Container(content=progress["bar"], width=500,
                         alignment=ft.Alignment(0, 0)),
            progress["label"],
            progress["detail"],
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SCAN HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _handle_web_scan(page, state, progress, url_field, limit_field, on_done):
    """Execute web scan → index → notify."""
    url = url_field.value.strip()
    if not url:
        snack(page, "Please enter a website URL", TH.error_c)
        return
    if not url.startswith("http"):
        url = f"https://{url}"
    max_pages = int(limit_field.value or "50")

    progress["bar"].visible = True
    progress["bar"].value = 0
    progress["label"].value = "🌐 Starting web scan…"
    page.update()

    def pcb(done, total):
        """Report web-scan page progress to the UI."""
        progress["bar"].value = done / max(total, 1)
        progress["label"].value = f"📄 {done} / {total} pages"
        try:
            page.update()
        except Exception:
            logger.debug("[RAG] page.update() skipped (page may be closed)")

    try:
        from zena_mode.website_scraper import WebsiteScraper
        scraper = WebsiteScraper()
        loop = asyncio.get_running_loop()
        text, images, sources = await loop.run_in_executor(
            None, lambda: scraper.scan(url, max_pages=max_pages, progress_cb=pcb)
        )
        state["rag_content"] = text
        state["rag_sources"] = sources
        state["rag_images"] = images
        state["rag_source_name"] = url
        state["rag_source_type"] = "web"
        _persist_scan_results(state)

        # Index into RAG
        progress["label"].value = "⚙️ Indexing content…"
        page.update()
        from zena_mode.rag_pipeline import LocalRAG
        rag = LocalRAG()
        await loop.run_in_executor(
            None, lambda: rag.build_index(text, sources)
        )

        progress["bar"].visible = False
        progress["label"].value = ""
        snack(page, f"✅ Web scan complete — {len(sources)} pages indexed")
        on_done()
    except Exception as exc:
        progress["bar"].visible = False
        progress["label"].value = f"❌ Error: {exc}"
        progress["label"].color = TH.error_c
        page.update()
        logger.error("Web scan failed: %s", exc)


async def _handle_folder_scan(page, state, progress, folder_field, limit_field, on_done):
    """Execute folder scan → index → notify."""
    folder = folder_field.value.strip()
    if not folder or not Path(folder).is_dir():
        snack(page, "Please enter a valid directory path", TH.error_c)
        return
    max_files = int(limit_field.value or "500")

    progress["bar"].visible = True
    progress["bar"].value = 0
    progress["label"].value = "📁 Starting folder scan…"
    page.update()

    def pcb(done, total, status=""):
        """Report folder-scan file progress to the UI."""
        progress["bar"].value = done / max(total, 1) if total else 0
        progress["detail"].value = status or f"📄 {done} / {total}"
        try:
            page.update()
        except Exception:
            logger.debug("[RAG] page.update() skipped (page may be closed)")

    try:
        from zena_mode.universal_extractor import UniversalExtractor
        extractor = UniversalExtractor()
        loop = asyncio.get_running_loop()
        text, images, sources = await loop.run_in_executor(
            None, lambda: extractor.scan_directory(
                folder, max_files=max_files, progress_cb=pcb
            )
        )
        state["rag_content"] = text
        state["rag_sources"] = sources
        state["rag_images"] = images
        state["rag_source_name"] = folder
        state["rag_source_type"] = "folder"
        _persist_scan_results(state)

        progress["label"].value = "⚙️ Indexing content…"
        page.update()
        from zena_mode.rag_pipeline import LocalRAG
        rag = LocalRAG()
        await loop.run_in_executor(None, lambda: rag.build_index(text, sources))

        progress["bar"].visible = False
        progress["label"].value = ""
        snack(page, f"✅ Folder scan complete — {len(sources)} files indexed")
        on_done()
    except Exception as exc:
        progress["bar"].visible = False
        progress["label"].value = f"❌ Error: {exc}"
        progress["label"].color = TH.error_c
        page.update()
        logger.error("Folder scan failed: %s", exc)




def ___handle_email_scan_part2_part2():
    """Continue __handle_email_scan_part2 logic."""
    def pcb(done, total):
        """Report email-scan progress to the UI."""
        progress["bar"].value = done / max(total, 1)
        progress["label"].value = f"📧 {done} / {total} emails"
        try:
            page.update()
        except Exception:
            logger.debug("[RAG] page.update() skipped (page may be closed)")

    try:
        from zena_mode.email_ingestor import EmailIngestor
        ingestor = EmailIngestor()
        loop = asyncio.get_running_loop()

        if mode == "imap":
            text, images, sources = await loop.run_in_executor(
                None,
                lambda: ingestor.scan_imap(
                    server=fields["server"].value.strip(),
                    email_addr=fields["email"].value.strip(),
                    password=fields["password"].value.strip(),
                    folder=fields["folder"].value.strip() or "INBOX",
                    max_emails=int(fields["limit"].value or "100"),
                    days_back=int(fields["days"].value or "30"),
                    progress_cb=pcb,
                ),
            )
            name = fields["email"].value.strip()
        else:
            path = fields["path"].value.strip()
            if not path or not Path(path).exists():
                snack(page, "Please enter a valid email file path", TH.error_c)
                return
            text, images, sources = await loop.run_in_executor(
                None,
                lambda: ingestor.scan_local(
                    path=path,
                    max_emails=int(fields["limit"].value or "500"),
                    progress_cb=pcb,
                ),
            )
            name = path

        state["rag_content"] = text
        state["rag_sources"] = sources
        state["rag_images"] = images
        state["rag_source_name"] = name
        state["rag_source_type"] = "email"
        _persist_scan_results(state)

        progress["label"].value = "⚙️ Indexing content…"
        page.update()
        from zena_mode.rag_pipeline import LocalRAG
        rag = LocalRAG()
        await loop.run_in_executor(None, lambda: rag.build_index(text, sources))

        progress["bar"].visible = False
        progress["label"].value = ""
        snack(page, f"✅ Email scan complete — {len(sources)} emails indexed")
        on_done()
    except Exception as exc:
        progress["bar"].visible = False
        progress["label"].value = f"❌ Error: {exc}"
        progress["label"].color = TH.error_c
        page.update()
        logger.error("Email scan failed: %s", exc)


def __handle_email_scan_part2(mode):
    """Continue _handle_email_scan logic."""
    progress["label"].value = "📧 Starting email scan…"
    page.update()

    ___handle_email_scan_part2_part2()


async def _handle_email_scan(page, state, progress, fields, on_done):
    """Execute email scan (IMAP or local) → index → notify."""
    mode = fields.get("mode", "imap")
    progress["bar"].visible = True
    progress["bar"].value = 0
    __handle_email_scan_part2(mode)


# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE CONFIG PANEL (Pre-data landing)
# ═══════════════════════════════════════════════════════════════════════════════

def _source_hero() -> ft.Column:
    """Landing page hero: logo + tagline."""
    return ft.Column(
        [
            ft.Text("🧠", size=56, text_align=ft.TextAlign.CENTER),
            ft.Text(
                "ZenAI",
                size=36,
                weight=ft.FontWeight.BOLD,
                color=TH.accent,
                font_family=MONO_FONT,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Offline-first AI assistant — Your data stays local",
                size=13,
                color=TH.muted,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )


def _build_web_tab(page, state, progress, on_done):
    """Web URL scan card."""
    url_f = themed_text_field("Website URL", "https://example.com",
                              ft.Icons.LANGUAGE, expand=True)
    mp_f = num_field("Max Pages", "50")

    def on_scan(e):
        """Start the web-scan workflow."""
        page.run_task(_handle_web_scan, page, state, progress, url_f, mp_f, on_done)

    return glass_card(
        ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.LANGUAGE, color=TH.accent, size=30),
                    bgcolor=ft.Colors.with_opacity(0.08, TH.accent),
                    border_radius=12, width=56, height=56,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text("Scan Website", weight=ft.FontWeight.BOLD, size=16,
                        color=TH.text),
                ft.Text("Enter a URL to crawl and index web pages",
                        size=11, color=TH.muted),
                spacer(),
                ft.Row([url_f, mp_f], spacing=8),
                spacer(),
                accent_button("▶ Start Web Scan", on_click=on_scan),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=24,
        expand=True,
    )


def _build_folder_tab(page, state, progress, on_done):
    """Local folder scan card with file picker."""
    dir_f = themed_text_field("Directory Path", "C:\\Documents",
                              ft.Icons.FOLDER_OPEN, expand=True)
    mf_f = num_field("Max Files", "500")
    fp = ft.FilePicker()
    if not any(isinstance(s, ft.FilePicker) for s in page.overlay):
        page.overlay.append(fp)

    async def pick_folder(e):
        """Open a native folder-picker dialog."""
        fp.get_directory_path(dialog_title="Choose folder")

    def on_folder_result(e: ft.FilePickerResultEvent):
        """Handle the folder-picker result and populate the path field."""
        if e.path:
            dir_f.value = e.path
            page.update()

    fp.on_result = on_folder_result

    def on_scan(e):
        """Start the folder-scan workflow."""
        page.run_task(_handle_folder_scan, page, state, progress, dir_f, mf_f, on_done)

    return glass_card(
        ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.FOLDER_OPEN, color=TH.accent2, size=30),
                    bgcolor=ft.Colors.with_opacity(0.08, TH.accent2),
                    border_radius=12, width=56, height=56,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text("Scan Local Files", weight=ft.FontWeight.BOLD, size=16,
                        color=TH.text),
                ft.Text("Browse a folder to extract and index documents",
                        size=11, color=TH.muted),
                spacer(),
                ft.Row([dir_f, mf_f,
                        ft.IconButton(icon=ft.Icons.FOLDER_OPEN,
                                      icon_color=TH.accent2,
                                      on_click=pick_folder,
                                      tooltip="Browse")],
                       spacing=8),
                spacer(),
                accent_button("▶ Start Folder Scan", on_click=on_scan,
                              color=TH.accent2),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=24,
        expand=True,
    )





def ____build_email_tab_part2_part2_part2(email_color):
    """Continue ___build_email_tab_part2_part2 logic."""
    def on_local_scan(e):
        """Start the local email-scan workflow."""
        page.run_task(_handle_email_scan, page, state, progress, local_fields, on_done)

    return ft.Column(
        [
            # IMAP card
            glass_card(
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.MAIL_OUTLINE,
                                            color=email_color, size=30),
                            bgcolor=ft.Colors.with_opacity(0.08, email_color),
                            border_radius=12, width=56, height=56,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text("IMAP Email Scan", weight=ft.FontWeight.BOLD,
                                size=16, color=TH.text),
                        ft.Text("Connect to your inbox via IMAP",
                                size=11, color=TH.muted),
                        spacer(6),
                        ft.Row([srv_f], spacing=8),
                        ft.Row([addr_f, pw_f], spacing=8),
                        ft.Row([fld_f, me_f, db_f], spacing=8),
                        spacer(),
                        accent_button("▶ Start Email Scan", on_click=on_imap_scan,
                                      color=email_color),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=24,
                expand=True,
            ),
            spacer(12),
            # Local email card
            glass_card(
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.ATTACH_EMAIL_OUTLINED,
                                            color=TH.accent2, size=30),
                            bgcolor=ft.Colors.with_opacity(0.08, TH.accent2),
                            border_radius=12, width=56, height=56,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text("Local Email Files", weight=ft.FontWeight.BOLD,
                                size=16, color=TH.text),
                        ft.Text("Scan .eml or .mbox files from disk",
                                size=11, color=TH.muted),
                        spacer(6),
                        ft.Row([path_f, local_limit_f], spacing=8),
                        spacer(),
                        accent_button("▶ Scan Local Emails", on_click=on_local_scan,
                                      color=TH.accent2),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=24,
                expand=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def ___build_email_tab_part2_part2(imap_fields, local_fields, local_limit_f):
    """Continue __build_email_tab_part2 logic."""
    email_color = "#e91e63"

    def on_imap_scan(e):
        """Start the IMAP email-scan workflow."""
        page.run_task(_handle_email_scan, page, state, progress, imap_fields, on_done)

    return ____build_email_tab_part2_part2_part2(email_color)


def __build_email_tab_part2(addr_f, db_f, fld_f, me_f, path_f, pw_f, srv_f):
    """Continue _build_email_tab logic."""
    local_limit_f = num_field("Max Emails", "500")

    imap_fields = {
        "mode": "imap", "server": srv_f, "email": addr_f,
        "password": pw_f, "folder": fld_f, "limit": me_f, "days": db_f,
    }
    local_fields = {
        "mode": "local", "path": path_f, "limit": local_limit_f,
    }

    return ___build_email_tab_part2_part2(imap_fields, local_fields, local_limit_f)


def _build_email_tab(page, state, progress, on_done):
    """Email scan card — IMAP + local modes."""
    # IMAP fields
    srv_f = themed_text_field("IMAP Server", "imap.gmail.com",
                              ft.Icons.DNS_OUTLINED, expand=True)
    addr_f = themed_text_field("Email Address", "user@example.com",
                               ft.Icons.EMAIL_OUTLINED, expand=True)
    pw_f = ft.TextField(
        label="Password", hint_text="App password",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True, can_reveal_password=True,
        border_color=TH.border, color=TH.text,
        focused_border_color=TH.accent, expand=True,
    )
    fld_f = ft.TextField(label="Folder", value="INBOX", width=140,
                         border_color=TH.border, color=TH.text)
    me_f = num_field("Max Emails", "100")
    db_f = num_field("Days Back", "30")

    # Local email fields
    path_f = themed_text_field("Email File Path", "C:\\emails",
                               ft.Icons.FOLDER_SPECIAL_OUTLINED, expand=True)
    return __build_email_tab_part2(addr_f, db_f, fld_f, me_f, path_f, pw_f, srv_f)


def build_source_config_panel(
    page: ft.Page,
    state: dict,
    on_scan_complete: Callable,
) -> ft.Container:
    """Source configuration panel — 3 tabs: Web, Folder, Email."""
    progress = _make_progress()

    web_card = _build_web_tab(page, state, progress, on_scan_complete)
    folder_card = _build_folder_tab(page, state, progress, on_scan_complete)
    email_content = _build_email_tab(page, state, progress, on_scan_complete)

    panels = [
        ft.Container(content=web_card, padding=20, alignment=ft.Alignment(0, 0)),
        ft.Container(content=folder_card, padding=20, alignment=ft.Alignment(0, 0)),
        ft.Container(content=email_content, padding=20, alignment=ft.Alignment(0, 0)),
    ]
    panel_box = ft.Column([panels[0]], expand=True)

    def on_tab_change(e):
        """Switch the visible source-configuration panel by tab index."""
        idx = e.control.selected_index
        panel_box.controls = [panels[idx]]
        page.update()

    tabs_bar = ft.Tabs(
        tabs=[
            ft.Tab(text="🌐  Web"),
            ft.Tab(text="📁  Folder"),
            ft.Tab(text="📧  Email"),
        ],
        selected_index=0,
        on_change=on_tab_change,
    )

    return ft.Container(
        content=ft.Column(
            [
                spacer(20),
                _source_hero(),
                spacer(16),
                tabs_bar,
                panel_box,
                _progress_column(progress),
                spacer(8),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        alignment=ft.Alignment(0, 0),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA INSPECTOR PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_data_inspector_panel(page: ft.Page, state: dict) -> ft.Column:
    """View indexed sources, chunks, and images."""
    sources = state.get("rag_sources", [])
    content = state.get("rag_content", "")
    images = state.get("rag_images", [])

    metrics = ft.Row(
        [
            metric_tile("📄", len(sources), "Sources"),
            metric_tile("📝", f"{len(content):,}", "Characters"),
            metric_tile("🖼️", len(images), "Images"),
        ],
        spacing=8,
    )

    source_tiles = []
    for i, src in enumerate(sources[:100]):
        title = src.get("title", src.get("path", f"Source {i + 1}"))
        url = src.get("path", src.get("url", ""))
        chars = src.get("chars", 0)
        icon = "🌐" if "http" in str(url) else "📄"
        source_tiles.append(
            ft.ExpansionTile(
                title=ft.Text(f"{icon} {title}", size=13),
                subtitle=ft.Text(f"{url} · {chars:,} chars", size=11, color=TH.muted),
                controls=[
                    ft.Container(
                        content=ft.Text(
                            content[max(0, i * 500):(i + 1) * 500][:500]
                            if content else "No content preview",
                            font_family=MONO_FONT, size=11, selectable=True,
                            color=TH.dim,
                        ),
                        bgcolor=TH.code_bg,
                        border_radius=8,
                        padding=10,
                    )
                ],
                initially_expanded=False,
            )
        )

    if not source_tiles:
        source_tiles = [ft.Text("No data indexed yet.", color=TH.muted)]

    return ft.Column(
        [
            section_title("Your Data", "📊"),
            metrics,
            ft.Divider(color=TH.divider, height=20),
            section_title(f"Sources ({len(sources)})", "📋"),
            ft.ListView(controls=source_tiles, expand=True, spacing=4,
                        auto_scroll=False),
        ],
        spacing=10,
        expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  DB CONTENTS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_db_contents_panel(page: ft.Page, state: dict) -> ft.Column:
    """Vector database contents — what's stored in Qdrant."""
    info_text = ft.Text("Loading…", size=12, color=TH.dim)
    doc_list = ft.ListView(controls=[], expand=True, spacing=4)

    async def _load():
        """Load vector database contents asynchronously."""
        try:
            from zena_mode.rag_pipeline import LocalRAG
            rag = LocalRAG()
            stats = rag.get_stats()
            docs = rag.list_documents() if hasattr(rag, "list_documents") else []
            backend = stats.get("backend", "unknown")
            n_docs = stats.get("documents_uploaded", 0)

            info_text.value = f"Backend: {backend} · Documents: {n_docs}"

            doc_list.controls.clear()
            for doc in docs:
                name = doc.get("name", doc.get("path", "Unknown"))
                size = doc.get("size", 0)
                ts = doc.get("uploaded_at", "")
                icon = "🌐" if "http" in str(doc.get("path", "")) else "📄"
                doc_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{icon} {name}", size=12, color=TH.text,
                                    expand=True),
                            ft.Text(f"{size / 1024:.1f} KB" if size > 1024
                                    else f"{size} B",
                                    size=11, color=TH.muted, width=80),
                            ft.Text(ts[:16].replace("T", " ") if ts else "",
                                    size=11, color=TH.muted, width=130),
                        ]),
                        bgcolor=TH.card, border=ft.Border.all(1, TH.border),
                        border_radius=8,
                        padding=ft.Padding.symmetric(vertical=6, horizontal=10),
                    )
                )
            if not docs:
                doc_list.controls.append(
                    ft.Text("No documents indexed yet.", color=TH.muted, size=12)
                )
            page.update()
        except Exception as exc:
            info_text.value = f"Error: {exc}"
            page.update()

    page.run_task(_load)

    return ft.Column(
        [
            section_title("Vector Database Contents", "🗄️"),
            info_text,
            ft.Divider(color=TH.divider, height=16),
            doc_list,
        ],
        spacing=10,
        expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANUP PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_cleanup_panel(page: ft.Page, state: dict) -> ft.Column:
    """KB cleanup — find conflicts and stale content."""
    status_text = ft.Text("", size=12, color=TH.dim)
    results_list = ft.ListView(controls=[], expand=True, spacing=4)

    async def on_run_cleanup(e):
        """Scan the knowledge base for duplicate or conflicting entries."""
        status_text.value = "🔍 Scanning for conflicts…"
        results_list.controls.clear()
        page.update()
        try:
            from zena_mode.rag_pipeline import LocalRAG
            rag = LocalRAG()
            docs = rag.list_documents() if hasattr(rag, "list_documents") else []
            seen, conflicts = {}, []
            for doc in docs:
                src = doc.get("path", "")
                if src in seen:
                    conflicts.append((src, seen[src]))
                else:
                    seen[src] = doc
            if conflicts:
                status_text.value = (
                    f"⚠️ Found {len(conflicts)} potential duplicates"
                )
                for src, orig in conflicts:
                    results_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"🔄 Duplicate: {src}", size=12,
                                        color=TH.warning_c,
                                        weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"First indexed: {orig.get('uploaded_at', '?')}",
                                    size=11, color=TH.muted),
                            ]),
                            bgcolor=TH.card, border=ft.Border.all(1, TH.border),
                            border_radius=8,
                            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                        )
                    )
            else:
                status_text.value = "✅ No conflicts found — KB is clean"
        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
        page.update()

    return ft.Column(
        [
            section_title("KB Cleanup", "🧹"),
            ft.Text("Find and resolve conflicts in your knowledge base.",
                    size=12, color=TH.muted),
            spacer(),
            ft.Row([
                accent_button("🔍 Run Cleanup Scan", on_click=on_run_cleanup,
                              color=TH.accent2, width=220),
                status_text,
            ], spacing=12),
            ft.Divider(color=TH.divider, height=16),
            results_list,
        ],
        spacing=10,
        expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CACHE PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_cache_panel(page: ft.Page, state: dict) -> ft.Column:
    """Semantic cache performance dashboard."""
    info_text = ft.Text("Loading cache stats…", size=12, color=TH.dim)

    async def _load():
        """Load semantic cache statistics asynchronously."""
        try:
            from zena_mode.rag_pipeline import LocalRAG
            rag = LocalRAG()
            if hasattr(rag, "semantic_cache") and hasattr(rag.semantic_cache, "get_stats"):
                stats = rag.semantic_cache.get_stats()
                hits = stats.get("hits", 0)
                misses = stats.get("misses", 0)
                total = hits + misses
                rate = (hits / total * 100) if total > 0 else 0
                info_text.value = (
                    f"Cache hits: {hits} · Misses: {misses} · "
                    f"Hit rate: {rate:.1f}%"
                )
            else:
                info_text.value = "Semantic cache not available"
        except Exception:
            info_text.value = "Semantic cache not available"
        page.update()

    page.run_task(_load)

    return ft.Column(
        [
            section_title("Cache Dashboard", "💾"),
            ft.Text("Semantic cache performance analytics.", size=12, color=TH.muted),
            spacer(12),
            info_text,
        ],
        spacing=10,
        expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  EVALUATION PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_eval_panel(page: ft.Page, state: dict) -> ft.Column:
    """Evaluation dashboard — answer quality metrics."""
    chat_history = state.get("chat_history", [])
    n_turns = len([m for m in chat_history if m.get("role") == "assistant"])

    return ft.Column(
        [
            section_title("Evaluation Dashboard", "📊"),
            ft.Text("Answer quality metrics and analytics.", size=12, color=TH.muted),
            spacer(12),
            ft.Row([
                metric_tile("💬", n_turns, "Answers Given"),
                metric_tile("📝", len(chat_history), "Total Messages"),
                metric_tile("📚", len(state.get("rag_sources", [])), "Sources Used"),
            ], spacing=8),
        ],
        spacing=10,
        expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  DEDUP PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def build_dedup_panel(page: ft.Page, state: dict) -> ft.Column:
    """Deduplication tools panel."""
    status_text = ft.Text("", size=12, color=TH.dim)
    results_list = ft.ListView(controls=[], expand=True, spacing=4)

    async def on_run_dedup(e):
        """Scan for and report duplicate documents in the vector store."""
        status_text.value = "🔍 Checking for duplicates…"
        results_list.controls.clear()
        page.update()
        try:
            from zena_mode.rag_pipeline import LocalRAG
            rag = LocalRAG()
            docs = rag.list_documents() if hasattr(rag, "list_documents") else []
            seen, dupes = {}, []
            for doc in docs:
                name = doc.get("name", doc.get("path", ""))
                if name in seen:
                    dupes.append((name, doc))
                else:
                    seen[name] = doc
            if dupes:
                status_text.value = f"Found {len(dupes)} duplicate documents"
                for name, _doc in dupes:
                    results_list.controls.append(
                        ft.Container(
                            content=ft.Text(f"🗑️ {name}", size=12,
                                            color=TH.warning_c),
                            bgcolor=TH.card, border=ft.Border.all(1, TH.border),
                            border_radius=8,
                            padding=ft.Padding.symmetric(vertical=6, horizontal=10),
                        )
                    )
            else:
                status_text.value = "✅ No duplicates found"
            page.update()
        except Exception as exc:
            status_text.value = f"❌ Error: {exc}"
            page.update()

    return ft.Column(
        [
            section_title("Deduplication Tools", "🗑️"),
            ft.Text("Find and remove duplicate content.", size=12, color=TH.muted),
            spacer(),
            ft.Row([
                accent_button("🔍 Check for Duplicates", on_click=on_run_dedup,
                              color=TH.accent2, width=240),
                status_text,
            ], spacing=12),
            ft.Divider(color=TH.divider, height=16),
            results_list,
        ],
        spacing=10,
        expand=True,
    )
