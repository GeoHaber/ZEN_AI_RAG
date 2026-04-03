/// test_ui_visual_contrast::py - Visual Contrast and Visibility Testing
/// 
/// WHAT:
/// Tests actual visual appearance of UI elements in both light and dark modes.
/// Validates color contrast ratios, icon visibility, text readability.
/// Identifies elements that blend into background or have insufficient contrast.
/// 
/// WHY:
/// - Purpose: Ensure UI is actually visible and usable in both themes
/// - Problem solved: Mock tests passed but real UI has visibility issues
/// - Design decision: Test actual colors, not just structure
/// 
/// HOW:
/// 1. Define light and dark mode color schemes
/// 2. Calculate contrast ratios for each element
/// 3. Check WCAG AAA standards (7:1 for text, 3:1 for UI)
/// 4. Identify elements with poor visibility
/// 5. Generate fix recommendations
/// 
/// TESTING:
/// Run visual contrast tests:
/// python tests/test_ui_visual_contrast::py
/// 
/// AUTHOR: ZenAI Team
/// MODIFIED: 2026-01-24
/// VERSION: 1.0.0

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LIGHT_MODE: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static DARK_MODE: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static ELEMENTS_LIGHT_MODE: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

pub static ELEMENTS_DARK_MODE: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

/// Convert hex color to RGB tuple.
pub fn hex_to_rgb(hex_color: String) -> (i64, i64, i64) {
    // Convert hex color to RGB tuple.
    let mut hex_color = hex_color.trim_start_matches(|c: char| "#".to_string().contains(c)).to_string();
    if hex_color.len() == 3 {
        let mut hex_color = hex_color.iter().map(|c| (c * 2)).collect::<Vec<_>>().join(&"".to_string());
    }
    /* tuple */ ((0, 2, 4).iter().map(|i| int(hex_color[i..(i + 2)], 16)).collect::<Vec<_>>())
}

/// Calculate relative luminance of RGB color (WCAG formula).
pub fn rgb_to_luminance(rgb: (i64, i64, i64)) -> f64 {
    // Calculate relative luminance of RGB color (WCAG formula).
    let (mut r, mut g, mut b) = rgb.iter().map(|x| (x / 255.0_f64)).collect::<Vec<_>>();
    let adjust = |c| {
        if c <= 0.03928_f64 { (c / 12.92_f64) } else { (((c + 0.055_f64) / 1.055_f64)).pow(2.4_f64 as u32) }
    };
    let (mut r, mut g, mut b) = (adjust(r), adjust(g), adjust(b));
    (((0.2126_f64 * r) + (0.7152_f64 * g)) + (0.0722_f64 * b))
}

/// Calculate WCAG contrast ratio between two colors.
pub fn contrast_ratio(color1: String, color2: String) -> f64 {
    // Calculate WCAG contrast ratio between two colors.
    let mut l1 = rgb_to_luminance(hex_to_rgb(color1));
    let mut l2 = rgb_to_luminance(hex_to_rgb(color2));
    let mut lighter = l1.max(l2);
    let mut darker = l1.min(l2);
    ((lighter + 0.05_f64) / (darker + 0.05_f64))
}

/// Check if contrast ratio passes WCAG AA standards.
pub fn passes_wcag_aa(ratio: f64, is_large_text: bool) -> bool {
    // Check if contrast ratio passes WCAG AA standards.
    if is_large_text { ratio >= 3.0_f64 } else { ratio >= 4.5_f64 }
}

/// Check if contrast ratio passes WCAG AAA standards.
pub fn passes_wcag_aaa(ratio: f64, is_large_text: bool) -> bool {
    // Check if contrast ratio passes WCAG AAA standards.
    if is_large_text { ratio >= 4.5_f64 } else { ratio >= 7.0_f64 }
}

/// Test contrast ratio for a single element.
pub fn test_element_contrast(element: HashMap<String, serde_json::Value>, mode: String) -> HashMap {
    // Test contrast ratio for a single element.
    let mut name = element["name".to_string()];
    let mut bg = element["bg".to_string()];
    let mut fg = element["fg".to_string()];
    let mut elem_type = element["type".to_string()];
    if fg.is_none() {
        HashMap::from([("name".to_string(), name), ("mode".to_string(), mode), ("type".to_string(), elem_type), ("status".to_string(), "SKIP".to_string()), ("ratio".to_string(), None), ("wcag_aa".to_string(), None), ("wcag_aaa".to_string(), None), ("issue".to_string(), None)])
    }
    let mut ratio = contrast_ratio(bg, fg);
    let mut is_large = vec!["heading".to_string(), "logo".to_string()].contains(&elem_type);
    let mut aa_pass = passes_wcag_aa(ratio, is_large);
    let mut aaa_pass = passes_wcag_aaa(ratio, is_large);
    if vec!["icon".to_string(), "ui".to_string()].contains(&elem_type) {
        let mut aa_pass = ratio >= 3.0_f64;
        let mut aaa_pass = ratio >= 4.5_f64;
    }
    let mut status = if aa_pass { "PASS".to_string() } else { "FAIL".to_string() };
    let mut issue = None;
    if !aa_pass {
        if elem_type == "text".to_string() {
            let mut issue = format!("Text contrast too low ({:.2}:1, need 4.5:1)", ratio);
        } else if elem_type == "icon".to_string() {
            let mut issue = format!("Icon contrast too low ({:.2}:1, need 3:1)", ratio);
        } else if elem_type == "ui".to_string() {
            let mut issue = format!("UI element contrast too low ({:.2}:1, need 3:1)", ratio);
        }
    }
    HashMap::from([("name".to_string(), name), ("mode".to_string(), mode), ("type".to_string(), elem_type), ("bg".to_string(), bg), ("fg".to_string(), fg), ("ratio".to_string(), ratio), ("wcag_aa".to_string(), aa_pass), ("wcag_aaa".to_string(), aaa_pass), ("status".to_string(), status), ("issue".to_string(), issue)])
}

/// Helper: setup phase for run_contrast_tests.
pub fn _do_run_contrast_tests_setup() -> () {
    // Helper: setup phase for run_contrast_tests.
    println!("{}", ("=".to_string() * 80));
    println!("{}", "VISUAL CONTRAST & VISIBILITY TESTING".to_string());
    println!("{}", ("=".to_string() * 80));
    println!();
    let mut results = HashMap::from([("light".to_string(), vec![]), ("dark".to_string(), vec![])]);
    println!("{}", "LIGHT MODE".to_string());
    println!("{}", ("-".to_string() * 80));
    for element in ELEMENTS_LIGHT_MODE.iter() {
        let mut result = test_element_contrast(element, "light".to_string());
        results["light".to_string()].push(result);
        if result["status".to_string()] == "SKIP".to_string() {
            continue;
        }
        let mut status_icon = if result["status".to_string()] == "PASS".to_string() { "[OK]".to_string() } else { "[FAIL]".to_string() };
        let mut ratio_str = if result["ratio".to_string()] { format!("{:.2}:1", result["ratio".to_string()]) } else { "N/A".to_string() };
        println!("{} {:<30} {:>10} {:>10}", status_icon, result["name".to_string()], ratio_str, result["type".to_string()]);
        if result["issue".to_string()] {
            println!("      -> {}", result["issue".to_string()]);
            // pass
        }
    }
    println!();
    println!("{}", "DARK MODE".to_string());
    println!("{}", ("-".to_string() * 80));
    for element in ELEMENTS_DARK_MODE.iter() {
        let mut result = test_element_contrast(element, "dark".to_string());
        results["dark".to_string()].push(result);
        if result["status".to_string()] == "SKIP".to_string() {
            continue;
        }
        let mut status_icon = if result["status".to_string()] == "PASS".to_string() { "[OK]".to_string() } else { "[FAIL]".to_string() };
        let mut ratio_str = if result["ratio".to_string()] { format!("{:.2}:1", result["ratio".to_string()]) } else { "N/A".to_string() };
        println!("{} {:<30} {:>10} {:>10}", status_icon, result["name".to_string()], ratio_str, result["type".to_string()]);
        if result["issue".to_string()] {
            println!("      -> {}", result["issue".to_string()]);
            // pass
        }
    }
    println!();
    println!("{}", ("=".to_string() * 80));
    results
}

/// Run contrast tests on all elements in both modes.
pub fn run_contrast_tests() -> () {
    // Run contrast tests on all elements in both modes.
    let mut results = _do_run_contrast_tests_setup();
    let mut light_fail = results["light".to_string()].iter().filter(|r| r["status".to_string()] == "FAIL".to_string()).map(|r| r).collect::<Vec<_>>();
    let mut dark_fail = results["dark".to_string()].iter().filter(|r| r["status".to_string()] == "FAIL".to_string()).map(|r| r).collect::<Vec<_>>();
    println!("{}", "SUMMARY".to_string());
    println!("{}", ("=".to_string() * 80));
    println!("Light Mode: {} failures out of {}", light_fail.len(), results["light".to_string()].iter().filter(|r| r["status".to_string()] != "SKIP".to_string()).map(|r| r).collect::<Vec<_>>().len());
    println!("Dark Mode:  {} failures out of {}", dark_fail.len(), results["dark".to_string()].iter().filter(|r| r["status".to_string()] != "SKIP".to_string()).map(|r| r).collect::<Vec<_>>().len());
    println!();
    if (light_fail || dark_fail) {
        println!("{}", "ISSUES FOUND:".to_string());
        println!("{}", ("-".to_string() * 80));
        if light_fail {
            println!("{}", "\nLight Mode Issues:".to_string());
            for r in light_fail.iter() {
                println!("  - {}: {}", r["name".to_string()], r["issue".to_string()]);
                println!("    BG: {} | FG: {}", r["bg".to_string()], r["fg".to_string()]);
                println!("    Recommended FG for 4.5:1 contrast: Use darker/lighter color");
                // pass
            }
        }
        if dark_fail {
            println!("{}", "\nDark Mode Issues:".to_string());
            for r in dark_fail.iter() {
                println!("  - {}: {}", r["name".to_string()], r["issue".to_string()]);
                println!("    BG: {} | FG: {}", r["bg".to_string()], r["fg".to_string()]);
                println!("    Recommended FG for 4.5:1 contrast: Use lighter color");
                // pass
            }
        }
        println!();
        generate_fixes(light_fail, dark_fail);
        false
    } else {
        println!("{}", "[OK] All contrast tests passed!".to_string());
        true
    }
}

/// Generate CSS fixes for failing elements.
pub fn generate_fixes(light_fail: Vec<HashMap>, dark_fail: Vec<HashMap>) -> () {
    // Generate CSS fixes for failing elements.
    println!("{}", ("=".to_string() * 80));
    println!("{}", "RECOMMENDED FIXES".to_string());
    println!("{}", ("=".to_string() * 80));
    println!();
    if light_fail {
        println!("{}", "/* Light Mode Fixes */".to_string());
        for item in light_fail.iter() {
            if (item["name".to_string()].contains(&"Icon".to_string()) || item["type".to_string()].contains(&"icon".to_string())) {
                println!("/* {} - increase icon color darkness */", item["name".to_string()]);
                println!(".icon-class {{ color: #374151; /* gray-700 for better contrast */ }}");
                // pass
            } else if item["name".to_string()].contains(&"Toggle".to_string()) {
                println!("/* {} - increase toggle visibility */", item["name".to_string()]);
                println!(".q-toggle__track {{ opacity: 1 !important; background: #D1D5DB !important; }}");
                // pass
            } else if item["name".to_string()].contains(&"Border".to_string()) {
                println!("/* {} - darken border */", item["name".to_string()]);
                println!(".border {{ border-color: #9CA3AF !important; }}");
                // pass
            }
        }
        println!();
    }
    if dark_fail {
        println!("{}", "/* Dark Mode Fixes */".to_string());
        for item in dark_fail.iter() {
            if (item["name".to_string()].contains(&"Icon".to_string()) || item["type".to_string()].contains(&"icon".to_string())) {
                println!("/* {} - increase icon color lightness */", item["name".to_string()]);
                println!(".dark .icon-class {{ color: #E2E8F0; /* slate-200 for better contrast */ }}");
                // pass
            } else if item["name".to_string()].contains(&"Toggle".to_string()) {
                println!("/* {} - increase toggle visibility */", item["name".to_string()]);
                println!(".dark .q-toggle__track {{ opacity: 1 !important; background: #475569 !important; }}");
                // pass
            } else if item["name".to_string()].contains(&"Border".to_string()) {
                println!("/* {} - lighten border */", item["name".to_string()]);
                println!(".dark .border {{ border-color: #475569 !important; }}");
                // pass
            }
        }
        println!();
    }
}
