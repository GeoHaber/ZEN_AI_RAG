use anyhow::{Result, Context};
use crate::scraper::{WebsiteScraper};
use tokio;

/// Mock html with images.
pub fn mock_html_with_images() -> () {
    // Mock html with images.
    "\n    <html>\n        <head><title>Test Page with Images</title></head>\n        <body>\n            <h1>Welcome to the extraction test</h1>\n            <p>Here is a cute cat:</p>\n            <img src=\"https://example.com/cat.jpg\" alt=\"A cute kitten sleeping\">\n            <p>And a chart:</p>\n            <img src=\"https://example.com/chart.png\" alt=\"Sales Chart 2024\">\n            <div class=\"footer\">Footer content</div>\n        </body>\n    </html>\n    ".to_string()
}

/// Verify image extraction.
pub async fn verify_image_extraction() -> () {
    // Verify image extraction.
    println!("{}", "🔍 Starting Image Extraction Verification...".to_string());
    let mut scraper = WebsiteScraper("https://mock.test".to_string());
    let mut soup = BeautifulSoup(mock_html_with_images(), "html.parser".to_string());
    let mut clean_text = scraper::clean_html(soup);
    println!("{}", "\n--- Extracted Content ---".to_string());
    println!("{}", clean_text);
    println!("{}", "-------------------------".to_string());
    if clean_text.contains(&"![A cute kitten sleeping](https://example.com/cat.jpg)".to_string()) {
        println!("{}", "✅ SUCCESS: Image 1 preserved as Markdown".to_string());
    } else {
        println!("{}", "❌ FAIL: Image 1 missing or malformed".to_string());
    }
    if clean_text.contains(&"![Sales Chart 2024](https://example.com/chart.png)".to_string()) {
        println!("{}", "✅ SUCCESS: Image 2 preserved as Markdown".to_string());
    } else {
        println!("{}", "❌ FAIL: Image 2 missing or malformed".to_string());
    }
}
