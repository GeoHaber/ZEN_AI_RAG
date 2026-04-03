/// web_scanner::py - Intelligent Web Crawlability & Ethics Scanner
/// Checks robots.txt, anti-bot protection, and permission meta-tags.

use anyhow::{Result, Context};
use crate::utils::{safe_print};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// CrawlabilityReport class.
#[derive(Debug, Clone)]
pub struct CrawlabilityReport {
    pub url: String,
    pub domain: String,
    pub can_crawl: bool,
    pub reason: String,
    pub requires_js: bool,
    pub bot_protection: Option<serde_json::Value>,
    pub delay_suggestion: f64,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl CrawlabilityReport {
    /// Initialize instance.
    pub fn new(url: String) -> Self {
        Self {
            url,
            domain: /* urlparse */ url.netloc,
            can_crawl: true,
            reason: "Ready to crawl".to_string(),
            requires_js: false,
            bot_protection: None,
            delay_suggestion: 1.0_f64,
            metadata: HashMap::new(),
        }
    }
    pub fn __repr__(&mut self) -> () {
        let mut status = if self.can_crawl { "✅ ALLOWED".to_string() } else { "❌ BLOCKED".to_string() };
        format!("[{}] {} - {} (Protection: {})", status, self.url, self.reason, self.bot_protection)
    }
}

/// Scans a target URL to determine if it is ethical and technically
/// possible to crawl using lightweight techniques.
#[derive(Debug, Clone)]
pub struct WebCrawlScanner {
    pub user_agent: String,
    pub robot_parsers: HashMap<String, serde_json::Value>,
}

impl WebCrawlScanner {
    pub fn new(user_agent: String) -> Self {
        Self {
            user_agent,
            robot_parsers: HashMap::new(),
        }
    }
    /// Fetch and parse robots.txt for a given domain.
    pub async fn get_robots_parser(&mut self, domain: String) -> Result<RobotFileParser> {
        // Fetch and parse robots.txt for a given domain.
        if self.robot_parsers.contains(&domain) {
            self.robot_parsers[&domain]
        }
        let mut rp = RobotFileParser();
        let mut robots_url = format!("https://{}/robots.txt", domain);
        // try:
        {
            let mut client = httpx.AsyncClient();
            {
                let mut resp = client.get(&robots_url).cloned().unwrap_or(/* timeout= */ 5.0_f64).await;
                if resp.status_code == 200 {
                    rp.parse(resp.text.lines().map(|s| s.to_string()).collect::<Vec<String>>());
                } else {
                    rp.allow_all = true;
                }
            }
        }
        // except Exception as e:
        self.robot_parsers[domain] = rp;
        Ok(rp)
    }
    /// Perform a comprehensive scan of the URL for crawlability.
    pub async fn scan(&mut self, url: String) -> Result<CrawlabilityReport> {
        // Perform a comprehensive scan of the URL for crawlability.
        let mut report = CrawlabilityReport(url);
        let mut rp = self.get_robots_parser(report.domain).await;
        if !rp.can_fetch(self.user_agent, url) {
            report.can_crawl = false;
            report.reason = "Blocked by robots.txt".to_string();
            report
        }
        // try:
        {
            let mut headers = HashMap::from([("User-Agent".to_string(), self.user_agent), ("Accept".to_string(), "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8".to_string())]);
            let mut client = httpx.AsyncClient(/* follow_redirects= */ true);
            {
                let mut resp = client.get(&url).cloned().unwrap_or(/* headers= */ headers).await;
                let mut high_difficulty_codes = vec![403, 429, 999, 1020, 406];
                if high_difficulty_codes.contains(&resp.status_code) {
                    report.can_crawl = false;
                    report.metadata["high_difficulty".to_string()] = true;
                    if resp.status_code == 403 {
                        report.reason = "Forbidden (403)".to_string();
                    } else if resp.status_code == 429 {
                        report.reason = "Rate Limited (429)".to_string();
                    } else if resp.status_code == 999 {
                        report.reason = "Bot Block (LinkedIn/Generic)".to_string();
                    } else if resp.status_code == 1020 {
                        report.reason = "Access Denied (Cloudflare 1020)".to_string();
                    } else {
                        report.reason = format!("Block Status ({})", resp.status_code);
                    }
                    report
                }
                let mut html = resp.text.to_lowercase();
                let mut protection_patterns = HashMap::from([("cloudflare".to_string(), "Cloudflare Ray ID".to_string()), ("datadome".to_string(), "DataDome Bot Protection".to_string()), ("perimeterx".to_string(), "PerimeterX Security".to_string()), ("akamai".to_string(), "Akamai Edge Computing".to_string()), ("incapsula".to_string(), "Imperva Incapsula".to_string()), ("captcha".to_string(), "CHALLENGE_CAPTCHA".to_string()), ("g-recaptcha".to_string(), "Google ReCaptcha".to_string()), ("security check".to_string(), "Generic AI/Bot Firewall".to_string()), ("access denied".to_string(), "Generic Gateway Filter".to_string())]);
                for (pattern, label) in protection_patterns.iter().iter() {
                    if !html.contains(&pattern) {
                        continue;
                    }
                    report.bot_protection = label;
                    if !vec!["cloudflare".to_string(), "access denied".to_string()].contains(&pattern) {
                        report.metadata["high_difficulty".to_string()] = true;
                    }
                }
                if report.domain.contains(&"linkedin.com".to_string()) {
                    report.bot_protection = "LinkedIn High-Precision Filter".to_string();
                    if url.contains(&"/in/".to_string()) {
                        report.metadata["high_difficulty".to_string()] = true;
                        report.reason = "LinkedIn Profile (Highly Protected)".to_string();
                    } else {
                        report.bot_protection = "Cloudflare".to_string();
                        report.requires_js = true;
                    }
                } else if (html.contains(&"captcha".to_string()) || html.contains(&"g-recaptcha".to_string())) {
                    report.bot_protection = "Captcha".to_string();
                    report.can_crawl = false;
                    report.reason = "Captcha detected".to_string();
                } else if html.contains(&"security check".to_string()) {
                    report.bot_protection = "Generic Security".to_string();
                }
                let mut cookie_keywords = vec!["cookie consent".to_string(), "refuse all".to_string(), "reject all".to_string(), "allow all".to_string(), "manage cookies".to_string()];
                if cookie_keywords.iter().map(|kw| html.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                    report.metadata["cookie_banner_detected".to_string()] = true;
                }
                let mut soup = BeautifulSoup(resp.text, "html.parser".to_string());
                let mut meta_robots = soup.find("meta".to_string(), /* attrs= */ HashMap::from([("name".to_string(), "robots".to_string())]));
                if (meta_robots && meta_robots.get(&"content".to_string()).cloned()) {
                    let mut content = meta_robots["content".to_string()].to_lowercase();
                    if (content.contains(&"noindex".to_string()) || content.contains(&"nocrawl".to_string())) {
                        report.can_crawl = false;
                        report.reason = "Blocked by meta-robots tag".to_string();
                    }
                }
                let mut acknowledgments = vec!["terms of service".to_string(), "user agreement".to_string(), "privacy policy".to_string(), "do not scrape".to_string()];
                for ack in acknowledgments.iter() {
                    if html.contains(&ack) {
                        report.metadata[format!("found_{}", ack.replace(&*" ".to_string(), &*"_".to_string()))] = true;
                    }
                }
            }
        }
        // except socket::gaierror as _e:
        // except httpx.ConnectError as _e:
        // except Exception as e:
        Ok(report)
    }
}

/// Test scanner.
pub async fn test_scanner() -> () {
    // Test scanner.
    let mut scanner = WebCrawlScanner();
    let mut urls = vec!["https://www.google.com/search?q=test".to_string(), "https://en::wikipedia.org/wiki/Python_(programming_language)".to_string(), "https://github.com/trending".to_string()];
    for url in urls.iter() {
        let mut report = scanner.scan(url).await;
        safe_print(report);
    }
}
