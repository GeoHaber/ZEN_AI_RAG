/// Compact Tokens — Reduce conversation token count by 10-50x.
/// 
/// Pipeline (applied in order):
/// 1. Deduplicate     — Drop exact duplicate messages
/// 2. System Coalesce — Combine multiple system prompts into one
/// 3. Role Merge      — Merge consecutive same-role messages
/// 4. Whitespace Norm — Collapse multiple spaces/newlines
/// 5. Text Compress   — Remove filler words/phrases
/// 6. History Summarize— Collapse old turns into a context line
/// 7. Hard Truncate   — Fit target context window (tokens or chars)
/// 
/// Usage:
/// from compact_tokens import compact_messages, compact_for_inference, CompactConfig
/// 
/// compacted, stats = compact_messages(messages)
/// compacted = compact_for_inference(messages, keep_last_n=4, target_tokens=4096)

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _FILLER_PATTERNS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub const _COMPILED_FILLERS: &str = "[(re::compile(p, re::IGNORECASE), r) for p, r in _FILLER_PATTERNS]";

pub static _MULTI_SPACE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static _MULTI_NEWLINE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static _THINKING_BLOCK_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static _THINKING_OPEN_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// Configuration for the compaction pipeline.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactConfig {
    pub keep_last_n: i64,
    pub summarize_older: bool,
    pub summary_max_chars: i64,
    pub merge_same_role: bool,
    pub deduplicate: bool,
    pub compress_text: bool,
    pub normalize_whitespace: bool,
    pub max_total_chars: i64,
    pub target_ctx_tokens: i64,
    pub chars_per_token: f64,
    pub protect_system: bool,
}

/// Remove <think>...</think> blocks from model output (e.g. Qwen3). Use for UI display;
/// thinking content remains in backend logs only when log_stripped is true.
pub fn strip_thinking_blocks(text: String, log_stripped: bool) -> String {
    // Remove <think>...</think> blocks from model output (e.g. Qwen3). Use for UI display;
    // thinking content remains in backend logs only when log_stripped is true.
    if (!text || !/* /* isinstance(text, str) */ */ true) {
        (text || "".to_string())
    }
    let mut out = _THINKING_BLOCK_RE.sub("".to_string(), text);
    let mut out = _THINKING_OPEN_RE.sub("".to_string(), out);
    let mut out = out.trim().to_string();
    if (log_stripped && out.len() != text.trim().to_string().len()) {
        let mut stripped = if text.len() > 500 { text.trim().to_string()[..500] } else { text.trim().to_string() };
        logger.debug("Stripped thinking block from response (not shown in UI): %.200s...".to_string(), stripped);
    }
    out
}

/// Collapse multiple spaces/newlines, strip edges.
pub fn _normalize_whitespace(text: String) -> String {
    // Collapse multiple spaces/newlines, strip edges.
    let mut text = _MULTI_SPACE.sub(" ".to_string(), text);
    let mut text = _MULTI_NEWLINE.sub("\n\n".to_string(), text);
    text.trim().to_string()
}

/// Apply linguistic compression — remove filler without losing meaning.
pub fn _compress_text(text: String) -> String {
    // Apply linguistic compression — remove filler without losing meaning.
    for (pattern, replacement) in _COMPILED_FILLERS.iter() {
        let mut text = pattern.sub(replacement, text);
    }
    let mut text = _MULTI_SPACE.sub(" ".to_string(), text);
    text.trim().to_string()
}

/// Remove exact duplicate messages (keep first occurrence).
pub fn _deduplicate(messages: Vec<HashMap<String, String>>) -> Vec<HashMap<String, String>> {
    // Remove exact duplicate messages (keep first occurrence).
    let mut seen = HashSet::new();
    let mut result = vec![];
    for msg in messages.iter() {
        let mut key = format!("{}|{}", msg.get(&"role".to_string()).cloned().unwrap_or("".to_string()), msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()));
        let mut h = hashlib::md5(key.as_bytes().to_vec()).hexdigest();
        if !seen.contains(&h) {
            seen.insert(h);
            result.push(msg);
        }
    }
    result
}

/// Merge consecutive messages from the same role into one.
pub fn _merge_same_role(messages: Vec<HashMap<String, String>>) -> Vec<HashMap<String, String>> {
    // Merge consecutive messages from the same role into one.
    if !messages {
        messages
    }
    let mut merged = vec![messages[0].clone()];
    for msg in messages[1..].iter() {
        if msg.get(&"role".to_string()).cloned() == merged[-1].get(&"role".to_string()).cloned() {
            merged[-1]["content".to_string()] = ((merged[-1].get(&"content".to_string()).cloned().unwrap_or("".to_string()) + "\n".to_string()) + msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()));
        } else {
            merged.push(msg.clone());
        }
    }
    merged
}

/// Combine multiple system messages into a single one at the start.
pub fn _coalesce_system(messages: Vec<HashMap<String, String>>) -> Vec<HashMap<String, String>> {
    // Combine multiple system messages into a single one at the start.
    let mut system_parts = vec![];
    let mut non_system = vec![];
    for msg in messages.iter() {
        if msg.get(&"role".to_string()).cloned() == "system".to_string() {
            let mut content = msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
            if content {
                system_parts.push(content);
            }
        } else {
            non_system.push(msg);
        }
    }
    let mut result = vec![];
    if system_parts {
        result.push(HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_parts.join(&"\n".to_string()))]));
    }
    result.extend(non_system);
    result
}

/// Collapse older messages into a brief context summary.
/// 
/// Keeps the last `keep_last_n` messages verbatim and replaces
/// everything before them with a concise "[Prior conversation context]".
pub fn _summarize_older(messages: Vec<HashMap<String, String>>, keep_last_n: i64, max_chars: i64) -> Vec<HashMap<String, String>> {
    // Collapse older messages into a brief context summary.
    // 
    // Keeps the last `keep_last_n` messages verbatim and replaces
    // everything before them with a concise "[Prior conversation context]".
    if messages.len() <= keep_last_n {
        messages
    }
    let mut system_msgs = messages.iter().filter(|m| m.get(&"role".to_string()).cloned() == "system".to_string()).map(|m| m).collect::<Vec<_>>();
    let mut non_system = messages.iter().filter(|m| m.get(&"role".to_string()).cloned() != "system".to_string()).map(|m| m).collect::<Vec<_>>();
    if non_system.len() <= keep_last_n {
        messages
    }
    let mut older = non_system[..-keep_last_n];
    let mut recent = non_system[-keep_last_n..];
    let mut summary_parts = vec![];
    for msg in older.iter() {
        let mut role = msg.get(&"role".to_string()).cloned().unwrap_or("?".to_string())[0].to_uppercase();
        let mut content = (msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()) || "".to_string()).trim().to_string();
        summary_parts.push(format!("{}: {}", role, content));
    }
    let mut summary_text = summary_parts.join(&"\n\n".to_string());
    if summary_text.len() > max_chars {
        let mut summary_text = (summary_text[..(max_chars - 3)] + "...".to_string());
    }
    let mut result = system_msgs.into_iter().collect::<Vec<_>>();
    result.push(HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), format!("[Prior conversation context: {}]", summary_text))]));
    result.extend(recent);
    result
}

/// Hard-truncate to fit within max_chars total content.
/// 
/// Preserves system messages and the last non-system message.
/// Trims from the oldest non-system messages first.
pub fn _hard_truncate(messages: Vec<HashMap<String, String>>, max_chars: i64) -> Vec<HashMap<String, String>> {
    // Hard-truncate to fit within max_chars total content.
    // 
    // Preserves system messages and the last non-system message.
    // Trims from the oldest non-system messages first.
    let _total_chars = |msgs| {
        msgs.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>()
    };
    if _total_chars(messages) <= max_chars {
        messages
    }
    let mut system = messages.iter().filter(|m| m.get(&"role".to_string()).cloned() == "system".to_string()).map(|m| m).collect::<Vec<_>>();
    let mut non_system = messages.iter().filter(|m| m.get(&"role".to_string()).cloned() != "system".to_string()).map(|m| m).collect::<Vec<_>>();
    if !non_system {
        messages
    }
    let mut last_msg = non_system[-1];
    let mut middle = non_system[..-1];
    let mut system_chars = _total_chars(system);
    let mut last_chars = last_msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len();
    let mut budget = ((max_chars - system_chars) - last_chars);
    if budget <= 0 {
        let mut truncated = last_msg.get(&"content".to_string()).cloned().unwrap_or("".to_string())[..(max_chars - system_chars)];
        (system + vec![HashMap::from([("role".to_string(), last_msg["role".to_string()]), ("content".to_string(), truncated)])])
    }
    let mut kept_middle = vec![];
    let mut used = 0;
    for msg in middle.iter().rev().iter() {
        let mut msg_chars = msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len();
        if (used + msg_chars) <= budget {
            kept_middle.insert(0, msg);
            used += msg_chars;
        } else {
            break;
        }
    }
    ((system + kept_middle) + vec![last_msg])
}

/// Apply the full compaction pipeline to a conversation.
/// 
/// Returns (compacted_messages, stats_dict).
pub fn compact_messages(messages: Vec<HashMap<String, String>>, config: Option<CompactConfig>) -> (Vec<HashMap<String, String>>, HashMap<String, Box<dyn std::any::Any>>) {
    // Apply the full compaction pipeline to a conversation.
    // 
    // Returns (compacted_messages, stats_dict).
    if config::is_none() {
        let mut config = CompactConfig();
    }
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut original_chars = messages.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
    let mut original_count = messages.len();
    let mut stages_applied = vec![];
    let mut result = messages.iter().map(|m| m.clone()).collect::<Vec<_>>();
    if config::deduplicate {
        let mut before = result.len();
        let mut result = _deduplicate(result);
        if result.len() < before {
            stages_applied.push(format!("dedup: {} -> {} msgs", before, result.len()));
        }
    }
    let mut system_count = result.iter().filter(|m| m.get(&"role".to_string()).cloned() == "system".to_string()).map(|m| 1).collect::<Vec<_>>().iter().sum::<i64>();
    if system_count > 1 {
        let mut result = _coalesce_system(result);
        stages_applied.push(format!("system_coalesce: {} -> 1", system_count));
    }
    if config::merge_same_role {
        let mut before = result.len();
        let mut result = _merge_same_role(result);
        if result.len() < before {
            stages_applied.push(format!("merge_roles: {} -> {} msgs", before, result.len()));
        }
    }
    if config::normalize_whitespace {
        for msg in result.iter() {
            if (msg.get(&"role".to_string()).cloned() != "system".to_string() || !config::protect_system) {
                msg["content".to_string()] = _normalize_whitespace(msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()));
            }
        }
    }
    if config::compress_text {
        let mut chars_before = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        for msg in result.iter() {
            if (msg.get(&"role".to_string()).cloned() != "system".to_string() || !config::protect_system) {
                msg["content".to_string()] = _compress_text(msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()));
            }
        }
        let mut chars_after = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        let mut saved = (chars_before - chars_after);
        if saved > 0 {
            stages_applied.push(format!("compress: saved {} chars", saved));
        }
    }
    if (config::summarize_older && result.len() > config::keep_last_n) {
        let mut before_count = result.len();
        let mut result = _summarize_older(result, /* keep_last_n= */ config::keep_last_n, /* max_chars= */ config::summary_max_chars);
        stages_applied.push(format!("summarize: {} -> {} msgs (kept last {})", before_count, result.len(), config::keep_last_n));
    }
    if config::target_ctx_tokens > 0 {
        let mut max_chars = (config::target_ctx_tokens * config::chars_per_token).to_string().parse::<i64>().unwrap_or(0);
        let mut chars_before = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        let mut result = _hard_truncate(result, /* max_chars= */ max_chars);
        let mut chars_after = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        if chars_after < chars_before {
            stages_applied.push(format!("truncate: {} -> {} chars (fit {} tokens)", chars_before, chars_after, config::target_ctx_tokens));
        }
    }
    if config::max_total_chars > 0 {
        let mut chars_before = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        let mut result = _hard_truncate(result, /* max_chars= */ config::max_total_chars);
        let mut chars_after = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        if chars_after < chars_before {
            stages_applied.push(format!("max_chars: {} -> {} chars", chars_before, chars_after));
        }
    }
    let mut final_chars = result.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
    let mut elapsed_ms = ((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) * 1000);
    let mut est_original = 1.max((original_chars / config::chars_per_token).to_string().parse::<i64>().unwrap_or(0));
    let mut est_final = 1.max((final_chars / config::chars_per_token).to_string().parse::<i64>().unwrap_or(0));
    let mut ratio = if est_original > 0 { (est_final / est_original) } else { 1.0_f64 };
    let mut reduction = (1.0_f64 - ratio);
    let mut stats = HashMap::from([("original_messages".to_string(), original_count), ("compacted_messages".to_string(), result.len()), ("original_chars".to_string(), original_chars), ("compacted_chars".to_string(), final_chars), ("original_tokens_est".to_string(), est_original), ("compacted_tokens_est".to_string(), est_final), ("reduction_ratio".to_string(), ((reduction as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("compression_factor".to_string(), if ratio > 0 { format!("{:.1}x", (1 / ratio)) } else { "inf".to_string() }), ("stages_applied".to_string(), stages_applied), ("elapsed_ms".to_string(), ((elapsed_ms as f64) * 10f64.powi(2)).round() / 10f64.powi(2))]);
    if stages_applied {
        logger.info(format!("[compact] {} msgs -> {} msgs, {} -> {} tokens ({} reduction) in {:.1}ms", original_count, result.len(), est_original, est_final, stats["compression_factor".to_string()], elapsed_ms));
    }
    (result, stats)
}

/// Quick compact for use inside inference handlers. Returns messages only.
pub fn compact_for_inference(messages: Vec<HashMap<String, String>>) -> Vec<HashMap<String, String>> {
    // Quick compact for use inside inference handlers. Returns messages only.
    let mut cfg = CompactConfig(/* keep_last_n= */ keep_last_n, /* target_ctx_tokens= */ target_tokens);
    let (mut compacted, _) = compact_messages(messages, cfg);
    compacted
}
