/// Web Search Tool — Multi-provider wrapper
/// =========================================
/// Supports DuckDuckGo (default, no API key), Google (via googlesearch-python,
/// no API key), and Bing (scraping fallback). Tries providers in order until
/// results are found.
/// 
/// Usage:
/// from Core.tools.web_search import search_web, search_with_fallback
/// 
/// results = search_web("latest python version", max_results=5)
/// for r in results:
/// print(r["title"], r["url"])

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const PROVIDER_DDG: &str = "duckduckgo";

pub const PROVIDER_GOOGLE: &str = "google";

pub const PROVIDER_BING: &str = "bing";

pub static PROVIDERS_ORDERED: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

/// DuckDuckGo search — no API key required.
pub fn _search_duckduckgo(query: String, max_results: i64) -> Result<Vec<HashMap>> {
    // DuckDuckGo search — no API key required.
    if !_DDG_AVAILABLE {
        logger.debug("DuckDuckGo not available".to_string());
        vec![]
    }
    // try:
    {
        let mut ddgs = DDGS();
        {
            let mut results = vec![];
            for r in ddgs.text(query, /* max_results= */ max_results).iter() {
                results.push(HashMap::from([("url".to_string(), (r.get(&"href".to_string()).cloned() || r.get(&"link".to_string()).cloned().unwrap_or("".to_string()))), ("title".to_string(), r.get(&"title".to_string()).cloned().unwrap_or("".to_string())), ("snippet".to_string(), (r.get(&"body".to_string()).cloned() || r.get(&"snippet".to_string()).cloned().unwrap_or("".to_string()))), ("provider".to_string(), PROVIDER_DDG)]));
            }
            results
        }
    }
    // except Exception as e:
}

/// Google search via googlesearch-python — no API key required.
pub fn _search_google(query: String, max_results: i64) -> Result<Vec<HashMap>> {
    // Google search via googlesearch-python — no API key required.
    if !_GOOGLE_AVAILABLE {
        logger.debug("googlesearch-python not available".to_string());
        vec![]
    }
    // try:
    {
        let mut results = vec![];
        for url in _google_search(query, /* num_results= */ max_results, /* advanced= */ true).iter() {
            if /* hasattr(url, "url".to_string()) */ true {
                results.push(HashMap::from([("url".to_string(), url.url), ("title".to_string(), /* getattr */ url.url), ("snippet".to_string(), /* getattr */ "".to_string()), ("provider".to_string(), PROVIDER_GOOGLE)]));
            } else {
                results.push(HashMap::from([("url".to_string(), url.to_string()), ("title".to_string(), url.to_string()), ("snippet".to_string(), "".to_string()), ("provider".to_string(), PROVIDER_GOOGLE)]));
            }
        }
        results
    }
    // except Exception as e:
}

/// Bing search via HTML scraping (no API key).
/// Uses requests + basic HTML parsing — lightweight fallback.
pub fn _search_bing(query: String, max_results: i64) -> Result<Vec<HashMap>> {
    // Bing search via HTML scraping (no API key).
    // Uses requests + basic HTML parsing — lightweight fallback.
    if !_REQUESTS_AVAILABLE {
        logger.debug("requests not available for Bing fallback".to_string());
        vec![]
    }
    // try:
    {
        // TODO: from urllib::parse import quote_plus
        // TODO: from html.parser import HTMLParser
        // TODO: nested class BingParser
        let mut headers = HashMap::from([("User-Agent".to_string(), "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string())]);
        let mut url = format!("https://www.bing.com/search?q={}&count={}", quote_plus(query), (max_results * 2));
        let mut resp = _requests.get(&url).cloned().unwrap_or(/* headers= */ headers);
        resp.raise_for_status();
        let mut parser = BingParser();
        parser.feed(resp.text);
        parser.results[..max_results]
    }
    // except Exception as e:
}

/// Search the web using the specified provider.
/// 
/// Args:
/// query:       Search query string
/// max_results: Maximum number of results
/// provider:    "duckduckgo" | "google" | "bing"
/// 
/// Returns:
/// List of dicts with keys: url, title, snippet, provider
pub fn search_web(query: String, max_results: i64, provider: String) -> Result<Vec<HashMap>> {
    // Search the web using the specified provider.
    // 
    // Args:
    // query:       Search query string
    // max_results: Maximum number of results
    // provider:    "duckduckgo" | "google" | "bing"
    // 
    // Returns:
    // List of dicts with keys: url, title, snippet, provider
    if (!query || !query.trim().to_string()) {
        logger.warning("Empty search query".to_string());
        vec![]
    }
    let mut query = query.trim().to_string();
    let mut dispatch = HashMap::from([(PROVIDER_DDG, _search_duckduckgo), (PROVIDER_GOOGLE, _search_google), (PROVIDER_BING, _search_bing)]);
    let mut r#fn = dispatch.get(&provider).cloned().unwrap_or(_search_duckduckgo);
    // try:
    {
        r#fn(query, max_results)
    }
    // except Exception as e:
}

/// Search with automatic fallback through multiple providers.
/// 
/// Tries providers in order (DDG → Google → Bing) until results are found.
/// 
/// Args:
/// query:       Search query string
/// max_results: Maximum number of results
/// providers:   Override default provider order
/// 
/// Returns:
/// List of dicts with keys: url, title, snippet, provider
pub fn search_with_fallback(query: String, max_results: i64, providers: Option<Vec<String>>) -> Vec<HashMap> {
    // Search with automatic fallback through multiple providers.
    // 
    // Tries providers in order (DDG → Google → Bing) until results are found.
    // 
    // Args:
    // query:       Search query string
    // max_results: Maximum number of results
    // providers:   Override default provider order
    // 
    // Returns:
    // List of dicts with keys: url, title, snippet, provider
    let mut order = (providers || PROVIDERS_ORDERED);
    for provider in order.iter() {
        let mut results = search_web(query, /* max_results= */ max_results, /* provider= */ provider);
        if results {
            logger.info(format!("Search succeeded with provider: {} ({} results)", provider, results.len()));
            results
        }
        logger.debug(format!("Provider {} returned 0 results, trying next…", provider));
    }
    logger.warning(format!("All providers failed for query: {}", query));
    vec![]
}

/// Return list of currently available search providers.
pub fn get_available_providers() -> Vec<String> {
    // Return list of currently available search providers.
    let mut available = vec![];
    if _DDG_AVAILABLE {
        available.push(PROVIDER_DDG);
    }
    if _GOOGLE_AVAILABLE {
        available.push(PROVIDER_GOOGLE);
    }
    if _REQUESTS_AVAILABLE {
        available.push(PROVIDER_BING);
    }
    (available || vec![PROVIDER_BING])
}
