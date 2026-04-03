use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::model_data::{MODEL_INFO};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Retrieve metadata for a model filename.
pub fn get_model_metadata(filename: String) -> () {
    // Retrieve metadata for a model filename.
    MODEL_INFO.get(&filename).cloned().unwrap_or(HashMap::from([("name".to_string(), /* title */ filename.replace(&*".gguf".to_string(), &*"".to_string()).replace(&*"-".to_string(), &*" ".to_string()).to_string()), ("desc".to_string(), "Local GGUF Model".to_string()), ("size".to_string(), "Unknown".to_string()), ("icon".to_string(), "🤖".to_string()), ("good_for".to_string(), vec![]), ("speed".to_string(), "Unknown".to_string()), ("quality".to_string(), "Unknown".to_string())]))
}

/// Create the interactive Model Gallery (Council Chamber).
pub fn create_model_gallery(ui_state: String, app_state: String) -> Result<()> {
    // Create the interactive Model Gallery (Council Chamber).
    let mut dialog = ui.dialog();
    let _ctx = ui.card().classes("w-full max-w-4xl h-[80vh] bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700".to_string());
    {
        let _ctx = ui.row().classes("w-full items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-700".to_string());
        {
            ui.label("🤖 Council of LLMs".to_string()).classes("text-xl font-bold text-slate-800 dark:text-slate-100".to_string());
            ui.button(/* icon= */ "close".to_string(), /* on_click= */ dialog.close).props("flat round dense".to_string());
        }
        let mut grid_container = ui.grid(/* columns= */ 3).classes("w-full gap-4 p-4 overflow-y-auto flex-grow".to_string());
        let refresh_models = || {
            // Refresh models.
            grid_container.clear();
            // try:
            {
                let mut resp = /* reqwest::get( */&format!("http://127.0.0.1:{}/list", config::mgmt_port)).cloned().unwrap_or(/* timeout= */ 10);
                if resp.status_code == 200 {
                    let mut models = resp.json().get(&"models".to_string()).cloned().unwrap_or(vec![]);
                    let _ctx = grid_container;
                    {
                        for model_file in models::iter() {
                            let mut meta = get_model_metadata(model_file);
                            let _ctx = ui.card().classes("flex flex-col gap-2 p-3 hover:shadow-lg transition-shadow bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 h-[180px] justify-between relative overflow-hidden group".to_string());
                            {
                                let _ctx = ui.row().classes("items-start gap-3 w-full".to_string());
                                {
                                    let _ctx = ui.column().classes("w-12 h-12 flex-shrink-0 items-center justify-center bg-slate-100 dark:bg-slate-700 rounded-lg overflow-hidden".to_string());
                                    {
                                        ui.label(meta["icon".to_string()]).classes("text-3xl select-none transform transition-transform group-hover:scale-110".to_string());
                                    }
                                    let _ctx = ui.column().classes("gap-0 flex-grow min-w-0".to_string());
                                    {
                                        ui.label(meta["name".to_string()]).classes("font-bold text-slate-800 dark:text-slate-100 text-sm leading-tight truncate w-full".to_string()).props(format!("title=\"{}\"", meta["name".to_string()]));
                                        ui.label(meta["size".to_string()]).classes("text-[10px] text-slate-400".to_string());
                                    }
                                }
                                ui.label(meta["desc".to_string()]).classes("text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed".to_string());
                                let _ctx = ui.row().classes("gap-1 flex-wrap".to_string());
                                {
                                    for tag in meta.get(&"good_for".to_string()).cloned().unwrap_or(vec![])[..2].iter() {
                                        ui.label(tag).classes("text-[9px] px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 rounded-md border border-blue-100 dark:border-blue-800/50".to_string());
                                    }
                                }
                                ui.separator().classes("my-0 opacity-50".to_string());
                                let _ctx = ui.row().classes("w-full justify-end gap-2".to_string());
                                {
                                    let swap = |m| {
                                        ui.notify(format!("Swapping to {}...", m), /* color= */ "orange".to_string());
                                        /* reqwest::post( */format!("http://127.0.0.1:{}/swap", config::mgmt_port), /* json= */ HashMap::from([("model".to_string(), m)]), /* timeout= */ 30);
                                        dialog.close();
                                    };
                                    ui.button("Swap".to_string(), /* on_click= */ swap).props("outline size=sm color=orange".to_string());
                                    let launch = |m| {
                                        // Launch.
                                        ui.notify(format!("Summoning Expert: {}...", m), /* color= */ "purple".to_string());
                                        /* reqwest::post( */format!("http://127.0.0.1:{}/swarm/launch", config::mgmt_port), /* json= */ HashMap::from([("model".to_string(), m), ("port".to_string(), 8005)]), /* timeout= */ 30);
                                        ui.notify("Expert Summoned!".to_string(), /* color= */ "positive".to_string());
                                    };
                                    ui.button("Summon".to_string(), /* on_click= */ launch).props("unelevated size=sm color=purple".to_string());
                                }
                            }
                        }
                    }
                }
            }
            // except Exception as e:
        };
        refresh_models();
        dialog.open();
        dialog
    }
}
