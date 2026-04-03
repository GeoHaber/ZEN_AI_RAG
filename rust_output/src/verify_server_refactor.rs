use anyhow::{Result, Context};

/// Test routes.
pub fn test_routes() -> Result<()> {
    // Test routes.
    let mut base_url = "http://127.0.0.1:8002".to_string();
    let mut routes = vec!["/api/test-llm".to_string(), "/list".to_string(), "/startup/progress".to_string(), "/models/popular".to_string()];
    println!("{}", "--- ZenAI Server Smoke Test ---".to_string());
    for route in routes.iter() {
        // try:
        {
            println!("Testing {}...", route);
            let mut resp = /* reqwest::get( */&format!("{}{}", base_url, route)).cloned().unwrap_or(/* timeout= */ 2);
            if resp.status_code == 200 {
                println!("OK ({} bytes)", resp.text.len());
                // pass
            } else {
                println!("FAILED ({}): {}", resp.status_code, resp.text);
                // pass
            }
        }
        // except Exception as e:
    }
}
