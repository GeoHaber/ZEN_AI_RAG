use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Test rag.
pub fn test_rag() -> Result<()> {
    // Test rag.
    // try:
    {
        // TODO: from config_system import config
        // TODO: from zena_mode.rag_pipeline import LocalRAG
        let mut rag_cache = (config::BASE_DIR / "rag_cache".to_string());
        logger.info(format!("Using RAG cache: {}", rag_cache));
        let mut rag = LocalRAG(/* cache_dir= */ rag_cache);
        let mut stats = rag.get_stats();
        logger.info(format!("RAG Stats: {}", stats));
        if stats.get(&"total_chunks".to_string()).cloned().unwrap_or(0) == 0 {
            logger.warning("No chunks found in RAG! Indexing a test document...".to_string());
            let mut test_docs = vec![HashMap::from([("title".to_string(), "ZenAI Info".to_string()), ("content".to_string(), "ZenAI is a professional AI assistant with advanced RAG capabilities and modular UI.".to_string()), ("url".to_string(), "https://zenai.local/info".to_string())])];
            rag.build_index(test_docs);
            logger.info("Indexing complete.".to_string());
            let mut stats = rag.get_stats();
            logger.info(format!("Updated RAG Stats: {}", stats));
        }
        let mut query = "What is ZenAI?".to_string();
        logger.info(format!("Searching for: '{}'", query));
        let mut results = rag.search(query, /* k= */ 3);
        if results {
            logger.info(format!("Found {} results:", results.len()));
            for (i, res) in results.iter().enumerate().iter() {
                logger.info(format!("[{}] Score: {}", i, res.get(&"score".to_string()).cloned().unwrap_or("N/A".to_string())));
                logger.info(format!("    Title: {}", res.get(&"title".to_string()).cloned()));
                logger.info(format!("    Text: {}...", res.get(&"text".to_string()).cloned()[..100]));
            }
        } else {
            logger.error("No results found for search!".to_string());
        }
        logger.info(format!("Hybrid Searching for: '{}'", query));
        let mut results = rag.hybrid_search(query, /* k= */ 3);
        if results {
            logger.info(format!("Found {} hybrid results.", results.len()));
        } else {
            logger.error("No hybrid results found!".to_string());
        }
    }
    // except Exception as e:
}
