/// Live end-to-end tests for RAG Test Bench — NO MOCKS.
/// 
/// Everything runs for real:
/// - Real web crawl (httpbin.org — a tiny, stable test site)
/// - Real sentence-transformers embedding
/// - Real llama-server LLM (auto-started with smallest available model)
/// - Real Flask app via test client
/// 
/// Prerequisites (auto-detected, test skips if missing):
/// - Internet connection (for crawling httpbin.org)
/// - llama-server binary (zen_core_libs.llm.find_llama_server_binary)
/// - At least one GGUF model in C:\AI\Models or standard paths
/// - sentence-transformers installed
/// 
/// Run:  python -m pytest test_live_e2e::py -v -m live
/// (excluded from default `pytest` run — needs explicit -m live)

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};

pub const CRAWL_URL: &str = "https://httpbin.org";

pub const CRAWL_DEPTH: i64 = 1;

pub const CRAWL_MAX_PAGES: i64 = 5;

pub const APP_PORT: i64 = 5051;

pub const APP_BASE: &str = "f'http://localhost:{APP_PORT}";

pub const LLM_PORT: i64 = 8091;

pub const PYTESTMARK: &str = "pytest.mark.live";

/// Verify the app serves its UI.
#[derive(Debug, Clone)]
pub struct TestLiveLandingPage {
}

impl TestLiveLandingPage {
    pub fn test_homepage_loads(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/".to_string()).cloned();
        assert!(r.status_code == 200);
        assert!(r.data.contains(&b"RAG Test Bench"));
    }
}

/// Add a real site, crawl it live, verify real chunks in the index.
#[derive(Debug, Clone)]
pub struct TestLiveSiteAndCrawl {
}

impl TestLiveSiteAndCrawl {
    pub fn test_add_site(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), CRAWL_URL), ("depth".to_string(), CRAWL_DEPTH), ("max_pages".to_string(), CRAWL_MAX_PAGES)]));
        assert!(r.status_code == 201);
        let mut data = r.get_json();
        assert!(data["url".to_string()] == CRAWL_URL);
    }
    pub fn test_crawl_completes(&self, app_client: String) -> () {
        let mut sites = app_client.get(&"/api/sites".to_string()).cloned().get_json();
        if !sites {
            app_client.post("/api/sites".to_string(), /* json= */ HashMap::from([("url".to_string(), CRAWL_URL), ("depth".to_string(), CRAWL_DEPTH), ("max_pages".to_string(), CRAWL_MAX_PAGES)]));
        }
        let mut r = app_client.post("/api/crawl".to_string());
        assert!(r.get_json()["started".to_string()] == true);
        let mut status = _wait_crawl(app_client);
        assert!(status["running".to_string()] == false);
        assert!(status["progress".to_string()].len() >= 1);
        let mut done = status["progress".to_string()].iter().filter(|p| p.get(&"status".to_string()).cloned() == "done".to_string()).map(|p| p).collect::<Vec<_>>();
        assert!(done.len() >= 1);
        assert!(done[0]["pages".to_string()] >= 1);
    }
    pub fn test_index_has_chunks(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats["n_chunks".to_string()] > 0, "Index should have chunks after crawl");
    }
    pub fn test_site_record_updated(&self, app_client: String) -> () {
        let mut sites = app_client.get(&"/api/sites".to_string()).cloned().get_json();
        let mut site = next(sites.iter().filter(|s| s["url".to_string()] == CRAWL_URL).map(|s| s).collect::<Vec<_>>(), None);
        assert!(site.is_some());
        assert!(site["last_crawled".to_string()].is_some());
        assert!(site["pages_crawled".to_string()] >= 1);
    }
}

/// Search the real indexed data.
#[derive(Debug, Clone)]
pub struct TestLiveSearch {
}

impl TestLiveSearch {
    pub fn test_search_returns_results(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed — crawl may have failed".to_string());
        }
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "HTTP request methods".to_string()), ("k".to_string(), 3)]));
        assert!(r.status_code == 200);
        let mut data = r.get_json();
        assert!(data["results".to_string()].len() > 0);
        assert!(data["elapsed_sec".to_string()] > 0);
    }
    pub fn test_search_scores_are_real(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "httpbin".to_string()), ("k".to_string(), 5)]));
        let mut data = r.get_json();
        for result in data["results".to_string()].iter() {
            assert!(/* /* isinstance(result["score".to_string()], float) */ */ true);
            assert!(result["source_url".to_string()].starts_with(&*"http".to_string()));
            assert!(result["text".to_string()].len() > 0);
        }
    }
    pub fn test_search_has_routing(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "What methods does httpbin support?".to_string())]));
        let mut data = r.get_json();
        assert!(data.contains(&"intent".to_string()));
        assert!(data.contains(&"intent_confidence".to_string()));
    }
}

/// Verify LLM health endpoint against real running server.
#[derive(Debug, Clone)]
pub struct TestLiveLLMHealth {
}

impl TestLiveLLMHealth {
    pub fn test_llm_health_ok(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/api/llm/health".to_string()).cloned();
        let mut data = r.get_json();
        assert!(data["ok".to_string()] == true, "LLM health failed: {}", data.get(&"error").cloned());
    }
}

/// Chat with a real LLM using real RAG context.
#[derive(Debug, Clone)]
pub struct TestLiveChat {
}

impl TestLiveChat {
    pub fn test_chat_produces_real_answer(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What is httpbin?".to_string())])]), ("rag_k".to_string(), 3)]));
        assert!(r.status_code == 200);
        assert!(r.content_type.contains(&"text/event-stream".to_string()));
        let mut events = _parse_sse(r.data);
        assert!(events.len() > 0, "Should receive SSE events");
        let mut source_events = events.iter().filter(|e| e.contains(&"sources".to_string())).map(|e| e).collect::<Vec<_>>();
        assert!(source_events.len() >= 1, "Chat should include RAG sources");
        let mut content_parts = events.iter().filter(|e| e.contains(&"content".to_string())).map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>();
        let mut full_answer = content_parts.join(&"".to_string());
        assert!(full_answer.len() > 10, "LLM should generate a real answer, got: {}", full_answer);
    }
    pub fn test_chat_has_rag_timing(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Tell me about HTTP methods".to_string())])])]));
        let mut events = _parse_sse(r.data);
        let mut timing_events = events.iter().filter(|e| e.contains(&"rag_timing".to_string())).map(|e| e).collect::<Vec<_>>();
        assert!(timing_events.len() >= 1);
        let mut timing = timing_events[0]["rag_timing".to_string()];
        assert!(timing.contains(&"rag_chunks_sent".to_string()));
        assert!(timing["rag_chunks_sent".to_string()] >= 0);
    }
    pub fn test_multi_turn_chat(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        let mut r = app_client.post("/api/chat".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What is httpbin?".to_string())]), HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), "httpbin is an HTTP testing service.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What endpoints does it have?".to_string())])])]));
        let mut events = _parse_sse(r.data);
        let mut content = events.iter().filter(|e| e.contains(&"content".to_string())).map(|e| e.get(&"content".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"".to_string());
        assert!(content.len() > 5, "Multi-turn should produce a response");
    }
}

/// Multi-pipeline comparison with real LLM.
#[derive(Debug, Clone)]
pub struct TestLiveChatCompare {
}

impl TestLiveChatCompare {
    pub fn test_compare_two_pipelines(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        if stats["n_chunks".to_string()] == 0 {
            pytest.skip("No chunks indexed".to_string());
        }
        app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "full_stack".to_string()])]));
        let mut r = app_client.post("/api/chat/compare".to_string(), /* json= */ HashMap::from([("messages".to_string(), vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "What does httpbin do?".to_string())])])]));
        assert!(r.status_code == 200);
        let mut events = _parse_sse(r.data);
        assert!(events.len() > 0);
        let mut pipelines_seen = HashSet::new();
        for e in events.iter() {
            if e.contains(&"pipeline".to_string()) {
                pipelines_seen.insert(e["pipeline".to_string()]);
            }
        }
        assert!(pipelines_seen.len() >= 1, "Expected pipeline events, saw: {}", pipelines_seen);
    }
}

/// Pipeline CRUD against real app state.
#[derive(Debug, Clone)]
pub struct TestLivePipelineManagement {
}

impl TestLivePipelineManagement {
    pub fn test_list_pipelines(&self, app_client: String) -> () {
        let mut r = app_client.get(&"/api/pipelines".to_string()).cloned();
        let mut data = r.get_json();
        assert!(data.len() >= 4);
        let mut labels = data.iter().map(|p| p["label".to_string()]).collect::<Vec<_>>();
        assert!(labels.contains(&"Baseline".to_string()));
        assert!(labels.contains(&"Full Stack".to_string()));
    }
    pub fn test_activate_pipelines(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/pipelines/active".to_string(), /* json= */ HashMap::from([("pipelines".to_string(), vec!["baseline".to_string(), "reranked".to_string(), "routed".to_string()])]));
        assert!(r.status_code == 200);
        assert!(r.get_json()["active".to_string()].len() == 3);
    }
}

/// Verify metrics are tracked from real operations.
#[derive(Debug, Clone)]
pub struct TestLiveMetrics {
}

impl TestLiveMetrics {
    pub fn test_metrics_recorded(&self, app_client: String) -> () {
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats.contains(&"metrics".to_string()));
        assert!(stats.contains(&"cache".to_string()));
        assert!(stats.contains(&"reranker".to_string()));
    }
}

/// Clear and verify empty — last test to run.
#[derive(Debug, Clone)]
pub struct TestLiveClearAndReload {
}

impl TestLiveClearAndReload {
    pub fn test_clear_index(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/clear".to_string());
        assert!(r.get_json()["ok".to_string()] == true);
        let mut stats = app_client.get(&"/api/stats".to_string()).cloned().get_json();
        assert!(stats["n_chunks".to_string()] == 0);
    }
    pub fn test_search_empty_after_clear(&self, app_client: String) -> () {
        let mut r = app_client.post("/api/search".to_string(), /* json= */ HashMap::from([("query".to_string(), "anything".to_string())]));
        let mut data = r.get_json();
        assert!(data["results".to_string()] == vec![]);
    }
}

pub fn _has_internet() -> Result<bool> {
    // try:
    {
        /* reqwest::head( */"https://httpbin.org".to_string(), /* timeout= */ 5);
        true
    }
    // except (requests.ConnectionError, requests.Timeout) as _e:
}

pub fn _has_llama_server() -> Result<(bool, String)> {
    // try:
    {
        // TODO: from zen_core_libs.llm import find_llama_server_binary
        let mut binary = find_llama_server_binary();
        (binary.is_some(), (binary || "".to_string()))
    }
    // except ImportError as _e:
}

pub fn _smallest_model() -> Result<Option<String>> {
    // try:
    {
        // TODO: from zen_core_libs.llm import discover_models
        let mut models = discover_models();
        if !models {
            None
        }
        models::sort(/* key= */ |m| m.get(&"size_gb".to_string()).cloned().unwrap_or(999));
        models[0]["path".to_string()]
    }
    // except ImportError as _e:
}

/// Check all prerequisites once per module. Skip entire module if missing.
pub fn live_prereqs() -> () {
    // Check all prerequisites once per module. Skip entire module if missing.
    if !_has_internet() {
        pytest.skip("No internet connection — cannot crawl live site".to_string());
    }
    let (mut has_llama, mut binary) = _has_llama_server();
    if !has_llama {
        pytest.skip("llama-server binary not found".to_string());
    }
    let mut model_path = _smallest_model();
    if !model_path {
        pytest.skip("No GGUF models found".to_string());
    }
    HashMap::from([("binary".to_string(), binary), ("model_path".to_string(), model_path)])
}

/// Start a real llama-server with the smallest model, yield when ready, stop after.
pub fn llm_server(live_prereqs: String) -> Result<()> {
    // Start a real llama-server with the smallest model, yield when ready, stop after.
    // TODO: from zen_core_libs.llm import LlamaServerManager
    let mut mgr = LlamaServerManager();
    let mut model_path = live_prereqs["model_path".to_string()];
    println!("\n  Starting llama-server with {}...", os::path.basename(model_path));
    // try:
    {
        let mut result = mgr.start(/* model_path= */ model_path, /* port= */ LLM_PORT, /* ctx_size= */ 2048, /* gpu_layers= */ 99, /* timeout= */ 120);
    }
    // except Exception as e:
    if !mgr.is_running {
        pytest.skip(format!("llama-server did not start: {}", result));
    }
    let mut base_url = format!("http://localhost:{}/v1", LLM_PORT);
    println!("  llama-server ready on port {}", LLM_PORT);
    /* yield HashMap::from([("base_url".to_string(), base_url), ("model".to_string(), os::path.basename(model_path)), ("mgr".to_string(), mgr)]) */;
    println!("{}", "\n  Stopping llama-server...".to_string());
    Ok(mgr.stop())
}

/// Start the Flask app as a test client with real dependencies.
/// 
/// Uses isolated data files so we don't corrupt the user's real sites.json.
pub fn app_client(live_prereqs: String, llm_server: String, tmp_path_factory: String) -> Result<()> {
    // Start the Flask app as a test client with real dependencies.
    // 
    // Uses isolated data files so we don't corrupt the user's real sites.json.
    let mut tmp = tmp_path_factory.mktemp("live_e2e".to_string());
    // TODO: import app as app_module
    app_module.SITES_FILE = (tmp / "sites.json".to_string());
    app_module._ACTIVE_PIPELINES_FILE = (tmp / "active_pipelines.json".to_string());
    app_module.LLM_CONFIG_FILE = (tmp / "llm_config.json".to_string());
    app_module.INDEX.clear();
    let mut llm_cfg = HashMap::from([("base_url".to_string(), llm_server["base_url".to_string()]), ("api_key".to_string(), "not-needed".to_string()), ("model".to_string(), llm_server["model".to_string()])]);
    let mut f = File::create((tmp / "llm_config.json".to_string()))?;
    {
        json::dump(llm_cfg, f);
    }
    app_module.app::config["TESTING".to_string()] = true;
    let mut client = app_module.app::test_client();
    {
        /* yield client */;
    }
    Ok(app_module.INDEX.clear())
}

/// Poll crawl status until done.
pub fn _wait_crawl(client: String, timeout: String) -> () {
    // Poll crawl status until done.
    let mut deadline = (time::monotonic() + timeout);
    while time::monotonic() < deadline {
        let mut r = client.get(&"/api/crawl/status".to_string()).cloned();
        let mut status = r.get_json();
        if !status["running".to_string()] {
            status
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(0.5_f64));
    }
    pytest.fail(format!("Crawl did not finish within {}s", timeout));
}

/// Parse SSE byte stream into list of JSON events.
pub fn _parse_sse(data: Vec<u8>) -> Result<Vec<HashMap>> {
    // Parse SSE byte stream into list of JSON events.
    let mut events = vec![];
    let mut text = data.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
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
