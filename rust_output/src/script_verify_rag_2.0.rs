use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Helper: setup phase for test_rag_upgrade.
pub fn _do_test_rag_upgrade_setup() -> () {
    // Helper: setup phase for test_rag_upgrade.
    logger.info("🚀 Starting RAG 2.0 Verification".to_string());
    logger.info(format!("Target Model: {}", config::embedding_config.MODELS["balanced".to_string()]));
    logger.info(format!("Chunk Strategy: {}", config::rag.chunk_strategy));
    config::rag.chunk_strategy = "semantic".to_string();
    config::rag.embedding_model = "balanced".to_string();
    logger.info("Initializing LocalRAG (this may take time for model download)...".to_string());
    let mut rag = LocalRAG();
    logger.info("Testing Semantic Chunking...".to_string());
    let mut sample_text = "Artificial Intelligence is a broad field. Machine learning is a subset of AI. Deep learning uses neural networks. The quick brown fox jumps over the lazy dog. Baking cookies requires flour and sugar. Preheat the oven to 350 degrees.".to_string();
    let mut doc = HashMap::from([("content".to_string(), sample_text), ("title".to_string(), "AI and Cookies".to_string()), ("url".to_string(), "test://1".to_string())]);
    let mut chunks = rag.chunk_documents(vec![doc], /* chunk_size= */ 200, /* overlap= */ 0);
    for (i, c) in chunks.iter().enumerate().iter() {
        logger.info(format!("Chunk {}: {}... ({} chars)", i, c["text".to_string()][..50], c["text".to_string()].len()));
    }
    (chunks, rag)
}

/// Test rag upgrade.
pub fn test_rag_upgrade() -> () {
    // Test rag upgrade.
    let (mut chunks, mut rag) = _do_test_rag_upgrade_setup();
    if chunks.len() >= 2 {
        logger.info("✅ Semantic Chunking looks active (multiple chunks formed)".to_string());
    } else {
        logger.warning(format!("⚠️ Only {} chunks formed. Tune threshold?", chunks.len()));
    }
    logger.info("Testing Semantic Cache...".to_string());
    rag.cache::clear();
    rag.add_chunks(chunks);
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    rag.search("How to bake cookies?".to_string(), /* k= */ 1);
    let mut t1 = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
    logger.info(format!("Query 1 (Miss): {:.4}s", t1));
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    rag.search("Baking instruction".to_string(), /* k= */ 1);
    (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
    if rag.cache::_semantic_cache {
        logger.info(format!("Cache entries: {}", rag.cache::_semantic_cache.len()));
        logger.info("✅ Semantic Cache populated".to_string());
    } else {
        logger.error("❌ Semantic Cache EMPTY".to_string());
    }
    logger.info("✅ RAG 2.0 Verification Complete".to_string());
}
