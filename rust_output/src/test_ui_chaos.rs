use anyhow::{Result, Context};
use tokio;

/// Navigate to app.
pub async fn navigate_to_app(page: Page) -> Result<()> {
    // Navigate to app.
    let mut port = std::env::var(&"NICEGUI_SCREEN_TEST_PORT".to_string()).unwrap_or_default().cloned().unwrap_or("8080".to_string());
    let mut url = format!("http://localhost:{}", port);
    // try:
    {
        page.goto(url, /* timeout= */ 10000).await;
    }
    // except Exception as e:
    Ok(/* yield */)
}

/// Helper: setup phase for test_chaos_monkey.
pub fn _do_test_chaos_monkey_setup() -> () {
    // Helper: setup phase for test_chaos_monkey.
    println!("{}", "\n🐒 Unleashing Chaos Monkey...".to_string());
    let mut selectors = vec!["button".to_string(), "input[class*='q-field__native']".to_string(), ".q-toggle".to_string(), ".q-btn".to_string()];
    let mut interactions = 25;
    let mut errors = vec![];
    (errors, interactions, selectors)
}

/// Test chaos monkey.
pub async fn test_chaos_monkey(page: Page) -> Result<()> {
    // Test chaos monkey.
    let (mut errors, mut interactions, mut selectors) = _do_test_chaos_monkey_setup();
    page.wait_for_timeout(2000).await;
    for i in 0..interactions.iter() {
        // try:
        {
            let mut candidates = vec![];
            for sel in selectors.iter() {
                let mut elements = page.locator(sel).all().await;
                for el in elements.iter() {
                    if el.is_visible().await {
                        candidates.push(el);
                    }
                }
            }
            if !candidates {
                page.wait_for_timeout(200).await;
                continue;
            }
            let mut target = random.choice(candidates);
            // try:
            {
                let mut tag_name = target.evaluate("el => el.tagName.toLowerCase()".to_string(), /* timeout= */ 200).await;
                if tag_name == "input".to_string() {
                    let mut text = random.choices("abcdef".to_string(), /* k= */ 3).join(&"".to_string());
                    target.fill(text, /* timeout= */ 200).await;
                } else {
                    target.click(/* timeout= */ 200, /* no_wait_after= */ true).await;
                }
            }
            // except Exception as _e:
            if page.locator("text='Connection lost'".to_string()).is_visible().await {
                errors.push(format!("Connection Lost detected at step {}", i));
                break;
            }
            page.wait_for_timeout(50).await;
        }
        // except Exception as _e:
    }
    if errors {
        pytest.fail(format!("❌ Application Crashed: {}", errors));
    }
    assert!(true);
    Ok(println!("{}", "✅ Application Survived!".to_string()))
}
