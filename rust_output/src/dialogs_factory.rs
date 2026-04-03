use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Factory for creating application dialogs.
#[derive(Debug, Clone)]
pub struct DialogsFactory {
}

impl DialogsFactory {
    /// Creates reusable dialogs (Model Download, Llama Update, Settings).
    /// Returns a dict referencing them: {'model': dialog, 'llama': dialog, 'settings': dialog}
    pub fn setup_common_dialogs(backend: String, app_state: String, on_settings_save: String, on_language_change: String, on_dark_mode: String) -> Result<()> {
        // Creates reusable dialogs (Model Download, Llama Update, Settings).
        // Returns a dict referencing them: {'model': dialog, 'llama': dialog, 'settings': dialog}
        let mut locale = get_locale();
        let mut dialogs = HashMap::new();
        let mut model_dialog = ui.dialog();
        let _ctx = ui.card().classes("w-full max-w-lg p-6 bg-white dark:bg-slate-800".to_string());
        {
            ui.label(locale.MODEL_CUSTOM_DOWNLOAD).classes(("text-lg font-bold mb-4 ".to_string() + Styles.TEXT_PRIMARY));
            let mut repo_input = ui.input("HuggingFace Repo".to_string(), /* placeholder= */ "TheBloke/Llama-2-7B-Chat-GGUF".to_string()).classes("w-full mb-2".to_string()).props("outlined dense".to_string());
            let mut file_input = ui.input("Filename".to_string(), /* placeholder= */ "llama-2-7b-chat::Q4_K_M.gguf".to_string()).classes("w-full mb-4".to_string()).props("outlined dense".to_string());
            let download_custom = || {
                // Download custom.
                let mut repo = repo_input.value.trim().to_string();
                let mut filename = file_input.value.trim().to_string();
                if (!repo || !filename) {
                    ui.notify("Please fill in both fields".to_string(), /* color= */ "warning".to_string());
                    return;
                }
                model_dialog.close();
                // TODO: import asyncio
                // TODO: import requests
                ui.notify(format!("⬇️ Requesting: {}...", filename), /* color= */ "info".to_string());
                // try:
                {
                    let mut response = asyncio.to_thread(requests.post, "http://127.0.0.1:8002/models/download".to_string(), /* json= */ HashMap::from([("repo_id".to_string(), repo), ("filename".to_string(), filename)]), /* timeout= */ 5).await;
                    if response.status_code == 200 {
                        ui.notify("✅ Download started!".to_string(), /* color= */ "positive".to_string());
                    } else {
                        ui.notify(format!("❌ Failed: {}", response.text), /* color= */ "negative".to_string());
                    }
                }
                // except Exception as e:
            };
            let _ctx = ui.row().classes("w-full justify-end gap-2".to_string());
            {
                ui.button(locale.BTN_CANCEL, /* on_click= */ model_dialog.close).props("flat color=grey".to_string());
                ui.button(locale.BTN_DOWNLOAD, /* on_click= */ download_custom).props("unelevated color=primary".to_string());
            }
        }
        dialogs["model".to_string()] = model_dialog;
        // TODO: from ui.settings_dialog import create_settings_dialog
        let mut settings_dialog = create_settings_dialog(/* on_save= */ on_settings_save, /* on_language_change= */ on_language_change, /* on_dark_mode_change= */ on_dark_mode);
        dialogs["settings".to_string()] = settings_dialog;
        let mut llama_dialog = ui.dialog();
        {
            let _ctx = ui.card().classes("w-full max-w-md p-6 bg-white dark:bg-slate-800".to_string());
            {
                ui.label("Update AI Engine".to_string()).classes(("text-lg font-bold mb-2 ".to_string() + Styles.TEXT_PRIMARY));
                let mut info_label = ui.label("Checking version...".to_string()).classes("text-sm text-gray-500 mb-4".to_string());
                let run_update = || {
                    // Run update.
                    info_label.text = "Updating...".to_string();
                    // TODO: import asyncio
                    asyncio.sleep(2).await;
                    ui.notify("Update feature placeholder".to_string(), /* color= */ "info".to_string());
                    llama_dialog.close();
                };
                let _ctx = ui.row().classes("w-full justify-end gap-2".to_string());
                {
                    ui.button("Cancel".to_string(), /* on_click= */ llama_dialog.close).props("flat color=grey".to_string());
                    ui.button("Update Now".to_string(), /* on_click= */ run_update).props("unelevated color=primary".to_string());
                }
                llama_dialog.info_label = info_label;
            }
        }
        dialogs["llama".to_string()] = llama_dialog;
        Ok(dialogs)
    }
}
