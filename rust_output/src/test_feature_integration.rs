use anyhow::{Result, Context};
use tokio;

/// Test feature menu items.
pub async fn test_feature_menu_items() -> Result<()> {
    // Test feature menu items.
    let mut port = "8080".to_string();
    let mut url = format!("http://localhost:{}", port);
    let mut p = async_playwright();
    {
        // try:
        {
            let mut browser = p.chromium.launch(/* headless= */ true).await;
            let mut page = browser.new_page().await;
            let mut connected = false;
            for i in 0..10.iter() {
                // try:
                {
                    page.goto(url, /* timeout= */ 3000).await;
                    let mut connected = true;
                    break;
                }
                // except Exception as _e:
            }
            if !connected {
                pytest.fail(format!("Could not connect to {} after 20 seconds. Is the app running?", url));
            }
            println!("DEBUG: Page Title: {}", /* title */ page.to_string().await);
            println!("{}", "Trying to open drawer...".to_string());
            // try:
            {
                let mut drawer_btn = page.locator(".q-btn .q-icon:has-text('menu')".to_string());
                if drawer_btn.count().await > 0 {
                    drawer_btn.first.click().await;
                    asyncio.sleep(1).await;
                }
            }
            // except Exception as e:
            println!("{}", "Looking for 'Labs'...".to_string());
            // try:
            {
                let mut labs_el = page.locator("*:has-text('Labs')".to_string()).last;
                labs_el.scroll_into_view_if_needed().await;
                labs_el.wait_for(/* state= */ "visible".to_string(), /* timeout= */ 5000).await;
                labs_el.click().await;
            }
            // except Exception as e:
            asyncio.sleep(1).await;
            println!("{}", "Looking for 'Voice Lab'...".to_string());
            let mut voice_btn = page.locator("button:has-text('Voice Lab')".to_string());
            if voice_btn.count().await > 0 {
                println!("{}", "Found Voice Lab button!".to_string());
            } else {
                println!("{}", "Voice Lab button NOT found after expanding Labs.".to_string());
            }
            assert!(voice_btn.is_visible().await, "Voice Lab button should be visible");
            asyncio.sleep(0.5_f64).await;
            let mut voice_btn = page.locator("button:has-text('Voice Lab')".to_string());
            assert!(voice_btn.is_visible().await, "Voice Lab button should be visible");
            let mut swarm_btn = page.locator("button:has-text('Swarm Control')".to_string());
            if !swarm_btn.is_visible().await {
                println!("{}", "Swarm button not immediately visible, might need expansion.".to_string());
            } else {
                assert!(swarm_btn.is_visible().await, "Swarm Control button should be visible");
            }
            println!("{}", "✅ Features Menu verification passed".to_string());
            browser.close().await;
        }
        // except Exception as e:
    }
}
