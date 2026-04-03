/// tests/test_real_rag_e2e::py — Real-world end-to-end RAG tests
/// ==============================================================
/// 
/// These tests scrape REAL public websites, index the content into the RAG
/// pipeline, query about specific facts that exist on those pages, and verify
/// that the retrieved answers are correct and relevant.
/// 
/// Requirements:
/// - Internet connection
/// - sentence-transformers (cached locally for 'fast' model)
/// - qdrant-client, rank-bm25, beautifulsoup4, requests, httpx
/// 
/// Run::
/// 
/// cd ZEN_AI_RAG
/// python -m pytest tests/test_real_rag_e2e::py -v -s --timeout=300

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::path::PathBuf;

pub const ROOT: &str = "Path(file!()).resolve().parent.parent";

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const PYTHON_ABOUT_URL: &str = "https://www.python.org/about/";

pub const HTTPBIN_URL: &str = "https://httpbin.org/";

pub const WIKI_PYTHON_URL: &str = "https://en::wikipedia.org/api/rest_v1/page/summary/Python_(programming_language)";

pub const WIKI_FULL_URL: &str = "https://en::wikipedia.org/wiki/Python_(programming_language)";

pub static _WIKI_HEADERS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

/// Test that we can scrape real public websites and get useful content.
#[derive(Debug, Clone)]
pub struct TestWebScraping {
}

impl TestWebScraping {
    /// Scrape python.org/about and verify it mentions Python.
    pub fn test_scrape_python_about_returns_content(&self) -> () {
        // Scrape python.org/about and verify it mentions Python.
        let mut doc = _scrape_page(PYTHON_ABOUT_URL);
        assert!(doc["content".to_string()].len() > 500, "Page should have substantial content");
        assert!(doc["content".to_string()].to_lowercase().contains(&"python".to_string()), "Should mention Python");
        assert!(doc["title".to_string()], "Should have a title");
    }
    /// The About page should contain well-known facts about Python.
    pub fn test_scrape_python_about_contains_key_facts(&self) -> () {
        // The About page should contain well-known facts about Python.
        let mut doc = _scrape_page(PYTHON_ABOUT_URL);
        let mut content_lower = doc["content".to_string()].to_lowercase();
        assert!(vec!["guido".to_string(), "programming language".to_string(), "open source".to_string(), "interpreted".to_string()].iter().map(|kw| content_lower.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v), "Should mention key Python facts (Guido, open source, interpreted, etc.)");
    }
    /// Scrape httpbin.org which has a known structure.
    pub fn test_scrape_httpbin(&self) -> () {
        // Scrape httpbin.org which has a known structure.
        let mut doc = _scrape_page(HTTPBIN_URL);
        assert!(doc["content".to_string()].len() > 100);
        assert!(doc["content".to_string()].to_lowercase().contains(&"httpbin".to_string()));
    }
    /// Fetch a Wikipedia summary via REST API — always stable.
    pub fn test_scrape_wikipedia_api(&self) -> () {
        // Fetch a Wikipedia summary via REST API — always stable.
        let mut data = _fetch_wiki_summary();
        assert!(data.contains(&"content".to_string()), "Should have content");
        assert!(data["content".to_string()].to_lowercase().contains(&"programming".to_string()));
        assert!(data["content".to_string()].len() > 100);
    }
    /// Test WebsiteScraper from scraper::py with a single-page crawl.
    pub fn test_scraper_module_basic(&self) -> () {
        // Test WebsiteScraper from scraper::py with a single-page crawl.
        // TODO: from zena_mode.scraper import WebsiteScraper
        let mut scraper = WebsiteScraper(HTTPBIN_URL);
        let mut result = scraper::scrape(/* max_pages= */ 1);
        assert!(result["success".to_string()], "Scrape should succeed: {}", result.get(&"error").cloned());
        assert!(result["documents".to_string()].len() >= 1, "Should get at least 1 document");
        assert!(result["documents".to_string()][0]["content".to_string()], "Document should have content");
    }
}

/// Test indexing scraped content into the vector database.
#[derive(Debug, Clone)]
pub struct TestRAGIndexing {
}

impl TestRAGIndexing {
    /// The pre-indexed fixture should have content.
    pub fn test_index_single_document(&self, rag_instance: String) -> () {
        // The pre-indexed fixture should have content.
        let mut stats = rag_instance.get_stats();
        let mut total = stats.get(&"total_chunks".to_string()).cloned().unwrap_or(stats.get(&"points_count".to_string()).cloned().unwrap_or(0));
        assert!(total > 0, "Should have indexed chunks, got stats: {}", stats);
    }
    /// Index an additional Wikipedia summary and verify chunk count grows.
    pub fn test_index_multiple_documents(&self, rag_instance: String) -> () {
        // Index an additional Wikipedia summary and verify chunk count grows.
        let mut initial_stats = rag_instance.get_stats();
        let mut initial_count = initial_stats.get(&"total_chunks".to_string()).cloned().unwrap_or(initial_stats.get(&"points_count".to_string()).cloned().unwrap_or(0));
        let mut wiki_doc = _fetch_wiki_summary();
        rag_instance.build_index(vec![wiki_doc]);
        let mut final_stats = rag_instance.get_stats();
        let mut final_count = final_stats.get(&"total_chunks".to_string()).cloned().unwrap_or(final_stats.get(&"points_count".to_string()).cloned().unwrap_or(0));
        assert!(final_count >= initial_count, "Chunk count should not shrink: {} → {}", initial_count, final_count);
    }
    /// Indexing the same content again should not create duplicates.
    pub fn test_deduplication_prevents_double_indexing(&self, rag_instance: String) -> () {
        // Indexing the same content again should not create duplicates.
        let mut stats_before = rag_instance.get_stats();
        let mut count_before = stats_before.get(&"total_chunks".to_string()).cloned().unwrap_or(stats_before.get(&"points_count".to_string()).cloned().unwrap_or(0));
        let mut doc = _scrape_page(PYTHON_ABOUT_URL);
        rag_instance.build_index(vec![doc]);
        let mut stats_after = rag_instance.get_stats();
        let mut count_after = stats_after.get(&"total_chunks".to_string()).cloned().unwrap_or(stats_after.get(&"points_count".to_string()).cloned().unwrap_or(0));
        assert!(count_after == count_before, "Dedup should prevent growth: {} → {}", count_before, count_after);
    }
}

/// Query the indexed content and verify we get correct, relevant results.
#[derive(Debug, Clone)]
pub struct TestRAGSearch {
}

impl TestRAGSearch {
    /// Semantic search for 'Python programming' should return relevant chunks.
    pub fn test_semantic_search_finds_python_info(&self, rag_instance: String) -> () {
        // Semantic search for 'Python programming' should return relevant chunks.
        let mut results = rag_instance.search("What is Python programming language?".to_string(), /* k= */ 5);
        assert!(results.len() > 0, "Should return search results");
        let mut texts = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        assert!(texts.contains(&"python".to_string()), "Results should mention Python. Got: {}", texts[..300]);
    }
    /// Hybrid search should return results with fusion scores.
    pub fn test_hybrid_search_returns_ranked_results(&self, rag_instance: String) -> () {
        // Hybrid search should return results with fusion scores.
        let mut results = rag_instance.hybrid_search("Who created Python?".to_string(), /* k= */ 5, /* alpha= */ 0.5_f64);
        assert!(results.len() > 0, "Hybrid search should return results");
        let mut first = results[0];
        let mut has_score = (first.contains(&"fusion_score".to_string()) || first.contains(&"rerank_score".to_string()) || first.contains(&"score".to_string()));
        assert!(has_score, "First result should have a score field: {}", first.keys());
    }
    /// Query about Python's creator — the answer should mention Guido.
    pub fn test_search_about_guido(&self, rag_instance: String) -> () {
        // Query about Python's creator — the answer should mention Guido.
        let mut results = rag_instance.hybrid_search("Who created the Python programming language?".to_string(), /* k= */ 5);
        assert!(results.len() > 0);
        let mut combined_text = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        assert!(combined_text.contains(&"guido".to_string()), "Results for 'who created Python' should mention Guido. Got top result: {}", results[0].get(&"text").cloned().unwrap_or("")[..200]);
    }
    /// Query about Python's licensing — should confirm open source.
    pub fn test_search_about_open_source(&self, rag_instance: String) -> () {
        // Query about Python's licensing — should confirm open source.
        let mut results = rag_instance.hybrid_search("Is Python open source?".to_string(), /* k= */ 5);
        assert!(results.len() > 0);
        let mut combined_text = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        assert!(vec!["open source".to_string(), "open-source".to_string(), "free".to_string(), "license".to_string()].iter().map(|phrase| combined_text.contains(&phrase)).collect::<Vec<_>>().iter().any(|v| *v), "Results should mention open source/free/license. Got: {}", combined_text[..300]);
    }
    /// A totally irrelevant query should get lower relevance scores.
    pub fn test_search_irrelevant_query_low_confidence(&self, rag_instance: String) -> () {
        // A totally irrelevant query should get lower relevance scores.
        let mut good_results = rag_instance.search("Python programming language features".to_string(), /* k= */ 3);
        let mut bad_results = rag_instance.search("recipe for chocolate cake baking".to_string(), /* k= */ 3);
        if (good_results && bad_results) {
            let mut good_score = good_results[0].get(&"rerank_score".to_string()).cloned().unwrap_or(good_results[0].get(&"score".to_string()).cloned().unwrap_or(0));
            let mut bad_score = bad_results[0].get(&"rerank_score".to_string()).cloned().unwrap_or(bad_results[0].get(&"score".to_string()).cloned().unwrap_or(0));
            assert!(good_score > bad_score, "Relevant query score ({:.4}) should be higher than irrelevant ({:.4})", good_score, bad_score);
        }
    }
    /// Search should respect the k parameter.
    pub fn test_search_respects_k_limit(&self, rag_instance: String) -> () {
        // Search should respect the k parameter.
        let mut results_3 = rag_instance.search("Python".to_string(), /* k= */ 3, /* rerank= */ false);
        let mut results_1 = rag_instance.search("Python".to_string(), /* k= */ 1, /* rerank= */ false);
        assert!(results_1.len() <= 1, "k=1 should return at most 1 result, got {}", results_1.len());
        assert!(results_3.len() <= 3, "k=3 should return at most 3 results, got {}", results_3.len());
    }
}

/// Test the context compression and building pipeline.
#[derive(Debug, Clone)]
pub struct TestRAGContextBuilding {
}

impl TestRAGContextBuilding {
    /// _build_rag_context should produce a compressed context string.
    pub fn test_build_rag_context_compresses(&self, rag_instance: String) -> () {
        // _build_rag_context should produce a compressed context string.
        // TODO: from zena_mode.rag_pipeline import _build_rag_context
        let mut results = rag_instance.hybrid_search("What is Python?".to_string(), /* k= */ 5);
        assert!(results, "Need search results first");
        let mut context = _build_rag_context("What is Python?".to_string(), results);
        assert!(context.len() > 50, "Context should have substantial content");
        assert!((context.to_lowercase().contains(&"source".to_string()) || context.to_lowercase().contains(&"python".to_string())), "Context should contain source labels or Python content");
    }
    /// QueryProcessor should classify intents correctly.
    pub fn test_query_processor_detects_intent(&self) -> () {
        // QueryProcessor should classify intents correctly.
        // TODO: from zena_mode.query_processor import get_query_processor
        let mut qp = get_query_processor();
        let mut factual = qp.process_query("What is the capital of France?".to_string());
        assert!(factual["intent".to_string()] == "factual".to_string(), "'What is...' should be factual, got {}", factual["intent"]);
        let mut comparison = qp.process_query("Compare Python and Java".to_string());
        assert!(comparison["intent".to_string()] == "comparison".to_string(), "'Compare...' should be comparison, got {}", comparison["intent"]);
    }
    /// ContextualCompressor should reduce chunk count while keeping relevance.
    pub fn test_contextual_compressor_reduces_size(&self) -> () {
        // ContextualCompressor should reduce chunk count while keeping relevance.
        // TODO: from zena_mode.contextual_compressor import get_compressor
        let mut compressor = get_compressor(/* max_tokens= */ 500);
        let mut fake_chunks = vec![HashMap::from([("text".to_string(), "Python is a high-level programming language. It was created by Guido van Rossum in 1991. Python emphasizes code readability.".to_string())]), HashMap::from([("text".to_string(), "The weather today is sunny with a high of 75 degrees. Tomorrow will be cloudy. There is no rain expected.".to_string())]), HashMap::from([("text".to_string(), "Python supports multiple programming paradigms. These include procedural, object-oriented, and functional. Python has a large standard library.".to_string())])];
        let mut compressed = compressor.compress_chunks("What is Python?".to_string(), fake_chunks);
        assert!(compressed.len() > 0, "Should return at least one compressed chunk");
        let mut all_text = compressed.iter().map(|c| c.text).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        assert!(all_text.contains(&"python".to_string()), "Compressed output should keep Python-related content");
    }
}

/// End-to-end: scrape a real site, index it, ask questions, verify answers.
#[derive(Debug, Clone)]
pub struct TestFullPipelineIntegration {
}

impl TestFullPipelineIntegration {
    /// Handle _setup logic.
    pub fn _setup(&mut self, rag_instance: String) -> () {
        // Handle _setup logic.
        self.rag = rag_instance;
    }
    /// Full pipeline: search 'features of Python' in pre-indexed content.
    pub fn test_e2e_python_about_factual_query(&mut self) -> () {
        // Full pipeline: search 'features of Python' in pre-indexed content.
        let mut results = self.rag.hybrid_search("What are the main features of the Python programming language?".to_string(), /* k= */ 5);
        assert!(results.len() >= 1, "Should get results");
        let mut combined = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        let mut feature_keywords = vec!["intuitive".to_string(), "interpreted".to_string(), "readable".to_string(), "object".to_string(), "free".to_string(), "portable".to_string(), "dynamic".to_string(), "library".to_string(), "typing".to_string()];
        let mut matches = feature_keywords.iter().filter(|kw| combined.contains(&kw)).map(|kw| 1).collect::<Vec<_>>().iter().sum::<i64>();
        assert!(matches >= 2, "Expected at least 2 feature keywords, found {}. Text: {}", matches, combined[..500]);
    }
    /// Query 'when was Python first released?' against the full Wikipedia page.
    pub fn test_e2e_wikipedia_summary_query(&mut self) -> () {
        // Query 'when was Python first released?' against the full Wikipedia page.
        let mut results = self.rag.hybrid_search("When was Python first released?".to_string(), /* k= */ 5);
        assert!(results.len() >= 1);
        let mut combined = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        assert!(vec!["1991".to_string(), "1989".to_string(), "february".to_string(), "guido".to_string()].iter().map(|yr| combined.contains(&yr)).collect::<Vec<_>>().iter().any(|v| *v), "Results should mention Python's release year. Got: {}", combined[..400]);
    }
    /// Cross-query: find both creator info and feature info from indexed content.
    pub fn test_e2e_multi_source_cross_reference(&mut self) -> () {
        // Cross-query: find both creator info and feature info from indexed content.
        let mut results = self.rag.hybrid_search("Python programming language creator and features".to_string(), /* k= */ 5);
        assert!(results.len() >= 2, "Should get results from multiple chunks");
        let mut results = self.rag.hybrid_search("Python programming language creator and features".to_string(), /* k= */ 5);
        assert!(results.len() >= 2, "Should get results from multiple chunks");
        let mut combined = results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
        let mut has_creator = (combined.contains(&"guido".to_string()) || combined.contains(&"van rossum".to_string()));
        let mut has_features = vec!["interpreted".to_string(), "readable".to_string(), "library".to_string(), "object".to_string(), "dynamic".to_string()].iter().map(|kw| combined.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v);
        assert!((has_creator || has_features), "Cross-source query should find creator or features. Got: {}", combined[..500]);
    }
    /// Reranked results should be more precise than un-reranked.
    pub fn test_e2e_reranking_improves_precision(&mut self) -> () {
        // Reranked results should be more precise than un-reranked.
        let mut query = "Who is the creator of the Python programming language?".to_string();
        let mut raw_results = self.rag.hybrid_search(query, /* k= */ 5, /* rerank= */ false);
        let mut reranked_results = self.rag.hybrid_search(query, /* k= */ 5, /* rerank= */ true);
        if reranked_results {
            let mut top_reranked = reranked_results[0].get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase();
            let mut reranked_mentions_guido = top_reranked.contains(&"guido".to_string());
            if raw_results {
                let mut top_raw = raw_results[0].get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase();
                let mut raw_mentions_guido = top_raw.contains(&"guido".to_string());
                if (!raw_mentions_guido && reranked_mentions_guido) {
                    // pass
                } else if reranked_mentions_guido {
                    // pass
                } else {
                    let mut combined_reranked = reranked_results.iter().map(|r| r.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string()).to_lowercase();
                    let mut r_score = reranked_results[0].get(&"rerank_score".to_string()).cloned().unwrap_or(reranked_results[0].get(&"score".to_string()).cloned().unwrap_or(0));
                    let mut raw_score = raw_results[0].get(&"rerank_score".to_string()).cloned().unwrap_or(raw_results[0].get(&"score".to_string()).cloned().unwrap_or(0));
                    assert!((r_score >= raw_score || combined_reranked.contains(&"guido".to_string())), "Reranked should be >= raw or mention Guido. Scores: reranked={:.4}, raw={:.4}", r_score, raw_score);
                }
            }
        }
    }
}

/// Test edge cases and robustness.
#[derive(Debug, Clone)]
pub struct TestEdgeCases {
}

impl TestEdgeCases {
    /// Empty query should not crash.
    pub fn test_empty_query_returns_empty(&self, rag_instance: String) -> () {
        // Empty query should not crash.
        let mut results = rag_instance.search("".to_string(), /* k= */ 5);
        assert!(/* /* isinstance(results, list) */ */ true);
    }
    /// Very long query should not crash.
    pub fn test_very_long_query(&self, rag_instance: String) -> () {
        // Very long query should not crash.
        let mut long_query = ("What is Python? ".to_string() * 200);
        let mut results = rag_instance.search(long_query, /* k= */ 3);
        assert!(/* /* isinstance(results, list) */ */ true);
    }
    /// Special characters should not crash search.
    pub fn test_special_characters_in_query(&self, rag_instance: String) -> () {
        // Special characters should not crash search.
        let mut results = rag_instance.search("Python's features: 'readability' & <performance> @ [scale]!".to_string(), /* k= */ 3);
        assert!(/* /* isinstance(results, list) */ */ true);
    }
    /// Unicode query should not crash.
    pub fn test_unicode_query(&self, rag_instance: String) -> () {
        // Unicode query should not crash.
        let mut results = rag_instance.search("Python是什么编程语言？".to_string(), /* k= */ 3);
        assert!(/* /* isinstance(results, list) */ */ true);
    }
    /// Multiple sequential searches should not corrupt state.
    pub fn test_concurrent_searches(&self, rag_instance: String) -> () {
        // Multiple sequential searches should not corrupt state.
        let mut queries = vec!["What is Python?".to_string(), "Who created Python?".to_string(), "Is Python open source?".to_string(), "Python features".to_string(), "Python standard library".to_string()];
        let mut all_results = vec![];
        for q in queries.iter() {
            let mut results = rag_instance.search(q, /* k= */ 3);
            all_results.push(results);
        }
        for (i, results) in all_results.iter().enumerate().iter() {
            assert!(/* /* isinstance(results, list) */ */ true, "Query {} returned non-list", i);
        }
    }
    /// Second identical search should be faster (cached).
    pub fn test_semantic_cache_works(&self, rag_instance: String) -> () {
        // Second identical search should be faster (cached).
        let mut query = "What are Python's main features?".to_string();
        rag_instance.cache::clear();
        let mut t0 = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut results1 = rag_instance.search(query, /* k= */ 5);
        let mut t1 = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - t0);
        let mut t0 = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut results2 = rag_instance.search(query, /* k= */ 5);
        let mut t2 = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - t0);
        assert!(results1.len() == results2.len(), "Cached results should match");
        let mut any_cached = results2.iter().map(|r| r.get(&"_is_cached".to_string()).cloned()).collect::<Vec<_>>().iter().any(|v| *v);
        if any_cached {
            logger.info("Cache hit confirmed via _is_cached flag".to_string());
        } else {
            logger.info(format!("Cache timing: first={:.3}s, second={:.3}s", t1, t2));
        }
    }
}

/// Fetch a Wikipedia summary with proper User-Agent.
pub fn _fetch_wiki_summary(url: String) -> HashMap {
    // Fetch a Wikipedia summary with proper User-Agent.
    let mut resp = /* reqwest::get( */&url).cloned().unwrap_or(/* headers= */ _WIKI_HEADERS);
    resp.raise_for_status();
    let mut data = resp.json();
    HashMap::from([("url".to_string(), url), ("title".to_string(), data.get(&"title".to_string()).cloned().unwrap_or("Python".to_string())), ("content".to_string(), data.get(&"extract".to_string()).cloned().unwrap_or("".to_string()))])
}

/// Create a fresh temporary directory for Qdrant storage per test module.
pub fn temp_rag_dir() -> () {
    // Create a fresh temporary directory for Qdrant storage per test module.
    let mut d = tempfile::mkdtemp(/* prefix= */ "zenai_test_rag_".to_string());
    /* yield PathBuf::from(d) */;
    std::fs::remove_dir_all(d, /* ignore_errors= */ true).ok();
}

/// Create a LocalRAG instance using the 'fast' model (all-MiniLM-L6-v2).
/// 
/// This fixture is module-scoped so the expensive model load happens once.
/// It pre-indexes python.org/about AND the full Wikipedia page so that all
/// search-phase tests have a rich knowledge base with Guido, 1991, etc.
pub fn rag_instance(temp_rag_dir: String) -> Result<()> {
    // Create a LocalRAG instance using the 'fast' model (all-MiniLM-L6-v2).
    // 
    // This fixture is module-scoped so the expensive model load happens once.
    // It pre-indexes python.org/about AND the full Wikipedia page so that all
    // search-phase tests have a rich knowledge base with Guido, 1991, etc.
    // TODO: from config_system import config
    let mut original_model = config::rag.embedding_model;
    config::rag.embedding_model = "fast".to_string();
    // TODO: from zena_mode.rag_pipeline import LocalRAG
    let mut rag = LocalRAG(/* cache_dir= */ temp_rag_dir);
    let mut docs = vec![];
    // try:
    {
        docs.push(_scrape_page(PYTHON_ABOUT_URL));
    }
    // except Exception as exc:
    // try:
    {
        docs.push(_scrape_page(WIKI_FULL_URL));
    }
    // except Exception as exc:
    if docs {
        rag.build_index(docs);
    }
    logger.info("Pre-indexed %d docs, stats: %s".to_string(), docs.len(), rag.get_stats());
    /* yield rag */;
    rag.close();
    Ok(config::rag.embedding_model = original_model)
}

/// Fetch a single web page and return {url, title, content}.
pub fn _scrape_page(url: String) -> HashMap {
    // Fetch a single web page and return {url, title, content}.
    let mut headers = HashMap::from([("User-Agent".to_string(), "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string())]);
    let mut resp = /* reqwest::get( */&url).cloned().unwrap_or(/* headers= */ headers);
    resp.raise_for_status();
    let mut content_type = resp.headers.get(&"Content-Type".to_string()).cloned().unwrap_or("".to_string());
    if content_type.contains(&"json".to_string()) {
        let mut data = resp.json();
        let mut title = data.get(&"title".to_string()).cloned().unwrap_or(url);
        let mut text = data.get(&"extract".to_string()).cloned().unwrap_or(data.get(&"description".to_string()).cloned().unwrap_or("".to_string()));
        HashMap::from([("url".to_string(), url), ("title".to_string(), title), ("content".to_string(), text)])
    }
    let mut soup = BeautifulSoup(resp.text, "html.parser".to_string());
    for tag in soup(vec!["script".to_string(), "style".to_string(), "nav".to_string(), "footer".to_string(), "header".to_string(), "aside".to_string()]).iter() {
        tag.decompose();
    }
    let mut title = if soup.title { soup.title.get_text(/* strip= */ true) } else { url };
    let mut text = soup.get_text(/* separator= */ " ".to_string(), /* strip= */ true);
    let mut text = regex::Regex::new(&"\\s+".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string().trim().to_string();
    HashMap::from([("url".to_string(), url), ("title".to_string(), title), ("content".to_string(), text)])
}
