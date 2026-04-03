use anyhow::{Result, Context};
use std::collections::HashMap;

/// Test swarm endpoint.
pub fn test_swarm_endpoint() -> Result<()> {
    // Test swarm endpoint.
    println!("{}", "Testing Swarm Endpoint to verify TaskType fix...".to_string());
    let mut url = "http://127.0.0.1:8004/api/chat/swarm".to_string();
    let mut payload = HashMap::from([("message".to_string(), "Why is the sky blue? Explain simply.".to_string())]);
    // try:
    {
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        println!("Sending POST to {}...", url);
        let mut response = /* reqwest::post( */url, /* json= */ payload, /* timeout= */ 120);
        println!("Status Code: {}", response.status_code);
        if response.status_code == 200 {
            let mut data = response.json();
            println!("{}", "✅ Success! Response received.".to_string());
            println!("Response Preview: {}...", data.to_string()[..200]);
            if (data.contains(&"experts".to_string()) && data.contains(&"response".to_string())) {
                println!("{}", "✅ Structure Valid: 'experts' and 'response' present.".to_string());
            } else {
                println!("{}", "⚠️ Warning: Unexpected response structure.".to_string());
            }
        } else if response.status_code == 500 {
            let mut data = response.json();
            println!("❌ Failed: Server Error 500. Message: {}", data.get(&"error".to_string()).cloned());
            if data.get(&"error".to_string()).cloned().unwrap_or("".to_string()).to_string().contains(&"TaskType".to_string()) {
                println!("{}", "❌ 'TaskType' error still persistent!".to_string());
            }
        } else {
            println!("❌ Failed: Unexpected status code {}", response.status_code);
            println!("{}", response.text);
        }
    }
    // except Exception as e:
}
