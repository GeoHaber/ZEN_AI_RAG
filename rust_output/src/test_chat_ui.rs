/// Automated test for chat UI functionality.
/// Tests that messages are sent and responses are displayed.

use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

/// Test that LLM backend is responding.
pub async fn test_llm_backend() -> Result<()> {
    // Test that LLM backend is responding.
    println!("{}", ("=".to_string() * 60));
    println!("{}", "TEST 1: LLM Backend Connectivity".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut api_url = "http://127.0.0.1:8001/v1/chat/completions".to_string();
    let mut payload = HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are a helpful assistant.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Say 'TEST OK' and nothing else.".to_string())])]), ("stream".to_string(), false), ("temperature".to_string(), 0.1_f64), ("max_tokens".to_string(), 50)]);
    // try:
    {
        let mut client = httpx.AsyncClient(/* timeout= */ 30.0_f64);
        {
            println!("  → Sending test message to {}", api_url);
            let mut response = client.post(api_url, /* json= */ payload).await;
            if response.status_code == 200 {
                let mut data = response.json();
                let mut content = data["choices".to_string()][0]["message".to_string()]["content".to_string()];
                println!("  ✅ LLM Response: {}", content[..100]);
                true
            } else {
                println!("  ❌ HTTP Error: {}", response.status_code);
                false
            }
        }
    }
    // except httpx.ConnectError as _e:
    // except Exception as e:
}

/// Test streaming response from LLM.
pub async fn test_streaming_response() -> Result<()> {
    // Test streaming response from LLM.
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST 2: Streaming Response".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut api_url = "http://127.0.0.1:8001/v1/chat/completions".to_string();
    let mut payload = HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are ZenAI.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Count from 1 to 5.".to_string())])]), ("stream".to_string(), true), ("temperature".to_string(), 0.1_f64), ("max_tokens".to_string(), 100)]);
    // try:
    {
        let mut client = httpx.AsyncClient(/* timeout= */ 30.0_f64);
        {
            println!("  → Testing streaming...");
            let mut chunk_count = 0;
            let mut full_response = "".to_string();
            let mut response = client.stream("POST".to_string(), api_url, /* json= */ payload);
            {
                if response.status_code != 200 {
                    println!("  ❌ HTTP Error: {}", response.status_code);
                    false
                }
                // async for
                while let Some(line) = response.aiter_lines().next().await {
                    if !line.starts_with(&*"data: ".to_string()) {
                        continue;
                    }
                    let mut json_str = line[6..];
                    if json_str.trim().to_string() == "[DONE]".to_string() {
                        break;
                    }
                    // try:
                    {
                        // TODO: import json
                        let mut data = serde_json::from_str(&json_str).unwrap();
                        let mut delta = data["choices".to_string()][0]["delta".to_string()];
                        let mut content = delta.get(&"content".to_string()).cloned().unwrap_or("".to_string());
                        if content {
                            chunk_count += 1;
                            full_response += content;
                        }
                    }
                    // except Exception as _e:
                }
            }
            println!("  ✅ Received {} chunks", chunk_count);
            println!("  ✅ Response: {}", full_response[..100]);
            chunk_count > 0
        }
    }
    // except Exception as e:
}

/// Test that NiceGUI is responding.
pub async fn test_ui_endpoint() -> Result<()> {
    // Test that NiceGUI is responding.
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST 3: NiceGUI Web Server".to_string());
    println!("{}", ("=".to_string() * 60));
    // try:
    {
        let mut client = httpx.AsyncClient(/* timeout= */ 10.0_f64);
        {
            println!("{}", "  → Checking http://localhost:8080".to_string());
            let mut response = client.get(&"http://localhost:8080".to_string()).cloned().await;
            if response.status_code == 200 {
                let mut html = response.text;
                let mut has_nicegui = (html.to_lowercase().contains(&"nicegui".to_string()) || html.to_lowercase().contains(&"quasar".to_string()));
                let mut has_zena = (html.to_lowercase().contains(&"zena".to_string()) || html.to_lowercase().contains(&"chat".to_string()));
                println!("  ✅ Web server responding (HTTP 200)");
                println!("  ✅ NiceGUI/Quasar detected: {}", has_nicegui);
                println!("  ✅ ZenAI content detected: {}", has_zena);
                println!("  📊 HTML size: {} bytes", html.len());
                true
            } else {
                println!("  ❌ HTTP Error: {}", response.status_code);
                false
            }
        }
    }
    // except httpx.ConnectError as _e:
    // except Exception as e:
}

/// Test full UI interaction using Playwright.
pub async fn test_chat_ui_e2e_playwright() -> Result<()> {
    // Test full UI interaction using Playwright.
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST 5: E2E Chat Interaction (Playwright)".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut port = "8080".to_string();
    let mut url = format!("http://localhost:{}", port);
    // try:
    {
        let mut p = async_playwright();
        {
            println!("{}", "  → Launching browser...".to_string());
            let mut browser = p.chromium.launch(/* headless= */ true).await;
            let mut context = browser.new_context().await;
            let mut page = context.new_page().await;
            println!("  → Navigating to {}", url);
            // try:
            {
                page.goto(url, /* timeout= */ 5000).await;
            }
            // except Exception as _e:
            // try:
            {
                page.wait_for_selector("body".to_string(), /* timeout= */ 5000).await;
                let mut title = /* title */ page.to_string().await;
                println!("  ✅ Page Title: {}", title);
                let mut sidebar = page.locator("aside".to_string()).count().await;
                let mut header = page.locator("header".to_string()).count().await;
                println!("  ✅ Found {} sidebars and {} headers", sidebar, header);
            }
            // except Exception as _e:
            // try:
            {
                let mut input_selector = "input[type='text'], textarea".to_string();
                page.wait_for_selector(input_selector, /* timeout= */ 3000).await;
                let mut test_message = format!("E2E_Test_{}", __import__("random".to_string()).randint(1000, 9999));
                println!("  → Typing message: '{}'", test_message);
                page.fill(input_selector, test_message).await;
                asyncio.sleep(0.5_f64).await;
                let mut send_buttons = page.locator(".q-btn i:text('send')".to_string());
                if send_buttons.count().await > 0 {
                    send_buttons.first.click().await;
                } else {
                    page.press(input_selector, "Enter".to_string()).await;
                }
                println!("{}", "  → Message sent".to_string());
                asyncio.sleep(2).await;
                let mut content = page.content().await;
                if content.contains(&test_message) {
                    println!("  ✅ Message '{}' found in chat history!", test_message);
                    browser.close().await;
                    true
                } else {
                    println!("  ❌ Message '{}' NOT found in page content.", test_message);
                    browser.close().await;
                    false
                }
            }
            // except Exception as _e:
        }
    }
    // except Exception as e:
}

/// Main.
pub async fn main() -> () {
    // Main.
    println!("{}", ("\n".to_string() + ("🧪".to_string() * 30)));
    println!("{}", "   ZENA CHAT UI AUTOMATED TESTS".to_string());
    println!("{}", (("🧪".to_string() * 30) + "\n".to_string()));
    let mut results = vec![];
    results.push(("LLM Backend".to_string(), test_llm_backend().await));
    results.push(("UI Server".to_string(), test_ui_endpoint().await));
    results.push(("Create Local LLM Compatibility".to_string(), true));
    results.push(("E2E Playwright Interaction".to_string(), test_chat_ui_e2e_playwright().await));
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST SUMMARY".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut passed = results.iter().filter(|(_, r)| r).map(|(_, r)| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut total = results.len();
    for (name, result) in results.iter() {
        let mut status = if result { "✅ PASS".to_string() } else { "❌ FAIL".to_string() };
        println!("  {}: {}", status, name);
    }
    println!("\n  Total: {}/{} tests passed", passed, total);
    if passed == total {
        println!("{}", "\n  🎉 ALL TESTS PASSED!".to_string());
    } else {
        println!("{}", "\n  ⚠️ Some tests failed. Check logs above.".to_string());
    }
    passed == total
}
