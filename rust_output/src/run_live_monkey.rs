/// run_live_monkey::py - Live UI Monkey Test Runner
/// ================================================
/// Run this while ZenAI is running to perform live chaos testing!
/// Open your browser to http://localhost:8080 to watch the chaos unfold.
/// 
/// Usage: python tests/run_live_monkey::py

use anyhow::{Result, Context};
use std::collections::HashMap;

pub const BASE_URL: &str = "http://127.0.0.1:8080";

pub static BUTTON_IDS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static QUICK_ACTION_BUTTONS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static CHAOS_MESSAGES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Print banner.
pub fn print_banner() -> () {
    // Print banner.
    println!("{}", "\n╔═══════════════════════════════════════════════════════════════╗\n║                    🐒  LIVE MONKEY TEST  🐒                    ║\n║                                                               ║\n║  Watch your browser at http://localhost:8080 to see the UI   ║\n║  react to random chaos clicks and messages!                  ║\n╚═══════════════════════════════════════════════════════════════╝\n".to_string());
}

/// Verify ZenAI is running.
pub fn check_connection() -> Result<()> {
    // Verify ZenAI is running.
    println!("⏳ Waiting for ZenAI at {}...", BASE_URL);
    for i in 0..20.iter() {
        // try:
        {
            let mut r = /* reqwest::get( */&BASE_URL).cloned().unwrap_or(/* timeout= */ 5);
            if r.status_code == 200 {
                println!("{}", "✅ ZenAI is running at".to_string(), BASE_URL);
                true
            }
        }
        // except Exception as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(2));
        if (i % 2) == 0 {
            println!("   ... attempting connection ({}s)", (i * 2));
            // pass
        }
    }
    println!("{}", "❌ Cannot connect to ZenAI (Timeout)".to_string());
    Ok(false)
}

/// Trigger a click on a UI element via the app's test API.
pub fn trigger_click(element_id: String) -> Result<()> {
    // Trigger a click on a UI element via the app's test API.
    // try:
    {
        /* reqwest::post( */format!("{}/_nicegui/api/run_javascript", BASE_URL), /* json= */ HashMap::from([("code".to_string(), format!("\n                const btn = document.querySelector('[id*=\"{}\"]', timeout=30) || \n                            document.evaluate('//*[contains(text(), \"{}\")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;\n                if (btn) {{ btn.click(); console.log('Clicked: {}'); }}\n            ", element_id, element_id, element_id))]), /* timeout= */ 2);
        println!("   🖱️  Clicked: {}", element_id);
    }
    // except Exception as _e:
    Ok(std::thread::sleep(std::time::Duration::from_secs_f64(0.3_f64)))
}

/// Send a message by typing in the input and clicking send.
pub fn send_message(text: String) -> Result<()> {
    // Send a message by typing in the input and clicking send.
    // try:
    {
        let mut escaped_text = text.replace(&*"'".to_string(), &*"\\'".to_string()).replace(&*"\"".to_string(), &*"\\\"".to_string())[..200];
        /* reqwest::post( */format!("{}/_nicegui/api/run_javascript", BASE_URL), /* json= */ HashMap::from([("code".to_string(), format!("\n                const input = document.querySelector('input[placeholder*=\"anything\"]', timeout=30) || \n                              document.querySelector('textarea');\n                if (input) {{\n                    input.value = '{}';\n                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));\n                    const sendBtn = document.querySelector('[id*=\"send\"]') ||\n                                    document.querySelector('button[class*=\"primary\"]');\n                    if (sendBtn) sendBtn.click();\n                }}\n            ", escaped_text))]), /* timeout= */ 2);
        println!("   💬 Sent: {}{}", text[..50], if text.len() > 50 { "...".to_string() } else { "".to_string() });
    }
    // except Exception as _e:
    Ok(std::thread::sleep(std::time::Duration::from_secs_f64(0.5_f64)))
}

/// Run chaos monkey for specified duration.
pub fn run_chaos_sequence(duration_seconds: String) -> () {
    // Run chaos monkey for specified duration.
    println!("\n🐒 Starting {}s chaos sequence...", duration_seconds);
    println!("{}", "   Watch your browser!\n".to_string());
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut action_count = 0;
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) < duration_seconds {
        let mut action = random.choice(vec!["click".to_string(), "message".to_string(), "wait".to_string()]);
        if action == "click".to_string() {
            let mut target = random.choice((BUTTON_IDS + QUICK_ACTION_BUTTONS));
            trigger_click(target);
            action_count += 1;
        } else if action == "message".to_string() {
            let mut msg = random.choice(CHAOS_MESSAGES);
            send_message(msg);
            action_count += 1;
        } else {
            let mut pause = random.uniform(0.1_f64, 0.5_f64);
            std::thread::sleep(std::time::Duration::from_secs_f64(pause));
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(random.uniform(0.1_f64, 0.3_f64)));
    }
    action_count
}

/// Interactive chaos mode - press Enter for each action.
pub fn run_manual_chaos() -> () {
    // Interactive chaos mode - press Enter for each action.
    println!("{}", "\n🐒 MANUAL CHAOS MODE".to_string());
    println!("{}", "   Press Enter to trigger random action, 'q' to quit\n".to_string());
    let mut action_count = 0;
    while true {
        let mut user_input = input(format!("[{}] Press Enter (or 'q' to quit): ", action_count));
        if user_input.to_lowercase() == "q".to_string() {
            break;
        }
        let mut action = random.choice(vec!["click".to_string(), "click".to_string(), "message".to_string()]);
        if action == "click".to_string() {
            let mut target = random.choice((BUTTON_IDS + QUICK_ACTION_BUTTONS));
            trigger_click(target);
        } else {
            let mut msg = random.choice(CHAOS_MESSAGES);
            send_message(msg);
        }
        action_count += 1;
    }
    action_count
}

/// Main.
pub fn main() -> () {
    // Main.
    print_banner();
    if !check_connection() {
        std::process::exit(1);
    }
    println!("{}", "\n📋 Available modes:".to_string());
    println!("{}", "   1. Auto chaos (30 seconds of random actions)".to_string());
    println!("{}", "   2. Manual chaos (you control the pace)".to_string());
    println!("{}", "   3. Quick burst (10 rapid actions)".to_string());
    let mut choice = input("\nSelect mode (1/2/3): ".to_string()).trim().to_string();
    if choice == "1".to_string() {
        let mut count = run_chaos_sequence(30);
        println!("\n✅ Completed {} chaotic actions!", count);
    } else if choice == "2".to_string() {
        let mut count = run_manual_chaos();
        println!("\n✅ Completed {} chaotic actions!", count);
    } else if choice == "3".to_string() {
        println!("{}", "\n🐒 Quick burst mode - 10 rapid actions!".to_string());
        for i in 0..10.iter() {
            let mut target = random.choice(BUTTON_IDS);
            trigger_click(target);
            std::thread::sleep(std::time::Duration::from_secs_f64(0.2_f64));
        }
        println!("{}", "✅ Done!".to_string());
    } else {
        println!("{}", "Invalid choice. Running auto mode...".to_string());
        let mut count = run_chaos_sequence(15);
        println!("\n✅ Completed {} chaotic actions!", count);
    }
    println!("{}", "\n📊 Check your browser to see the results!".to_string());
    println!("{}", "   Any crashes or errors would be visible in the ZenAI console.".to_string());
}
