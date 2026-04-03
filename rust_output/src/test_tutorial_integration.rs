use anyhow::{Result, Context};

pub const BASE_URL: &str = "http://127.0.0.1:8080";

/// Test tutorial trigger.
pub fn test_tutorial_trigger() -> Result<()> {
    // Test tutorial trigger.
    println!("{}", "🚀 Starting Tutorial Integration Test...".to_string());
    // try:
    {
        let mut resp = /* reqwest::get( */&format!("{}/", BASE_URL)).cloned().unwrap_or(/* timeout= */ 5);
        println!("✅ Server is UP (Status: {})", resp.status_code);
    }
    // except Exception as _e:
    println!("{}", "Checking initial UI state...".to_string());
    let mut state_resp = /* reqwest::get( */&format!("{}/test/state", BASE_URL)).cloned().unwrap_or(/* timeout= */ 30);
    if state_resp.status_code == 200 {
        let mut state = state_resp.json();
        println!("Initial Notifications: {}", state::get(&"notifications".to_string()).cloned().unwrap_or(vec![]));
    }
    println!("{}", "Triggering 'Start Quick Tour' button...".to_string());
    let mut click_resp = /* reqwest::post( */format!("{}/test/click/ui-btn-start-tour", BASE_URL), /* timeout= */ 30);
    if click_resp.status_code == 200 {
        println!("{}", "✅ Click command sent successfully.".to_string());
    } else {
        println!("❌ Failed to send click command: {}", click_resp.text);
        false
    }
    println!("{}", "Waiting for tutorial dialog to appear (3s)...".to_string());
    std::thread::sleep(std::time::Duration::from_secs_f64(3));
    let mut state_resp = /* reqwest::get( */&format!("{}/test/state", BASE_URL)).cloned().unwrap_or(/* timeout= */ 30);
    if state_resp.status_code == 200 {
        let mut state = state_resp.json();
        let mut active_dialogs = state::get(&"active_dialogs".to_string()).cloned().unwrap_or(0);
        println!("Active Dialogs: {}", active_dialogs);
        if active_dialogs > 0 {
            println!("{}", "✅ Tutorial Dialog DETECTED!".to_string());
            true
        } else {
            println!("{}", "❌ No Tutorial Dialog detected. Tour failed to start.".to_string());
            false
        }
    }
    Ok(false)
}
