use anyhow::{Result, Context};

/// Run chaos.
pub fn run_chaos() -> Result<()> {
    // Run chaos.
    let mut port = std::env::var(&"NICEGUI_SCREEN_TEST_PORT".to_string()).unwrap_or_default().cloned().unwrap_or("8080".to_string());
    let mut url = format!("http://localhost:{}", port);
    println!("🐒 Unleashing Chaos Monkey on {}...", url);
    let mut p = sync_playwright();
    {
        let mut browser = p.chromium.launch();
        let mut page = browser.new_page();
        // try:
        {
            page.goto(url, /* timeout= */ 10000);
        }
        // except Exception as _e:
        page.wait_for_timeout(2000);
        let mut selectors = vec!["button".to_string(), "input[class*='q-field__native']".to_string(), ".q-toggle".to_string(), ".q-btn".to_string()];
        let mut interactions = 25;
        let mut errors = vec![];
        println!("{}", "⚡ Starting frenzy...".to_string());
        for i in 0..interactions.iter() {
            // try:
            {
                let mut candidates = vec![];
                for sel in selectors.iter() {
                    let mut elements = page.locator(sel).all();
                    for el in elements.iter() {
                        if el.is_visible() {
                            candidates.push(el);
                        }
                    }
                }
                if !candidates {
                    page.wait_for_timeout(200);
                    continue;
                }
                let mut target = random.choice(candidates);
                // try:
                {
                    let mut tag = target.evaluate("el => el.tagName.toLowerCase()".to_string());
                    if tag == "input".to_string() {
                        let mut text = random.choices("xyz".to_string(), /* k= */ 3).join(&"".to_string());
                        target.fill(text, /* timeout= */ 200);
                    } else {
                        target.click(/* timeout= */ 200, /* no_wait_after= */ true);
                    }
                }
                // except Exception as _e:
                if page.locator("text='Connection lost'".to_string()).is_visible() {
                    println!("🚨 CRASH DETECTED at step {}", i);
                    errors.push("Connection Lost".to_string());
                    break;
                }
                page.wait_for_timeout(50);
            }
            // except Exception as e:
        }
        if errors {
            println!("{}", "❌ Test Failed: Application Crashed".to_string());
            std::process::exit(1);
        } else {
            println!("{}", "✅ Application Survived! (Sync Chaos Test Passed)".to_string());
        }
        browser.close();
    }
}
