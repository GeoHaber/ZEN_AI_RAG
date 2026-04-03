/// End-to-end tests for RAG Test Bench.
/// 
/// Simulates the full user journey through the Flask app using the test client:
/// 1. Landing page loads
/// 2. Add a site (URL, depth, max_pages)
/// 3. Trigger crawl and wait for completion
/// 4. Verify index has chunks (stats)
/// 5. Search the indexed data
/// 6. Configure LLM settings
/// 7. Check LLM health
/// 8. Chat with RAG context (single pipeline)
/// 9. Chat compare (multi-pipeline)
/// 10. Pipeline management (list, activate)
/// 11. Clear index and verify empty
/// 12. Edge cases: duplicate site, bad params, empty chat
/// 
/// All external HTTP calls (crawl fetches, LLM API) are mocked so tests run
/// offline in < 5 seconds.
/// 
/// Run:  python -m pytest test_e2e::py -v

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static FAKE_PAGES: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct _FakeCrawlResult {
    pub url: String,
    pub title: String,
    pub text: String,
    pub depth: i64,
    pub status: i64,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct _FakeCrawlStats {
    pub pages_fetched: i64,
    pub pages_skipped: i64,
    pub pages_errored: i64,
    pub total_chars: i64,
    pub elapsed_sec: f64,
    pub urls_visited: i64,
    pub content_types: HashMap<String, serde_json::Value>,
}

impl _FakeCrawlStats {
    pub fn __post_init__(&mut self) -> () {
        if self.content_types.is_none() {
            self.content_types = HashMap::from([("text/html".to_string(), self.pages_fetched)]);
        }
    }
}

/// Deterministic embedder: hashes text into a 384-d unit vector.
#[derive(Debug, Clone)]
pub struct _FakeEmbedder {
}

impl _FakeEmbedder {
    pub fn encode(&self, texts: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> () {
        // TODO: import hashlib
        let mut vecs = vec![];
        for t in if /* /* isinstance(texts, list) */ */ true { texts } else { vec![texts] }.iter() {
            let mut h = hashlib::sha256(t.as_bytes().to_vec()).digest();
            let mut v = numpy.frombuffer((h * 12), /* dtype= */ numpy.float32)[..384];
            let mut v = (v / (numpy.linalg.norm(v) + 1e-09_f64));
            vecs.push(v);
        }
        numpy.array(vecs, /* dtype= */ numpy.float32)
    }
}

/// Mimics a streaming requests.Response from an OpenAI-compatible API.
#[derive(Debug, Clone)]
pub struct _FakeLLMResponse {
    pub status_code: i64,
    pub headers: HashMap<String, serde_json::Value>,
    pub _lines: _make_llm_stream,
    pub ok: bool,
}

impl _FakeLLMResponse {
    pub fn new(text: String) -> Self {
        Self {
            status_code: 200,
            headers: HashMap::from([("content-type".to_string(), "text/event-stream".to_string())]),
            _lines: _make_llm_stream(text),
            ok: true,
        }
    }
    pub fn raise_for_status(&self) -> () {
        // pass
    }
    pub fn iter_lines(&mut self, decode_unicode: String) -> () {
        for line in self._lines.iter() {
            let mut decoded = if /* /* isinstance(line, bytes) */ */ true { String::from_utf8_lossy(&line).to_string() } else { line };
            /* yield decoded.trim().to_string() */;
        }
    }
    pub fn json(&self) -> () {
        HashMap::from([("choices".to_string(), vec![HashMap::from([("message".to_string(), HashMap::from([("content".to_string(), "mocked".to_string())]))])])])
    }
}

/// Mimics GET /v1/models response.
#[derive(Debug, Clone)]
pub struct _FakeLLMModelsResponse {
}

impl _FakeLLMModelsResponse {
    pub fn raise_for_status(&self) -> () {
        // pass
    }
    pub fn json(&self) -> () {
        HashMap::from([("data".to_string(), vec![HashMap::from([("id".to_string(), "test-model".to_string())])])])
    }
}

/// Phase 1: User opens the website.
#[derive(Debug, Clone)]
pub struct TestLandingPage {
}

impl TestLandingPage {
    pub fn test_index_page_loads(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/".to_string()).cloned();
        assert!(r.status_code == 200);
        assert!(r.data.contains(&b"RAG Test Bench"));
    }
    pub fn test_no_cache_headers(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/".to_string()).cloned();
        assert!(r.headers.get(&"Cache-Control".to_string()).cloned().unwrap_or("".to_string()).contains(&"no-cache".to_string()));
    }
}

/// Phase 2: User adds sites to scan.
#[derive(Debug, Clone)]
pub struct TestSiteManagement {
}

impl TestSiteManagement {
    pub fn test_add_site(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2), ("max_pages".to_string(), 50)]));
        assert!(r.status_code == 201);
        let mut data = r.get_json();
        assert!(data["url".to_string()] == "https://example.com".to_string());
        assert!(data["depth".to_string()] == 2);
        assert!(data["max_pages".to_string()] == 50);
    }
    pub fn test_list_sites(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string())]));
        let mut r = app_client.get(&"/api/sites".to_string()).cloned();
        let mut sites = r.get_json();
        assert!(sites.len() == 1);
        assert!(sites[0]["url".to_string()] == "https://example.com".to_string());
    }
    pub fn test_duplicate_site_rejected(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string())]));
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string())]));
        assert!(r.status_code == 409);
    }
    pub fn test_auto_prepend_https(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "example.com".to_string())]));
        assert!(r.status_code == 201);
        assert!(r.get_json()["url".to_string()] == "https://example.com".to_string());
    }
    pub fn test_empty_url_rejected(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "".to_string())]));
        assert!(r.status_code == 400);
    }
    pub fn test_depth_clamped(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 99), ("max_pages".to_string(), 10)]));
        assert!(r.get_json()["depth".to_string()] == 10);
    }
    pub fn test_max_pages_clamped(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("max_pages".to_string(), 99999)]));
        assert!(r.get_json()["max_pages".to_string()] == 5000);
    }
}

/// Phase 3: User triggers crawl → data gets indexed.
#[derive(Debug, Clone)]
pub struct TestCrawlAndIndex {
}

impl TestCrawlAndIndex {
    pub fn test_crawl_indexes_data(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2), ("max_pages".to_string(), 50)]));
        let mut r = app_client.post("/api/crawl".to_string());
        assert!(r.get_json()["started".to_string()] == true);
        let mut status = _wait_crawl(app_client);
        assert!(status["running".to_string()] == false);
        assert!(status["progress".to_string()].len() >= 1);
        assert!(status["progress".to_string()][0]["status".to_string()] == "done".to_string());
        assert!(status["progress".to_string()][0]["pages".to_string()] >= 1);
    }
    pub fn test_stats_after_crawl(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
        let mut r = app_client.get(&"/api/stats".to_string()).cloned();
        let mut stats = r.get_json();
        assert!(stats["n_chunks".to_string()] > 0);
    }
    pub fn test_crawl_updates_site_record(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
        let mut sites = app_client.get(&"/api/sites".to_string()).cloned().get_json();
        assert!(sites[0]["last_crawled".to_string()].is_some());
        assert!(sites[0]["pages_crawled".to_string()] >= 1);
        assert!(sites[0]["chunks_indexed".to_string()] >= 1);
    }
    pub fn test_crawl_cancel(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string())]));
        app_client.post("/api/crawl".to_string());
        let mut r = app_client.post("/api/crawl/cancel".to_string());
        assert!(r.get_json()["ok".to_string()] == true);
        let mut status = _wait_crawl(app_client);
        assert!(status["running".to_string()] == false);
    }
}

/// Phase 4: User searches the indexed data.
#[derive(Debug, Clone)]
pub struct TestSearch {
}

impl TestSearch {
    pub fn _crawled(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
    }
    pub fn test_search_returns_results(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "artificial intelligence".to_string())]));
        assert!(r.status_code == 200);
        let mut data = r.get_json();
        assert!(data["query".to_string()] == "artificial intelligence".to_string());
        assert!(data["results".to_string()].len() > 0);
    }
    pub fn test_search_result_fields(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "machine learning".to_string()), ("k".to_string(), 3)]));
        let mut data = r.get_json();
        for result in data["results".to_string()].iter() {
            assert!(result.contains(&"text".to_string()));
            assert!(result.contains(&"source_url".to_string()));
            assert!(result.contains(&"page_title".to_string()));
            assert!(result.contains(&"score".to_string()));
            assert!(/* /* isinstance(result["score".to_string()], float) */ */ true);
        }
    }
    pub fn test_search_has_intent(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "products".to_string())]));
        let mut data = r.get_json();
        assert!(data.contains(&"intent".to_string()));
        assert!(data.contains(&"intent_confidence".to_string()));
    }
    pub fn test_search_empty_query_rejected(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "".to_string())]));
        assert!(r.status_code == 400);
    }
    pub fn test_search_k_respected(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "example".to_string()), ("k".to_string(), 1)]));
        let mut data = r.get_json();
        assert!(data["results".to_string()].len() <= 1);
    }
}

/// Phase 5: User configures LLM settings.
#[derive(Debug, Clone)]
pub struct TestLLMConfig {
}

impl TestLLMConfig {
    pub fn test_get_llm_config(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/api/llm/config".to_string()).cloned();
        assert!(r.status_code == 200);
        let mut data = r.get_json();
        assert!(data.contains(&"base_url".to_string()));
        assert!(data.contains(&"model".to_string()));
    }
    pub fn test_set_llm_config(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/llm/config".to_string(), /* json= */ HashMap::from([("base_url".to_string(), "http://localhost:9999/v1".to_string()), ("api_key".to_string(), "test-key".to_string()), ("model".to_string(), "test-model".to_string())]));
        assert!(r.status_code == 200);
        let mut cfg = app_client.get(&"/api/llm/config".to_string()).cloned().get_json();
        assert!(cfg["base_url".to_string()] == "http://localhost:9999/v1".to_string());
        assert!(cfg["model".to_string()] == "test-model".to_string());
    }
}

/// Phase 6: Check LLM connectivity before chatting.
#[derive(Debug, Clone)]
pub struct TestLLMHealth {
}

impl TestLLMHealth {
    pub fn test_llm_healthy(&self, app_client: String) -> () {
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.get(&"/api/llm/health".to_string()).cloned();
            let mut data = r.get_json();
            assert!(data["ok".to_string()] == true);
        }
    }
    pub fn test_llm_unreachable(&self, app_client: String) -> () {
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.get(&"/api/llm/health".to_string()).cloned();
            let mut data = r.get_json();
            assert!(data["ok".to_string()] == false);
            assert!(data.contains(&"error".to_string()));
            assert!((data["error".to_string()].to_lowercase().contains(&"not running".to_string()) || data["error".to_string()].to_lowercase().contains(&"running".to_string())));
        }
    }
    pub fn test_llm_timeout(&self, app_client: String) -> () {
        // TODO: from requests.exceptions import Timeout
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.get(&"/api/llm/health".to_string()).cloned();
            let mut data = r.get_json();
            assert!(data["ok".to_string()] == false);
            assert!(data["error".to_string()].to_lowercase().contains(&"timed out".to_string()));
        }
    }
}

/// Phase 7: User chats with RAG-augmented LLM (single pipeline).
#[derive(Debug, Clone)]
pub struct TestChat {
}

impl TestChat {
    pub fn _crawled(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
    }
    /// Parse SSE stream into list of JSON objects.
    pub fn _parse_sse(&self, response_data: Vec<u8>) -> Result<Vec<HashMap>> {
        // Parse SSE stream into list of JSON objects.
        let mut events = vec![];
        let mut text = response_data.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
        for line in text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            let mut line = line.trim().to_string();
            if (line.starts_with(&*"data: ".to_string()) && line[6..].trim().to_string() != "[DONE]".to_string()) {
                // try:
                {
                    events.push(serde_json::from_str(&line[6..]).unwrap());
                }
                // except json::JSONDecodeError as _e:
            }
        }
        Ok(events)
    }
    pub fn test_chat_streams_response(&mut self, app_client: String) -> () {
        let mut llm_answer = "Example Corp was founded in 2010 in San Francisco.".to_string();
        let mut fake_resp = _FakeLLMResponse(llm_answer);
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "When was Example Corp founded?".to_string())])])]));
            assert!(r.status_code == 200);
            assert!(r.content_type.contains(&"text/event-stream".to_string()));
            let mut events = self._parse_sse(r.data);
            assert!(events.len() > 0);
            let mut first = events[0];
            assert!((first.contains(&"sources".to_string()) || first.contains(&"content".to_string())));
            let mut full_text = events.iter().map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"".to_string());
            assert!((full_text.contains(&"Example Corp".to_string()) || full_text.to_lowercase().contains(&"founded".to_string())));
        }
    }
    pub fn test_chat_includes_rag_sources(&mut self, app_client: String) -> () {
        let mut fake_resp = _FakeLLMResponse("Founded in San Francisco.".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Where is the headquarters?".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut source_events = events.iter().filter(|e| e.contains(&"sources".to_string())).map(|e| e).collect::<Vec<_>>();
            assert!(source_events.len() >= 1);
            let mut sources = source_events[0]["sources".to_string()];
            assert!(/* /* isinstance(sources, list) */ */ true);
        }
    }
    pub fn test_chat_includes_rag_timing(&mut self, app_client: String) -> () {
        let mut fake_resp = _FakeLLMResponse("Products include RAG Engine.".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What products do they offer?".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut timing_events = events.iter().filter(|e| e.contains(&"rag_timing".to_string())).map(|e| e).collect::<Vec<_>>();
            assert!(timing_events.len() >= 1);
            let mut timing = timing_events[0]["rag_timing".to_string()];
            assert!(timing.contains(&"rag_chunks_sent".to_string()));
        }
    }
    pub fn test_chat_empty_messages_rejected(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![])]));
        assert!(r.status_code == 400);
    }
    pub fn test_chat_llm_error_returns_friendly_message(&mut self, app_client: String) -> () {
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "test".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut error_events = events.iter().filter(|e| e.contains(&"error".to_string())).map(|e| e).collect::<Vec<_>>();
            assert!(error_events.len() >= 1);
            assert!((error_events[0]["error".to_string()].to_lowercase().contains(&"not running".to_string()) || error_events[0]["error".to_string()].to_lowercase().contains(&"running".to_string())));
        }
    }
    pub fn test_chat_with_history(&mut self, app_client: String) -> () {
        let mut fake_resp = _FakeLLMResponse("They have offices worldwide.".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Tell me about Example Corp".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "Example Corp is an AI company.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Where are their offices?".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut full_text = events.iter().map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"".to_string());
            assert!(full_text.len() > 0);
        }
    }
    /// If the answer has content and RAG context, hallucination check runs.
    pub fn test_chat_hallucination_detection(&mut self, app_client: String) -> () {
        // If the answer has content and RAG context, hallucination check runs.
        let mut fake_resp = _FakeLLMResponse("Example Corp was founded in 2010 and has 300 employees.".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Tell me about Example Corp".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut hallu_events = events.iter().filter(|e| e.contains(&"hallucination".to_string())).map(|e| e).collect::<Vec<_>>();
            if hallu_events {
                let mut h = hallu_events[0]["hallucination".to_string()];
                assert!(h.contains(&"score".to_string()));
                assert!(h.contains(&"has_hallucinations".to_string()));
            }
        }
    }
}

/// Phase 8: Multi-pipeline comparison chat.
#[derive(Debug, Clone)]
pub struct TestChatCompare {
}

impl TestChatCompare {
    pub fn _crawled(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
    }
    pub fn _parse_sse(&self, response_data: Vec<u8>) -> Result<Vec<HashMap>> {
        let mut events = vec![];
        let mut text = response_data.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
        for line in text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            let mut line = line.trim().to_string();
            if (line.starts_with(&*"data: ".to_string()) && line[6..].trim().to_string() != "[DONE]".to_string()) {
                // try:
                {
                    events.push(serde_json::from_str(&line[6..]).unwrap());
                }
                // except json::JSONDecodeError as _e:
            }
        }
        Ok(events)
    }
    pub fn test_compare_streams_per_pipeline(&mut self, app_client: String) -> () {
        app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "reranked".to_string()])]));
        let mut fake_resp = _FakeLLMResponse("Example Corp is an AI company.".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat/compare".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What is Example Corp?".to_string())])])]));
            assert!(r.status_code == 200);
            let mut events = self._parse_sse(r.data);
            let mut pipelines_seen = HashSet::new();
            for e in events.iter() {
                if e.contains(&"pipeline".to_string()) {
                    pipelines_seen.insert(e["pipeline".to_string()]);
                }
            }
            assert!(pipelines_seen.len() >= 1);
        }
    }
    pub fn test_compare_empty_messages_rejected(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/chat/compare".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![])]));
        assert!(r.status_code == 400);
    }
}

/// Phase 9: Managing pipeline presets.
#[derive(Debug, Clone)]
pub struct TestPipelineManagement {
}

impl TestPipelineManagement {
    pub fn test_list_pipelines(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/api/pipelines".to_string()).cloned();
        let mut data = r.get_json();
        assert!(data.len() >= 4);
        let mut ids = data.iter().map(|p| p["id".to_string()]).collect::<Vec<_>>();
        assert!(ids.contains(&"baseline".to_string()));
        assert!(ids.contains(&"full_stack".to_string()));
    }
    pub fn test_pipeline_has_features(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/api/pipelines".to_string()).cloned();
        for p in r.get_json().iter() {
            assert!(p.contains(&"features".to_string()));
            assert!(p.contains(&"label".to_string()));
            assert!(p.contains(&"color".to_string()));
        }
    }
    pub fn test_set_active_pipelines(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "routed".to_string()])]));
        assert!(r.status_code == 200);
        assert!(r.get_json()["active".to_string()].into_iter().collect::<HashSet<_>>() == HashSet::from(["baseline".to_string(), "routed".to_string()]));
    }
    pub fn test_set_active_requires_valid_ids(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["nonexistent".to_string()])]));
        assert!(r.status_code == 400);
    }
    pub fn test_max_four_pipelines(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "reranked".to_string(), "routed".to_string(), "full_stack".to_string(), "baseline".to_string()])]));
        assert!(r.get_json()["active".to_string()].len() <= 4);
    }
}

/// Phase 10: Reset and reload operations.
#[derive(Debug, Clone)]
pub struct TestClearAndReload {
}

impl TestClearAndReload {
    pub fn test_clear_index(&self, app_client: String) -> () {
        app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2)]));
        app_client.post("/api/crawl".to_string());
        _wait_crawl(app_client);
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats["n_chunks".to_string()] > 0);
        let mut r = app_client.post("/api/clear".to_string());
        assert!(r.get_json()["ok".to_string()] == true);
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats["n_chunks".to_string()] == 0);
    }
    pub fn test_search_on_empty_index(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "anything".to_string())]));
        let mut data = r.get_json();
        assert!(data["results".to_string()] == vec![]);
    }
}

/// Complete end-to-end: add site → crawl → search → configure LLM → chat.
#[derive(Debug, Clone)]
pub struct TestFullJourney {
}

impl TestFullJourney {
    pub fn _parse_sse(&self, response_data: Vec<u8>) -> Result<Vec<HashMap>> {
        let mut events = vec![];
        let mut text = response_data.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
        for line in text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            let mut line = line.trim().to_string();
            if (line.starts_with(&*"data: ".to_string()) && line[6..].trim().to_string() != "[DONE]".to_string()) {
                // try:
                {
                    events.push(serde_json::from_str(&line[6..]).unwrap());
                }
                // except json::JSONDecodeError as _e:
            }
        }
        Ok(events)
    }
    pub fn test_complete_user_journey(&mut self, app_client: String) -> () {
        assert!(app_client.get(&"/".to_string()).cloned().status_code == 200);
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), "https://example.com".to_string()), ("depth".to_string(), 2), ("max_pages".to_string(), 50)]));
        assert!(r.status_code == 201);
        let mut r = app_client.post("/api/crawl".to_string());
        assert!(r.get_json()["started".to_string()] == true);
        let mut status = _wait_crawl(app_client);
        assert!(status["progress".to_string()][0]["status".to_string()] == "done".to_string());
        let mut pages_crawled = status["progress".to_string()][0]["pages".to_string()];
        assert!(pages_crawled >= 1);
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        let mut n_chunks = stats["n_chunks".to_string()];
        assert!(n_chunks > 0);
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "artificial intelligence machine learning".to_string()), ("k".to_string(), 5)]));
        let mut search_data = r.get_json();
        assert!(search_data["results".to_string()].len() > 0);
        assert!(search_data["results".to_string()][0]["score".to_string()] >= 0);
        let mut r = app_client.post("/api/llm/config".to_string(), /* json= */ HashMap::from([("base_url".to_string(), "http://localhost:8090/v1".to_string()), ("api_key".to_string(), "test-key".to_string()), ("model".to_string(), "test-model".to_string())]));
        assert!(r.status_code == 200);
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut health = app_client.get(&"/api/llm/health".to_string()).cloned().get_json();
            assert!(health["ok".to_string()] == true);
        }
        let mut llm_answer = "Example Corp was founded in 2010 by Dr. Jane Smith and Dr. John Doe. They specialize in artificial intelligence and machine learning solutions, serving over 500 clients from their headquarters in San Francisco.".to_string();
        let mut fake_resp = _FakeLLMResponse(llm_answer);
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Tell me about Example Corp's history and founders".to_string())])])]));
            assert!(r.status_code == 200);
            let mut events = self._parse_sse(r.data);
            let mut source_events = events.iter().filter(|e| e.contains(&"sources".to_string())).map(|e| e).collect::<Vec<_>>();
            assert!(source_events.len() >= 1);
            let mut full_text = events.iter().map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"".to_string());
            assert!(full_text.contains(&"Example Corp".to_string()));
            assert!(full_text.contains(&"2010".to_string()));
            let mut timing_events = events.iter().filter(|e| e.contains(&"rag_timing".to_string())).map(|e| e).collect::<Vec<_>>();
            assert!(timing_events.len() >= 1);
        }
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Tell me about Example Corp".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), full_text)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What products do they offer?".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            let mut followup = events.iter().map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"".to_string());
            assert!(followup.len() > 0);
        }
        app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "full_stack".to_string()])]));
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut r = app_client.post("/api/chat/compare".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "How many employees?".to_string())])])]));
            let mut events = self._parse_sse(r.data);
            assert!(events.len() > 0);
        }
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats.contains(&"metrics".to_string()));
        app_client.post("/api/clear".to_string());
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats["n_chunks".to_string()] == 0);
    }
}

/// Return fake crawl results from FAKE_PAGES.
pub fn _fake_crawl_site(start_url: String, max_depth: String, max_pages: String, on_page: String, cancel_event: String) -> () {
    // Return fake crawl results from FAKE_PAGES.
    let mut results = vec![];
    let mut visited = HashSet::new();
    let mut queue = vec![(start_url, 0)];
    while (queue && results.len() < max_pages) {
        let (mut url, mut depth) = queue.remove(&0);
        if (visited.contains(&url) || depth > max_depth) {
            continue;
        }
        visited.insert(url);
        let mut page = FAKE_PAGES.get(&url).cloned();
        if !page {
            continue;
        }
        let mut cr = _FakeCrawlResult(/* url= */ url, /* title= */ page["title".to_string()], /* text= */ page["text".to_string()], /* depth= */ depth);
        results.push(cr);
        if on_page {
            on_page(cr);
        }
        for link in page.get(&"links".to_string()).cloned().unwrap_or(vec![]).iter() {
            if !visited.contains(&link) {
                queue.push((link, (depth + 1)));
            }
        }
    }
    let mut stats = _FakeCrawlStats(/* pages_fetched= */ results.len(), /* urls_visited= */ visited.len(), /* total_chars= */ results.iter().map(|r| r.text.len()).collect::<Vec<_>>().iter().sum::<i64>());
    (results, stats)
}

/// Build SSE byte lines that mimic an OpenAI chat/completions stream.
pub fn _make_llm_stream(text: String) -> Vec<Vec<u8>> {
    // Build SSE byte lines that mimic an OpenAI chat/completions stream.
    let mut lines = vec![];
    let mut words = text.split(" ".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
    for (i, word) in words.iter().enumerate().iter() {
        let mut token = if i == 0 { word } else { (" ".to_string() + word) };
        let mut chunk = HashMap::from([("choices".to_string(), vec![HashMap::from([("delta".to_string(), HashMap::from([("content".to_string(), token)])), ("index".to_string(), 0)])])]);
        lines.push(format!("data: {}\n\n", serde_json::to_string(&chunk).unwrap()).as_bytes().to_vec());
    }
    lines.push(b"data: [DONE]

");
    lines
}

/// Create a Flask test client with mocked crawler and isolated data files.
pub fn app_client(tmp_path: String, monkeypatch: String) -> () {
    // Create a Flask test client with mocked crawler and isolated data files.
    monkeypatch.setattr("app::SITES_FILE".to_string(), (tmp_path / "sites.json".to_string()));
    monkeypatch.setattr("app::_ACTIVE_PIPELINES_FILE".to_string(), (tmp_path / "active_pipelines.json".to_string()));
    // TODO: import app as app_module
    app_module.INDEX.clear();
    monkeypatch.setattr("app::crawl_site".to_string(), _fake_crawl_site);
    let mut fake_emb = _FakeEmbedder();
    monkeypatch.setattr("app::INDEX._embedder".to_string(), fake_emb, /* raising= */ false);
    monkeypatch.setattr("zen_core_libs.rag.rag_index._get_embedder".to_string(), || fake_emb, /* raising= */ false);
    app_module.app::config["TESTING".to_string()] = true;
    let mut client = app_module.app::test_client();
    {
        /* yield client */;
    }
    app_module.INDEX.clear();
}

/// Poll /api/crawl/status until crawl finishes.
pub fn _wait_crawl(client: String, timeout: String) -> () {
    // Poll /api/crawl/status until crawl finishes.
    let mut deadline = (time::monotonic() + timeout);
    while time::monotonic() < deadline {
        let mut r = client.get(&"/api/crawl/status".to_string()).cloned();
        let mut status = r.get_json();
        if !status["running".to_string()] {
            status
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(0.1_f64));
    }
    pytest.fail("Crawl did not finish within timeout".to_string());
}
