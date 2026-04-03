use anyhow::{Result, Context};
use crate::markdown_converter::{HTMLToStructuredMarkdown, _sanitize_text};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _HTML_CONVERTER: std::sync::LazyLock<HTMLToStructuredMarkdown> = std::sync::LazyLock::new(|| Default::default());

/// World-class web crawler with structure-preserving extraction.
#[derive(Debug, Clone)]
pub struct WebScanner {
    pub timeout: String,
    pub user_agent: String,
    pub max_retries: String,
    pub max_chars_per_page: String,
    pub _seen_hashes: HashSet<String>,
}

impl WebScanner {
    pub fn new(timeout: i64, user_agent: String, max_retries: i64, max_chars_per_page: i64) -> Self {
        Self {
            timeout,
            user_agent: (user_agent || "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 RAG_RAT/2.0".to_string()),
            max_retries,
            max_chars_per_page,
            _seen_hashes: HashSet::new(),
        }
    }
    pub fn scan(&mut self, start_url: String, max_pages: i64, progress_callback: Option<Box<dyn Fn>>, page_callback: Option<Box<dyn Fn(serde_json::Value)>>, completed_items: Vec<String>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
        let mut visited = HashSet::new();
        let mut queue = vec![start_url];
        let mut base_domain = /* urlparse */ start_url.netloc;
        let mut all_text = vec![];
        let mut all_images = vec![];
        let mut all_sources = vec![];
        let mut pages_crawled = 0;
        while (queue && pages_crawled < max_pages) {
            let mut url = queue.remove(&0);
            if visited.contains(&url) {
                continue;
            }
            visited.insert(url);
            let mut is_completed = (completed_items && completed_items.contains(&url));
            if progress_callback {
                let mut status = if is_completed { format!("Resuming: {}", url) } else { format!("Scanning: {}", url) };
                // try:
                {
                    progress_callback(pages_crawled, max_pages, status, /* completed_item= */ url);
                }
                // except TypeError as _e:
            }
            if is_completed {
                let mut html = self._fetch_with_retry(url);
                if html.is_some() {
                    // try:
                    {
                        let mut soup = BeautifulSoup(html, "html.parser".to_string());
                        let mut add_budget = 0.max((max_pages - pages_crawled));
                        if add_budget > 0 {
                            let mut added = 0;
                            for a in soup.find_all("a".to_string(), /* href= */ true).iter() {
                                if added >= add_budget {
                                    break;
                                }
                                let mut link = self._normalize_link(a["href".to_string()], url, base_domain);
                                if (link && !visited.contains(&link) && !queue.contains(&link)) {
                                    queue.push(link);
                                    added += 1;
                                }
                            }
                        }
                    }
                    // except Exception as exc:
                }
                continue;
            }
            pages_crawled += 1;
            let mut html = self._fetch_with_retry(url);
            if html.is_none() {
                continue;
            }
            // try:
            {
                let mut soup = BeautifulSoup(html, "html.parser".to_string());
                let mut meta = _extract_page_metadata(soup, url);
                let mut page_images = self._extract_images(soup, url);
                all_images.extend(page_images);
                let mut structured_text = _html_converter.convert(soup);
                let mut structured_text = _sanitize_text(structured_text);
            }
            // except Exception as parse_err:
            let mut content_hash = hash(structured_text[..2000]);
            if self._seen_hashes.contains(&content_hash) {
                continue;
            }
            self._seen_hashes.insert(content_hash);
            if structured_text.len() > self.max_chars_per_page {
                let mut structured_text = (structured_text[..self.max_chars_per_page] + "\n\n[... truncated ...]".to_string());
            }
            let mut header = format!("=== PAGE: {} ===\nURL: {}\n", meta.get(&"title".to_string()).cloned().unwrap_or(url), url);
            if meta.get(&"description".to_string()).cloned() {
                header += format!("Description: {}\n", meta["description".to_string()]);
            }
            header += (("-".to_string() * 60) + "\n".to_string());
            let mut page_block = (header + structured_text);
            all_text.push(page_block);
            let mut source_entry = HashMap::from([("type".to_string(), "web".to_string()), ("path".to_string(), url), ("title".to_string(), meta.get(&"title".to_string()).cloned().unwrap_or(url)), ("chars".to_string(), structured_text.len()), ("images".to_string(), page_images.len())]);
            all_sources.push(source_entry);
            if (page_callback && !is_completed) {
                // try:
                {
                    page_callback(page_block, source_entry);
                }
                // except Exception as exc:
            }
            if pages_crawled < max_pages {
                for a in soup.find_all("a".to_string(), /* href= */ true).iter() {
                    let mut link = self._normalize_link(a["href".to_string()], url, base_domain);
                    if (link && !visited.contains(&link) && !queue.contains(&link)) {
                        queue.push(link);
                    }
                }
            }
        }
        Ok((all_text.join(&"\n\n".to_string()), all_images[..500], all_sources))
    }
    pub fn _fetch_with_retry(&mut self, url: String) -> Result<Option<String>> {
        for attempt in 0..(self.max_retries + 1).iter() {
            // try:
            {
                let mut r = /* reqwest::get( */&url).cloned().unwrap_or(/* timeout= */ self.timeout);
                if r.status_code == 200 {
                    if (RUST_AVAILABLE && decode_response_text) {
                        let mut text = decode_response_text(r.content, r.encoding);
                        if text {
                            text
                        }
                    }
                    r.text
                } else if (429, 503).contains(&r.status_code) {
                    std::thread::sleep(std::time::Duration::from_secs_f64((2)).pow((attempt + 1) as u32));
                    continue;
                }
                None
            }
            // except Exception as exc:
        }
        Ok(None)
    }
    pub fn _extract_images(&mut self, soup: BeautifulSoup, page_url: String) -> Result<Vec<HashMap>> {
        if (RUST_AVAILABLE && extract_images_rust) {
            // try:
            {
                extract_images_rust(soup.to_string(), page_url)
            }
            // except Exception as exc:
        }
        let mut images = vec![];
        let mut seen_srcs = HashSet::new();
        for img in soup.find_all("img".to_string()).iter() {
            let mut src = (img.get(&"src".to_string()).cloned() || img.get(&"data-src".to_string()).cloned() || img.get(&"data-lazy-src".to_string()).cloned());
            if !src {
                continue;
            }
            let mut src = urljoin(page_url, src);
            if self.JUNK_IMG_PATTERNS.iter().map(|x| src.to_lowercase().contains(&x)).collect::<Vec<_>>().iter().any(|v| *v) {
                continue;
            }
            if seen_srcs.contains(&src) {
                continue;
            }
            seen_srcs.insert(src);
            images.push(HashMap::from([("url".to_string(), src), ("alt".to_string(), img.get(&"alt".to_string()).cloned().unwrap_or("".to_string())), ("source".to_string(), page_url)]));
        }
        Ok(images)
    }
    pub fn _normalize_link(&self, href: String, current_url: String, base_domain: String) -> Option<String> {
        if (!href || href.starts_with(&*("#".to_string(), "mailto:".to_string(), "tel:".to_string(), "javascript:".to_string()))) {
            None
        }
        let mut href = urljoin(current_url, href);
        let mut parsed = /* urlparse */ href;
        if parsed.netloc != base_domain {
            None
        }
        format!("{}://{}{}", parsed.scheme, parsed.netloc, parsed.path)
    }
}

/// Extract rich metadata from an HTML page.
pub fn _extract_page_metadata(soup: BeautifulSoup, url: String) -> HashMap {
    // Extract rich metadata from an HTML page.
    let mut meta = HashMap::from([("url".to_string(), url)]);
    if (soup.title && soup.title.string) {
        meta["title".to_string()] = _sanitize_text(soup.title.string.trim().to_string());
    } else {
        let mut og = soup.find("meta".to_string(), /* attrs= */ HashMap::from([("property".to_string(), "og:title".to_string())]));
        meta["title".to_string()] = if (og && og.get(&"content".to_string()).cloned()) { og["content".to_string()].trim().to_string() } else { url };
    }
    let mut desc = (soup.find("meta".to_string(), /* attrs= */ HashMap::from([("name".to_string(), "description".to_string())])) || soup.find("meta".to_string(), /* attrs= */ HashMap::from([("property".to_string(), "og:description".to_string())])));
    if (desc && desc.get(&"content".to_string()).cloned()) {
        meta["description".to_string()] = _sanitize_text(desc["content".to_string()].trim().to_string()[..500]);
    }
    let mut author = soup.find("meta".to_string(), /* attrs= */ HashMap::from([("name".to_string(), "author".to_string())]));
    if (author && author.get(&"content".to_string()).cloned()) {
        meta["author".to_string()] = author["content".to_string()].trim().to_string();
    }
    for attr in vec!["article:published_time".to_string(), "datePublished".to_string(), "date".to_string()].iter() {
        let mut tag = (soup.find("meta".to_string(), /* attrs= */ HashMap::from([("property".to_string(), attr)])) || soup.find("meta".to_string(), /* attrs= */ HashMap::from([("name".to_string(), attr)])));
        if (tag && tag.get(&"content".to_string()).cloned()) {
            meta["date".to_string()] = tag["content".to_string()].trim().to_string();
            break;
        }
    }
    let mut html_tag = soup.find(&*"html".to_string()).map(|i| i as i64).unwrap_or(-1);
    if (html_tag && html_tag.get(&"lang".to_string()).cloned()) {
        meta["language".to_string()] = html_tag["lang".to_string()];
    }
    let mut canonical = soup.find("link".to_string(), /* attrs= */ HashMap::from([("rel".to_string(), "canonical".to_string())]));
    if (canonical && canonical.get(&"href".to_string()).cloned()) {
        meta["canonical".to_string()] = canonical["href".to_string()];
    }
    meta
}
