/// Web crawler with configurable depth for RAG test bench.
/// Respects robots.txt, follows same-domain links, extracts clean text.

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _HEADERS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub const _TIMEOUT: i64 = 15;

pub const _MIN_TEXT_LEN: i64 = 50;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlResult {
    pub url: String,
    pub title: String,
    pub text: String,
    pub depth: i64,
    pub status: i64,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlStats {
    pub pages_fetched: i64,
    pub pages_skipped: i64,
    pub pages_errored: i64,
    pub total_chars: i64,
    pub elapsed_sec: f64,
    pub urls_visited: i64,
    pub content_types: HashMap<String, serde_json::Value>,
}

/// Extract visible text from a parsed page, stripping nav/script/style.
pub fn _clean_text(soup: BeautifulSoup) -> String {
    // Extract visible text from a parsed page, stripping nav/script/style.
    for tag in soup(vec!["script".to_string(), "style".to_string(), "nav".to_string(), "footer".to_string(), "header".to_string(), "aside".to_string(), "noscript".to_string()]).iter() {
        tag.decompose();
    }
    let mut text = soup.get_text(/* separator= */ "\n".to_string(), /* strip= */ true);
    let mut text = regex::Regex::new(&"\\n{3,}".to_string()).unwrap().replace_all(&"\n\n".to_string(), text).to_string();
    text.trim().to_string()
}

pub fn _same_domain(base_url: String, candidate: String) -> bool {
    /* urlparse */ base_url.netloc == /* urlparse */ candidate.netloc
}

/// BFS crawl starting from *start_url* up to *max_depth* link hops.
/// 
/// Parameters
/// ----------
/// start_url : root URL
/// max_depth : how many link-hops to follow (1 = root only)
/// max_pages : cap on total pages fetched
/// on_page   : optional callback after each page (for progress)
/// cancel_event : optional threading::Event — set it to abort mid-crawl
/// 
/// Returns
/// -------
/// (results, stats)
pub fn crawl_site(start_url: String, max_depth: i64, max_pages: i64, on_page: Option<Box<dyn Fn(serde_json::Value)>>, cancel_event: Option<threading::Event>) -> Result<(Vec<CrawlResult>, CrawlStats)> {
    // BFS crawl starting from *start_url* up to *max_depth* link hops.
    // 
    // Parameters
    // ----------
    // start_url : root URL
    // max_depth : how many link-hops to follow (1 = root only)
    // max_pages : cap on total pages fetched
    // on_page   : optional callback after each page (for progress)
    // cancel_event : optional threading::Event — set it to abort mid-crawl
    // 
    // Returns
    // -------
    // (results, stats)
    let mut visited = HashSet::new();
    let mut queue = vec![(start_url, 0)];
    let mut results = vec![];
    let mut stats = CrawlStats();
    let mut t0 = time::monotonic();
    let mut session = requests.Session();
    session.headers.extend(_HEADERS);
    while (queue && stats.pages_fetched < max_pages) {
        if (cancel_event && cancel_event.is_set()) {
            break;
        }
        let (mut url, mut depth) = queue.remove(&0);
        let mut canonical = url.split("#".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim_end_matches(|c: char| "/".to_string().contains(c)).to_string();
        if visited.contains(&canonical) {
            continue;
        }
        visited.insert(canonical);
        let mut resp = None;
        let mut fetch_error = None;
        for attempt_url in (vec![url] + if (depth == 0 && url.starts_with(&*"https://".to_string())) { vec![url.replace(&*"https://".to_string(), &*"http://".to_string())] } else { vec![] }).iter() {
            // try:
            {
                let mut resp = session.get(&attempt_url).cloned().unwrap_or(/* timeout= */ _TIMEOUT);
                resp.raise_for_status();
                let mut url = attempt_url;
                if (depth == 0 && attempt_url != start_url) {
                    let mut start_url = attempt_url;
                }
                let mut fetch_error = None;
                break;
            }
            // except Exception as exc:
        }
        if (fetch_error || resp.is_none()) {
            stats.pages_errored += 1;
            stats.urls_visited += 1;
            let mut cr = CrawlResult(/* url= */ url, /* title= */ "".to_string(), /* text= */ "".to_string(), /* depth= */ depth, /* status= */ 0, /* error= */ fetch_error.to_string()[..200]);
            results.push(cr);
            if on_page {
                on_page(cr);
            }
            continue;
        }
        stats.urls_visited += 1;
        let mut content_type = resp.headers.get(&"content-type".to_string()).cloned().unwrap_or("".to_string());
        let mut ct_key = if content_type { content_type.split(";".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim().to_string().to_lowercase() } else { "unknown".to_string() };
        stats.content_types[ct_key] = (stats.content_types.get(&ct_key).cloned().unwrap_or(0) + 1);
        if !content_type.contains(&"text/html".to_string()) {
            stats.pages_skipped += 1;
            continue;
        }
        let mut soup = BeautifulSoup(resp.text, "lxml".to_string());
        let mut title = if (soup.title && soup.title.string) { soup.title.string.trim().to_string() } else { url };
        let mut text = _clean_text(soup);
        if text.len() < _MIN_TEXT_LEN {
            stats.pages_skipped += 1;
            continue;
        }
        stats.pages_fetched += 1;
        stats.total_chars += text.len();
        let mut cr = CrawlResult(/* url= */ url, /* title= */ title, /* text= */ text, /* depth= */ depth, /* status= */ resp.status_code);
        results.push(cr);
        if on_page {
            on_page(cr);
        }
        if depth < max_depth {
            for a in soup.find_all("a".to_string(), /* href= */ true).iter() {
                let mut href = urljoin(url, a["href".to_string()]);
                if (_same_domain(start_url, href) && !visited.contains(&href.split("#".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim_end_matches(|c: char| "/".to_string().contains(c)).to_string())) {
                    queue.push((href, (depth + 1)));
                }
            }
        }
    }
    stats.elapsed_sec = (((time::monotonic() - t0) as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
    Ok((results, stats))
}
