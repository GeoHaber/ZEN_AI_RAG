/// ui_test_stub.py - Professional UI Test Harness for ZenAI (v4)
/// 
/// Features:
/// - Proper NiceGUI dark mode API
/// - API response logging
/// - Stress Test popup with accelerating speed
/// - Complete action matrix coverage

use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub const ROOT: &str = "Path(file!()).parent.parent";

pub const DARK_BG: &str = "#0f172a";

pub const LIGHT_BG: &str = "#ffffff";

pub static STATE: std::sync::LazyLock<TestState> = std::sync::LazyLock::new(|| Default::default());

pub static MODELS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static DARK_MODE_CTRL: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static HEADER_PANEL: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static DRAWER_PANEL: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static FOOTER_PANEL: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static WINDOW_SIZES: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub static ALL_ACTIONS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub static STRESS_PHASES: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

/// TestState class.
#[derive(Debug, Clone)]
pub struct TestState {
}

/// Log action with API call and response.
pub fn log(action: String, api_call: String, response: String) -> Result<()> {
    // Log action with API call and response.
    let mut ts = datetime::now().strftime("%H:%M:%S.%f".to_string())[..-3];
    if api_call {
        let mut entry = format!("[{}] {}: {} → {}", ts, action, api_call, response);
    } else {
        let mut entry = format!("[{}] {}", ts, action);
    }
    println!("{}", entry);
    state::logs.push(entry);
    state::action_count += 1;
    if state::logs.len() > 200 {
        state::logs = state::logs[-200..];
    }
    // try:
    {
        log_panel.refresh();
    }
    // except Exception as _e:
}

/// Update Quasar component props based on state.
pub fn update_theme() -> () {
    // Update Quasar component props based on state.
    if !(header_panel && drawer_panel && footer_panel) {
        return;
    }
    if state::is_dark {
        header_panel.props("dark".to_string());
        drawer_panel.props("dark".to_string());
        footer_panel.props("dark".to_string());
    } else {
        header_panel.props(/* remove= */ "dark".to_string());
        drawer_panel.props(/* remove= */ "dark".to_string());
        footer_panel.props(/* remove= */ "dark".to_string());
    }
    log("THEME_UPDATE".to_string(), format!("Props updated for dark={}", state::is_dark), "OK".to_string());
}

/// Use proper NiceGUI dark mode API.
pub fn set_dark_mode(enable: bool) -> Result<()> {
    // Use proper NiceGUI dark mode API.
    // global/nonlocal dark_mode_ctrl
    if dark_mode_ctrl.is_none() {
        return;
    }
    if enable {
        dark_mode_ctrl.enable();
        state::is_dark = true;
        log("DARK_MODE".to_string(), "dark_mode.enable()".to_string(), "true".to_string());
    } else {
        dark_mode_ctrl.disable();
        state::is_dark = false;
        log("DARK_MODE".to_string(), "dark_mode.disable()".to_string(), "false".to_string());
    }
    update_theme();
    // try:
    {
        drawer_content.refresh();
    }
    // except Exception as _e:
}

pub fn toggle_dark_mode() -> () {
    set_dark_mode(!state::is_dark);
}

pub fn toggle_tts() -> () {
    state::tts_on = !state::tts_on;
    log("TTS".to_string(), format!("state::tts_on = {}", state::tts_on), "OK".to_string());
}

pub fn toggle_rag() -> () {
    state::rag_on = !state::rag_on;
    log("RAG".to_string(), format!("state::rag_on = {}", state::rag_on), "OK".to_string());
}

pub fn select_model(m: String) -> () {
    log("MODEL".to_string(), format!("select('{}')", m), "OK".to_string());
}

/// Send message.
pub fn send_message(text: String) -> Result<()> {
    // Send message.
    if !text.trim().to_string() {
        return;
    }
    log("USER_MSG".to_string(), if text.len() > 30 { format!("send('{}...')", text[..30]) } else { format!("send('{}')", text) }, "Queued".to_string());
    state::messages.push(HashMap::from([("role".to_string(), "user".to_string()), ("text".to_string(), text), ("is_rag".to_string(), false)]));
    let mut is_rag_reply = state::rag_on;
    if is_rag_reply {
        let mut reply = format!("Thinking with RAG...\nFound context in {} files.\nHere is the answer based on your data: {}", random.randint(1, 4), text);
    } else {
        let mut reply = random.choice(vec!["Mock response OK".to_string(), "Test reply ✓".to_string(), "Bot says hello! 🤖".to_string()]);
    }
    state::messages.push(HashMap::from([("role".to_string(), "bot".to_string()), ("text".to_string(), reply), ("is_rag".to_string(), is_rag_reply)]));
    log("BOT_REPLY".to_string(), format!("mock_reply('{}...', rag={})", reply[..20], is_rag_reply), "Sent".to_string());
    // try:
    {
        chat_panel::refresh();
    }
    // except Exception as _e:
}

pub fn menu_click(item: String) -> () {
    log("MENU".to_string(), format!("click('{}')", item), "OK".to_string());
}

pub fn voice_click() -> () {
    log("VOICE".to_string(), "button.click()".to_string(), "Recording mock".to_string());
}

/// Clear chat.
pub fn clear_chat() -> Result<()> {
    // Clear chat.
    state::messages = vec![];
    log("CLEAR".to_string(), "messages.clear()".to_string(), "OK".to_string());
    // try:
    {
        chat_panel::refresh();
    }
    // except Exception as _e:
}

pub fn toggle_drawer() -> () {
    state::drawer_open = !state::drawer_open;
    log("DRAWER".to_string(), format!("toggle() → {}", if state::drawer_open { "OPEN".to_string() } else { "CLOSED".to_string() }), "OK".to_string());
    drawer_panel.toggle();
}

pub fn scan_action() -> () {
    log("SCAN".to_string(), "rag_scan.start()".to_string(), "Mock started".to_string());
}

pub fn notify_test() -> () {
    ui.notify("Test notification!".to_string(), /* color= */ "info".to_string(), /* position= */ "top".to_string());
    log("NOTIFY".to_string(), "ui.notify('Test')".to_string(), "Shown".to_string());
}

/// Resize browser viewport simulation via CSS.
pub async fn resize_window(width: i64, height: i64, name: String) -> Result<()> {
    // Resize browser viewport simulation via CSS.
    // try:
    {
        let mut js = format!("\n        document.body.style.maxWidth = \"{}px\";\n        document.body.style.margin = \"0 auto\";\n        document.body.style.border = \"4px solid #333\";\n        document.body.style.boxShadow = \"0 0 20px rgba(0,0,0,0.5)\";\n        window.dispatchEvent(new Event('resize'));\n        ", width);
        if width >= 1920 {
            let mut js = "\n            document.body.style.maxWidth = \"\";\n            document.body.style.margin = \"\";\n            document.body.style.border = \"\";\n            document.body.style.boxShadow = \"\";\n            window.dispatchEvent(new Event('resize'));\n            ".to_string();
        }
        ui.run_javascript(js).await;
        log("RESIZE".to_string(), format!("Viewport -> {}x{}", width, height), format!("{}", name));
    }
    // except Exception as e:
}

/// Trigger random resize.
pub fn resize_random() -> () {
    // Trigger random resize.
    let (mut w, mut h, mut name) = random.choice(WINDOW_SIZES);
    asyncio.create_task(resize_window(w, h, name));
}

/// Run accelerating stress test through all phases.
pub async fn run_stress_test() -> Result<()> {
    // Run accelerating stress test through all phases.
    if state::stress_running {
        log("STRESS".to_string(), "Already running!".to_string(), "SKIP".to_string());
        return;
    }
    state::stress_running = true;
    state::action_count = 0;
    log("STRESS".to_string(), "=== STRESS TEST STARTED ===".to_string(), "".to_string());
    // try:
    {
        for (phase_idx, phase) in STRESS_PHASES.iter().enumerate().iter() {
            state::stress_phase = (phase_idx + 1);
            log("STRESS".to_string(), format!("Phase {}/5: {}", (phase_idx + 1), phase["name".to_string()]), format!("Delay={}s", phase["delay".to_string()]));
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time) < phase["duration".to_string()] {
                if state::stress_running {
                    continue;
                }
                log("STRESS".to_string(), "Stopped by user".to_string(), "ABORT".to_string());
                return;
                let (mut action_name, mut action_fn) = random.choice(ALL_ACTIONS);
                // try:
                {
                    action_fn();
                }
                // except Exception as e:
                asyncio.sleep(phase["delay".to_string()]).await;
            }
        }
        log("STRESS".to_string(), format!("=== COMPLETED: {} actions ===", state::action_count), "SUCCESS".to_string());
    }
    // finally:
        state::stress_running = false;
        Ok(state::stress_phase = 0)
}

pub fn stop_stress_test() -> () {
    state::stress_running = false;
    log("STRESS".to_string(), "Stop requested".to_string(), "Stopping...".to_string());
}

/// Action log panel.
pub fn log_panel() -> Result<()> {
    // Action log panel.
    let _ctx = ui.column().classes("w-full h-72 bg-gray-900 rounded p-2 overflow-y-auto font-mono text-xs".to_string());
    {
        for entry in state::logs[-20..].iter() {
            if entry.contains(&"ERROR".to_string()) {
                let mut color = "text-red-400".to_string();
            } else if entry.contains(&"STRESS".to_string()) {
                let mut color = "text-yellow-400".to_string();
            } else if (entry.contains(&"API".to_string()) || entry.contains(&"→".to_string())) {
                let mut color = "text-cyan-400".to_string();
            } else {
                let mut color = "text-green-400".to_string();
            }
            ui.label(entry).classes(format!("{} whitespace-nowrap", color));
        }
    }
}

/// Chat messages panel.
pub fn chat_panel() -> () {
    // Chat messages panel.
    let _ctx = ui.column().classes("w-full gap-2".to_string());
    {
        if !state::messages {
            ui.label("Send a message...".to_string()).classes("text-gray-400 italic text-sm".to_string());
        }
        for msg in state::messages[-8..].iter() {
            let mut is_rag = msg.get(&"is_rag".to_string()).cloned().unwrap_or(false);
            let mut bg_class = if is_rag { "bg-green-100 dark:bg-green-900 border-green-500".to_string() } else { "bg-gray-100 dark:bg-slate-600".to_string() };
            if msg["role".to_string()] == "user".to_string() {
                let _ctx = ui.row().classes("w-full justify-end".to_string());
                {
                    ui.label(msg["text".to_string()]).classes("bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100 p-2 rounded-lg max-w-[80%]".to_string());
                }
            } else {
                let _ctx = ui.row().classes("w-full justify-start items-start gap-2".to_string());
                {
                    if is_rag {
                        ui.icon("auto_awesome".to_string()).classes("text-green-500 mt-1".to_string());
                    }
                    ui.label(msg["text".to_string()]).classes(format!("{} text-gray-800 dark:text-gray-100 p-2 rounded-lg max-w-[80%] whitespace-pre-wrap", bg_class));
                }
            }
        }
    }
}

/// Stress test status display.
pub fn stress_status() -> () {
    // Stress test status display.
    if state::stress_running {
        ui.label(format!("🔥 STRESS TEST: Phase {}/5 | Actions: {}", state::stress_phase, state::action_count)).classes("text-yellow-400 font-bold".to_string());
    } else {
        ui.label("Ready for testing".to_string()).classes("text-gray-400".to_string());
    }
}

/// Drawer content that refreshes on theme change.
pub fn drawer_content() -> () {
    // Drawer content that refreshes on theme change.
    let mut text_class = if state::is_dark { "text-white".to_string() } else { "text-gray-800".to_string() };
    let mut btn_text_class = if state::is_dark { "text-white".to_string() } else { "text-gray-700".to_string() };
    ui.label("Menu".to_string()).classes(format!("text-lg font-bold mb-4 {}", text_class));
    for item in vec!["Home".to_string(), "Settings".to_string(), "Scan Folder".to_string(), "Download Model".to_string(), "About".to_string()].iter() {
        ui.button(item, /* icon= */ "chevron_right".to_string(), /* on_click= */ |i| menu_click(i)).props("flat align=left".to_string()).classes(format!("w-full justify-start mb-1 {}", btn_text_class));
    }
    ui.separator().classes("my-4".to_string());
    ui.label("Model".to_string()).classes(format!("font-bold mb-2 {}", text_class));
    ui.select(MODELS, /* value= */ MODELS[2], /* on_change= */ |e| select_model(e.value)).classes("w-full".to_string());
}

/// Create stress dialog.
pub fn create_stress_dialog() -> () {
    // Create stress dialog.
    let mut dialog = ui.dialog();
    let _ctx = ui.card().classes("p-6 w-[500px]".to_string());
    {
        ui.label("🧪 UI Stress Test".to_string()).classes("text-2xl font-bold mb-4".to_string());
        ui.markdown("\n**This test will:**\n1. Run ALL possible UI actions randomly\n2. Start SLOW (1s delay) → Get FASTER (0.05s delay)\n3. 5 phases, ~40 seconds total\n4. Log every action and API response\n\n**Purpose:** Find UI bugs, race conditions, and crashes.\n        ".to_string()).classes("mb-4".to_string());
        let _ctx = ui.card().classes("bg-gray-100 dark:bg-slate-800 p-3 mb-4".to_string());
        {
            ui.label("Phases:".to_string()).classes("font-bold mb-2".to_string());
            for (i, p) in STRESS_PHASES.iter().enumerate().iter() {
                ui.label(format!("{}. {}: {}s @ {}s delay", (i + 1), p["name".to_string()], p["duration".to_string()], p["delay".to_string()])).classes("text-sm font-mono".to_string());
            }
        }
        let _ctx = ui.row().classes("gap-2 w-full".to_string());
        {
            ui.button("🚀 START".to_string(), /* on_click= */ || vec![dialog.close(), asyncio.create_task(run_stress_test())]).props("color=positive".to_string()).classes("flex-grow".to_string());
            ui.button("Cancel".to_string(), /* on_click= */ dialog.close).props("flat".to_string());
        }
    }
    dialog
}

/// Helper: setup phase for build_ui.
pub fn _do_build_ui_setup() -> () {
    // Helper: setup phase for build_ui.
    // global/nonlocal dark_mode_ctrl, header_panel, drawer_panel, footer_panel
    let mut dark_mode_ctrl = ui.dark_mode(true);
    let mut stress_dialog = create_stress_dialog();
    let mut header_panel = ui.header().classes("p-3 shadow-sm transition-all duration-300".to_string());
    header_panel.classes("bg-white dark:bg-slate-800 text-gray-800 dark:text-white border-b border-gray-200 dark:border-slate-700".to_string());
    let _ctx = header_panel;
    let _ctx = ui.row().classes("w-full items-center justify-between".to_string());
    {
        ui.button(/* icon= */ "menu".to_string(), /* on_click= */ || drawer_panel.toggle()).props("flat".to_string()).classes("text-gray-700 dark:text-white".to_string());
        ui.button(/* icon= */ "dark_mode".to_string(), /* on_click= */ toggle_dark_mode).props("flat".to_string()).classes("text-gray-700 dark:text-white".to_string()).tooltip("Toggle Dark/Light".to_string());
        ui.label("ZenAI".to_string()).classes("text-xl font-bold text-gray-800 dark:text-white".to_string());
        let _ctx = ui.row().classes("gap-2 items-center".to_string());
        {
            ui.button(/* icon= */ "volume_up".to_string(), /* on_click= */ toggle_tts).props("flat".to_string()).classes("text-gray-700 dark:text-white".to_string()).tooltip("TTS".to_string());
            let mut scan_button = ui.button("Start Scanning".to_string(), /* icon= */ "book".to_string(), /* on_click= */ scan_action).props("flat".to_string()).classes("text-blue-600 dark:text-blue-400".to_string());
            scan_button.visible = false;
            let on_rag_toggle = |e| {
                // On rag toggle.
                state::rag_on = e.value;
                scan_button.visible = e.value;
                let mut status = if e.value { "enabled".to_string() } else { "disabled".to_string() };
                ui.notify(format!("RAG mode {}", status), /* color= */ if e.value { "positive".to_string() } else { "info".to_string() });
                log("RAG".to_string(), format!("toggle({})", e.value), format!("scan_button.visible={}", e.value));
            };
            ui.switch("Scan & Learn".to_string(), /* value= */ false, /* on_change= */ on_rag_toggle).props("color=cyan keep-color".to_string()).classes("text-gray-700 dark:text-white".to_string());
            ui.button("🧪 STRESS".to_string(), /* on_click= */ stress_dialog.open).props("color=warning dense".to_string());
        }
    }
    let mut drawer_panel = ui.left_drawer(/* value= */ true).classes("p-4 transition-all duration-300".to_string());
    drawer_panel.classes("bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-white".to_string());
    let _ctx = drawer_panel;
    {
        drawer_content();
    }
}

/// Build the professional test UI.
pub fn build_ui() -> () {
    // Build the professional test UI.
    _do_build_ui_setup();
    let _ctx = ui.row().classes("w-full flex-grow p-4 gap-4 main-content-row".to_string());
    {
        let _ctx = ui.column().classes("w-full md:w-1/2 gap-4 content-col".to_string());
        {
            ui.label("💬 Chat".to_string()).classes("text-lg font-bold".to_string());
            let _ctx = ui.card().classes("w-full min-h-60".to_string());
            {
                chat_panel();
            }
        }
        let _ctx = ui.column().classes("w-full md:w-1/2 gap-2 content-col".to_string());
        {
            ui.label("📟 Action Log".to_string()).classes("text-lg font-bold".to_string());
            stress_status();
            log_panel();
            let _ctx = ui.row().classes("gap-2 mt-2".to_string());
            {
                ui.button("Run Random".to_string(), /* icon= */ "shuffle".to_string(), /* on_click= */ || asyncio.create_task(run_random_quick())).props("color=primary".to_string());
                ui.button("Stop".to_string(), /* icon= */ "stop".to_string(), /* on_click= */ stop_stress_test).props("color=negative flat".to_string());
                ui.button("Clear Log".to_string(), /* on_click= */ || vec![state::logs.clear(), log_panel.refresh()]).props("flat".to_string());
            }
        }
    }
    let mut footer_panel = ui.footer().classes("p-3 transition-all duration-300".to_string());
    footer_panel.classes("bg-white dark:bg-slate-800 text-gray-800 dark:text-white border-t border-gray-200 dark:border-slate-700".to_string());
    let _ctx = footer_panel;
    let _ctx = ui.row().classes("w-full items-center gap-2".to_string());
    {
        ui.button(/* icon= */ "mic".to_string(), /* on_click= */ voice_click).props("round color=primary".to_string());
        let mut msg_input = ui.input(/* placeholder= */ "Type a message...".to_string()).classes("flex-grow bg-white dark:bg-slate-900 rounded".to_string()).props("outlined dense".to_string());
        let do_send = || {
            if msg_input.value {
                send_message(msg_input.value);
                msg_input.value = "".to_string();
            }
        };
        msg_input.on("keydown.enter".to_string(), do_send);
        ui.button(/* icon= */ "send".to_string(), /* on_click= */ do_send).props("round color=primary".to_string());
        ui.button("Clear".to_string(), /* on_click= */ clear_chat).props("flat color=grey".to_string());
    }
    set_dark_mode(true);
    update_theme();
    ui.add_head_html("\n    <script>\n    window.addEventListener('error', function(e) {\n        console.log('[JS_ERROR]', e.message, e.filename, e.lineno);\n    });\n    window.addEventListener('unhandledrejection', function(e) {\n        console.log('[JS_PROMISE_ERROR]', e.reason);\n    });\n    </script>\n    ".to_string());
    log("SETUP".to_string(), "JavaScript error handlers".to_string(), "Installed".to_string());
}

/// Resize app simulation via CSS injection for fixed elements.
pub async fn resize_window(width: i64, height: i64, name: String) -> Result<()> {
    // Resize app simulation via CSS injection for fixed elements.
    // try:
    {
        if width >= 1920 {
            let mut css = "\n            document.body.style.maxWidth = '';\n            document.body.style.margin = '';\n            document.body.style.border = '';\n            \n            // Reset layout container\n            var layout = document.querySelector('.q-layout');\n            if(layout) layout::style.maxWidth = '';\n            if(layout) layout::style.margin = '';\n\n            // Fix header/footer width\n            document.querySelectorAll('.q-header, .q-footer, .q-drawer').forEach(el => {\n                el.style.maxWidth = '';\n                el.style.left = '';\n                el.style.right = '';\n                el.style.width = '';\n            });\n            window.dispatchEvent(new Event('resize'));\n            ".to_string();
        } else {
            let mut css = format!("\n            document.body.style.maxWidth = '{}px';\n            document.body.style.margin = '0 auto';\n            document.body.style.border = '4px solid #F59E0B';\n            \n            // Constrain layout container\n            var layout = document.querySelector('.q-layout');\n            if(layout) layout::style.maxWidth = '{}px';\n            if(layout) layout::style.margin = '0 auto';\n            \n            // Force fixed elements to respect the new body width\n            document.querySelectorAll('.q-header, .q-footer').forEach(el => {{\n                el.style.maxWidth = '{}px';\n                el.style.left = '50%';\n                el.style.transform = 'translateX(-50%)';\n                el.style.width = '100%';\n            }});\n            \n            window.dispatchEvent(new Event('resize'));\n            ", width, width, width);
        }
        let mut is_mobile = width < 800;
        let mut js_layout = format!("\n        const mainRow = document.querySelector('.main-content-row');\n        const cols = document.querySelectorAll('.content-col');\n        \n        if ({}) {{\n            // Mobile: Stack vertically\n            if(mainRow) {{\n                mainRow.classList.remove('flex-row', 'gap-4');\n                mainRow.classList.add('flex-col', 'gap-2');\n            }}\n            cols.forEach(c => {{\n                c.classList.remove('w-1/2'); // Remove desktop width\n                c.classList.add('w-full');   // Force full width\n            }});\n        }} else {{\n            // Desktop: Side by side\n            if(mainRow) {{\n                mainRow.classList.remove('flex-col', 'gap-2');\n                mainRow.classList.add('flex-row', 'gap-4');\n            }}\n            cols.forEach(c => {{\n                c.classList.remove('w-full');\n                c.classList.add('w-1/2');\n            }});\n        }}\n        ", is_mobile.to_string().to_lowercase());
        ui.run_javascript(css).await;
        ui.run_javascript(js_layout).await;
        log("RESIZE".to_string(), format!("App -> {}px", width), format!("{} (Reflowed)", name));
    }
    // except Exception as e:
}

/// Quick random test (10 actions).
pub async fn run_random_quick() -> Result<()> {
    // Quick random test (10 actions).
    log("QUICK".to_string(), "=== Quick Random Test ===".to_string(), "".to_string());
    for i in 0..10.iter() {
        let (mut name, mut r#fn) = random.choice(ALL_ACTIONS);
        // try:
        {
            r#fn();
        }
        // except Exception as _e:
        asyncio.sleep(0.3_f64).await;
    }
    Ok(log("QUICK".to_string(), "=== Done ===".to_string(), "".to_string()))
}

/// Main.
pub fn main() -> () {
    // Main.
    let index = || {
        build_ui();
        log("STARTUP".to_string(), "UI Test Stub v4 ready!".to_string(), "Professional Edition".to_string());
    };
    println!("{}", "[UI Test Stub v4] Starting on port 8090...".to_string());
    ui.run(/* title= */ "ZenAI Test Stub v4".to_string(), /* port= */ 8090, /* reload= */ false);
}
