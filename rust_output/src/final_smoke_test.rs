use anyhow::{Result, Context};
use std::collections::HashMap;

/// Run test.
pub fn run_test() -> Result<()> {
    // Run test.
    println!("{}", "🚀 Starting Final Integration Smoke Test...".to_string());
    let mut ui_url = "http://127.0.0.1:8080".to_string();
    // try:
    {
        let mut r = /* reqwest::get( */&ui_url).cloned().unwrap_or(/* timeout= */ 5);
        println!("✅ UI is up (Status {})", r.status_code);
    }
    // except Exception as _e:
    let mut payload = HashMap::from([("text".to_string(), "Hello ZenAI! Who are you?".to_string())]);
    println!("🔎 Sending message: '{}'", payload["text".to_string()]);
    // try:
    {
        let mut r = /* reqwest::post( */format!("{}/test/send", ui_url), /* json= */ payload, /* timeout= */ 5);
        if r.status_code == 200 {
            println!("{}", "✅ Send command accepted by UI.".to_string());
        } else {
            println!("❌ Send command failed: {} - {}", r.status_code, r.text);
            std::process::exit(1);
        }
    }
    // except Exception as _e:
    println!("{}", "⏳ Waiting for LLM response to propagate to UI...".to_string());
    let mut max_wait = 15;
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time) < max_wait {
        // try:
        {
            let mut r = /* reqwest::get( */&format!("{}/test/state", ui_url)).cloned().unwrap_or(/* timeout= */ 2);
            r.json();
            std::thread::sleep(std::time::Duration::from_secs_f64(2));
        }
        // except Exception as e:
    }
    println!("{}", "\n========================================".to_string());
    println!("{}", "🏁 Smoke Test Finished.".to_string());
    println!("{}", "Please check the zena.py and start_llm::py logs for '[AsyncBackend] Received chunk' and '[AsyncBackend] Done' messages.".to_string());
    Ok(println!("{}", "========================================".to_string()))
}
