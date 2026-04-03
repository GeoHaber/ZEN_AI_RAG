use anyhow::{Result, Context};
use crate::scraper::{WebsiteScraper};

/// Verify scraper adds https:// to bare domains.
pub fn test_scraper_normalizes_url() -> () {
    // Verify scraper adds https:// to bare domains.
    let mut scraper = WebsiteScraper("example.com".to_string());
    assert!(scraper::base_url == "https://example.com".to_string());
    assert!(scraper::domain == "example.com".to_string());
    let mut scraper_local = WebsiteScraper("localhost:8000".to_string());
    assert!(scraper_local.base_url == "http://localhost:8000".to_string());
    let mut scraper_valid = WebsiteScraper("http://test.com".to_string());
    assert!(scraper_valid.base_url == "http://test.com".to_string());
    let mut scraper_spaces = WebsiteScraper("  google.com  ".to_string());
    assert!(scraper_spaces.base_url == "https://google.com".to_string());
}
