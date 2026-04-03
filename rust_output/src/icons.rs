/// ui/icons::py - Icon Constants
/// Centralized icon names for consistent use throughout the app.
/// 
/// Uses Material Icons (available in NiceGUI/Quasar).

use anyhow::{Result, Context};
use std::collections::HashMap;

/// Material icon names used throughout the application.
/// Centralizing these makes it easy to change icons app-wide.
#[derive(Debug, Clone)]
pub struct Icons {
}

impl Icons {
    /// Get emoji for a given icon concept.
    pub fn emoji(name: String) -> String {
        // Get emoji for a given icon concept.
        let mut emoji_map = HashMap::from([("success".to_string(), "✅".to_string()), ("error".to_string(), "❌".to_string()), ("warning".to_string(), "⚠️".to_string()), ("info".to_string(), "ℹ️".to_string()), ("search".to_string(), "🔍".to_string()), ("file".to_string(), "📄".to_string()), ("folder".to_string(), "📁".to_string()), ("database".to_string(), "💾".to_string()), ("web".to_string(), "🌐".to_string()), ("robot".to_string(), "🤖".to_string()), ("sparkles".to_string(), "✨".to_string()), ("loading".to_string(), "💡".to_string()), ("thinking".to_string(), "💭".to_string()), ("timer".to_string(), "⏱️".to_string()), ("download".to_string(), "📥".to_string()), ("upload".to_string(), "📤".to_string()), ("check".to_string(), "✓".to_string()), ("star".to_string(), "⭐".to_string()), ("fire".to_string(), "🔥".to_string()), ("lightning".to_string(), "⚡".to_string()), ("rocket".to_string(), "🚀".to_string()), ("gear".to_string(), "⚙️".to_string()), ("mic".to_string(), "🎤".to_string()), ("speaker".to_string(), "🔊".to_string())]);
        emoji_map.get(&name).cloned().unwrap_or("".to_string())
    }
}
