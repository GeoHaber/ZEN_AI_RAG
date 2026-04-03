use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

pub const UI_URL: &str = "http://localhost:8080";

pub static TEST_DATA_DIR: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

/// E2E Test: Open RAG Dialog -> Enter URL -> Scan -> Verify Chat Response.
pub async fn test_rag_ui_website_ingestion() -> Result<()> {
    // E2E Test: Open RAG Dialog -> Enter URL -> Scan -> Verify Chat Response.
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST: RAG Website Ingestion (UI)".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut p = async_playwright();
    {
        let mut browser = p.chromium.launch(/* headless= */ true).await;
        let mut page = browser.new_page().await;
        // try:
        {
            println!("  → Navigating to {}", UI_URL);
            page.goto(UI_URL).await;
            page.wait_for_load_state("networkidle".to_string()).await;
            println!("{}", "  → Opening RAG Dialog...".to_string());
            let mut rag_btn = page.locator("button:has-text('Knowledge Base'), button i:text('library_books')".to_string());
            if rag_btn.count().await > 0 {
                rag_btn.first.click().await;
            } else {
                println!("{}", "  ⚠️ Could not find intuitive RAG button, checking specific IDs...".to_string());
                page.click("button >> i:has-text('library_books')".to_string()).await;
            }
            page.wait_for_selector("text=Knowledge Base Scanner".to_string(), /* timeout= */ 5000).await;
            println!("{}", "  ✅ RAG Dialog Opened".to_string());
            let mut target_url = "https://example.com".to_string();
            println!("  → Entering URL: {}", target_url);
            let mut url_input = page.locator("label:has-text('Website URL') input".to_string());
            url_input.fill(target_url).await;
            println!("{}", "  → Clicking Start Scan...".to_string());
            page.click("button:has-text('Start Scan')".to_string()).await;
            println!("{}", "  → Waiting for ingestion...".to_string());
            page.wait_for_selector("text=Ingestion Complete".to_string(), /* timeout= */ 30000).await;
            println!("{}", "  ✅ Ingestion Validated (Visual confirmation)".to_string());
            println!("{}", "  → Closing Dialog...".to_string());
            page.click("button:has-text('Start Chatting')".to_string()).await;
            println!("{}", "  → Sending Query...".to_string());
            let mut chat_input = page.locator("input[type='text'], textarea".to_string());
            chat_input.fill("What is this website about?".to_string()).await;
            chat_input.press("Enter".to_string()).await;
            println!("{}", "  → Waiting for response...".to_string());
            page.wait_for_selector("text=illustrative examples".to_string(), /* timeout= */ 15000).await;
            println!("{}", "  ✅ Chat response verified!".to_string());
            true
        }
        // except Exception as e:
        // finally:
            browser.close().await;
    }
}

/// E2E Test: Open RAG Dialog -> Local File Tab -> Scan Dir -> Verify Chat.
pub async fn test_rag_ui_directory_ingestion() -> Result<()> {
    // E2E Test: Open RAG Dialog -> Local File Tab -> Scan Dir -> Verify Chat.
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "TEST: RAG Directory Ingestion (UI)".to_string());
    println!("{}", ("=".to_string() * 60));
    TEST_DATA_DIR.create_dir_all();
    let mut secret_phrase = "The purple ostrich dances at dawn.".to_string();
    (TEST_DATA_DIR / "secret.txt".to_string())std::fs::write(&format!("CONFIDENTIAL: {}"));
    let mut abs_path = TEST_DATA_DIR.canonicalize().unwrap_or_default().to_string();
    let mut p = async_playwright();
    {
        let mut browser = p.chromium.launch(/* headless= */ true).await;
        let mut page = browser.new_page().await;
        // try:
        {
            page.goto(UI_URL).await;
            page.click("button >> i:has-text('library_books')".to_string()).await;
            page.wait_for_selector("text=Knowledge Base Scanner".to_string()).await;
            println!("{}", "  → Switching to Local Files...".to_string());
            page.click("div[role='tab']:has-text('Local Files')".to_string()).await;
            println!("  → Entering Path: {}", abs_path);
            let mut dir_input = page.locator("label:has-text('Directory Path') input".to_string());
            dir_input.fill(abs_path).await;
            page.click("button:has-text('Start Scan')".to_string()).await;
            page.wait_for_selector("text=Ingestion Complete".to_string(), /* timeout= */ 10000).await;
            println!("{}", "  ✅ Directory Ingestion Complete".to_string());
            page.click("button:has-text('Start Chatting')".to_string()).await;
            let mut chat_input = page.locator("input[type='text'], textarea".to_string());
            chat_input.fill("What does the purple ostrich do?".to_string()).await;
            chat_input.press("Enter".to_string()).await;
            println!("{}", "  → Verifying secret phrase retrieval...".to_string());
            page.wait_for_selector(format!("text=dances at dawn"), /* timeout= */ 15000).await;
            println!("{}", "  ✅ Secret phrase matched!".to_string());
            true
        }
        // except Exception as e:
        // finally:
            browser.close().await;
            if TEST_DATA_DIR.exists() {
                std::fs::remove_dir_all(TEST_DATA_DIR).ok();
            }
    }
}
