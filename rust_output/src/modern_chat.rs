/// ui/modern_chat::py - Modern Chat Interface Components
/// Beautiful, Claude-inspired chat UI with smooth animations.
/// 
/// This module provides reusable chat components that can be integrated
/// into the main zena.py application without modifying the backend.

use anyhow::{Result, Context};
use crate::modern_theme::{ModernTheme};
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

/// Modern chat message component with beautiful styling.
/// 
/// Features:
/// - Smooth appearance animations
/// - Role-based styling (user, AI, system, RAG)
/// - Avatar support
/// - Markdown rendering
/// - Source citations (for RAG)
#[derive(Debug, Clone)]
pub struct ModernChatMessage {
    pub role: String,
    pub content: String,
    pub avatar_text: String,
    pub rag_enhanced: String,
    pub sources: String,
}

impl ModernChatMessage {
    /// Create a modern chat message.
    /// 
    /// Args:
    /// role: Message role ('user', 'assistant', 'system')
    /// content: Message content (supports Markdown)
    /// avatar_text: Text for avatar (e.g., 'Z' for Zena, 'U' for User)
    /// rag_enhanced: Whether message uses RAG context
    /// sources: List of sources for RAG messages (optional)
    pub fn new(role: String, content: String, avatar_text: String, rag_enhanced: bool, sources: Vec<serde_json::Value>) -> Self {
        Self {
            role,
            content,
            avatar_text: (avatar_text || if role == "user".to_string() { "U".to_string() } else { "Z".to_string() }),
            rag_enhanced,
            sources: (sources || vec![]),
        }
    }
    /// Render the message in the chat interface.
    pub fn render(&mut self, container: String) -> () {
        // Render the message in the chat interface.
        if self.role == "system".to_string() {
            let mut row_class = MT.ChatBubbles.ROW_SYSTEM;
        } else if self.role == "user".to_string() {
            let mut row_class = MT.ChatBubbles.ROW_USER;
        } else {
            let mut row_class = MT.ChatBubbles.ROW_AI;
        }
        let mut msg_row = ui.row().classes((row_class + " chat-message".to_string()));
        if container {
            msg_row.move(container);
        }
        let _ctx = msg_row;
        {
            if (self.role != "user".to_string() && self.role != "system".to_string()) {
                ui.avatar(self.avatar_text, /* color= */ if !self.rag_enhanced { "purple".to_string() } else { "blue".to_string() }, /* text_color= */ "white".to_string()).classes(MT.Avatars.AI_FULL);
            }
            let _ctx = ui.column().classes("gap-1 max-w-3xl".to_string());
            {
                if self.role != "system".to_string() {
                    let mut sender = if self.role == "user".to_string() { "You".to_string() } else { "Zena".to_string() };
                    ui.label(sender).classes(MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, "ml-1".to_string()));
                }
                let mut bubble_class = MT.get_chat_bubble(self.role, self.rag_enhanced);
                ui.markdown(self.content).classes((bubble_class + " markdown-content".to_string()));
                if (self.rag_enhanced && self.sources) {
                    self._render_sources();
                }
            }
            if self.role == "user".to_string() {
                ui.avatar(self.avatar_text, /* color= */ "gray".to_string(), /* text_color= */ "white".to_string()).classes(MT.Avatars.USER_FULL);
            }
        }
    }
    /// Render sources expansion panel for RAG messages.
    pub fn _render_sources(&mut self) -> () {
        // Render sources expansion panel for RAG messages.
        let _ctx = ui.expansion("View Sources".to_string(), /* icon= */ "source".to_string()).classes((MT.Cards.INFO + " mt-2".to_string()));
        {
            let _ctx = ui.column().classes("gap-2 p-2".to_string());
            {
                for (i, source) in self.sources.iter().enumerate().iter() {
                    let mut title = source.get(&"title".to_string()).cloned().unwrap_or("Untitled".to_string());
                    let mut url = source.get(&"url".to_string()).cloned().unwrap_or("N/A".to_string());
                    let mut text_preview = (source.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..200] + "...".to_string());
                    let _ctx = ui.card().classes((MT.Cards.BASE + " p-3".to_string()));
                    {
                        let mut is_cached = source.get(&"_is_cached".to_string()).cloned().unwrap_or(false);
                        let mut score = (source.get(&"rerank_score".to_string()).cloned() || source.get(&"fusion_score".to_string()).cloned() || source.get(&"score".to_string()).cloned().unwrap_or(0));
                        let mut score_label = if /* /* isinstance(score, float) */ */ true { format!("{:.2}", score) } else { score.to_string() };
                        let _ctx = ui.row().classes("w-full items-center justify-between".to_string());
                        {
                            if url.starts_with(&*"http".to_string()) {
                                ui.link(format!("[{}] {}", i, title), url, /* new_tab= */ true).classes((MT.TextColors.LINK + " font-semibold text-sm".to_string()));
                            } else {
                                ui.label(format!("[{}] {}", i, title)).classes((MT.TextColors.PRIMARY + " font-semibold text-sm".to_string()));
                            }
                            let _ctx = ui.row().classes("gap-1".to_string());
                            {
                                if is_cached {
                                    ui.badge("⚡ MEMORY".to_string(), /* color= */ "purple".to_string()).props("outline rounded".to_string()).classes("text-[10px]".to_string());
                                } else if source.get(&"rerank_score".to_string()).cloned() {
                                    ui.badge(format!("🎯 {}", score_label), /* color= */ "green".to_string()).props("outline rounded".to_string()).classes("text-[10px]".to_string());
                                } else {
                                    ui.badge(format!("🔍 {}", score_label), /* color= */ "grey".to_string()).props("outline rounded".to_string()).classes("text-[10px]".to_string());
                                }
                            }
                        }
                        ui.label(format!("Location: {}", url)).classes(MT.combine(MT.TEXT_XS, MT.TextColors.MUTED));
                        ui.label(format!("\"{}\"", text_preview)).classes(MT.combine(MT.TEXT_SM, MT.TextColors.SECONDARY, "italic border-l-2 border-gray-300 pl-2 mt-1".to_string()));
                    }
                }
            }
        }
    }
}

/// Animated typing indicator for AI responses.
/// 
/// Shows three pulsing dots to indicate the AI is "thinking".
#[derive(Debug, Clone)]
pub struct ModernTypingIndicator {
    pub container: Option<serde_json::Value>,
}

impl ModernTypingIndicator {
    pub fn new() -> Self {
        Self {
            container: None,
        }
    }
    /// Show typing indicator.
    pub fn render(&mut self, chat_container: String) -> () {
        // Show typing indicator.
        let mut row = ui.row().classes((MT.ChatBubbles.ROW_AI + " chat-message".to_string()));
        if chat_container {
            row.move(chat_container);
        }
        self.container = row;
        let _ctx = row;
        {
            ui.avatar("Z".to_string(), /* color= */ "purple".to_string(), /* text_color= */ "white".to_string()).classes(MT.Avatars.AI_FULL);
            let _ctx = ui.column().classes("gap-1".to_string());
            {
                ui.label("Zena".to_string()).classes(MT.combine(MT.TEXT_XS, MT.TextColors.SECONDARY, "ml-1".to_string()));
                let _ctx = ui.card().classes((MT.ChatBubbles.AI_FULL + " flex items-center justify-center min-h-12".to_string()));
                {
                    ui.html("\n                        <div class=\"typing-indicator\">\n                            <span></span>\n                            <span></span>\n                            <span></span>\n                        </div>\n                    ".to_string());
                }
            }
        }
    }
    /// Remove typing indicator from chat.
    pub fn remove(&mut self) -> () {
        // Remove typing indicator from chat.
        if self.container {
            self.container.delete();
            self.container = None;
        }
    }
}

/// Modern input bar component with file upload and voice support.
/// 
/// Features:
/// - Large, rounded input field
/// - Attach file button
/// - Voice record button
/// - Send button
/// - Smooth focus ring
#[derive(Debug, Clone)]
pub struct ModernInputBar {
    pub on_send: String,
    pub on_upload: String,
    pub on_voice: String,
    pub placeholder: String,
    pub input_field: Option<serde_json::Value>,
    pub attachment_preview: Option<serde_json::Value>,
}

impl ModernInputBar {
    /// Create modern input bar.
    /// 
    /// Args:
    /// on_send: Callback for send button click (async function)
    /// on_upload: Callback for file upload (async function)
    /// on_voice: Callback for voice recording (async function)
    /// placeholder: Input placeholder text
    pub fn new(on_send: String, on_upload: String, on_voice: String, placeholder: String) -> Self {
        Self {
            on_send,
            on_upload,
            on_voice,
            placeholder,
            input_field: None,
            attachment_preview: None,
        }
    }
    /// Render the input bar.
    pub fn render(&mut self, container: String) -> () {
        // Render the input bar.
        let mut input_col = ui.column().classes("w-full max-w-4xl mx-auto gap-2".to_string());
        if container {
            input_col.move(container);
        }
        let _ctx = input_col;
        {
            self.attachment_preview = ui.label("".to_string()).classes((MT.Cards.INFO + " text-sm self-start".to_string())).props("visible=false".to_string());
            let _ctx = ui.row().classes(MT.Inputs.CHAT_BAR);
            {
                if self.on_upload {
                    let mut uploader = ui.upload(/* on_upload= */ self.on_upload, /* auto_upload= */ true).classes("hidden".to_string());
                    ui.button(/* icon= */ "attach_file".to_string(), /* on_click= */ || uploader.run_method("pickFiles".to_string())).props("flat round dense".to_string()).classes((MT.Buttons.ICON + " text-gray-500 hover:text-purple-600".to_string()));
                }
                self.input_field = ui.input(/* placeholder= */ self.placeholder).classes(MT.Inputs.CHAT).props("borderless".to_string());
                if self.on_send {
                    self.input_field.on("keydown.enter.prevent".to_string(), self._handle_send);
                }
                if self.on_voice {
                    ui.button(/* icon= */ "mic".to_string(), /* on_click= */ self.on_voice).props("flat round dense".to_string()).classes((MT.Buttons.ICON + " text-gray-500 hover:text-purple-600".to_string()));
                }
                if self.on_send {
                    ui.button(/* icon= */ "send".to_string(), /* on_click= */ self._handle_send).props("round unelevated".to_string()).classes((MT.Buttons.PRIMARY_FULL + " w-10 h-10".to_string()));
                }
            }
        }
    }
    /// Handle send button click.
    pub async fn _handle_send(&mut self, e: String) -> () {
        // Handle send button click.
        if !(self.on_send && self.input_field) {
            return;
        }
        let mut message = self.input_field.value.trim().to_string();
        if message {
            self.on_send(message).await;
            self.input_field.value = "".to_string();
        }
    }
    /// Show attachment preview.
    pub fn show_attachment(&mut self, filename: String, size: i64) -> () {
        // Show attachment preview.
        if self.attachment_preview {
            self.attachment_preview.text = format!("Attached: {} ({} bytes)", filename, size);
            self.attachment_preview.props("visible=true".to_string());
        }
    }
    /// Hide attachment preview.
    pub fn hide_attachment(&mut self) -> () {
        // Hide attachment preview.
        if self.attachment_preview {
            self.attachment_preview.props("visible=false".to_string());
            self.attachment_preview.text = "".to_string();
        }
    }
}

/// Quick action chips for guided interactions.
/// 
/// Shows pill-shaped buttons for common queries.
#[derive(Debug, Clone)]
pub struct ModernActionChips {
    pub actions: String,
    pub on_click: String,
}

impl ModernActionChips {
    /// Create action chips.
    /// 
    /// Args:
    /// actions: List of action dictionaries with 'label' and 'value'
    /// on_click: Callback when chip is clicked (async function)
    pub fn new(actions: Vec<serde_json::Value>, on_click: String) -> Self {
        Self {
            actions,
            on_click,
        }
    }
    /// Render action chips.
    pub fn render(&mut self, container: String) -> () {
        // Render action chips.
        let mut chips_col = ui.column().classes("w-full gap-2".to_string());
        if container {
            chips_col.move(container);
        }
        let _ctx = chips_col;
        {
            ui.label("Quick Actions".to_string()).classes(MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, "ml-1".to_string()));
            let _ctx = ui.row().classes("gap-2 flex-wrap".to_string());
            {
                for action in self.actions::iter() {
                    let mut label = action.get(&"label".to_string()).cloned().unwrap_or("".to_string());
                    let mut value = action.get(&"value".to_string()).cloned().unwrap_or(label);
                    let chip_click = |val| {
                        if self.on_click {
                            self.on_click(val).await;
                        }
                    };
                    ui.button(label, /* on_click= */ chip_click).classes(MT.Badges.CHIP).props("outline size=sm no-caps".to_string());
                }
            }
        }
    }
}

/// Beautiful welcome message for new sessions.
/// 
/// Features:
/// - Large, centered greeting
/// - Feature highlights
/// - Smooth fade-in animation
#[derive(Debug, Clone)]
pub struct ModernWelcomeMessage {
    pub app_name: String,
    pub features: String,
    pub custom_message: String,
}

impl ModernWelcomeMessage {
    /// Create welcome message.
    /// 
    /// Args:
    /// app_name: Application name
    /// features: List of feature strings
    /// custom_message: Custom welcome message (optional)
    pub fn new(app_name: String, features: Vec<serde_json::Value>, custom_message: String) -> Self {
        Self {
            app_name,
            features: (features || vec!["Fast local AI responses".to_string(), "RAG-enhanced knowledge retrieval".to_string(), "Multi-LLM consensus".to_string(), "Voice interaction support".to_string()]),
            custom_message,
        }
    }
    /// Render welcome message.
    pub fn render(&mut self, container: String) -> () {
        // Render welcome message.
        let mut welcome_col = ui.column().classes("w-full max-w-2xl mx-auto text-center gap-4 p-8 animate-fade-in".to_string());
        if container {
            welcome_col.move(container);
        }
        let _ctx = welcome_col;
        {
            ui.label(format!("Welcome to {}", self.app_name)).classes(MT.combine(MT.TEXT_3XL, MT.FONT_BOLD, MT.TextColors.PRIMARY));
            let mut message = (self.custom_message || format!("Your intelligent AI assistant powered by local LLMs"));
            ui.label(message).classes(MT.combine(MT.TEXT_LG, MT.TextColors.SECONDARY, "mb-4".to_string()));
            let _ctx = ui.row().classes("gap-4 justify-center flex-wrap".to_string());
            {
                for feature in self.features.iter() {
                    let _ctx = ui.card().classes((MT.Cards.PADDED + " min-w-48".to_string()));
                    {
                        ui.label(feature).classes(MT.combine(MT.TEXT_SM, MT.TextColors.SECONDARY, "text-center".to_string()));
                    }
                }
            }
            ui.label("Try asking a question or use the quick actions below".to_string()).classes(MT.combine(MT.TEXT_SM, MT.TextColors.MUTED, "italic mt-4".to_string()));
        }
    }
}

/// Add modern CSS styles to the page.
/// 
/// This should be called once during page initialization.
pub fn add_modern_css(page_container: String) -> () {
    // Add modern CSS styles to the page.
    // 
    // This should be called once during page initialization.
    // TODO: from .modern_theme import MODERN_CSS
    ui.add_head_html(MODERN_CSS);
}

/// Create a modern chat container with proper styling.
/// 
/// Args:
/// scroll_container: The scroll area containing chat messages
/// 
/// Returns:
/// Column element for chat messages
pub fn create_modern_chat_container(scroll_container: String) -> () {
    // Create a modern chat container with proper styling.
    // 
    // Args:
    // scroll_container: The scroll area containing chat messages
    // 
    // Returns:
    // Column element for chat messages
    let _ctx = scroll_container;
    {
        let mut chat_log = ui.column().classes(MT.Layout.CHAT_CONTAINER);
    }
    chat_log
}
