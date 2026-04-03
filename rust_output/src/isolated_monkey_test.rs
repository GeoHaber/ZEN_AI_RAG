/// tests/isolated_monkey_test::py - Headless UI Monkey Test
/// Hits the test endpoints of zena.py to simulate user interactions.

use anyhow::{Result, Context};
use crate::registry::{MONKEY_TARGETS};

pub const BASE_URL: &str = "http://127.0.0.1:8080";

/// Run monkey test.
pub fn run_monkey_test() -> Result<()> {
    // Run monkey test.
    println!("🚀 Starting Isolated Monkey Test on {}", BASE_URL);
    let mut passed = 0;
    let mut failed = 0;
    // try:
    {
        /* reqwest::get( */&BASE_URL).cloned().unwrap_or(/* timeout= */ 5);
        println!("{}", "✅ UI Server is reachable.".to_string());
    }
    // except Exception as _e:
    for element_id in MONKEY_TARGETS.iter() {
        println!("🔎 Poking {}...", element_id);
        // try:
        {
            let mut resp = /* reqwest::post( */format!("{}/test/click/{}", BASE_URL, element_id), /* timeout= */ 5);
            if resp.status_code == 200 {
                println!("{}", "OK".to_string());
                passed += 1;
            } else {
                println!("FAIL (Status {})", resp.status_code);
                failed += 1;
            }
        }
        // except Exception as e:
        std::thread::sleep(std::time::Duration::from_secs_f64(0.5_f64));
    }
    println!("{}", ("\n".to_string() + ("=".to_string() * 40)));
    println!("🐒 Monkey Test Finished: {} PASSED, {} FAILED", passed, failed);
    println!("{}", ("=".to_string() * 40));
    if failed > 0 {
        println!("{}", "⚠️ Warning: Some UI elements caused errors. Check zena.py console/logs.".to_string());
        std::process::exit(1);
    } else {
        println!("{}", "✨ All UI elements responded correctly!".to_string());
        std::process::exit(0);
    }
}
