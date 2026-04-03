/// async_scraper::py - Safe parallel async web scraper for RAG
/// Implements polite scraping practices to avoid DoS detection

use anyhow::{Result, Context};
use crate::web_scanner::{WebCrawlScanner};
use std::collections::HashMap;
use std::collections::HashSet;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Safe parallel async website scraper with anti-DoS measures.
/// 
/// Safety Features:
/// - Rate limiting (max 5 concurrent requests)
/// - Delays between requests (0.5s minimum)
/// - Proper User-Agent header
/// - Timeout handling
/// - Polite retry logic
#[derive(Debug, Clone)]
pub struct SafeAsyncScraper {
    pub base_url: String,
    pub domain: String,
    pub max_concurrent: String,
    pub delay: String,
    pub timeout: String /* aiohttp.ClientTimeout */,
    pub visited: HashSet<String>,
    pub documents: Vec<serde_json::Value>,
    pub headers: HashMap<String, serde_json::Value>,
    pub scanner: WebCrawlScanner,
    pub crawl_report: Option<serde_json::Value>,
}

impl SafeAsyncScraper {
    /// Initialize instance.
    pub fn new(base_url: String, max_concurrent: i64, delay_between_requests: f64, timeout: i64) -> Self {
        Self {
            base_url,
            domain: /* urlparse */ base_url.netloc,
            max_concurrent,
            delay: delay_between_requests,
            timeout: aiohttp.ClientTimeout(/* total= */ timeout),
            visited: HashSet::new(),
            documents: vec![],
            headers: HashMap::from([("User-Agent".to_string(), "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string()), ("Accept".to_string(), "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8".to_string()), ("Accept-Language".to_string(), "en-US,en;q=0.5".to_string()), ("Accept-Encoding".to_string(), "gzip, deflate".to_string()), ("Connection".to_string(), "keep-alive".to_string())]),
            scanner: WebCrawlScanner(/* user_agent= */ self.headers["User-Agent".to_string()]),
            crawl_report: None,
        }
    }
    /// Scrape a single page with safety measures.
    /// 
    /// Args:
    /// session: aiohttp session
    /// url: URL to scrape
    /// semaphore: Rate limiting semaphore
    /// 
    /// Returns:
    /// Document dict or None if failed
    pub async fn scrape_page(&mut self, session: aiohttp::ClientSession, url: String, semaphore: Semaphore) -> Result<()> {
        // Scrape a single page with safety measures.
        // 
        // Args:
        // session: aiohttp session
        // url: URL to scrape
        // semaphore: Rate limiting semaphore
        // 
        // Returns:
        // Document dict or None if failed
        let _ctx = semaphore;
        {
            if self.visited.contains(&url) {
                None
            }
            self.visited.insert(url);
            // try:
            {
                asyncio.sleep(self.delay).await;
                let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                let mut fetch_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                let mut response = session.get(&url).cloned().unwrap_or(/* headers= */ self.headers);
                {
                    if response.status == 429 {
                        logger.warning(format!("[SafeScraper] ⏸️ Rate limited by server: {}", url));
                        asyncio.sleep(5).await;
                        None
                    }
                    if response.status != 200 {
                        logger.warning(format!("[SafeScraper] ❌ {} returned {}", url, response.status));
                        None
                    }
                    let mut html = response.text().await;
                }
                let mut fetch_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - fetch_start);
                let mut parse_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                let mut soup = BeautifulSoup(html, "html.parser".to_string());
                let mut title = soup.find(&*"title".to_string()).map(|i| i as i64).unwrap_or(-1);
                let mut title_text = if title { title.get_text().trim().to_string() } else { url };
                for element in soup(vec!["script".to_string(), "style".to_string(), "nav".to_string(), "footer".to_string(), "header".to_string(), "aside".to_string()]).iter() {
                    element.decompose();
                }
                let mut text = soup.get_text(/* separator= */ " ".to_string(), /* strip= */ true);
                let mut parse_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - parse_start);
                let mut clean_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                let mut text = text.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().join(&" ".to_string());
                (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - clean_start);
                let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
                logger.info(format!("[SafeScraper] ✅ {} ({} chars) | Fetch: {:.2}s, Parse: {:.2}s, Total: {:.2}s", url, text.len(), fetch_time, parse_time, total_time));
                HashMap::from([("url".to_string(), url), ("title".to_string(), title_text), ("content".to_string(), text)])
            }
            // except asyncio.TimeoutError as _e:
            // except aiohttp.ClientError as e:
            // except Exception as e:
        }
    }
    /// Check if URL is valid and belongs to same domain.
    pub fn _is_valid_url(&mut self, url: String) -> Result<bool> {
        // Check if URL is valid and belongs to same domain.
        // try:
        {
            let mut parsed = /* urlparse */ url;
            (vec!["http".to_string(), "https".to_string()].contains(&parsed.scheme) && parsed.netloc == self.domain && !url.ends_with(&*(".pdf".to_string(), ".jpg".to_string(), ".png".to_string(), ".gif".to_string(), ".zip".to_string(), ".exe".to_string())))
        }
        // except Exception as _e:
    }
    /// Discover URLs using BFS (sequential to be polite).
    /// 
    /// Args:
    /// session: aiohttp session
    /// start_url: Starting URL
    /// max_pages: Maximum pages to discover
    /// 
    /// Returns:
    /// List of URLs to scrape
    pub async fn discover_urls(&mut self, session: aiohttp::ClientSession, start_url: String, max_pages: i64) -> Result<Vec> {
        // Discover URLs using BFS (sequential to be polite).
        // 
        // Args:
        // session: aiohttp session
        // start_url: Starting URL
        // max_pages: Maximum pages to discover
        // 
        // Returns:
        // List of URLs to scrape
        let mut discovered = HashSet::new();
        let mut queue = vec![start_url];
        while (queue && discovered.len() < max_pages) {
            let mut url = queue.remove(&0);
            if (discovered.contains(&url) || !self._is_valid_url(url)) {
                continue;
            }
            discovered.insert(url);
            // try:
            {
                asyncio.sleep(self.delay).await;
                let mut response = session.get(&url).cloned().unwrap_or(/* headers= */ self.headers);
                {
                    if response.status != 200 {
                        continue;
                    }
                    let mut html = response.text().await;
                    let mut soup = BeautifulSoup(html, "html.parser".to_string());
                    for link in soup.find_all("a".to_string(), /* href= */ true).iter() {
                        let mut absolute_url = urljoin(url, link["href".to_string()]);
                        if (self._is_valid_url(absolute_url) && !discovered.contains(&absolute_url)) {
                            queue.push(absolute_url);
                        }
                    }
                }
            }
            // except Exception as e:
        }
        logger.info(format!("[SafeScraper] 🔍 Discovered {} URLs", discovered.len()));
        discovered.into_iter().collect::<Vec<_>>()
        Ok(discovered.into_iter().collect::<Vec<_>>())
    }
    /// Scrape website with parallel requests and safety measures.
    /// 
    /// Args:
    /// max_pages: Maximum pages to scrape
    /// progress_callback: Optional callback(current, total, url)
    /// 
    /// Returns:
    /// List of scraped documents
    pub async fn scrape_website(&mut self, max_pages: i64, progress_callback: String) -> Vec {
        // Scrape website with parallel requests and safety measures.
        // 
        // Args:
        // max_pages: Maximum pages to scrape
        // progress_callback: Optional callback(current, total, url)
        // 
        // Returns:
        // List of scraped documents
        let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        logger.info(format!("[SafeScraper] 🚀 Starting safe parallel scrape: max {} pages, {} concurrent, {}s delay", max_pages, self.max_concurrent, self.delay));
        self.crawl_report = self.scanner.scan(self.base_url).await;
        if !self.crawl_report.can_crawl {
            logger.error(format!("[SafeScraper] 🛑 Scrape aborted: {}", self.crawl_report.reason));
            vec![]
        }
        if self.crawl_report.bot_protection {
            logger.warning(format!("[SafeScraper] ⚠️ Target site has {} protection. Results may be limited.", self.crawl_report.bot_protection));
        }
        let mut connector = aiohttp.TCPConnector(/* limit= */ self.max_concurrent);
        let mut session = aiohttp.ClientSession(/* connector= */ connector);
        {
            let mut urls_to_scrape = self.discover_urls(session, self.base_url, max_pages).await;
            let mut total_urls = urls_to_scrape.len();
            if total_urls == 0 {
                logger.warning("[SafeScraper] No URLs discovered".to_string());
                vec![]
            }
            let mut semaphore = Semaphore(self.max_concurrent);
            let mut tasks = urls_to_scrape.iter().map(|url| self.scrape_page(session, url, semaphore)).collect::<Vec<_>>();
            let mut completed = 0;
            for coro in asyncio.as_completed(tasks).iter() {
                let mut result = coro.await;
                if result {
                    self.documents.push(result);
                }
                completed += 1;
                if progress_callback {
                    progress_callback(completed, total_urls, if result { result["url".to_string()] } else { "".to_string() });
                }
            }
        }
        let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
        let mut avg_time = if total_urls > 0 { (total_time / total_urls) } else { 0 };
        logger.info(format!("[SafeScraper] ✅ Completed: {} pages in {:.2}s ({:.2}s/page avg)", self.documents.len(), total_time, avg_time));
        self.documents
    }
}
