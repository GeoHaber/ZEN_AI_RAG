/// ui/modern_ui_demo::py - Modern UI Component Demo
/// Standalone demo showcasing the new modern UI components.
/// 
/// Run this file to see the modern UI in action:
/// python ui/modern_ui_demo::py
/// 
/// This demonstrates:
/// - Modern chat bubbles (user, AI, RAG-enhanced)
/// - Smooth animations
/// - Beautiful typography
/// - Purple accent colors (Claude-inspired)
/// - Dark mode support
/// - Modern input bar
/// - Action chips

use anyhow::{Result, Context};
use crate::modern_chat::{ModernChatMessage, ModernTypingIndicator, ModernInputBar, ModernActionChips, ModernWelcomeMessage, add_modern_cs};
use crate::modern_theme::{ModernTheme, MODERN_CSS};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub const PARENT_DIR: &str = "Path(file!()).parent.parent";

/// Continue demo_page logic.
pub fn _demo_page_continued(avatar_text: String, chat_container: String, content: String, features: String, icon: String, indicator: String, on_click: String, rag_enhanced: String, role: String, scroll_area: String, sources: String) -> () {
    // Continue demo_page logic.
    let mut msg2 = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ "The new UI features a **Claude-inspired design** with:\n\n**Visual Improvements:**\n- Purple primary color (#8B5CF6)\n- Clean, rounded chat bubbles\n- Smooth animations and transitions\n- Better typography with Inter font\n\n**User Experience:**\n- Larger padding for better readability\n- Clear visual hierarchy\n- Subtle shadows for depth\n- Responsive design\n\n**Dark Mode:**\n- Cohesive dark color scheme\n- Proper contrast ratios\n- Smooth theme transitions\n\nTry clicking the dark mode button to see it in action!".to_string(), /* avatar_text= */ "Z".to_string());
    msg2.render(chat_container);
    let mut msg3 = ModernChatMessage(/* role= */ "system".to_string(), /* content= */ "UI components loaded successfully".to_string());
    msg3.render(chat_container);
    let mut msg4 = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ "Based on the documentation, here's how to use the modern theme:\n\n```python\nfrom ui.modern_theme import ModernTheme as MT\n\n# Use predefined styles\nbutton = ui.button('Click me').classes(MT.Buttons.PRIMARY_FULL)\n\n# Combine multiple classes\nlabel = ui.label('Hello').classes(\n    MT.combine(MT.TEXT_LG, MT.FONT_BOLD, MT.TextColors.ACCENT)\n)\n```\n\nThe theme provides organized classes for all UI elements!".to_string(), /* avatar_text= */ "Z".to_string(), /* rag_enhanced= */ true, /* sources= */ vec![HashMap::from([("title".to_string(), "ModernTheme Documentation".to_string()), ("url".to_string(), "ui/modern_theme::py".to_string()), ("text".to_string(), "The ModernTheme class provides Claude-inspired color palette, modern typography, and organized style classes for all UI components...".to_string())])]);
    msg4.render(chat_container);
    let _ctx = ui.footer().classes(MT.Layout.FOOTER);
    {
        let handle_send = |message| {
            // Handle message send
            let mut user_msg = ModernChatMessage(/* role= */ "user".to_string(), /* content= */ message, /* avatar_text= */ "U".to_string());
            user_msg.render(chat_container);
            let mut indicator = ModernTypingIndicator();
            indicator.render(chat_container);
            scroll_area.scroll_to(/* percent= */ 1.0_f64);
            // TODO: import asyncio
            asyncio.sleep(1.5_f64).await;
            indicator.remove();
            let mut ai_msg = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ format!("You said: \"{}\"\n\nThis is a demo response showing the modern UI in action!", message), /* avatar_text= */ "Z".to_string());
            ai_msg.render(chat_container);
            scroll_area.scroll_to(/* percent= */ 1.0_f64);
        };
        let handle_upload = |e| {
            // Handle file upload
            ui.notify(format!("File uploaded: {}", e.name), /* color= */ "positive".to_string());
        };
        let handle_voice = || {
            // Handle voice recording
            ui.notify("Voice recording not implemented in demo".to_string(), /* color= */ "info".to_string());
        };
        let mut input_bar = ModernInputBar(/* on_send= */ handle_send, /* on_upload= */ handle_upload, /* on_voice= */ handle_voice, /* placeholder= */ "Type a message to see it in the modern UI...".to_string());
        input_bar.render();
    }
    let mut info_dialog = ui.dialog();
    {
        let _ctx = ui.card().classes((MT.Cards.PADDED + " w-96".to_string()));
        {
            ui.label("About This Demo".to_string()).classes(MT.combine(MT.TEXT_XL, MT.FONT_BOLD, "mb-4".to_string()));
            ui.markdown("This demo showcases the new **Modern UI components** for ZenAI.\n\n**Key Features:**\n- Claude-inspired purple theme\n- Beautiful chat bubbles\n- Smooth animations\n- Dark mode support\n- Modern typography\n\n**Components Used:**\n- `ModernChatMessage`\n- `ModernTypingIndicator`\n- `ModernInputBar`\n- `ModernActionChips`\n- `ModernWelcomeMessage`\n\nAll components are **separate from the backend**, making them easy to integrate and test!".to_string()).classes("mb-4".to_string());
            ui.button("Close".to_string(), /* on_click= */ info_dialog.close).classes((MT.Buttons.PRIMARY_FULL + " w-full".to_string()));
        }
    }
    let _ctx = ui.header().classes(MT.Layout.HEADER);
    {
        ui.button(/* icon= */ "info".to_string(), /* on_click= */ info_dialog.open).props("flat".to_string()).classes(MT.Buttons.ICON);
    }
}

/// Modern UI Demo Page
pub fn demo_page() -> () {
    // Modern UI Demo Page
    add_modern_css(None);
    let mut dark_mode = ui.dark_mode(/* value= */ false);
    let _ctx = ui.header().classes(MT.Layout.HEADER);
    {
        ui.button(/* icon= */ "menu".to_string()).props("flat".to_string()).classes(MT.Buttons.ICON);
        ui.label("Modern UI Demo".to_string()).classes(MT.combine(MT.TEXT_XL, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY));
        ui.space();
        let toggle_dark = || {
            // Toggle dark.
            if dark_mode.value {
                dark_mode.disable();
            } else {
                dark_mode.enable();
            }
        };
        ui.button(/* icon= */ if !dark_mode.value { "dark_mode".to_string() } else { "light_mode".to_string() }, /* on_click= */ toggle_dark).props("flat".to_string()).classes(MT.Buttons.ICON);
    }
    let mut scroll_area = ui.scroll_area().classes("w-full".to_string()).style("height: calc(100vh - 200px); min-height: 300px;".to_string());
    let _ctx = scroll_area;
    {
        let mut chat_container = ui.column().classes(MT.Layout.CHAT_CONTAINER);
    }
    let mut welcome = ModernWelcomeMessage(/* app_name= */ "ZenAI".to_string(), /* features= */ vec!["Beautiful Claude-inspired UI".to_string(), "Smooth animations & transitions".to_string(), "Purple accent colors".to_string(), "Modern typography".to_string()], /* custom_message= */ "Experience the new modern interface".to_string());
    welcome.render(chat_container);
    let mut actions = vec![HashMap::from([("label".to_string(), "Show User Message".to_string()), ("value".to_string(), "user".to_string())]), HashMap::from([("label".to_string(), "Show AI Response".to_string()), ("value".to_string(), "ai".to_string())]), HashMap::from([("label".to_string(), "Show RAG Message".to_string()), ("value".to_string(), "rag".to_string())]), HashMap::from([("label".to_string(), "Show Typing".to_string()), ("value".to_string(), "typing".to_string())])];
    let handle_chip_click = |value| {
        // Handle quick action clicks
        if value == "user".to_string() {
            let mut msg = ModernChatMessage(/* role= */ "user".to_string(), /* content= */ "Hello! This is a user message with **markdown** support.".to_string(), /* avatar_text= */ "U".to_string());
            msg.render(chat_container);
        } else if value == "ai".to_string() {
            let mut msg = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ "This is an AI response! I can help you with:\n\n1. Answering questions\n2. Generating code\n3. Explaining concepts\n4. And much more!\n\n**Note:** I support *Markdown* formatting!".to_string(), /* avatar_text= */ "Z".to_string());
            msg.render(chat_container);
        } else if value == "rag".to_string() {
            let mut msg = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ "This response is enhanced with RAG! I found relevant information from your knowledge base.".to_string(), /* avatar_text= */ "Z".to_string(), /* rag_enhanced= */ true, /* sources= */ vec![HashMap::from([("title".to_string(), "ZenAI Documentation".to_string()), ("url".to_string(), "https://example.com/docs".to_string()), ("text".to_string(), "ZenAI is a powerful local AI assistant with multi-LLM consensus capabilities...".to_string())]), HashMap::from([("title".to_string(), "User Guide".to_string()), ("url".to_string(), "docs/USER_GUIDE.md".to_string()), ("text".to_string(), "To get started with ZenAI, first install the dependencies and download a model...".to_string())])]);
            msg.render(chat_container);
        } else if value == "typing".to_string() {
            let mut indicator = ModernTypingIndicator();
            indicator.render(chat_container);
            // TODO: import asyncio
            asyncio.sleep(2).await;
            indicator.remove();
            let mut msg = ModernChatMessage(/* role= */ "assistant".to_string(), /* content= */ "Typing indicator disappeared! This is the response.".to_string(), /* avatar_text= */ "Z".to_string());
            msg.render(chat_container);
        }
        scroll_area.scroll_to(/* percent= */ 1.0_f64);
    };
    let mut chips = ModernActionChips(/* actions= */ actions, /* on_click= */ handle_chip_click);
    chips.render(chat_container);
    ui.label("Sample Messages".to_string()).classes(MT.combine(MT.TEXT_LG, MT.FONT_SEMIBOLD, MT.TextColors.PRIMARY, "mt-8 mb-4".to_string())).move(chat_container);
    let mut msg1 = ModernChatMessage(/* role= */ "user".to_string(), /* content= */ "What can you tell me about the new UI?".to_string(), /* avatar_text= */ "U".to_string());
    msg1.render(chat_container);
    _demo_page_continued(avatar_text, chat_container, content, features, icon, indicator, on_click, rag_enhanced, role, scroll_area, sources);
}
