use anyhow::{Result, Context};
use crate::registry::{UI_IDS};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Run a spotlight tour of the interface.
pub async fn start_tutorial(client: String) -> Result<()> {
    // Run a spotlight tour of the interface.
    ui.notify("🚀 Starting Guided Tour...".to_string(), /* color= */ "accent".to_string());
    ui.add_head_html("\n        <style>\n            .spotlight {\n                position: relative;\n                z-index: 9999 !important;\n                box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.75) !important;\n                pointer-events: none;\n                border-radius: 8px;\n                transition: all 0.5s ease;\n            }\n        </style>\n    ".to_string());
    let mut steps = vec![HashMap::from([("id".to_string(), None), ("msg".to_string(), "👋 **Welcome to ZenAI!**<br>I'm your local AI powerhouse.<br>Let me show you around.".to_string())]), HashMap::from([("id".to_string(), format!("#{}", UI_IDS.INPUT_CHAT)), ("msg".to_string(), "💬 **Chat Input**<br>Type here to chat, or use **Drag & Drop** to analyze files.".to_string())]), HashMap::from([("id".to_string(), format!("#{}", UI_IDS.BTN_BATCH_START)), ("msg".to_string(), "🏗️ **Batch Mode**<br>Analyze entire folders of code at once.".to_string())]), HashMap::from([("id".to_string(), "ui-drawer-btn".to_string()), ("msg".to_string(), "📂 **Sidebar**<br>Access settings, models, and RAG configuration here.".to_string())])];
    let mut tour_dialog = ui.dialog();
    let _ctx = ui.card().classes("w-96 items-center text-center".to_string());
    {
        let mut lbl = ui.markdown().classes("text-lg mb-4".to_string());
        ui.button("Next".to_string(), /* on_click= */ || tour_dialog.submit(true));
    }
    tour_dialog.open();
    for step in steps.iter() {
        lbl.content = step["msg".to_string()];
        if step["id".to_string()] {
            ui.run_javascript(format!("document.querySelector('{}').classList.add('spotlight');", step["id".to_string()]));
        }
        tour_dialog.await;
        tour_dialog.open();
        if step["id".to_string()] {
            ui.run_javascript(format!("document.querySelector('{}').classList.remove('spotlight');", step["id".to_string()]));
        }
    }
    tour_dialog.close();
    Ok(ui.notify("✨ Tour Complete! You're ready to go.".to_string(), /* color= */ "positive".to_string()))
}
