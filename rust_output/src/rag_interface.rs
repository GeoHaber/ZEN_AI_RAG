use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

/// Render a colorful, detailed summary card after ingestion.
pub fn render_rag_summary(stats: String, container: String, on_reset: String, on_close: String) -> () {
    // Render a colorful, detailed summary card after ingestion.
    container.clear();
    let _ctx = container;
    let _ctx = ui.card().classes("w-full bg-white dark:bg-slate-800 border-l-4 border-green-500 p-4 animate-fade-in".to_string());
    {
        let _ctx = ui.row().classes("w-full items-center justify-between mb-3".to_string());
        let _ctx = ui.row().classes("items-center gap-2".to_string());
        {
            ui.icon("check_circle".to_string(), /* size= */ "28px".to_string()).classes("text-green-500".to_string());
            let _ctx = ui.column().classes("gap-0".to_string());
            {
                ui.label("Ingestion Complete".to_string()).classes("text-lg font-bold text-green-700 dark:text-green-400".to_string());
                ui.label(format!("Processed in {:.1}s", stats["time_taken".to_string()])).classes("text-xs text-gray-400".to_string());
            }
            ui.badge(format!("{}", stats["total_size".to_string()]), /* color= */ "green".to_string()).props("outline".to_string()).classes("text-xs font-mono".to_string());
        }
        ui.separator().classes("mb-3 opacity-50".to_string());
        let _ctx = ui.grid(/* columns= */ 3).classes("w-full gap-2 mb-4".to_string());
        {
            let stat_box = |label, value, icon, color| {
                // Stat box.
                let _ctx = ui.column().classes(format!("p-2 rounded bg-{}-50 dark:bg-{}-900/20 items-center justify-center text-center", color, color));
                {
                    ui.icon(icon, /* size= */ "20px".to_string()).classes(format!("text-{}-500 mb-1", color));
                    ui.label(value.to_string()).classes(format!("text-lg font-bold text-{}-700 dark:text-{}-300 leading-none", color, color));
                    ui.label(label).classes(format!("text-[10px] uppercase tracking-wider text-{}-600/70 dark:text-{}-400/70", color, color));
                }
            };
            stat_box("Files".to_string(), stats["files".to_string()], "description".to_string(), "blue".to_string());
            stat_box("Chunks".to_string(), stats["chunks".to_string()], "segment".to_string(), "purple".to_string());
            stat_box("Images".to_string(), stats["images".to_string()], "image".to_string(), "orange".to_string());
        }
        ui.label("Content Distribution".to_string()).classes("text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide".to_string());
        let _ctx = ui.column().classes("w-full gap-1".to_string());
        {
            for (ftype, count) in stats["breakdown".to_string()].iter().iter() {
                let mut pct = if stats["files".to_string()] > 0 { ((count / stats["files".to_string()]) * 100) } else { 0 };
                let _ctx = ui.row().classes("w-full items-center gap-2 text-xs".to_string());
                {
                    ui.label(ftype).classes("w-12 font-mono text-gray-600 dark:text-gray-400".to_string());
                    ui.linear_progress(/* value= */ (pct / 100), /* show_value= */ false, /* color= */ "grey".to_string()).classes("flex-grow h-1.5 rounded-full opacity-50".to_string());
                    ui.label(count.to_string()).classes("w-6 text-right font-bold".to_string());
                }
            }
        }
        let _ctx = ui.row().classes("w-full gap-2 mt-4".to_string());
        {
            let handle_chat_click = || {
                ui.notify("Ready to chat!".to_string());
                if on_close {
                    on_close();
                }
            };
            ui.button("Start Chatting".to_string(), /* icon= */ "chat".to_string(), /* on_click= */ handle_chat_click).props("flat dense flex-grow text-green-500".to_string());
            if on_reset {
                ui.button("New Scan".to_string(), /* icon= */ "refresh".to_string(), /* on_click= */ on_reset).props("flat dense text-gray-500".to_string()).classes("w-auto".to_string());
            }
        }
    }
}

/// Setup the RAG dialog and its logic in a clean, modular way.
pub fn setup_rag_dialog(app_state: String, ZENA_MODE: String, ZENA_CONFIG: String, locale: String, rag_system: String, Styles: String) -> Result<()> {
    // Setup the RAG dialog and its logic in a clean, modular way.
    let mut rag_dialog = ui.dialog().classes("z-50".to_string());
    app_state["open_rag_dialog".to_string()] = rag_dialog.open;
    let _ctx = rag_dialog;
    let _ctx = ui.card().classes("w-[600px] max-w-[95vw] max-h-[85vh] p-0 rounded-2xl shadow-2xl bg-white dark:bg-slate-900 flex flex-col overflow-hidden".to_string());
    {
        if ZENA_MODE {
            let _ctx = ui.column().classes("w-full p-6 pb-2".to_string());
            let _ctx = ui.row().classes("items-center gap-2".to_string());
            {
                ui.icon("library_books".to_string(), /* size= */ "28px".to_string()).classes("text-blue-500".to_string());
                ui.label("Knowledge Base Scanner".to_string()).classes(("text-xl font-bold ".to_string() + Styles.TEXT_PRIMARY));
                ui.label("Add websites or local files to the AI's knowledge".to_string()).classes("text-sm text-gray-500 dark:text-gray-400".to_string());
            }
            let _ctx = ui.column().classes("w-full px-6 overflow-y-auto".to_string()).style("max-height: 60vh".to_string());
            {
                let mut content_container = ui.column().classes("w-full".to_string());
                let _ctx = content_container;
                {
                    let mut mode_tabs = ui.tabs().classes("w-full mb-4".to_string());
                    {
                        ui.tab("website".to_string(), /* label= */ "🌐 Website".to_string());
                        ui.tab("email".to_string(), /* label= */ "📧 Email Archive".to_string());
                        ui.tab("directory".to_string(), /* label= */ "📁 Local Files".to_string());
                    }
                    mode_tabs.bind_value(app_state, "rag_mode".to_string());
                    let _ctx = ui.tab_panels(mode_tabs, /* value= */ "website".to_string()).classes("w-full".to_string());
                    {
                        let _ctx = ui.tab_panel("website".to_string());
                        let _ctx = ui.column().classes("w-full gap-3".to_string());
                        {
                            ui.input("Website URL".to_string(), /* placeholder= */ "https://example.com".to_string(), /* value= */ ZENA_CONFIG.get(&"website_url".to_string()).cloned().unwrap_or("".to_string())).props("outlined".to_string()).classes("w-full".to_string()).bind_value(app_state, "rag_url".to_string());
                            let _ctx = ui.row().classes("w-full gap-2".to_string());
                            {
                                ui.number("Max Pages".to_string(), /* value= */ 50, /* min= */ 1, /* max= */ 500).props("outlined dense".to_string()).classes("w-24".to_string()).bind_value(app_state, "rag_max_pages".to_string());
                                ui.label("pages to scan".to_string()).classes("text-sm text-gray-400 self-center".to_string());
                            }
                        }
                        let _ctx = ui.tab_panel("email".to_string());
                        let _ctx = ui.column().classes("w-full gap-3".to_string());
                        {
                            ui.input("Archive Path (.mbox, .pst)".to_string(), /* placeholder= */ "C:/Users/Me/backup.pst".to_string()).props("outlined".to_string()).classes("w-full".to_string()).bind_value(app_state, "rag_email_path".to_string());
                            ui.label("Supports: legacy formats (MBOX, PST, OST) from Outlook/Thunderbird.".to_string()).classes("text-xs text-gray-400".to_string());
                        }
                        let _ctx = ui.tab_panel("directory".to_string());
                        let _ctx = ui.column().classes("w-full gap-3".to_string());
                        {
                            ui.input("Directory Path".to_string(), /* placeholder= */ "C:/Users/YourName/Documents".to_string()).props("outlined".to_string()).classes("w-full".to_string()).bind_value(app_state, "rag_dir".to_string());
                            let _ctx = ui.row().classes("w-full gap-2".to_string());
                            {
                                ui.number("Max Files".to_string(), /* value= */ 1000, /* min= */ 1, /* max= */ 10000).props("outlined dense".to_string()).classes("w-24".to_string()).bind_value(app_state, "rag_max_files".to_string());
                                ui.label("files to index".to_string()).classes("text-sm text-gray-400 self-center".to_string());
                            }
                            ui.label("Supports: .txt, .md, .py, .pdf, .docx, .png, .jpg".to_string()).classes("text-xs text-gray-400".to_string());
                        }
                    }
                }
                ui.separator().classes("my-4".to_string());
                let mut progress_section = ui.column().classes("w-full gap-2".to_string());
                {
                    let mut progress_label = ui.label("".to_string()).classes("text-sm font-medium text-blue-600 dark:text-blue-400".to_string());
                    let mut progress_bar = ui.linear_progress(/* value= */ 0, /* show_value= */ true).classes("w-full".to_string());
                    progress_bar.visible = false;
                    let mut stats_label = ui.label("".to_string()).classes("text-xs text-gray-500".to_string());
                }
                app_state["rag_progress_label".to_string()] = progress_label;
                app_state["rag_progress_bar".to_string()] = progress_bar;
                app_state["rag_stats_label".to_string()] = stats_label;
                let mut summary_container = ui.column().classes("w-full mt-2".to_string());
            }
            let reset_view = || {
                content_container.visible = true;
                summary_container.clear();
            };
            // TODO: from zena_mode.scraper import WebsiteScraper
            // TODO: from zena_mode.email_ingestor import EmailIngestor
            let start_scan = || {
                // Start scan.
                content_container.visible = false;
                progress_bar.visible = true;
                progress_bar.value = 0;
                progress_label.text = "🔍 Initializing...".to_string();
                stats_label.text = "".to_string();
                summary_container.clear();
                let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                let mut mode = app_state.get(&"rag_mode".to_string()).cloned().unwrap_or("website".to_string());
                let mut docs = vec![];
                // try:
                {
                    if mode == "website".to_string() {
                        let mut url = app_state.get(&"rag_url".to_string()).cloned().unwrap_or("".to_string());
                        let mut max_pages = app_state.get(&"rag_max_pages".to_string()).cloned().unwrap_or(50).to_string().parse::<i64>().unwrap_or(0);
                        if !url {
                            return Err(anyhow::anyhow!("Exception('Please enter a valid URL')"));
                        }
                        progress_label.text = format!("🌐 Scanning {}...", url);
                        let run_scraper_thread = || {
                            let mut scraper = WebsiteScraper(url);
                            scraper::scrape(/* max_pages= */ max_pages, /* progress_callback= */ None)
                        };
                        let mut result = asyncio.to_thread(run_scraper_thread).await;
                        if !result["success".to_string()] {
                            return Err(anyhow::anyhow!("Exception(result.get('error', 'Unknown scraping error'))"));
                        }
                        let mut docs = result["documents".to_string()];
                        if !docs {
                            return Err(anyhow::anyhow!("Exception('No content found on website')"));
                        }
                    } else if mode == "email".to_string() {
                        let mut path = app_state.get(&"rag_email_path".to_string()).cloned().unwrap_or("".to_string());
                        if !path {
                            return Err(anyhow::anyhow!("Exception('Please enter an archive path')"));
                        }
                        progress_label.text = format!("📧 Parsing email archive: {}...", path);
                        let run_email_thread = || {
                            let mut ingestor = EmailIngestor();
                            ingestor.ingest(path)
                        };
                        let mut docs = asyncio.to_thread(run_email_thread).await;
                        if !docs {
                            return Err(anyhow::anyhow!("Exception('No emails found or format unsupported')"));
                        }
                    } else if mode == "directory".to_string() {
                        return Err(anyhow::anyhow!("Exception('Directory scan not fully wired in this snippet')"));
                    }
                    progress_bar.value = 0.5_f64;
                    progress_label.text = format!("🧠 Indexing {} items...", docs.len());
                    if /* hasattr(rag_system, "build_index_async".to_string()) */ true {
                        rag_system.build_index_async(docs).await;
                    } else {
                        asyncio.to_thread(rag_system.build_index, docs).await;
                    }
                    let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
                    progress_bar.value = 1.0_f64;
                    let mut breakdown = HashMap::new();
                    let mut images = 0;
                    let mut total_chars = docs.iter().map(|d| d["content".to_string()].len()).collect::<Vec<_>>().iter().sum::<i64>();
                    let mut total_size = format!("{:.1} KB", (total_chars / 1024));
                    breakdown["Web Pages".to_string()] = docs.len();
                    let mut real_stats = HashMap::from([("files".to_string(), docs.len()), ("chunks".to_string(), if /* hasattr(rag_system, "ntotal".to_string()) */ true { rag_system.ntotal } else { (docs.len() * 5) }), ("images".to_string(), images), ("total_size".to_string(), total_size), ("time_taken".to_string(), elapsed), ("breakdown".to_string(), breakdown)]);
                    progress_section.visible = false;
                    content_container.visible = false;
                    render_rag_summary(real_stats, summary_container, /* on_reset= */ reset_view, /* on_close= */ rag_dialog.close);
                    ui.notify(format!("Successfully indexed {} pages!", docs.len()), /* color= */ "positive".to_string());
                }
                // except Exception as e:
            };
            let _ctx = ui.column().classes("w-full p-6 pt-2 border-t dark:border-slate-800".to_string());
            let _ctx = ui.row().classes("w-full gap-2".to_string());
            {
                ui.button("Start Scan".to_string(), /* icon= */ "search".to_string(), /* on_click= */ start_scan).props("color=primary unelevated".to_string()).classes("flex-grow".to_string());
                ui.button("Close".to_string(), /* on_click= */ rag_dialog.close).props("flat".to_string()).classes("text-gray-500".to_string());
            }
        } else {
            ui.label("RAG not enabled in Zena mode".to_string()).classes("text-center text-gray-400".to_string());
            ui.button("Close".to_string(), /* on_click= */ rag_dialog.close).props("flat".to_string()).classes("w-full mt-2".to_string());
        }
    }
    Ok(rag_dialog)
}
