use anyhow::{Result, Context};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Test qdrant flow.
pub fn test_qdrant_flow() -> () {
    // Test qdrant flow.
    let mut test_dir = PathBuf::from("./test_qdrant_db".to_string());
    if test_dir.exists() {
        // TODO: import shutil
        std::fs::remove_dir_all(test_dir).ok();
    }
    println!("{}", "🚀 Initializing Qdrant LocalRAG...".to_string());
    let mut rag = LocalRAG(/* cache_dir= */ test_dir);
    let mut docs = vec![HashMap::from([("content".to_string(), "The capital of France is Paris. It is a major European city and a global center for art, fashion, gastronomy and culture.".to_string()), ("title".to_string(), "Geography".to_string()), ("url".to_string(), "geo.com".to_string())]), HashMap::from([("content".to_string(), "ZenAI is a high-performance RAG assistant specializing in logic, coding, and advanced knowledge retrieval using vector databases.".to_string()), ("title".to_string(), "ZenAI Info".to_string()), ("url".to_string(), "zen.ai".to_string())]), HashMap::from([("content".to_string(), "Quantum computing uses qubits to represent data, allowing for much faster processing of complex problems than classical computers.".to_string()), ("title".to_string(), "Quantum".to_string()), ("url".to_string(), "science.net".to_string())])];
    println!("{}", "📥 Building index (Semantics + BM25)...".to_string());
    rag.build_index(docs);
    println!("{}", "🔍 Testing Semantic Search (Paris)...".to_string());
    let mut results = rag.search("What is the capital of France?".to_string());
    assert!(results.len() > 0);
    assert!(results[0]["text".to_string()].contains(&"Paris".to_string()));
    println!("✅ Semantic Search Passed. Score: {:.4}", results[0]["score".to_string()]);
    println!("{}", "🔄 Testing Hybrid Search (ZenAI Spezial)...".to_string());
    let mut results = rag.hybrid_search("ZenAI Assistant specializing in performance".to_string(), /* alpha= */ 0.5_f64);
    assert!(results.len() > 0);
    assert!(results[0]["text".to_string()].contains(&"ZenAI".to_string()));
    println!("✅ Hybrid Search Passed. Fusion Score: {:.4}", results[0]["fusion_score".to_string()]);
    println!("{}", "📊 Stats check...".to_string());
    let mut stats = rag.get_stats();
    println!("Stats: {}", stats);
    assert!(stats["total_chunks".to_string()] >= 3);
}
