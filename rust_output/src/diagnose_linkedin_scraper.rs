use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Diagnose url.
pub fn diagnose_url(url: String) -> Result<()> {
    // Diagnose url.
    println!("\n🔍 Diagnosing URL: {}", url);
    println!("{}", ("-".to_string() * 50));
    let mut headers = HashMap::from([("User-Agent".to_string(), "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string()), ("Accept".to_string(), "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8".to_string()), ("Accept-Language".to_string(), "en-US,en;q=0.9".to_string()), ("Sec-Ch-Ua".to_string(), "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"".to_string()), ("Sec-Ch-Ua-Mobile".to_string(), "?0".to_string()), ("Sec-Ch-Ua-Platform".to_string(), "\"Windows\"".to_string())]);
    // try:
    {
        let mut response = /* reqwest::get( */&url).cloned().unwrap_or(/* headers= */ headers);
        println!("📡 HTTP Status: {}", response.status_code);
        println!("📏 Response Length: {} bytes", response.text.len());
        if response.status_code == 200 {
            let mut soup = BeautifulSoup(response.text, "html.parser".to_string());
            let mut title = if soup.title { soup.title.string } else { "No title".to_string() };
            println!("📑 Page Title: {}", title);
            if (response.url.contains(&"authwall".to_string()) || response.text.to_lowercase().contains(&"security-check".to_string())) {
                println!("{}", "⚠️  DETECTED: Redirected to Authwall/Security check.".to_string());
            }
            let mut text = soup.get_text();
            println!("📝 Extracted Text Preview (first 200 chars):\n{}...", text.trim().to_string()[..200]);
            if text.trim().to_string().len() < 100 {
                println!("{}", "❌ ERROR: Very little text extracted. JavaScript rendering might be required.".to_string());
            }
        } else {
            println!("❌ ERROR: Received non-200 status code.");
            if response.status_code == 403 {
                println!("{}", "💡 Suggestion: Site is blocking basic requests (Forbidden).".to_string());
            } else if response.status_code == 999 {
                println!("{}", "💡 Suggestion: LinkedIn specific request rejection code.".to_string());
            }
        }
    }
    // except Exception as _e:
}
