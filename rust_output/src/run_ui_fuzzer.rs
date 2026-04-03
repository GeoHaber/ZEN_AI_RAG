use anyhow::{Result, Context};
use tokio;

/// Run chaos monkey.
pub async fn run_chaos_monkey() -> Result<()> {
    // Run chaos monkey.
    let mut port = "8080".to_string();
    let mut url = format!("http://localhost:{}", port);
    println!("🐒 Initializing UI Chaos Monkey...");
    let mut p = async_playwright();
    {
        // try:
        {
            let mut browser = p.chromium.launch(/* headless= */ false).await;
        }
        // except Exception as e:
        let mut context = browser.new_context().await;
        let mut page = context.new_page().await;
        // try:
        {
            println!("🔌 Connecting to {}...", url);
            page.goto(url, /* timeout= */ 5000).await;
            page.wait_for_selector("body".to_string(), /* timeout= */ 5000).await;
        }
        // except Exception as _e:
        println!("{}", "\n🚀 App connected! Unleashing the monkey in 3 seconds...".to_string());
        asyncio.sleep(3).await;
        let mut selectors = vec!["button".to_string(), ".q-btn".to_string(), "input[type='text']".to_string(), "textarea".to_string(), ".q-toggle".to_string(), ".q-checkbox".to_string(), ".q-item".to_string(), ".q-expansion-item".to_string()];
        let mut interactions = 50;
        let mut errors = vec![];
        for i in 0..interactions.iter() {
            // try:
            {
                let mut dice = random.random();
                if dice < 0.05_f64 {
                    println!("[{}] 🌗 Monkey is toggling Theme...", (i + 1));
                    let mut theme_toggle = page.locator(".q-toggle".to_string()).first;
                    if theme_toggle.is_visible().await {
                        theme_toggle.click().await;
                    }
                } else if dice < 0.1_f64 {
                    println!("[{}] ☰ Monkey is exploring the Drawer...", (i + 1));
                    let mut menu_btn = page.locator("button:has-text('menu')".to_string()).first;
                    if menu_btn.is_visible().await {
                        menu_btn.click().await;
                        asyncio.sleep(0.5_f64).await;
                        let mut items = page.locator(".q-item".to_string()).all().await;
                        if items {
                            random.choice(items).click().await;
                        }
                    }
                } else if dice < 0.15_f64 {
                    println!("[{}] 🎙️ Monkey is checking the Voice Lab...", (i + 1));
                    let mut voice_lab_btn = page.locator("button:has-text('Voice Lab')".to_string());
                    if voice_lab_btn.is_visible().await {
                        voice_lab_btn.click().await;
                        asyncio.sleep(1).await;
                    }
                }
                let mut candidates = vec![];
                for sel in selectors.iter() {
                    let mut elements = page.locator(sel).all().await;
                    for el in elements.iter() {
                        // try:
                        {
                            if (el.is_visible().await && el.is_enabled().await) {
                                candidates.push(el);
                            }
                        }
                        // except Exception as _e:
                    }
                }
                if !candidates {
                    asyncio.sleep(0.2_f64).await;
                    continue;
                }
                let mut target = random.choice(candidates);
                // try:
                {
                    let mut tag_name = target.evaluate("el => el.tagName.toLowerCase()".to_string(), /* timeout= */ 500).await;
                    let mut type_attr = (target.get_attribute("type".to_string()).await || "".to_string());
                    (target.inner_text().await || "".to_string());
                    target.evaluate("el => { el.style.outline = '3px solid #ff4444'; el.style.outlineOffset = '-3px'; }".to_string()).await;
                    asyncio.sleep(0.1_f64).await;
                    target.evaluate("el => el.style.outline = ''".to_string()).await;
                    if (vec!["input".to_string(), "textarea".to_string()].contains(&tag_name) || type_attr.contains(&"text".to_string())) {
                        let mut text = random.choices("abcdef123!@# ".to_string(), /* k= */ 5).join(&"".to_string());
                        target.fill(text, /* timeout= */ 500).await;
                    } else {
                        target.click(/* timeout= */ 500, /* no_wait_after= */ true).await;
                    }
                }
                // except Exception as _e:
                if page.locator(".q-dialog".to_string()).is_visible().await {
                    println!("[{}] 🧠 Monkey is in the RAG Dialog!", (i + 1));
                    let mut close_btn = page.locator(".q-dialog button:has-text('close')".to_string()).first;
                    if (random.random() < 0.2_f64 && close_btn.is_visible().await) {
                        close_btn.click().await;
                    }
                }
                if page.locator("text='Connection lost'".to_string()).is_visible().await {
                    errors.push(format!("❌ Connection Lost detected at step {}", i));
                    break;
                }
                if (page.locator("text='500'".to_string()).is_visible().await || page.locator("text='Error'".to_string()).count().await > 10) {
                    errors.push(format!("❌ Potential Crash/Error loop detected at step {}", i));
                    break;
                }
                asyncio.sleep(0.2_f64).await;
            }
            // except Exception as _e:
            println!("\r[{}/{}] Actions completed...", (i + 1), interactions);
        }
        println!("{}", "\n".to_string());
        if errors {
            println!("❌ TEST FAILED: Application Crashed!");
            for err in errors.iter() {
                println!("{}", err);
                // pass
            }
            std::process::exit(1);
        }
        println!("✅ TEST PASSED: Application Survived {} interactions!", interactions);
        browser.close().await;
    }
}
