from nicegui import ui
from ui import Styles
import asyncio
import random
import time


def render_rag_summary(stats, container, on_reset=None, on_close=None):
    """Render a colorful, detailed summary card after ingestion."""
    container.clear()
    with (
        container,
        ui.card().classes("w-full bg-white dark:bg-slate-800 border-l-4 border-green-500 p-4 animate-fade-in"),
    ):
        # Header
        with ui.row().classes("w-full items-center justify-between mb-3"), ui.row().classes("items-center gap-2"):
            ui.icon("check_circle", size="28px").classes("text-green-500")
            with ui.column().classes("gap-0"):
                ui.label("Ingestion Complete").classes("text-lg font-bold text-green-700 dark:text-green-400")
                ui.label(f"Processed in {stats['time_taken']:.1f}s").classes("text-xs text-gray-400")

            ui.badge(f"{stats['total_size']}", color="green").props("outline").classes("text-xs font-mono")

        ui.separator().classes("mb-3 opacity-50")

        # Key Metrics Grid
        with ui.grid(columns=3).classes("w-full gap-2 mb-4"):

            def stat_box(label, value, icon, color):
                """Stat box."""
                with ui.column().classes(
                    f"p-2 rounded bg-{color}-50 dark:bg-{color}-900/20 items-center justify-center text-center"
                ):
                    ui.icon(icon, size="20px").classes(f"text-{color}-500 mb-1")
                    ui.label(str(value)).classes(
                        f"text-lg font-bold text-{color}-700 dark:text-{color}-300 leading-none"
                    )
                    ui.label(label).classes(
                        f"text-[10px] uppercase tracking-wider text-{color}-600/70 dark:text-{color}-400/70"
                    )

            stat_box("Files", stats["files"], "description", "blue")
            stat_box("Chunks", stats["chunks"], "segment", "purple")
            stat_box("Images", stats["images"], "image", "orange")

        # Detailed Breakdown
        ui.label("Content Distribution").classes("text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide")
        with ui.column().classes("w-full gap-1"):
            for ftype, count in stats["breakdown"].items():
                pct = (count / stats["files"]) * 100 if stats["files"] > 0 else 0
                with ui.row().classes("w-full items-center gap-2 text-xs"):
                    ui.label(ftype).classes("w-12 font-mono text-gray-600 dark:text-gray-400")
                    ui.linear_progress(value=pct / 100, show_value=False, color="grey").classes(
                        "flex-grow h-1.5 rounded-full opacity-50"
                    )
                    ui.label(str(count)).classes("w-6 text-right font-bold")

        # Footer Actions
        with ui.row().classes("w-full gap-2 mt-4"):

            def handle_chat_click():
                ui.notify("Ready to chat!")
                if on_close:
                    on_close()

            ui.button("Start Chatting", icon="chat", on_click=handle_chat_click).props(
                "flat dense flex-grow text-green-500"
            )
            if on_reset:
                ui.button("New Scan", icon="refresh", on_click=on_reset).props("flat dense text-gray-500").classes(
                    "w-auto"
                )


def setup_rag_dialog(app_state, ZENA_MODE, ZENA_CONFIG, locale, rag_system, Styles):
    """Setup the RAG dialog and its logic in a clean, modular way."""
    rag_dialog = ui.dialog().classes("z-50")
    app_state["open_rag_dialog"] = rag_dialog.open

    with (
        rag_dialog,
        ui.card().classes(
            "w-[600px] max-w-[95vw] max-h-[85vh] p-0 rounded-2xl shadow-2xl bg-white dark:bg-slate-900 flex flex-col overflow-hidden"
        ),
    ):
        if ZENA_MODE:
            # Header (Fixed padding)
            with ui.column().classes("w-full p-6 pb-2"), ui.row().classes("items-center gap-2"):
                ui.icon("library_books", size="28px").classes("text-blue-500")
                ui.label("Knowledge Base Scanner").classes("text-xl font-bold " + Styles.TEXT_PRIMARY)

                ui.label("Add websites or local files to the AI's knowledge").classes(
                    "text-sm text-gray-500 dark:text-gray-400"
                )

            # Scrollable Content (Padding inside)
            with ui.column().classes("w-full px-6 overflow-y-auto").style("max-height: 60vh"):
                # Content Area (Tabs or Summary)
                content_container = ui.column().classes("w-full")

                with content_container:
                    # Mode selector with clear tabs
                    with ui.tabs().classes("w-full mb-4") as mode_tabs:
                        ui.tab("website", label="🌐 Website")
                        ui.tab("email", label="📧 Email Archive")
                        ui.tab("directory", label="📁 Local Files")

                    # Bind tab value to state for access in start_scan
                    mode_tabs.bind_value(app_state, "rag_mode")

                    with ui.tab_panels(mode_tabs, value="website").classes("w-full"):
                        # Website Panel
                        with ui.tab_panel("website"), ui.column().classes("w-full gap-3"):
                            ui.input(
                                "Website URL",
                                placeholder="https://example.com",
                                value=ZENA_CONFIG.get("website_url", ""),
                            ).props("outlined").classes("w-full").bind_value(app_state, "rag_url")
                            with ui.row().classes("w-full gap-2"):
                                ui.number("Max Pages", value=50, min=1, max=500).props("outlined dense").classes(
                                    "w-24"
                                ).bind_value(app_state, "rag_max_pages")
                                ui.label("pages to scan").classes("text-sm text-gray-400 self-center")

                        # Email Panel
                        with ui.tab_panel("email"), ui.column().classes("w-full gap-3"):
                            ui.input("Archive Path (.mbox, .pst)", placeholder="C:/Users/Me/backup.pst").props(
                                "outlined"
                            ).classes("w-full").bind_value(app_state, "rag_email_path")
                            ui.label("Supports: legacy formats (MBOX, PST, OST) from Outlook/Thunderbird.").classes(
                                "text-xs text-gray-400"
                            )

                        # Directory Panel
                        with ui.tab_panel("directory"), ui.column().classes("w-full gap-3"):
                            ui.input("Directory Path", placeholder="C:/Users/YourName/Documents").props(
                                "outlined"
                            ).classes("w-full").bind_value(app_state, "rag_dir")
                            with ui.row().classes("w-full gap-2"):
                                ui.number("Max Files", value=1000, min=1, max=10000).props("outlined dense").classes(
                                    "w-24"
                                ).bind_value(app_state, "rag_max_files")
                                ui.label("files to index").classes("text-sm text-gray-400 self-center")
                            ui.label("Supports: .txt, .md, .py, .pdf, .docx, .png, .jpg").classes(
                                "text-xs text-gray-400"
                            )

                ui.separator().classes("my-4")

                # Progress section
                with ui.column().classes("w-full gap-2") as progress_section:
                    progress_label = ui.label("").classes("text-sm font-medium text-blue-600 dark:text-blue-400")
                    progress_bar = ui.linear_progress(value=0, show_value=True).classes("w-full")
                    progress_bar.visible = False
                    stats_label = ui.label("").classes("text-xs text-gray-500")

                app_state["rag_progress_label"] = progress_label
                app_state["rag_progress_bar"] = progress_bar
                app_state["rag_stats_label"] = stats_label

                # Summary Container
                summary_container = ui.column().classes("w-full mt-2")

            def reset_view():
                content_container.visible = True
                summary_container.clear()

            from zena_mode.scraper import WebsiteScraper
            from zena_mode.email_ingestor import EmailIngestor

            async def start_scan():
                """Start scan."""
                # Reset UI
                content_container.visible = False
                progress_bar.visible = True
                progress_bar.value = 0
                progress_label.text = "🔍 Initializing..."
                stats_label.text = ""
                summary_container.clear()

                start_time = time.time()
                mode = app_state.get("rag_mode", "website")

                docs = []

                try:
                    if mode == "website":
                        url = app_state.get("rag_url", "")
                        max_pages = int(app_state.get("rag_max_pages", 50))

                        if not url:
                            raise Exception("Please enter a valid URL")

                        # 1. SCRAPE WEBSITE
                        progress_label.text = f"🌐 Scanning {url}..."

                        def run_scraper_thread():
                            scraper = WebsiteScraper(url)
                            return scraper.scrape(max_pages=max_pages, progress_callback=None)

                        result = await asyncio.to_thread(run_scraper_thread)
                        if not result["success"]:
                            raise Exception(result.get("error", "Unknown scraping error"))
                        docs = result["documents"]
                        if not docs:
                            raise Exception("No content found on website")

                    elif mode == "email":
                        path = app_state.get("rag_email_path", "")
                        if not path:
                            raise Exception("Please enter an archive path")

                        # 1. SCAN EMAIL
                        progress_label.text = f"📧 Parsing email archive: {path}..."

                        def run_email_thread():
                            ingestor = EmailIngestor()
                            return ingestor.ingest(path)

                        docs = await asyncio.to_thread(run_email_thread)
                        if not docs:
                            raise Exception("No emails found or format unsupported")

                    elif mode == "directory":
                        # Placeholder for directory logic if needed, or raise error
                        raise Exception("Directory scan not fully wired in this snippet")

                    progress_bar.value = 0.5
                    progress_label.text = f"🧠 Indexing {len(docs)} items..."

                    # 2. INDEX
                    # rag_system is closed over from setup_rag_dialog scope
                    if hasattr(rag_system, "build_index_async"):
                        await rag_system.build_index_async(docs)
                    else:
                        await asyncio.to_thread(rag_system.build_index, docs)

                    # 3. STATS
                    elapsed = time.time() - start_time
                    progress_bar.value = 1.0

                    # Calc breakdown
                    breakdown = {}
                    images = 0  # Scraper v2 doesn't count images separately yet, assume 0 or parse text tags
                    total_chars = sum(len(d["content"]) for d in docs)
                    total_size = f"{total_chars / 1024:.1f} KB"

                    breakdown["Web Pages"] = len(docs)

                    real_stats = {
                        "files": len(docs),
                        "chunks": rag_system.ntotal if hasattr(rag_system, "ntotal") else len(docs) * 5,  # Approx
                        "images": images,
                        "total_size": total_size,
                        "time_taken": elapsed,
                        "breakdown": breakdown,
                    }

                    # Hide progress, show summary
                    progress_section.visible = False
                    content_container.visible = False

                    render_rag_summary(real_stats, summary_container, on_reset=reset_view, on_close=rag_dialog.close)
                    ui.notify(f"Successfully indexed {len(docs)} pages!", color="positive")

                except Exception as e:
                    progress_label.text = f"❌ Error: {str(e)}"
                    ui.notify(f"Scan failed: {str(e)}", color="negative")
                    # Don't hide progress so user sees error
                    progress_bar.color = "red"

            # Buttons (Footer, fixed padding)
            with (
                ui.column().classes("w-full p-6 pt-2 border-t dark:border-slate-800"),
                ui.row().classes("w-full gap-2"),
            ):
                ui.button("Start Scan", icon="search", on_click=start_scan).props("color=primary unelevated").classes(
                    "flex-grow"
                )
                ui.button("Close", on_click=rag_dialog.close).props("flat").classes("text-gray-500")
        else:
            ui.label("RAG not enabled in Zena mode").classes("text-center text-gray-400")
            ui.button("Close", on_click=rag_dialog.close).props("flat").classes("w-full mt-2")

    return rag_dialog
