/// RAG Test Bench — Flask application
/// ===================================
/// Web UI for managing websites, crawling, indexing, and testing RAG queries.
/// Includes a chatbot that converses with the indexed data via any OpenAI-compatible API.
/// 
/// Usage:
/// pip install -r requirements.txt
/// python app::py          # → http://localhost:5050
/// 
/// Environment variables (all optional):
/// RAG_MODEL      = sentence-transformer model  (default: all-MiniLM-L6-v2)
/// RAG_NBITS      = TurboQuant bit width          (default: 3)
/// RAG_CHUNK_SIZE = chunk size in chars            (default: 512)
/// RAG_PORT       = server port                    (default: 5050)
/// LLM_BASE_URL   = OpenAI-compatible API base     (default: http://localhost:11434/v1)
/// LLM_API_KEY    = API key                        (default: ollama)
/// LLM_MODEL      = model name                     (default: llama3.2)

use anyhow::{Result, Context};
use crate::crawler::{CrawlResult, crawl_site};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static APP: std::sync::LazyLock<Flask> = std::sync::LazyLock::new(|| Default::default());

pub static SITES_FILE: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub static INDEX: std::sync::LazyLock<RAGIndex> = std::sync::LazyLock::new(|| Default::default());

pub static LLAMA: std::sync::LazyLock<LlamaServerManager> = std::sync::LazyLock::new(|| Default::default());

pub static MODEL_HUB: std::sync::LazyLock<ModelHub> = std::sync::LazyLock::new(|| Default::default());

pub static DEDUPER: std::sync::LazyLock<SmartDeduplicator> = std::sync::LazyLock::new(|| Default::default());

pub static RERANKER: std::sync::LazyLock<Reranker> = std::sync::LazyLock::new(|| Default::default());

pub static ROUTER: std::sync::LazyLock<QueryRouter> = std::sync::LazyLock::new(|| Default::default());

pub static HALLUCINATION_DETECTOR: std::sync::LazyLock<HallucinationDetector> = std::sync::LazyLock::new(|| Default::default());

pub const DEFAULT_TOP_K: i64 = 5;

pub const MAX_ACTIVE_PIPELINES: i64 = 4;

pub const SCORE_THRESHOLD: f64 = 0.15;

pub const PIPELINE_CONTEXT_CHAR_LIMIT: i64 = 4800;

pub const HISTORY_BUDGET_CHARS: i64 = 8000;

pub const SEARCH_RESULT_PREVIEW_LEN: i64 = 500;

pub const LLM_TEMPERATURE: f64 = 0.3;

pub const LLM_MAX_TOKENS: i64 = 2048;

pub const LLM_STREAM_TIMEOUT: i64 = 120;

pub const PIPELINE_COMPARE_TIMEOUT: i64 = 180;

pub const SEARCH_CACHE_MAX_ENTRIES: i64 = 256;

pub const SEARCH_CACHE_TTL: i64 = 1800;

pub const MAX_HALLUCINATION_FINDINGS: i64 = 5;

pub const DEFAULT_LLAMA_PORT: i64 = 8090;

pub const DEFAULT_CTX_SIZE: i64 = 4096;

pub const LLM_HEALTH_TIMEOUT: i64 = 3;

pub const MAX_CRAWL_DEPTH: i64 = 10;

pub const MAX_CRAWL_PAGES: i64 = 5000;

pub const DEFAULT_CRAWL_DEPTH: i64 = 2;

pub const DEFAULT_CRAWL_PAGES: i64 = 50;

pub const HF_SEARCH_LIMIT_MAX: i64 = 50;

pub const MAX_SEARCH_K: i64 = 20;

pub static SEARCH_CACHE: std::sync::LazyLock<ZeroWasteCache> = std::sync::LazyLock::new(|| Default::default());

pub static METRICS: std::sync::LazyLock<get_tracker> = std::sync::LazyLock::new(|| Default::default());

pub static PIPELINE_PRESETS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static _ACTIVE_PIPELINES_FILE: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_BASE_URL: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_API_KEY: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_MODEL: std::sync::LazyLock<String /* os::environ.get */> = std::sync::LazyLock::new(|| Default::default());

pub static LLM_CONFIG_FILE: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub static _CRAWL_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

pub static _CRAWL_STATUS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static _CRAWL_CANCEL: std::sync::LazyLock<std::sync::Condvar> = std::sync::LazyLock::new(|| Default::default());

pub fn _load_active_pipelines() -> Result<Vec<String>> {
    if _ACTIVE_PIPELINES_FILE.exists() {
        // try:
        {
            let mut f = File::open(_ACTIVE_PIPELINES_FILE)?;
            {
                let mut ids = json::load(f);
            }
            ids.iter().filter(|pid| PIPELINE_PRESETS.contains(&pid)).map(|pid| pid).collect::<Vec<_>>()[..MAX_ACTIVE_PIPELINES]
        }
        // except (json::JSONDecodeError, ValueError, OSError) as _e:
    }
    Ok(vec!["full_stack".to_string()])
}

pub fn _save_active_pipelines(ids: Vec<String>) -> Result<()> {
    let mut f = File::create(_ACTIVE_PIPELINES_FILE)?;
    {
        json::dump(ids, f);
    }
}

/// Apply pipeline-specific retrieval strategy to the shared INDEX.
pub fn _pipeline_retrieve(pid: String, query: String, k: i64) -> () {
    // Apply pipeline-specific retrieval strategy to the shared INDEX.
    let mut cfg = PIPELINE_PRESETS[&pid];
    let mut t0 = time::monotonic();
    let mut timing = HashMap::from([("pipeline".to_string(), pid)]);
    let mut fetch_k = if (cfg["rerank".to_string()] || cfg["dedup".to_string()]) { (k * 3) } else { k };
    let mut routing = None;
    if cfg["query_routing".to_string()] {
        let mut routing = ROUTER.route(query);
        let mut routed_k = routing::config::get(&"top_k".to_string()).cloned().unwrap_or(k);
        let mut fetch_k = fetch_k.max((routed_k * 2));
        timing["intent".to_string()] = routing::intent.value;
        timing["intent_confidence".to_string()] = ((routing::confidence as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
    }
    let (mut results, mut search_timing) = INDEX.search_timed(query, /* k= */ fetch_k);
    timing.extend(search_timing);
    if (cfg["corrective_rag".to_string()] && results) {
        let mut chunk_dicts = results.iter().map(|r| HashMap::from([("text".to_string(), r.chunk.text), ("score".to_string(), r.score), ("source_url".to_string(), r.chunk.source_url), ("page_title".to_string(), r.chunk.page_title)])).collect::<Vec<_>>();
        let mut crag = CorrectiveRAG(/* retrieve_fn= */ |q, kk| INDEX.search(q, /* k= */ kk).iter().map(|r| HashMap::from([("text".to_string(), r.chunk.text), ("score".to_string(), r.score)])).collect::<Vec<_>>());
        let (mut grade, mut confidence) = crag._grade(query, chunk_dicts);
        timing["crag_grade".to_string()] = grade.value;
        timing["crag_confidence".to_string()] = ((confidence as f64) * 10f64.powi(3)).round() / 10f64.powi(3);
    }
    if (cfg["rerank".to_string()] && results) {
        let mut texts = results.iter().map(|r| r.chunk.text).collect::<Vec<_>>();
        let (mut reranked_texts, _) = RERANKER.rerank(query, texts, /* top_k= */ k, /* return_scores= */ true);
        let mut text_to_result = results.iter().map(|r| (r.chunk.text, r)).collect::<HashMap<_, _>>();
        let mut results = reranked_texts.iter().filter(|t| text_to_result.contains(&t)).map(|t| text_to_result[&t]).collect::<Vec<_>>();
    } else {
        let mut results = results[..k];
    }
    timing["total_ms".to_string()] = ((((time::monotonic() - t0) * 1000) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
    (results, timing)
}

/// Build RAG context for one pipeline.
pub fn _pipeline_build_context(pid: String, query: String, k: i64, threshold: f64) -> () {
    // Build RAG context for one pipeline.
    let (mut results, mut timing) = _pipeline_retrieve(pid, query, k);
    let mut strong = results.iter().filter(|r| r.score >= threshold).map(|r| r).collect::<Vec<_>>();
    timing["filtered_weak".to_string()] = (results.len() - strong.len());
    let (mut parts, mut sources) = (vec![], vec![]);
    let mut total_chars = 0;
    for r in strong.iter() {
        let mut chunk_str = format!("[{}] ({})\n{}", r.chunk.page_title, r.chunk.source_url, r.chunk.text);
        if (total_chars + chunk_str.len()) > PIPELINE_CONTEXT_CHAR_LIMIT {
            break;
        }
        parts.push(chunk_str);
        total_chars += chunk_str.len();
        sources.push(HashMap::from([("title".to_string(), r.chunk.page_title), ("url".to_string(), r.chunk.source_url), ("score".to_string(), ((r.score as f64) * 10f64.powi(4)).round() / 10f64.powi(4))]));
    }
    timing["chunks_sent".to_string()] = sources.len();
    (parts.join(&"\n\n---\n\n".to_string()), sources, timing)
}

/// Trim chat history to fit token budget, keeping most recent messages.
pub fn _trim_history(messages: Vec<serde_json::Value>, budget_chars: i64) -> Vec {
    // Trim chat history to fit token budget, keeping most recent messages.
    let mut trimmed = vec![];
    let mut total = 0;
    for m in messages.iter().rev().iter() {
        let mut mc = m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len();
        if (total + mc) > budget_chars {
            break;
        }
        trimmed.insert(0, m);
        total += mc;
    }
    if (!trimmed && messages) {
        let mut trimmed = vec![messages[-1]];
    }
    trimmed
}

/// Load persisted LLM config (overrides env vars via UI).
pub fn _load_llm_config() -> Result<HashMap> {
    // Load persisted LLM config (overrides env vars via UI).
    if LLM_CONFIG_FILE.exists() {
        // try:
        {
            let mut f = File::open(LLM_CONFIG_FILE)?;
            {
                json::load(f)
            }
        }
        // except (json::JSONDecodeError, ValueError) as _e:
    }
    Ok(HashMap::new())
}

pub fn _save_llm_config(cfg: HashMap<String, serde_json::Value>) -> Result<()> {
    let mut f = File::create(LLM_CONFIG_FILE)?;
    {
        json::dump(cfg, f, /* indent= */ 2);
    }
}

/// Return effective LLM settings (file overrides > env vars > defaults).
pub fn _get_llm_settings() -> HashMap {
    // Return effective LLM settings (file overrides > env vars > defaults).
    let mut cfg = _load_llm_config();
    HashMap::from([("base_url".to_string(), (cfg.get(&"base_url".to_string()).cloned() || LLM_BASE_URL)), ("api_key".to_string(), (cfg.get(&"api_key".to_string()).cloned() || LLM_API_KEY)), ("model".to_string(), (cfg.get(&"model".to_string()).cloned() || LLM_MODEL)), ("system_prompt".to_string(), cfg.get(&"system_prompt".to_string()).cloned().unwrap_or("".to_string()))])
}

pub fn _load_sites() -> Result<Vec<HashMap>> {
    if SITES_FILE.exists() {
        // try:
        {
            let mut f = File::open(SITES_FILE)?;
            {
                json::load(f)
            }
        }
        // except (json::JSONDecodeError, ValueError, OSError) as _e:
    }
    Ok(vec![])
}

pub fn _save_sites(sites: Vec<HashMap>) -> Result<()> {
    let mut f = File::create(SITES_FILE)?;
    {
        json::dump(sites, f, /* ensure_ascii= */ false, /* indent= */ 2);
    }
}

pub fn ui() -> () {
    let mut resp = make_response(render_template("index.html".to_string()));
    resp.headers["Cache-Control".to_string()] = "no-cache, no-store, must-revalidate".to_string();
    resp
}

pub fn get_sites() -> () {
    jsonify(_load_sites())
}

pub fn add_site() -> Result<()> {
    let mut data = request.get_json(/* force= */ true);
    let mut url = (data.get(&"url".to_string()).cloned() || "".to_string()).trim().to_string();
    if !url {
        (jsonify(HashMap::from([("error".to_string(), "url is required".to_string())])), 400)
    }
    if !url.starts_with(&*("http://".to_string(), "https://".to_string())) {
        let mut url = ("https://".to_string() + url);
    }
    // try:
    {
        let mut depth = 1.max(data.get(&"depth".to_string()).cloned().unwrap_or(DEFAULT_CRAWL_DEPTH).to_string().parse::<i64>().unwrap_or(0).min(MAX_CRAWL_DEPTH));
        let mut max_pages = 1.max(data.get(&"max_pages".to_string()).cloned().unwrap_or(DEFAULT_CRAWL_PAGES).to_string().parse::<i64>().unwrap_or(0).min(MAX_CRAWL_PAGES));
    }
    // except (ValueError, TypeError) as _e:
    let mut sites = _load_sites();
    if sites.iter().map(|s| s["url".to_string()] == url).collect::<Vec<_>>().iter().any(|v| *v) {
        (jsonify(HashMap::from([("error".to_string(), "URL already exists".to_string())])), 409)
    }
    let mut entry = HashMap::from([("url".to_string(), url), ("depth".to_string(), depth), ("max_pages".to_string(), max_pages), ("added".to_string(), time::strftime("%Y-%m-%d %H:%M:%S".to_string())), ("last_crawled".to_string(), None), ("pages_crawled".to_string(), 0), ("chunks_indexed".to_string(), 0)]);
    sites.push(entry);
    _save_sites(sites);
    Ok((jsonify(entry), 201))
}

pub fn remove_site() -> () {
    let mut data = request.get_json(/* force= */ true);
    let mut url = data.get(&"url".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    let mut sites = _load_sites();
    let mut sites = sites.iter().filter(|s| s["url".to_string()] != url).map(|s| s).collect::<Vec<_>>();
    _save_sites(sites);
    jsonify(HashMap::from([("ok".to_string(), true)]))
}

pub fn get_pipelines() -> () {
    let mut active = _load_active_pipelines();
    jsonify(PIPELINE_PRESETS.iter().iter().map(|(pid, cfg)| HashMap::from([("id".to_string(), pid), ("label".to_string(), cfg["label".to_string()]), ("desc".to_string(), cfg["desc".to_string()]), ("color".to_string(), cfg["color".to_string()]), ("active".to_string(), active.contains(&pid)), ("features".to_string(), cfg.iter().iter().filter(|(k, v)| !("label".to_string(), "desc".to_string(), "color".to_string()).contains(&k)).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>())])).collect::<Vec<_>>())
}

pub fn set_active_pipelines() -> () {
    let mut data = request.get_json(/* force= */ true);
    let mut ids = data.get(&"pipelines".to_string()).cloned().unwrap_or(vec![]).iter().filter(|pid| PIPELINE_PRESETS.contains(&pid)).map(|pid| pid).collect::<Vec<_>>();
    if !ids {
        (jsonify(HashMap::from([("error".to_string(), "At least one pipeline required".to_string())])), 400)
    }
    _save_active_pipelines(ids[..MAX_ACTIVE_PIPELINES]);
    jsonify(HashMap::from([("active".to_string(), ids[..MAX_ACTIVE_PIPELINES])]))
}

/// Crawl all sites (or one if ?url= given) and index results.
pub fn start_crawl() -> Result<()> {
    // Crawl all sites (or one if ?url= given) and index results.
    let _ctx = _crawl_lock;
    {
        if _crawl_status["running".to_string()] {
            (jsonify(HashMap::from([("error".to_string(), "Crawl already running".to_string())])), 409)
        }
        _crawl_status.clear();
        _crawl_status.extend(HashMap::from([("running".to_string(), true), ("progress".to_string(), vec![])]));
        _crawl_cancel.clear();
    }
    let mut target_url = request.args.get(&"url".to_string()).cloned();
    let mut sites = _load_sites();
    if target_url {
        let mut sites = sites.iter().filter(|s| (s["url".to_string()].contains(&target_url) || target_url.contains(&s["url".to_string()]))).map(|s| s).collect::<Vec<_>>();
    }
    let _run = || {
        // try:
        {
            let mut all_sites = _load_sites();
            for site in sites.iter() {
                if _crawl_cancel.is_set() {
                    _crawl_status["progress".to_string()].push(HashMap::from([("url".to_string(), "".to_string()), ("status".to_string(), "cancelled".to_string()), ("error".to_string(), "Cancelled by user".to_string())]));
                    break;
                }
                INDEX.remove_by_source(site["url".to_string()]);
                let mut prog = HashMap::from([("url".to_string(), site["url".to_string()]), ("status".to_string(), "crawling".to_string()), ("pages".to_string(), 0), ("chunks".to_string(), 0)]);
                _crawl_status["progress".to_string()].push(prog);
                let _on_page = |cr, _p| {
                    if !cr.error {
                        _p["pages".to_string()] = (_p.get(&"pages".to_string()).cloned().unwrap_or(0) + 1);
                    }
                };
                let (mut results, mut stats) = crawl_site(site["url".to_string()], /* max_depth= */ site.get(&"depth".to_string()).cloned().unwrap_or(DEFAULT_CRAWL_DEPTH), /* max_pages= */ site.get(&"max_pages".to_string()).cloned().unwrap_or(DEFAULT_CRAWL_PAGES), /* on_page= */ _on_page, /* cancel_event= */ _crawl_cancel);
                let mut all_chunks = vec![];
                for r in results.iter() {
                    if r.error {
                        continue;
                    }
                    all_chunks.extend(chunk_text(r.text, /* source_url= */ r.url, /* page_title= */ r.title));
                }
                prog["chunks".to_string()] = all_chunks.len();
                let mut chunks_before_dedup = all_chunks.len();
                if all_chunks {
                    let mut chunk_dicts = all_chunks.iter().map(|c| HashMap::from([("text".to_string(), c.text), ("source_url".to_string(), c.source_url), ("page_title".to_string(), c.page_title), ("chunk_idx".to_string(), c.chunk_idx), ("char_offset".to_string(), c.char_offset)])).collect::<Vec<_>>();
                    let mut dedup_result = DEDUPER.deduplicate(chunk_dicts);
                    let mut dedup_stats = dedup_result.stats;
                    let mut all_chunks = dedup_result.unique_chunks.iter().map(|d| Chunk(/* ** */ d)).collect::<Vec<_>>();
                    logger.info("Dedup: %d→%d chunks (removed %d dupes)".to_string(), dedup_stats.total_input, dedup_stats.total_output, dedup_stats.total_removed);
                    METRICS.record("dedup_removed".to_string(), dedup_stats.total_removed);
                }
                let mut n_added = if all_chunks { INDEX.add_chunks(all_chunks) } else { 0 };
                SEARCH_CACHE.invalidate();
                for s in all_sites.iter() {
                    if s["url".to_string()] == site["url".to_string()] {
                        s["last_crawled".to_string()] = time::strftime("%Y-%m-%d %H:%M:%S".to_string());
                        s["pages_crawled".to_string()] = stats.pages_fetched;
                        s["chunks_indexed".to_string()] = n_added;
                    }
                }
                _crawl_status["progress".to_string()][-1].extend(HashMap::from([("status".to_string(), "done".to_string()), ("pages".to_string(), stats.pages_fetched), ("chunks".to_string(), n_added), ("errors".to_string(), stats.pages_errored), ("skipped".to_string(), stats.pages_skipped), ("urls_visited".to_string(), stats.urls_visited), ("content_types".to_string(), stats.content_types), ("total_chars".to_string(), stats.total_chars), ("dedup_removed".to_string(), (chunks_before_dedup - n_added)), ("elapsed".to_string(), stats.elapsed_sec)]));
            }
            _save_sites(all_sites);
            INDEX.save();
        }
        // except Exception as exc:
        // finally:
            let _ctx = _crawl_lock;
            {
                _crawl_status["running".to_string()] = false;
            }
    };
    std::thread::spawn(|| {});
    Ok(jsonify(HashMap::from([("started".to_string(), true), ("sites".to_string(), sites.len())])))
}

pub fn crawl_status() -> () {
    jsonify(_crawl_status)
}

/// Cancel a running crawl.
pub fn cancel_crawl() -> () {
    // Cancel a running crawl.
    _crawl_cancel.set();
    let _ctx = _crawl_lock;
    {
        _crawl_status["running".to_string()] = false;
    }
    jsonify(HashMap::from([("ok".to_string(), true)]))
}

pub fn search() -> Result<()> {
    let mut data = request.get_json(/* force= */ true);
    let mut query = (data.get(&"query".to_string()).cloned() || "".to_string()).trim().to_string();
    if !query {
        (jsonify(HashMap::from([("error".to_string(), "query is required".to_string())])), 400)
    }
    // try:
    {
        let mut k = 1.max(data.get(&"k".to_string()).cloned().unwrap_or(DEFAULT_TOP_K).to_string().parse::<i64>().unwrap_or(0).min(MAX_SEARCH_K));
    }
    // except (ValueError, TypeError) as _e:
    let mut t0 = time::monotonic();
    let mut routing = ROUTER.route(query);
    let mut routed_k = routing::config::get(&"top_k".to_string()).cloned().unwrap_or(k);
    let mut effective_k = k.max(routed_k);
    let mut cached = SEARCH_CACHE.get_context(query);
    if cached.is_some() {
        let mut elapsed = (((time::monotonic() - t0) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
        METRICS.record("search_ms".to_string(), (elapsed * 1000));
        METRICS.increment("search_cache_hits".to_string());
        jsonify(HashMap::from([("elapsed_sec".to_string(), elapsed), ("cache_hit".to_string(), true)]))
    }
    let mut results = INDEX.search(query, /* k= */ effective_k);
    if (results && routing::config::get(&"rerank".to_string()).cloned().unwrap_or(true)) {
        let mut texts = results.iter().map(|r| r.chunk.text).collect::<Vec<_>>();
        let (mut reranked_texts, mut rerank_scores) = RERANKER.rerank(query, texts, /* top_k= */ k, /* return_scores= */ true);
        let mut text_to_result = results.iter().map(|r| (r.chunk.text, r)).collect::<HashMap<_, _>>();
        let mut results = reranked_texts.iter().filter(|t| text_to_result.contains(&t)).map(|t| text_to_result[&t]).collect::<Vec<_>>();
    } else {
        let mut results = results[..k];
    }
    let mut elapsed = (((time::monotonic() - t0) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
    METRICS.record("search_ms".to_string(), (elapsed * 1000));
    METRICS.increment("search_total".to_string());
    let mut response_data = HashMap::from([("query".to_string(), query), ("k".to_string(), k), ("elapsed_sec".to_string(), elapsed), ("intent".to_string(), routing::intent.value), ("intent_confidence".to_string(), ((routing::confidence as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("results".to_string(), results.iter().map(|r| HashMap::from([("text".to_string(), r.chunk.text[..SEARCH_RESULT_PREVIEW_LEN]), ("source_url".to_string(), r.chunk.source_url), ("page_title".to_string(), r.chunk.page_title), ("score".to_string(), ((r.score as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("chunk_idx".to_string(), r.chunk.chunk_idx)])).collect::<Vec<_>>())]);
    SEARCH_CACHE.put_context(query, response_data);
    Ok(jsonify(response_data))
}

pub fn stats() -> () {
    let mut base = INDEX.stats;
    base["reranker".to_string()] = RERANKER.get_stats();
    base["cache".to_string()] = SEARCH_CACHE.get_stats();
    base["metrics".to_string()] = METRICS.snapshot_all();
    jsonify(base)
}

pub fn clear_index() -> () {
    INDEX.clear();
    SEARCH_CACHE.invalidate();
    METRICS.reset();
    jsonify(HashMap::from([("ok".to_string(), true)]))
}

/// Load persisted index from disk.
pub fn load_index() -> () {
    // Load persisted index from disk.
    INDEX.load();
    jsonify(HashMap::from([("loaded".to_string(), INDEX.n_chunks), ("stats".to_string(), INDEX.stats)]))
}

/// Return curated model catalog with download status.
pub fn models_catalog() -> () {
    // Return curated model catalog with download status.
    let mut tier = request.args.get(&"tier".to_string()).cloned();
    let mut tag = request.args.get(&"tag".to_string()).cloned();
    let mut catalog = MODEL_HUB.catalog(/* tier= */ tier, /* tag= */ tag);
    for m in catalog.iter() {
        m["downloaded".to_string()] = MODEL_HUB.is_downloaded(m["filename".to_string()]);
    }
    jsonify(catalog)
}

/// List locally available GGUF models.
pub fn models_local() -> () {
    // List locally available GGUF models.
    jsonify(MODEL_HUB.list_local())
}

/// Recommend models based on system RAM.
pub fn models_recommend() -> () {
    // Recommend models based on system RAM.
    // TODO: import psutil
    let mut ram_gb = (psutil.virtual_memory().total / (1024).pow(3 as u32));
    jsonify(HashMap::from([("ram_gb".to_string(), ((ram_gb as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("models".to_string(), MODEL_HUB.recommend(/* ram_gb= */ ram_gb))]))
}

/// Download a model. SSE stream with progress events.
/// 
/// Body: {"catalog_id": "llama-3.2-3b"}
/// OR: {"repo_id": "bartowski/...", "filename": "model.gguf"}
pub fn models_download() -> () {
    // Download a model. SSE stream with progress events.
    // 
    // Body: {"catalog_id": "llama-3.2-3b"}
    // OR: {"repo_id": "bartowski/...", "filename": "model.gguf"}
    let mut data = request.get_json(/* force= */ true);
    let mut catalog_id = data.get(&"catalog_id".to_string()).cloned();
    let mut repo_id = data.get(&"repo_id".to_string()).cloned();
    let mut filename = data.get(&"filename".to_string()).cloned();
    let generate = || {
        if catalog_id {
            let mut gen = MODEL_HUB.download_catalog(catalog_id);
        } else if (repo_id && filename) {
            let mut gen = MODEL_HUB.download(repo_id, filename);
        } else {
            /* yield format!("data: {}\n\n", serde_json::to_string(&HashMap::from([("status".to_string(), "error".to_string()), ("error".to_string(), "catalog_id or repo_id+filename required".to_string())])).unwrap()) */;
            /* yield "data: [DONE]\n\n".to_string() */;
            return;
        }
        for event in gen.iter() {
            /* yield format!("data: {}\n\n", serde_json::to_string(&event.to_dict()).unwrap()) */;
        }
        /* yield "data: [DONE]\n\n".to_string() */;
    };
    Response(stream_with_context(generate()), /* mimetype= */ "text/event-stream".to_string(), /* headers= */ HashMap::from([("Cache-Control".to_string(), "no-cache".to_string()), ("X-Accel-Buffering".to_string(), "no".to_string())]))
}

/// Check status of active downloads.
pub fn models_downloads_active() -> () {
    // Check status of active downloads.
    jsonify(MODEL_HUB.active_downloads)
}

/// Delete a local model file.
pub fn models_delete(filename: String) -> () {
    // Delete a local model file.
    if !filename.ends_with(&*".gguf".to_string()) {
        (jsonify(HashMap::from([("error".to_string(), "Only .gguf files can be deleted".to_string())])), 400)
    }
    let mut ok = MODEL_HUB.delete_model(filename);
    jsonify(HashMap::from([("deleted".to_string(), ok), ("filename".to_string(), filename)]))
}

/// Search HuggingFace for GGUF models.
pub fn models_search() -> Result<()> {
    // Search HuggingFace for GGUF models.
    let mut query = request.args.get(&"q".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    if !query {
        (jsonify(HashMap::from([("error".to_string(), "q parameter required".to_string())])), 400)
    }
    // try:
    {
        let mut limit = request.args.get(&"limit".to_string()).cloned().unwrap_or(MAX_SEARCH_K).to_string().parse::<i64>().unwrap_or(0).min(HF_SEARCH_LIMIT_MAX);
    }
    // except (ValueError, TypeError) as _e:
    let mut results = MODEL_HUB.search_hf(query, /* limit= */ limit);
    Ok(jsonify(results))
}

/// List GGUF files in a HuggingFace repo.
pub fn models_repo_files(repo_id: String) -> () {
    // List GGUF files in a HuggingFace repo.
    let mut files = MODEL_HUB.list_repo_files(repo_id);
    jsonify(HashMap::from([("repo_id".to_string(), repo_id), ("files".to_string(), files)]))
}

/// Check if llama-server binary is available.
pub fn llm_binary() -> () {
    // Check if llama-server binary is available.
    let mut binary = find_llama_server_binary();
    jsonify(HashMap::from([("found".to_string(), binary.is_some()), ("path".to_string(), binary)]))
}

/// List available .gguf models on disk.
pub fn llm_models() -> () {
    // List available .gguf models on disk.
    let mut models = discover_models();
    let mut default = pick_default_model(models);
    jsonify(HashMap::from([("models".to_string(), models), ("default".to_string(), if default { default["path".to_string()] } else { None })]))
}

/// Start llama-server with a chosen model + optimization flags.
pub fn llm_start() -> Result<()> {
    // Start llama-server with a chosen model + optimization flags.
    let mut data = request.get_json(/* force= */ true);
    let mut model_path = data.get(&"model_path".to_string()).cloned().unwrap_or("".to_string());
    // try:
    {
        let mut port = data.get(&"port".to_string()).cloned().unwrap_or(DEFAULT_LLAMA_PORT).to_string().parse::<i64>().unwrap_or(0);
        let mut gpu_layers = data.get(&"gpu_layers".to_string()).cloned().unwrap_or(-1).to_string().parse::<i64>().unwrap_or(0);
        let mut ctx_size = data.get(&"ctx_size".to_string()).cloned().unwrap_or(DEFAULT_CTX_SIZE).to_string().parse::<i64>().unwrap_or(0);
    }
    // except (ValueError, TypeError) as _e:
    let mut kv_cache_type_k = data.get(&"kv_cache_type_k".to_string()).cloned().unwrap_or("q8_0".to_string());
    let mut kv_cache_type_v = data.get(&"kv_cache_type_v".to_string()).cloned().unwrap_or("q8_0".to_string());
    let mut flash_attn = data.get(&"flash_attn".to_string()).cloned().unwrap_or("on".to_string());
    let mut mlock = (data.get(&"mlock".to_string()).cloned().unwrap_or(true) != 0);
    let mut cont_batching = (data.get(&"cont_batching".to_string()).cloned().unwrap_or(true) != 0);
    // try:
    {
        let mut cache_reuse = data.get(&"cache_reuse".to_string()).cloned().unwrap_or(256).to_string().parse::<i64>().unwrap_or(0);
        let mut slot_prompt_similarity = data.get(&"slot_prompt_similarity".to_string()).cloned().unwrap_or(0.5_f64).to_string().parse::<f64>().unwrap_or(0.0);
    }
    // except (ValueError, TypeError) as _e:
    if !model_path {
        let mut models = discover_models();
        let mut default = pick_default_model(models);
        if !default {
            (jsonify(HashMap::from([("error".to_string(), "No .gguf models found".to_string())])), 404)
        }
        let mut model_path = default["path".to_string()];
    }
    let _start = || {
        // try:
        {
            LLAMA.start(model_path, /* port= */ port, /* gpu_layers= */ gpu_layers, /* ctx_size= */ ctx_size, /* kv_cache_type_k= */ kv_cache_type_k, /* kv_cache_type_v= */ kv_cache_type_v, /* flash_attn= */ flash_attn, /* mlock= */ mlock, /* cont_batching= */ cont_batching, /* cache_reuse= */ cache_reuse, /* slot_prompt_similarity= */ slot_prompt_similarity);
            let mut cfg = _load_llm_config();
            cfg["base_url".to_string()] = LLAMA.base_url;
            cfg["api_key".to_string()] = "none".to_string();
            cfg["model".to_string()] = LLAMA.model_name;
            _save_llm_config(cfg);
            logger.info("LLM config auto-set to local llama-server".to_string());
        }
        // except Exception as exc:
    };
    std::thread::spawn(|| {});
    Ok(jsonify(HashMap::from([("starting".to_string(), true), ("model".to_string(), os::path.basename(model_path)), ("port".to_string(), port)])))
}

/// Stop llama-server.
pub fn llm_stop() -> () {
    // Stop llama-server.
    jsonify(LLAMA.stop())
}

/// Current llama-server status.
pub fn llm_status() -> () {
    // Current llama-server status.
    jsonify(LLAMA.status())
}

pub fn get_llm_config() -> () {
    jsonify(_get_llm_settings())
}

pub fn set_llm_config() -> () {
    let mut data = request.get_json(/* force= */ true);
    let mut cfg = _load_llm_config();
    for key in ("base_url".to_string(), "api_key".to_string(), "model".to_string(), "system_prompt".to_string()).iter() {
        if (data.contains(&key) && data[&key].is_some()) {
            cfg[key] = data[&key].trim().to_string();
        }
    }
    _save_llm_config(cfg);
    jsonify(HashMap::from([("ok".to_string(), true)]))
}

/// Quick LLM connectivity check (< 3 s timeout).
pub fn llm_health() -> Result<()> {
    // Quick LLM connectivity check (< 3 s timeout).
    let mut llm = _get_llm_settings();
    let mut api_url = (llm["base_url".to_string()].trim_end_matches(|c: char| "/".to_string().contains(c)).to_string() + "/models".to_string());
    // try:
    {
        let mut r = /* reqwest::get( */&api_url).cloned().unwrap_or(/* timeout= */ LLM_HEALTH_TIMEOUT);
        r.raise_for_status();
        jsonify(HashMap::from([("ok".to_string(), true), ("base_url".to_string(), llm["base_url".to_string()]), ("model".to_string(), llm["model".to_string()])]))
    }
    // except Exception as exc:
}

/// Turn a raw requests/connection exception into a short human message.
pub fn _friendly_llm_error(exc: Exception) -> String {
    // Turn a raw requests/connection exception into a short human message.
    let mut msg = exc.to_string();
    if (msg.contains(&"ConnectionRefusedError".to_string()) || msg.contains(&"10061".to_string())) {
        "LLM server is not running. Start it in Settings or configure a remote endpoint.".to_string()
    }
    if (msg.contains(&"MaxRetryError".to_string()) || msg.contains(&"Max retries".to_string())) {
        "Cannot reach LLM server — is the URL correct?".to_string()
    }
    if (msg.contains(&"Timeout".to_string()) || msg.contains(&"timed out".to_string())) {
        "LLM server timed out — it may be loading a model.".to_string()
    }
    if (msg.contains(&"401".to_string()) || msg.contains(&"403".to_string())) {
        "Authentication failed — check your API key.".to_string()
    }
    if msg.contains(&"404".to_string()) {
        "LLM endpoint not found — check the Base URL.".to_string()
    }
    format!("LLM error: {}", msg[..150])
}

/// Chat endpoint. Retrieves RAG context, sends to LLM, streams response.
/// 
/// Advanced RAG pipeline (zen_core_libs):
/// 1. QueryRouter classifies intent → adjusts retrieval strategy
/// 2. ZeroWasteCache checks for cached answer
/// 3. CorrectiveRAG grades retrieval, auto-corrects if weak
/// 4. Reranker re-orders results by relevance
/// 5. Score threshold + token budget filtering
/// 6. Chat history trimming
/// 7. HallucinationDetector checks LLM output (post-stream)
/// 8. MetricsTracker records latency / cache hits
pub fn chat() -> Result<()> {
    // Chat endpoint. Retrieves RAG context, sends to LLM, streams response.
    // 
    // Advanced RAG pipeline (zen_core_libs):
    // 1. QueryRouter classifies intent → adjusts retrieval strategy
    // 2. ZeroWasteCache checks for cached answer
    // 3. CorrectiveRAG grades retrieval, auto-corrects if weak
    // 4. Reranker re-orders results by relevance
    // 5. Score threshold + token budget filtering
    // 6. Chat history trimming
    // 7. HallucinationDetector checks LLM output (post-stream)
    // 8. MetricsTracker records latency / cache hits
    let mut data = request.get_json(/* force= */ true);
    let mut messages = data.get(&"messages".to_string()).cloned().unwrap_or(vec![]);
    if !messages {
        (jsonify(HashMap::from([("error".to_string(), "messages required".to_string())])), 400)
    }
    // try:
    {
        let mut rag_k = data.get(&"rag_k".to_string()).cloned().unwrap_or(DEFAULT_TOP_K).to_string().parse::<i64>().unwrap_or(0);
        let mut rag_score_threshold = data.get(&"rag_score_threshold".to_string()).cloned().unwrap_or(SCORE_THRESHOLD).to_string().parse::<f64>().unwrap_or(0.0);
    }
    // except (ValueError, TypeError) as _e:
    let mut llm = _get_llm_settings();
    let mut t_chat_start = time::monotonic();
    let mut CTX_BUDGET = 3072;
    let mut RAG_TOKEN_BUDGET = 1200;
    let mut CHARS_PER_TOKEN = 4;
    let mut last_user_msg = "".to_string();
    for m in messages.iter().rev().iter() {
        if m.get(&"role".to_string()).cloned() == "user".to_string() {
            let mut last_user_msg = m.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            break;
        }
    }
    let mut routing = if last_user_msg { ROUTER.route(last_user_msg) } else { None };
    let mut routed_k = if routing { routing::config::get(&"top_k".to_string()).cloned().unwrap_or(rag_k) } else { rag_k };
    let mut effective_k = rag_k.max(routed_k);
    let mut cached_answer = if last_user_msg { SEARCH_CACHE.get_answer(last_user_msg) } else { None };
    if cached_answer.is_some() {
        METRICS.increment("chat_cache_hits".to_string());
    }
    let mut rag_context = "".to_string();
    let mut rag_sources = vec![];
    let mut rag_timing = HashMap::new();
    let mut rag_filtered = 0;
    let mut crag_info = HashMap::new();
    if (last_user_msg && INDEX.is_built) {
        let (mut results, mut rag_timing) = INDEX.search_timed(last_user_msg, /* k= */ effective_k);
        if results {
            let mut chunk_dicts = results.iter().map(|r| HashMap::from([("text".to_string(), r.chunk.text), ("score".to_string(), r.score), ("source_url".to_string(), r.chunk.source_url), ("page_title".to_string(), r.chunk.page_title)])).collect::<Vec<_>>();
            let mut crag = CorrectiveRAG(/* retrieve_fn= */ |q, k| INDEX.search(q, /* k= */ k).iter().map(|r| HashMap::from([("text".to_string(), r.chunk.text), ("score".to_string(), r.score)])).collect::<Vec<_>>());
            let (mut grade, mut confidence) = crag._grade(last_user_msg, chunk_dicts);
            let mut crag_info = HashMap::from([("grade".to_string(), grade.value), ("confidence".to_string(), ((confidence as f64) * 10f64.powi(3)).round() / 10f64.powi(3))]);
            rag_timing["crag_grade".to_string()] = grade.value;
            rag_timing["crag_confidence".to_string()] = ((confidence as f64) * 10f64.powi(3)).round() / 10f64.powi(3);
        }
        if (results && (routing::is_none() || routing::config::get(&"rerank".to_string()).cloned().unwrap_or(true))) {
            let mut texts = results.iter().map(|r| r.chunk.text).collect::<Vec<_>>();
            let (mut reranked_texts, _) = RERANKER.rerank(last_user_msg, texts, /* top_k= */ effective_k, /* return_scores= */ true);
            let mut text_to_result = results.iter().map(|r| (r.chunk.text, r)).collect::<HashMap<_, _>>();
            let mut results = reranked_texts.iter().filter(|t| text_to_result.contains(&t)).map(|t| text_to_result[&t]).collect::<Vec<_>>();
        }
        if results {
            let mut strong = results.iter().filter(|r| r.score >= rag_score_threshold).map(|r| r).collect::<Vec<_>>();
            let mut rag_filtered = (results.len() - strong.len());
            let mut parts = vec![];
            let mut total_chars = 0;
            let mut max_rag_chars = (RAG_TOKEN_BUDGET * CHARS_PER_TOKEN);
            for r in strong.iter() {
                let mut chunk_text_str = format!("[{}] ({})\n{}", r.chunk.page_title, r.chunk.source_url, r.chunk.text);
                if (total_chars + chunk_text_str.len()) > max_rag_chars {
                    break;
                }
                parts.push(chunk_text_str);
                total_chars += chunk_text_str.len();
                rag_sources.push(HashMap::from([("title".to_string(), r.chunk.page_title), ("url".to_string(), r.chunk.source_url), ("score".to_string(), ((r.score as f64) * 10f64.powi(4)).round() / 10f64.powi(4))]));
            }
            let mut rag_context = parts.join(&"\n\n---\n\n".to_string());
        }
    }
    rag_timing["rag_filtered_weak".to_string()] = rag_filtered;
    rag_timing["rag_chunks_sent".to_string()] = rag_sources.len();
    rag_timing["rag_context_chars".to_string()] = rag_context.len();
    rag_timing["rag_context_est_tokens".to_string()] = (rag_context.len() / CHARS_PER_TOKEN);
    if routing {
        rag_timing["query_intent".to_string()] = routing::intent.value;
        rag_timing["intent_confidence".to_string()] = ((routing::confidence as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
    }
    let mut system_parts = vec![];
    if llm["system_prompt".to_string()] {
        system_parts.push(llm["system_prompt".to_string()]);
    } else {
        system_parts.push("You are a helpful assistant. Always respond in the same language as the user's question. Answer questions based on the provided context. If the context doesn't contain the answer, say so honestly. Always cite your sources when using the retrieved context.".to_string());
    }
    if rag_context {
        system_parts.push(format!("\n\n## Retrieved Context\n\n{}", rag_context));
    }
    let mut system_msg = HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_parts.join(&"\n".to_string()))]);
    let mut system_tokens = (system_msg["content".to_string()].len() / CHARS_PER_TOKEN);
    let mut remaining = (CTX_BUDGET - system_tokens);
    let mut trimmed_messages = vec![];
    let mut total_msg_chars = 0;
    for m in messages.iter().rev().iter() {
        let mut mc = m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len();
        if (total_msg_chars + mc) > (remaining * CHARS_PER_TOKEN) {
            break;
        }
        trimmed_messages.insert(0, m);
        total_msg_chars += mc;
    }
    if (!trimmed_messages && messages) {
        let mut trimmed_messages = vec![messages[-1]];
    }
    let mut history_trimmed = (messages.len() - trimmed_messages.len());
    rag_timing["history_trimmed".to_string()] = history_trimmed;
    rag_timing["history_sent".to_string()] = trimmed_messages.len();
    let generate = || {
        let mut full_response = vec![];
        // try:
        {
            let mut api_url = (llm["base_url".to_string()].trim_end_matches(|c: char| "/".to_string().contains(c)).to_string() + "/chat/completions".to_string());
            let mut resp = /* reqwest::post( */api_url, /* headers= */ HashMap::from([("Authorization".to_string(), format!("Bearer {}", llm["api_key".to_string()])), ("Content-Type".to_string(), "application/json".to_string())]), /* json= */ HashMap::from([("model".to_string(), llm["model".to_string()]), ("messages".to_string(), (vec![system_msg] + trimmed_messages)), ("stream".to_string(), true), ("temperature".to_string(), LLM_TEMPERATURE), ("max_tokens".to_string(), LLM_MAX_TOKENS)]), /* stream= */ true, /* timeout= */ LLM_STREAM_TIMEOUT);
            resp.raise_for_status();
            /* yield format!("data: {}\n\n", serde_json::to_string(&HashMap::from([("sources".to_string(), rag_sources), ("rag_timing".to_string(), rag_timing)])).unwrap()) */;
            for line in resp.iter_lines(/* decode_unicode= */ true).iter() {
                if (!line || !line.starts_with(&*"data: ".to_string())) {
                    continue;
                }
                let mut payload = line[6..];
                if payload.trim().to_string() == "[DONE]".to_string() {
                    break;
                }
                // try:
                {
                    let mut chunk = serde_json::from_str(&payload).unwrap();
                    let mut delta = chunk.get(&"choices".to_string()).cloned().unwrap_or(vec![HashMap::new()])[0].get(&"delta".to_string()).cloned().unwrap_or(HashMap::new());
                    let mut content = delta.get(&"content".to_string()).cloned();
                    if content {
                        full_response.push(content);
                        /* yield format!("data: {}\n\n", serde_json::to_string(&HashMap::from([("content".to_string(), content)])).unwrap()) */;
                    }
                }
                // except (json::JSONDecodeError, IndexError, KeyError) as _e:
            }
            let mut answer_text = full_response.join(&"".to_string());
            if (answer_text && rag_context) {
                let mut h_report = HALLUCINATION_DETECTOR.detect(answer_text, rag_context);
                let mut hallucination_info = HashMap::from([("score".to_string(), ((h_report.score as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("has_hallucinations".to_string(), h_report.has_hallucinations), ("findings".to_string(), h_report.findings[..MAX_HALLUCINATION_FINDINGS].iter().map(|f| HashMap::from([("type".to_string(), f.type.value), ("severity".to_string(), ((f.severity as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("text".to_string(), f.text[..100]), ("explanation".to_string(), f.explanation[..200])])).collect::<Vec<_>>())]);
                /* yield format!("data: {}\n\n", serde_json::to_string(&HashMap::from([("hallucination".to_string(), hallucination_info)])).unwrap()) */;
                METRICS.record("hallucination_score".to_string(), h_report.score);
            }
            if (answer_text && last_user_msg) {
                SEARCH_CACHE.put_answer(last_user_msg, answer_text);
            }
            let mut chat_ms = ((((time::monotonic() - t_chat_start) * 1000) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
            METRICS.record("chat_ms".to_string(), chat_ms);
            METRICS.increment("chat_total".to_string());
            /* yield "data: [DONE]\n\n".to_string() */;
        }
        // except Exception as exc:
    };
    Ok(Response(stream_with_context(generate()), /* mimetype= */ "text/event-stream".to_string(), /* headers= */ HashMap::from([("Cache-Control".to_string(), "no-cache".to_string()), ("X-Accel-Buffering".to_string(), "no".to_string())])))
}

/// Fan-out same question to all active pipelines, stream interleaved.
pub fn chat_compare() -> Result<()> {
    // Fan-out same question to all active pipelines, stream interleaved.
    let mut data = request.get_json(/* force= */ true);
    let mut messages = data.get(&"messages".to_string()).cloned().unwrap_or(vec![]);
    if !messages {
        (jsonify(HashMap::from([("error".to_string(), "messages required".to_string())])), 400)
    }
    let mut active_ids = _load_active_pipelines();
    let mut llm = _get_llm_settings();
    // try:
    {
        let mut rag_k = data.get(&"rag_k".to_string()).cloned().unwrap_or(DEFAULT_TOP_K).to_string().parse::<i64>().unwrap_or(0);
    }
    // except (ValueError, TypeError) as _e:
    let mut last_user_msg = "".to_string();
    for m in messages.iter().rev().iter() {
        if m.get(&"role".to_string()).cloned() == "user".to_string() {
            let mut last_user_msg = m["content".to_string()];
            break;
        }
    }
    let mut pipeline_data = HashMap::new();
    for pid in active_ids.iter() {
        if INDEX.is_built {
            let (mut ctx, mut sources, mut timing) = _pipeline_build_context(pid, last_user_msg, /* k= */ rag_k);
        } else {
            let (mut ctx, mut sources, mut timing) = ("".to_string(), vec![], HashMap::from([("pipeline".to_string(), pid), ("total_ms".to_string(), 0)]));
        }
        let mut sp = llm.get(&"system_prompt".to_string()).cloned().unwrap_or("".to_string());
        let mut sys_text = if sp { sp } else { "You are a helpful assistant. Always respond in the same language as the user's question. Answer based on the provided context. If the context doesn't contain the answer, say so.".to_string() };
        if ctx {
            sys_text += format!("\n\n## Retrieved Context\n\n{}", ctx);
        }
        pipeline_data[pid] = HashMap::from([("system_msg".to_string(), HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), sys_text)])), ("sources".to_string(), sources), ("timing".to_string(), timing)]);
    }
    let mut trimmed = _trim_history(messages);
    let mut q = queue.Queue();
    let _worker = |pid| {
        let mut pd = pipeline_data[&pid];
        let mut full_text = vec![];
        let mut t0 = time::monotonic();
        // try:
        {
            q.put(HashMap::from([("pipeline".to_string(), pid), ("sources".to_string(), pd["sources".to_string()]), ("timing".to_string(), pd["timing".to_string()])]));
            let mut resp = /* reqwest::post( */(llm["base_url".to_string()].trim_end_matches(|c: char| "/".to_string().contains(c)).to_string() + "/chat/completions".to_string()), /* headers= */ HashMap::from([("Authorization".to_string(), format!("Bearer {}", llm["api_key".to_string()])), ("Content-Type".to_string(), "application/json".to_string())]), /* json= */ HashMap::from([("model".to_string(), llm["model".to_string()]), ("messages".to_string(), (vec![pd["system_msg".to_string()]] + trimmed)), ("stream".to_string(), true), ("temperature".to_string(), LLM_TEMPERATURE), ("max_tokens".to_string(), LLM_MAX_TOKENS)]), /* stream= */ true, /* timeout= */ LLM_STREAM_TIMEOUT);
            resp.raise_for_status();
            for line in resp.iter_lines(/* decode_unicode= */ true).iter() {
                if (!line || !line.starts_with(&*"data: ".to_string())) {
                    continue;
                }
                let mut payload = line[6..].trim().to_string();
                if payload == "[DONE]".to_string() {
                    break;
                }
                // try:
                {
                    let mut chunk = serde_json::from_str(&payload).unwrap();
                    let mut content = chunk.get(&"choices".to_string()).cloned().unwrap_or(vec![HashMap::new()])[0].get(&"delta".to_string()).cloned().unwrap_or(HashMap::new()).get(&"content".to_string()).cloned();
                    if content {
                        full_text.push(content);
                        q.put(HashMap::from([("pipeline".to_string(), pid), ("content".to_string(), content)]));
                    }
                }
                // except (json::JSONDecodeError, IndexError, KeyError) as _e:
            }
            let mut answer = full_text.join(&"".to_string());
            let mut hallu = None;
            let mut cfg = PIPELINE_PRESETS[&pid];
            if (cfg["hallucination_check".to_string()] && answer && pd["sources".to_string()]) {
                let mut ctx_text = pd["system_msg".to_string()]["content".to_string()];
                let mut report = HALLUCINATION_DETECTOR.detect(answer, ctx_text);
                let mut hallu = HashMap::from([("score".to_string(), ((report.score as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("has_hallucinations".to_string(), report.has_hallucinations)]);
            }
            q.put(HashMap::from([("pipeline".to_string(), pid), ("done".to_string(), true), ("latency_ms".to_string(), ((((time::monotonic() - t0) * 1000) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("answer_length".to_string(), answer.len()), ("hallucination".to_string(), hallu)]));
        }
        // except Exception as e:
    };
    for pid in active_ids.iter() {
        std::thread::spawn(|| {});
    }
    let generate = || {
        let mut done = 0;
        let mut total = active_ids.len();
        let mut deadline = (time::monotonic() + PIPELINE_COMPARE_TIMEOUT);
        while done < total {
            if time::monotonic() > deadline {
                /* yield format!("data: {}\n\n", serde_json::to_string(&HashMap::from([("error".to_string(), "Pipeline comparison timed out".to_string()), ("done".to_string(), true)])).unwrap()) */;
                break;
            }
            // try:
            {
                let mut event = q.get(&/* timeout= */ 0.1_f64).cloned();
            }
            // except queue.Empty as _e:
            if event.get(&"done".to_string()).cloned() {
                done += 1;
            }
            /* yield format!("data: {}\n\n", serde_json::to_string(&event).unwrap()) */;
        }
        /* yield "data: [DONE]\n\n".to_string() */;
    };
    Ok(Response(stream_with_context(generate()), /* mimetype= */ "text/event-stream".to_string(), /* headers= */ HashMap::from([("Cache-Control".to_string(), "no-cache".to_string()), ("X-Accel-Buffering".to_string(), "no".to_string())])))
}
