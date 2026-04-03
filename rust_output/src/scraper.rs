/// scraper::py - Website scraping for RAG pipeline with production-grade resilience
/// 
/// Enhanced Features (v2.0):
/// - Pre-flight web scanning (robots.txt, bot protection detection)
/// - Exponential backoff retry logic
/// - User-Agent rotation
/// - Cookie banner removal
/// - Polite delays (1-3s jitter)
/// - Anti-bot content detection
/// - Comprehensive user feedback

use anyhow::{Result, Context};
use crate::utils::{normalize_input};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static USER_AGENTS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// WebsiteScraper class.
#[derive(Debug, Clone)]
pub struct WebsiteScraper {
    pub base_url: normalize_input,
    pub visited: HashSet<String>,
    pub documents: Vec<serde_json::Value>,
    pub domain: String,
    pub scanner: WebCrawlScanner,
    pub crawl_report: Option<serde_json::Value>,
}

impl WebsiteScraper {
    /// Initialize instance.
    pub fn new(base_url: String) -> Self {
        Self {
            base_url: normalize_input(base_url),
            visited: HashSet::new(),
            documents: vec![],
            domain: /* urlparse */ self.base_url.netloc,
            scanner: Default::default(),
            crawl_report: None,
        }
    }
    /// Check if URL belongs to the same domain.
    pub fn is_same_domain(&mut self, url: String) -> bool {
        // Check if URL belongs to the same domain.
        /* urlparse */ url.netloc == self.domain
    }
    /// Remove scripts, styles, navigation, cookie banners, and extract clean text.
    /// 
    /// Enhanced with:
    /// - Content container prioritization (article, main, etc.)
    /// - Cookie banner removal
    /// - Multi-layer junk removal
    pub fn clean_html(&self, soup: BeautifulSoup) -> String {
        // Remove scripts, styles, navigation, cookie banners, and extract clean text.
        // 
        // Enhanced with:
        // - Content container prioritization (article, main, etc.)
        // - Cookie banner removal
        // - Multi-layer junk removal
        for img in soup.find_all("img".to_string(), /* src= */ true).iter() {
            let mut alt_text = img.get(&"alt".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
            let mut src = img["src".to_string()];
            img.replace_with(format!(" ![{}]({}) ", alt_text, src));
        }
        for tag in soup(vec!["script".to_string(), "style".to_string(), "nav".to_string(), "header".to_string(), "footer".to_string(), "aside".to_string(), "iframe".to_string(), "form".to_string(), "button".to_string()]).iter() {
            tag.decompose();
        }
        let mut cookie_keywords = vec!["cookie".to_string(), "consent".to_string(), "privacy policy".to_string(), "terms of use".to_string(), "gdpr".to_string()];
        for element in soup.find_all(vec!["div".to_string(), "section".to_string(), "aside".to_string()]).iter() {
            let mut classes = if element.get(&"class".to_string()).cloned() { element.get(&"class".to_string()).cloned().unwrap_or(vec![]).join(&" ".to_string()) } else { "".to_string() };
            let mut ids = element.get(&"id".to_string()).cloned().unwrap_or("".to_string()).to_string();
            if vec!["banner".to_string(), "modal".to_string(), "popup".to_string(), "consent".to_string(), "cookie".to_string()].iter().map(|kw| (classes + ids).to_lowercase().contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                let mut text_content = element.get_text().to_lowercase();
                if cookie_keywords.iter().map(|kw| text_content.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                    logger.debug(format!("[Scraper] Stripping cookie banner: {} {}", classes, ids));
                    element.decompose();
                }
            }
        }
        let mut text = soup.get_text(/* separator= */ " ".to_string());
        let mut lines = text.lines().map(|s| s.to_string()).collect::<Vec<String>>().iter().map(|line| line.trim().to_string()).collect::<Vec<_>>();
        let mut text = lines.iter().filter(|line| line).map(|line| line).collect::<Vec<_>>().join(&"\n".to_string());
        text
    }
}

/// Generate realistic browser headers with rotating User-Agent.
pub fn get_headers() -> () {
    // Generate realistic browser headers with rotating User-Agent.
    HashMap::from([("User-Agent".to_string(), random.choice(USER_AGENTS)), ("Accept".to_string(), "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8".to_string()), ("Accept-Language".to_string(), "en-US,en;q=0.9".to_string()), ("Referer".to_string(), "https://www.google.com/".to_string()), ("DNT".to_string(), "1".to_string()), ("Connection".to_string(), "keep-alive".to_string()), ("Upgrade-Insecure-Requests".to_string(), "1".to_string())])
}

/// Do scrape setup part1 part 2.
pub fn _do_scrape_setup_part1_part2() -> () {
    // Do scrape setup part1 part 2.
    let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
    let mut avg_time = if self.documents { (total_time / self.documents.len()) } else { 0 };
    logger.info(format!("[Scraper] ✅ Completed: {} pages in {:.2}s ({:.2}s/page)", self.documents.len(), total_time, avg_time));
    if failed_urls {
        logger.warning(format!("[Scraper] ⚠️ Failed to scrape {} URLs", failed_urls.len()));
        for (url, reason) in failed_urls[..5].iter() {
            logger.warning(format!("  - {}: {}", url, reason));
        }
    }
    let mut result = HashMap::from([("success".to_string(), self.documents.len() > 0), ("documents".to_string(), self.documents), ("stats".to_string(), HashMap::from([("total_visited".to_string(), self.visited.len()), ("total_saved".to_string(), self.documents.len()), ("total_failed".to_string(), failed_urls.len()), ("total_time".to_string(), total_time), ("avg_time_per_page".to_string(), avg_time)]))]);
    if failed_urls {
        result["warning".to_string()] = format!("{} URLs failed to scrape", failed_urls.len());
        result["failed_urls".to_string()] = failed_urls;
    }
    if (self.crawl_report && self.crawl_report.bot_protection) {
        result["warning".to_string()] = format!("Site has {} protection - results may be incomplete", self.crawl_report.bot_protection);
    }
    if self.crawl_report {
        result["report".to_string()] = self.crawl_report;
    }
    result
}

/// Do scrape setup part 1.
pub fn _do_scrape_setup_part1() -> Result<()> {
    // Do scrape setup part 1.
    while (queue && self.visited.len() < max_pages) {
        let mut url = queue.remove(&0);
        if self.visited.contains(&url) {
            continue;
        }
        // try:
        {
            if self.visited {
                let mut delay = random.uniform(1.0_f64, 3.0_f64);
                logger.debug(format!("[Scraper] Polite delay: {:.1}s", delay));
                std::thread::sleep(std::time::Duration::from_secs_f64(delay));
            }
            let mut page_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            logger.debug(format!("[Scraper] Fetching: {}", url));
            let mut response = None;
            let mut retries = 3;
            let mut backoff = 2;
            for attempt in 0..retries.iter() {
                // try:
                {
                    let mut response = /* reqwest::get( */&url).cloned().unwrap_or(/* timeout= */ 15);
                    if vec![429, 999].contains(&response.status_code) {
                        let mut wait_time = ((backoff).pow((attempt + 1) as u32) + random.uniform(1, 3));
                        logger.warning(format!("[Scraper] ⚠️ Blocked ({}) at {}. Retrying in {:.1}s... (Attempt {}/{})", response.status_code, url, wait_time, (attempt + 1), retries));
                        std::thread::sleep(std::time::Duration::from_secs_f64(wait_time));
                        continue;
                    }
                    if response.status_code == 200 {
                        break;
                    } else {
                        logger.warning(format!("[Scraper] ⚠️ Failed {} (Status: {})", url, response.status_code));
                        failed_urls.push((url, response.status_code));
                        break;
                    }
                }
                // except requests.exceptions::Timeout as _e:
                // except Exception as e:
            }
            if (!response || response.status_code != 200) {
                self.visited.insert(url);
                continue;
            }
            let mut fetch_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - page_start);
            let mut lower_text = response.text.to_lowercase();
            if vec!["security check".to_string(), "bot detection".to_string(), "captcha".to_string(), "cloudflare".to_string()].iter().map(|kw| lower_text.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                logger.error(format!("[Scraper] ❌ Anti-bot protection triggered at {}", url));
                failed_urls.push((url, "anti-bot".to_string()));
                self.visited.insert(url);
                continue;
            }
            let mut parse_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut soup = BeautifulSoup(response.text, "html.parser".to_string());
            let mut parse_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - parse_start);
            let mut clean_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut text = self.clean_html(soup);
            let mut clean_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - clean_start);
            if text.len() > 100 {
                self.documents.push(HashMap::from([("url".to_string(), url), ("title".to_string(), if soup.title { soup.title.string } else { url }), ("content".to_string(), text)]));
                logger.info(format!("[Scraper] ✅ Saved: {} ({} chars) | Fetch: {:.2}s, Parse: {:.2}s, Clean: {:.2}s", url, text.len(), fetch_time, parse_time, clean_time));
            } else {
                logger.warning(format!("[Scraper] ⚠️ Content too short for {} ({} chars). Skipped.", url, text.len()));
            }
            for link in soup.find_all("a".to_string(), /* href= */ true).iter() {
                let mut full_url = urljoin(url, link["href".to_string()]);
                if (self.is_same_domain(full_url) && full_url.starts_with(&*"http".to_string())) {
                    if (!self.visited.contains(&full_url) && !queue.contains(&full_url)) {
                        queue.push(full_url);
                    }
                }
            }
            self.visited.insert(url);
            if progress_callback {
                progress_callback(self.visited.len(), max_pages, url);
            }
        }
        // except Exception as e:
    }
    Ok(_do_scrape_setup_part1_part2())
}

/// Helper: setup phase for scrape.
pub fn _do_scrape_setup() -> Result<()> {
    // Helper: setup phase for scrape.
    if BeautifulSoup.is_none() {
        HashMap::from([("success".to_string(), false), ("error".to_string(), "BeautifulSoup4 is required for web scraping. Install with: pip install beautifulsoup4".to_string()), ("documents".to_string(), vec![])])
    }
    if self.scanner {
        // try:
        {
            logger.info(format!("[Scraper] Running pre-flight scan for {}...", self.base_url));
            self.crawl_report = asyncio.run(self.scanner.scan(self.base_url));
            if !self.crawl_report.can_crawl {
                logger.error(format!("[Scraper] 🛑 Scrape aborted: {}", self.crawl_report.reason));
                HashMap::from([("success".to_string(), false), ("error".to_string(), format!("Scrape blocked: {}", self.crawl_report.reason)), ("protection".to_string(), self.crawl_report.bot_protection), ("documents".to_string(), vec![]), ("report".to_string(), self.crawl_report)])
            }
            if self.crawl_report.bot_protection {
                logger.warning(format!("[Scraper] ⚠️ Target site has {} protection. Results may be limited.", self.crawl_report.bot_protection));
            }
        }
        // except Exception as e:
    }
    let scrape = |max_pages, progress_callback| {
        // Crawl website and extract text content with production-grade resilience.
        // 
        // Args:
        // max_pages: Maximum number of pages to scrape
        // progress_callback: Optional callable(count, max_pages, url) for UI updates
        // 
        // Returns:
        // dict with:
        // - success: bool
        // - documents: list of scraped documents
        // - error: str (if failed)
        // - warning: str (if partial success)
        // - report: CrawlabilityReport (if scanner available)
        _do_scrape_setup();
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    };
    Ok(_do_scrape_setup_part1())
}
