/// zena_mode/tutorial::py - Interactive Guided Tour for ZenAI
/// Provides step-by-step UI guidance with robust dialog management.

use anyhow::{Result, Context};
use crate::registry::{UI_IDS};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Manages the interactive guided tour sequence.
#[derive(Debug, Clone)]
pub struct UITutorial {
    pub client: String,
    pub current_step: i64,
    pub is_running: bool,
    pub dialog: Option<serde_json::Value>,
    pub title_label: Option<serde_json::Value>,
    pub message_label: Option<serde_json::Value>,
    pub btn_next: Option<serde_json::Value>,
    pub steps: Vec<HashMap<String, serde_json::Value>>,
}

impl UITutorial {
    /// Initialize instance.
    pub fn new(client: String) -> Self {
        Self {
            client,
            current_step: 0,
            is_running: false,
            dialog: None,
            title_label: None,
            message_label: None,
            btn_next: None,
            steps: vec![HashMap::from([("title".to_string(), "Welcome to ZenAI! 🚀".to_string()), ("message".to_string(), "Let's take a 1-minute tour of the key features.".to_string()), ("element_id".to_string(), None)]), HashMap::from([("title".to_string(), "The Brain (Chat Hub) 🧠".to_string()), ("message".to_string(), "Type your questions here. RAG searches your local docs first!".to_string()), ("element_id".to_string(), UI_IDS.INPUT_CHAT)]), HashMap::from([("title".to_string(), "Attach & Analyze 📎".to_string()), ("message".to_string(), "Upload PDFs or Images. I'll OCR them instantly.".to_string()), ("element_id".to_string(), UI_IDS.BTN_ATTACH)]), HashMap::from([("title".to_string(), "Voice Intelligence 🎙️".to_string()), ("message".to_string(), "Use the voice button for speech-to-text input.".to_string()), ("element_id".to_string(), UI_IDS.BTN_VOICE)]), HashMap::from([("title".to_string(), "Knowledge Management 📚".to_string()), ("message".to_string(), "Manage RAG sources, switch models, or toggle Swarm mode in the drawer.".to_string()), ("element_id".to_string(), "ui-drawer-btn".to_string())]), HashMap::from([("title".to_string(), "Settings ⚙️".to_string()), ("message".to_string(), "Configure language and AI behavior here.".to_string()), ("element_id".to_string(), UI_IDS.BTN_SETTINGS)]), HashMap::from([("title".to_string(), "Tour Complete! ✨".to_string()), ("message".to_string(), "You're all set. Ask me anything!".to_string()), ("element_id".to_string(), None)])],
        }
    }
    /// Begin the tour sequence.
    pub async fn start(&mut self) -> Result<()> {
        // Begin the tour sequence.
        if self.is_running {
            return;
        }
        self.is_running = true;
        self.current_step = 0;
        logger.info("[Tutorial] Starting guided tour...".to_string());
        // try:
        {
            let _ctx = self.client;
            {
                self._setup_dialog();
                self._run_step().await;
            }
        }
        // except Exception as e:
    }
    /// Creates the persistent dialog structure within the client context.
    pub fn _setup_dialog(&mut self) -> () {
        // Creates the persistent dialog structure within the client context.
        let mut self.dialog = ui.dialog().props("persistent".to_string());
        let _ctx = ui.card().classes("w-80 shadow-24 p-4 rounded-xl".to_string());
        {
            self.title_label = ui.label("Tour".to_string()).classes("text-h6 font-bold text-primary".to_string());
            self.message_label = ui.label("Message".to_string()).classes("text-body2 py-2 text-gray-600 dark:text-gray-300".to_string());
            let _ctx = ui.row().classes("w-full justify-end mt-4 gap-2".to_string());
            {
                ui.button("Skip".to_string(), /* on_click= */ self.stop).props("flat color=grey".to_string());
                self.btn_next = ui.button("Next".to_string(), /* on_click= */ self.next_step).props("unelevated color=primary".to_string());
            }
        }
    }
    /// Advance to the next step.
    pub async fn next_step(&mut self) -> Result<()> {
        // Advance to the next step.
        self.current_step += 1;
        if self.current_step < self.steps.len() {
            // try:
            {
                let _ctx = self.client;
                {
                    self._run_step().await;
                }
            }
            // except Exception as e:
        } else {
            self.stop();
        }
    }
    /// End the tour and cleanup.
    pub fn stop(&mut self) -> Result<()> {
        // End the tour and cleanup.
        self.is_running = false;
        // try:
        {
            let _ctx = self.client;
            {
                self._remove_highlights();
                if self.dialog {
                    self.dialog.close();
                }
                ui.notify("Tutorial completed!".to_string(), /* color= */ "positive".to_string(), /* icon= */ "check".to_string());
            }
        }
        // except Exception as _e:
        Ok(logger.info("[Tutorial] Tour ended.".to_string()))
    }
    /// Update the dialog and apply visual effects.
    pub async fn _run_step(&mut self) -> Result<()> {
        // Update the dialog and apply visual effects.
        let mut step = self.steps[&self.current_step];
        if self.title_label {
            self.title_label.text = step["title".to_string()];
        }
        if self.message_label {
            self.message_label.text = step["message".to_string()];
        }
        if self.btn_next {
            let mut is_last = self.current_step == (self.steps.len() - 1);
            self.btn_next.text = if is_last { "Finish".to_string() } else { "Next".to_string() };
            self.btn_next.props(format!("color={}", if is_last { "positive".to_string() } else { "primary".to_string() }));
        }
        if self.dialog {
            self.dialog.open();
        }
        self._remove_highlights();
        let mut target_id = step.get(&"element_id".to_string()).cloned();
        if target_id {
            logger.debug(format!("[Tutorial] Highlighting {}", target_id));
            self._apply_highlight(target_id);
        }
    }
    /// Inject CSS/JS to highlight element.
    pub fn _apply_highlight(&mut self, element_id: String) -> () {
        // Inject CSS/JS to highlight element.
        let mut js = format!("\n        (function() {{\n            const el = document.getElementById('{}');\n            if (el) {{\n                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});\n                el.style.boxShadow = '0 0 20px 8px rgba(25, 118, 210, 0.6)';\n                el.style.outline = '3px solid #1976d2';\n                el.classList.add('zena-tutorial-highlight');\n            }}\n        }})();\n        ", element_id);
        self.client.run_javascript(js);
    }
    /// Clear highlights.
    pub fn _remove_highlights(&mut self) -> () {
        // Clear highlights.
        let mut js = "\n        document.querySelectorAll('.zena-tutorial-highlight').forEach(el => {\n            el.style.boxShadow = '';\n            el.style.outline = '';\n            el.classList.remove('zena-tutorial-highlight');\n        });\n        ".to_string();
        self.client.run_javascript(js);
    }
}

/// Entry point.
pub fn start_tutorial(client: String) -> () {
    // Entry point.
    if !client {
        return;
    }
    let mut tut = UITutorial(client);
    asyncio.create_task(tut.start());
}
