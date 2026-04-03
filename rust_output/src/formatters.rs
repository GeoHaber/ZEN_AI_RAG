/// ui/formatters::py - Data Formatting Utilities
/// Consistent formatting for model info, file sizes, numbers, etc.

use anyhow::{Result, Context};
use std::collections::HashMap;

/// Base methods for Formatters.
#[derive(Debug, Clone)]
pub struct _FormattersBase {
}

impl _FormattersBase {
    /// Format bytes to human-readable size.
    /// 
    /// Args:
    /// bytes_size: Size in bytes
    /// precision: Decimal places
    /// 
    /// Returns:
    /// Formatted string like "4.2 GB"
    pub fn file_size(&self, bytes_size: i64, precision: i64) -> String {
        // Format bytes to human-readable size.
        // 
        // Args:
        // bytes_size: Size in bytes
        // precision: Decimal places
        // 
        // Returns:
        // Formatted string like "4.2 GB"
        if bytes_size < 0 {
            "0 B".to_string()
        }
        let mut units = vec!["B".to_string(), "KB".to_string(), "MB".to_string(), "GB".to_string(), "TB".to_string(), "PB".to_string()];
        let mut size = bytes_size.to_string().parse::<f64>().unwrap_or(0.0);
        let mut unit_index = 0;
        while (size >= 1024 && unit_index < (units.len() - 1)) {
            size /= 1024;
            unit_index += 1;
        }
        if unit_index == 0 {
            format!("{} {}", size.to_string().parse::<i64>().unwrap_or(0), units[&unit_index])
        }
        format!("{:.} {}", size, units[&unit_index])
    }
    /// Format GB value for display.
    pub fn gb_to_display(gb: f64) -> String {
        // Format GB value for display.
        if gb < 1 {
            format!("{} MB", (gb * 1024).to_string().parse::<i64>().unwrap_or(0))
        }
        format!("{:.1} GB", gb)
    }
    /// Format large numbers with K, M, B suffixes.
    /// 
    /// Args:
    /// num: Number to format
    /// 
    /// Returns:
    /// Formatted string like "1.2M+"
    pub fn number_abbreviated(num: i64) -> String {
        // Format large numbers with K, M, B suffixes.
        // 
        // Args:
        // num: Number to format
        // 
        // Returns:
        // Formatted string like "1.2M+"
        if num < 0 {
            "0".to_string()
        }
        if num >= 1000000000 {
            format!("{:.1}B+", (num / 1000000000))
        } else if num >= 1000000 {
            format!("{:.1}M+", (num / 1000000))
        } else if num >= 1000 {
            format!("{:.1}K+", (num / 1000))
        } else {
            num.to_string()
        }
    }
    /// Format download count for display.
    pub fn downloads(count: i64) -> String {
        // Format download count for display.
        format!("📊 {} downloads", Formatters.number_abbreviated(count))
    }
    /// Format star count for display.
    pub fn stars(count: i64) -> String {
        // Format star count for display.
        format!("⭐ {}", Formatters.number_abbreviated(count))
    }
    /// Estimate parameters from model size (rough Q4_K_M estimate).
    /// 
    /// Args:
    /// size_gb: Model file size in GB
    /// 
    /// Returns:
    /// Human-readable parameter count
    pub fn model_parameters(size_gb: f64) -> String {
        // Estimate parameters from model size (rough Q4_K_M estimate).
        // 
        // Args:
        // size_gb: Model file size in GB
        // 
        // Returns:
        // Human-readable parameter count
        let mut estimated_params = (size_gb / 0.56_f64);
        if estimated_params >= 1 {
            format!("~{:.0}B parameters", estimated_params)
        } else {
            format!("~{:.0}M parameters", (estimated_params * 1000))
        }
    }
    /// Estimate RAM needed for model.
    /// 
    /// Args:
    /// size_gb: Model file size in GB
    /// overhead: Multiplier for KV cache and overhead
    /// 
    /// Returns:
    /// RAM requirement string
    pub fn ram_estimate(size_gb: f64, overhead: f64) -> String {
        // Estimate RAM needed for model.
        // 
        // Args:
        // size_gb: Model file size in GB
        // overhead: Multiplier for KV cache and overhead
        // 
        // Returns:
        // RAM requirement string
        let mut ram_needed = (size_gb * overhead);
        if ram_needed < 4 {
            format!("~{:.1}GB RAM (runs on most systems)", ram_needed)
        } else if ram_needed < 8 {
            format!("~{:.0}GB RAM (needs decent GPU/RAM)", ram_needed)
        } else if ram_needed < 16 {
            format!("~{:.0}GB RAM (needs 16GB+ system)", ram_needed)
        } else {
            format!("~{:.0}GB RAM (needs high-end system)", ram_needed)
        }
    }
}

/// Data formatting utilities for consistent display across the UI.
#[derive(Debug, Clone)]
pub struct Formatters {
}

impl Formatters {
    /// Get speed and quality ratings based on model size.
    /// 
    /// Args:
    /// size_gb: Model file size in GB
    /// 
    /// Returns:
    /// Tuple of (speed_rating, quality_rating)
    pub fn speed_rating(size_gb: f64) -> (String, String) {
        // Get speed and quality ratings based on model size.
        // 
        // Args:
        // size_gb: Model file size in GB
        // 
        // Returns:
        // Tuple of (speed_rating, quality_rating)
        if size_gb <= 2.5_f64 {
            ("⚡⚡⚡ Fast".to_string(), "⭐⭐⭐".to_string())
        } else if size_gb <= 5 {
            ("⚡⚡ Balanced".to_string(), "⭐⭐⭐⭐".to_string())
        } else if size_gb <= 6 {
            ("⚡⚡ Balanced".to_string(), "⭐⭐⭐⭐".to_string())
        } else {
            ("⚡ Moderate".to_string(), "⭐⭐⭐⭐⭐".to_string())
        }
    }
    /// Convert quantization code to human-readable description.
    /// 
    /// Args:
    /// quant: Quantization string (e.g., "Q4_K_M")
    /// 
    /// Returns:
    /// Human-readable description
    pub fn quantization_human(quant: String) -> String {
        // Convert quantization code to human-readable description.
        // 
        // Args:
        // quant: Quantization string (e.g., "Q4_K_M")
        // 
        // Returns:
        // Human-readable description
        let mut quant_map = HashMap::from([("Q2_K".to_string(), "Tiny (lowest quality, fastest)".to_string()), ("Q3_K_S".to_string(), "Small (low quality, very fast)".to_string()), ("Q3_K_M".to_string(), "Small (low quality, fast)".to_string()), ("Q3_K_L".to_string(), "Small-Medium (decent quality, fast)".to_string()), ("Q4_0".to_string(), "Medium (good quality, balanced)".to_string()), ("Q4_K_S".to_string(), "Medium (good quality, balanced)".to_string()), ("Q4_K_M".to_string(), "Balanced (good speed + quality) ⭐ RECOMMENDED".to_string()), ("Q4_K_L".to_string(), "Medium-Large (better quality)".to_string()), ("Q5_0".to_string(), "Large (high quality, slower)".to_string()), ("Q5_K_S".to_string(), "Large (high quality, slower)".to_string()), ("Q5_K_M".to_string(), "Large (high quality, slower)".to_string()), ("Q6_K".to_string(), "Very Large (excellent quality, slow)".to_string()), ("Q8_0".to_string(), "Huge (best quality, slowest)".to_string()), ("F16".to_string(), "Full precision (research only)".to_string()), ("F32".to_string(), "Full precision (research only)".to_string())]);
        if quant_map.contains(&quant.to_uppercase()) {
            quant_map[&quant.to_uppercase()]
        }
        let mut quant_upper = quant.to_uppercase();
        for (key, value) in quant_map.iter().iter() {
            if quant_upper.contains(&key) {
                value
            }
        }
        "Balanced (good speed + quality) ⭐ RECOMMENDED".to_string()
    }
    /// Format context window size with word estimate.
    /// 
    /// Args:
    /// tokens: Number of tokens
    /// 
    /// Returns:
    /// Formatted string with word estimate
    pub fn context_window(tokens: i64) -> String {
        // Format context window size with word estimate.
        // 
        // Args:
        // tokens: Number of tokens
        // 
        // Returns:
        // Formatted string with word estimate
        let mut words = (tokens * 0.75_f64).to_string().parse::<i64>().unwrap_or(0);
        if tokens >= 1000 {
            let mut token_str = format!("{}K", (tokens / 1000));
        } else {
            let mut token_str = tokens.to_string();
        }
        if words >= 1000 {
            let mut word_str = format!("~{}K", (words / 1000));
        } else {
            let mut word_str = format!("~{}", words);
        }
        format!("{} tokens ({} words)", token_str, word_str)
    }
    /// Format duration in seconds to human-readable.
    /// 
    /// Args:
    /// seconds: Duration in seconds
    /// 
    /// Returns:
    /// Formatted string like "2m 30s"
    pub fn duration(seconds: f64) -> String {
        // Format duration in seconds to human-readable.
        // 
        // Args:
        // seconds: Duration in seconds
        // 
        // Returns:
        // Formatted string like "2m 30s"
        if seconds < 1 {
            format!("{:.0}ms", (seconds * 1000))
        } else if seconds < 60 {
            format!("{:.1}s", seconds)
        } else {
            let mut mins = (seconds / 60).to_string().parse::<i64>().unwrap_or(0);
            let mut secs = (seconds % 60).to_string().parse::<i64>().unwrap_or(0);
            format!("{}m {}s", mins, secs)
        }
    }
    /// Calculate and format ETA.
    /// 
    /// Args:
    /// elapsed: Seconds elapsed
    /// current: Current progress count
    /// total: Total count
    /// 
    /// Returns:
    /// ETA string like "2m 30s"
    pub fn eta(elapsed: f64, current: i64, total: i64) -> String {
        // Calculate and format ETA.
        // 
        // Args:
        // elapsed: Seconds elapsed
        // current: Current progress count
        // total: Total count
        // 
        // Returns:
        // ETA string like "2m 30s"
        if current <= 0 {
            "Calculating...".to_string()
        }
        let mut avg_time = (elapsed / current);
        let mut remaining = (avg_time * (total - current));
        Formatters.duration(remaining)
    }
    /// Format tokens per second rate.
    pub fn tokens_per_second(tokens: i64, seconds: f64) -> String {
        // Format tokens per second rate.
        if seconds <= 0 {
            "N/A".to_string()
        }
        let mut rate = (tokens / seconds);
        format!("{:.1} tok/s", rate)
    }
    /// Truncate text to max length with suffix.
    /// 
    /// Args:
    /// text: Text to truncate
    /// max_length: Maximum length including suffix
    /// suffix: String to append when truncated
    /// 
    /// Returns:
    /// Truncated string
    pub fn truncate(text: String, max_length: i64, suffix: String) -> String {
        // Truncate text to max length with suffix.
        // 
        // Args:
        // text: Text to truncate
        // max_length: Maximum length including suffix
        // suffix: String to append when truncated
        // 
        // Returns:
        // Truncated string
        if text.len() <= max_length {
            text
        }
        (text[..(max_length - suffix.len())] + suffix)
    }
    /// Create a preview of long text, removing newlines.
    pub fn preview(text: String, max_length: i64) -> String {
        // Create a preview of long text, removing newlines.
        let mut clean = text.trim().to_string().replace(&*"\n".to_string(), &*" ".to_string()).replace(&*"  ".to_string(), &*" ".to_string());
        Formatters.truncate(clean, max_length)
    }
}
