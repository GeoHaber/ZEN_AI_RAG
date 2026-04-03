/// verify_ethical_crawling::py - Demonstration of Intelligent & Ethical Web Crawling
/// Tests the new WebCrawlScanner integration in both sync and async scrapers.

use anyhow::{Result, Context};
use crate::async_scraper::{SafeAsyncScraper};
use crate::scraper::{WebsiteScraper};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Verify async politeness.
pub async fn verify_async_politeness() -> () {
    // Verify async politeness.
    logger.info("\n--- 🔍 VERIFYING ASYNC SCRAPER (POLITE MODE) ---".to_string());
    let mut url_blocked = "https://www.google.com/search?q=zenai".to_string();
    logger.info(format!("Testing blocked URL: {}", url_blocked));
    let mut scraper = SafeAsyncScraper(url_blocked);
    let mut results = scraper::scrape_website(/* max_pages= */ 1).await;
    if !results {
        logger.info(format!("✅ ASYNC: Successfully respected robots.txt/blocking for {}", url_blocked));
    }
    let mut url_allowed = "https://github.com/trending".to_string();
    logger.info(format!("Testing allowed URL: {}", url_allowed));
    let mut scraper = SafeAsyncScraper(url_allowed);
    let mut results = scraper::scrape_website(/* max_pages= */ 1).await;
    if results {
        logger.info(format!("✅ ASYNC: Successfully crawled allowed URL: {}", results[0]["url".to_string()]));
    }
}

/// Verify sync politeness.
pub fn verify_sync_politeness() -> () {
    // Verify sync politeness.
    logger.info("\n--- 🔍 VERIFYING SYNC SCRAPER (POLITE MODE) ---".to_string());
    let mut url_blocked = "https://www.google.com/search?q=zenai".to_string();
    logger.info(format!("Testing blocked URL: {}", url_blocked));
    let mut scraper = WebsiteScraper(url_blocked);
    let mut results = scraper::scrape(/* max_pages= */ 1);
    if !results {
        logger.info(format!("✅ SYNC: Successfully respected robots.txt/blocking for {}", url_blocked));
    }
    let mut url_allowed = "https://github.com/trending".to_string();
    logger.info(format!("Testing allowed URL: {}", url_allowed));
    let mut scraper = WebsiteScraper(url_allowed);
    let mut results = scraper::scrape(/* max_pages= */ 1);
    if results {
        logger.info(format!("✅ SYNC: Successfully crawled allowed URL: {}", results[0]["url".to_string()]));
    }
}
