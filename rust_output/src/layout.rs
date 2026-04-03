use anyhow::{Result, Context};
use crate::config_system::{config, EMOJI};
use crate::dashboard::{build_performance_dashboar};
use crate::examples::{EXAMPLES};
use crate::model_gallery::{create_model_gallery};
use crate::registry::{UI_IDS};
use crate::tour::{start_tutorial};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

/// Build the application header.
pub fn build_header(ui_state: String, drawer: String, locale: String, open_gallery: String) -> () {
    // Build the application header.
    let mut header = ui.header().classes(Styles.HEADER);
    {
        ui.button(/* on_click= */ || drawer.toggle(), /* icon= */ Icons.MENU).props("flat round id=ui-drawer-btn".to_string()).classes(Styles.TEXT_PRIMARY);
        let _ctx = ui.row().classes("items-center".to_string());
        {
            ui.label("ZenAI".to_string()).classes((("text-base md:text-lg font-bold ".to_string() + Styles.TEXT_ACCENT) + " ml-1 md:ml-2".to_string()));
        }
        ui.space();
        let _ctx = ui.row().classes("items-center gap-2".to_string());
        {
            let _ctx = ui.row().classes("items-center gap-1.5 px-3 py-1 rounded-full bg-gray-50/50 dark:bg-slate-800/50 border border-gray-100 dark:border-slate-700".to_string());
            {
                ui_state::status_dot = ui.label("●".to_string()).classes("text-green-500 animate-pulse text-[14px]".to_string()).props("id=header-status-dot".to_string());
                ui_state::status_indicator = ui.label("ONLINE".to_string()).classes("text-[10px] font-black tracking-widest text-green-500".to_string()).props("id=header-status-label".to_string());
            }
            ui_state::voice_status = ui.label("🎙️ REC".to_string()).classes("text-[10px] font-black tracking-widest text-red-500 animate-pulse hidden".to_string()).props("id=header-voice-label".to_string());
            if open_gallery {
                let _ctx = ui.button(/* icon= */ "smart_toy".to_string(), /* on_click= */ open_gallery).props("flat round dense".to_string()).classes((Styles.TEXT_MUTED + " hover:text-purple-500 transition-colors".to_string()));
                {
                    ui.tooltip("The Council (Models)".to_string());
                }
            }
            ui.button(/* icon= */ Icons.PERSON).props("flat round dense".to_string()).classes(Styles.TEXT_MUTED);
        }
        ui_state::status_text = ui.label(locale.CHAT_READY).classes((Styles.TEXT_SECONDARY + " text-xs md:text-sm ml-auto hidden xs:block".to_string()));
    }
    header
}

/// Build footer.
pub fn build_footer(ui_state: String, handlers: String, locale: String) -> Result<()> {
    // Build footer.
    let mut footer = ui.footer().classes("bg-transparent border-0 p-3 md:p-4".to_string());
    let _ctx = ui.column().classes("w-full max-w-3xl mx-auto gap-2".to_string());
    {
        ui_state::attachment_preview = ui.label("".to_string());
        ui_state::attachment_preview.set_visibility(false);
        ui_state::attachment_preview.classes("text-sm px-4 py-2 rounded-full self-start bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700".to_string());
        let _ctx = ui.card().classes("w-full p-3 rounded-3xl shadow-xl bg-white dark:bg-slate-800 border-2 border-gray-100 dark:border-slate-600 ".to_string()).props("flat".to_string());
        {
            let _ctx = ui.row().classes("items-center gap-2 w-full".to_string());
            {
                let mut uploader = ui.upload(/* on_upload= */ handlers::on_upload, /* auto_upload= */ true).classes("hidden".to_string());
                ui.button(/* on_click= */ || uploader.run_method("pickFiles".to_string()), /* icon= */ Icons.ATTACH).props(format!("flat round dense id={}", UI_IDS.BTN_ATTACH)).classes("text-gray-400 hover:text-blue-500 transition-colors".to_string());
                let mut placeholder_text = if config::zena_mode_enabled { /* getattr */ "Ask anything...".to_string() } else { /* getattr */ "Type a message...".to_string() };
                ui_state::user_input = ui.input(/* placeholder= */ placeholder_text).props(format!("borderless dense autogrow id={}", UI_IDS.INPUT_CHAT)).classes("flex-1 text-base bg-transparent".to_string());
                ui_state::user_input.on("keydown.enter.prevent".to_string(), || handlers::handle_send(ui_state::user_input.value));
                let setup_voice_devices = || {
                    // Initialize voice device selector.
                    // try:
                    {
                        // TODO: import httpx
                        let mut client = httpx.AsyncClient();
                        {
                            let mut response = client.get(&"http://localhost:8001/voice/devices".to_string()).cloned().await;
                            if response.status_code == 200 {
                                let mut data = response.json();
                                let mut input_devices = data.get(&"devices".to_string()).cloned().unwrap_or(vec![]).iter().filter(|d| d["is_input".to_string()]).map(|d| d).collect::<Vec<_>>();
                                let mut device_options = input_devices.iter().map(|d| (d["name".to_string()], d["id".to_string()])).collect::<HashMap<_, _>>();
                                if device_options {
                                    ui_state::mic_device_select.set_options(device_options);
                                    let mut default_id = data.get(&"default_device".to_string()).cloned();
                                    if default_id.is_some() {
                                        ui_state::mic_device_select.value = device_options.values().into_iter().collect::<Vec<_>>()[0];
                                    }
                                }
                            }
                        }
                    }
                    // except Exception as e:
                };
                ui_state::mic_device_select = ui.select(HashMap::new(), /* label= */ "🎤".to_string()).props("dense outlined".to_string()).classes("text-sm".to_string()).style("max-width: 200px; display: none;".to_string());
                ui_state::mic_device_select.tooltip = "Select microphone".to_string();
                ui.button(/* icon= */ Icons.RECORD, /* on_click= */ handlers::on_voice_click).props(format!("flat round dense id={}", UI_IDS.BTN_VOICE)).classes("text-gray-400 hover:text-purple-500 transition-colors".to_string()).tooltip("Click to toggle voice recording".to_string());
                ui.button(/* icon= */ Icons.SEND, /* on_click= */ || handlers::handle_send(ui_state::user_input.value)).props(format!("round dense unelevated id={}", UI_IDS.BTN_SEND)).classes("bg-gradient-to-r from-blue-500 to-violet-500 text-white w-10 h-10 shadow-md hover:shadow-lg transition-shadow".to_string());
            }
        }
    }
    Ok(footer)
}

/// Build the scrollable chat area.
pub fn build_chat_area(ui_state: String) -> () {
    // Build the scrollable chat area.
    ui_state::scroll_container = ui.scroll_area().classes("w-full".to_string()).style("height: calc(100vh - 160px); min-height: 250px;".to_string());
    let _ctx = ui_state::scroll_container;
    {
        ui_state::chat_log = ui.column().classes(((("w-full max-w-4xl mx-auto p-2 md:p-4 space-y-3 md:space-y-4 ".to_string() + Styles.CHAT_CONTAINER_LIGHT) + " ".to_string()) + Styles.CHAT_CONTAINER_DARK)).props("id=chat-log-container".to_string());
    }
    ui_state::scroll_container
}

/// Assemble the complete page layout.
pub fn build_page(ui_state: String, handlers: String, drawer_factory: String, rag_dialog_factory: String) -> () {
    // Assemble the complete page layout.
    let mut locale = get_locale();
    rag_dialog_factory();
    let mut gallery_dialog = create_model_gallery(ui_state, None);
    let mut drawer = drawer_factory();
    let mut header = build_header(ui_state, drawer, locale, /* open_gallery= */ gallery_dialog.open);
    build_performance_dashboard(ui_state);
    build_chat_area(ui_state);
    build_footer(ui_state, handlers, locale);
    if config::zena_mode_enabled {
        handlers::add_message("system".to_string(), format!(locale, "WELCOME_ZENAI".to_string(), /* source_msg= */ locale.WELCOME_SOURCE_KB));
    } else {
        handlers::add_message("system".to_string(), locale.WELCOME_DEFAULT);
    }
    let _ctx = ui_state::chat_log;
    let _ctx = ui.row().classes("w-full justify-center gap-2 mt-4 flex-wrap".to_string());
    {
        for item in EXAMPLES.iter() {
            let make_handler = |p| {
                ui_state::user_input.value = p;
                handlers::handle_send(p).await;
            };
            ui.button(item["title".to_string()], /* on_click= */ |p| make_handler(p)).props("outline rounded-full dense".to_string()).classes("text-[11px] px-3 py-1 normal-case hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors".to_string());
        }
    }
    HashMap::from([("header".to_string(), header), ("drawer".to_string(), drawer)])
}
