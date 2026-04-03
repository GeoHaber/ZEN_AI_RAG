use anyhow::{Result, Context};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;

/// Create a temporary RAG instance for testing using tmp_path for isolation.
pub fn temp_rag(tmp_path: String) -> Result<()> {
    // Create a temporary RAG instance for testing using tmp_path for isolation.
    let mut test_dir = (tmp_path / "test_rag_hybrid".to_string());
    test_dir.create_dir_all();
    let mut rag = LocalRAG(/* cache_dir= */ test_dir);
    /* yield rag */;
    rag.close();
    if test_dir.exists() {
        // try:
        {
            std::fs::remove_dir_all(test_dir, /* ignore_errors= */ true).ok();
        }
        // except Exception as _e:
    }
}

/// Test that Hybrid Search (Vector + BM25) can find specific keywords
/// that might be diluted in a semantic embedding.
pub fn test_hybrid_search_precision(temp_rag: String) -> () {
    // Test that Hybrid Search (Vector + BM25) can find specific keywords
    // that might be diluted in a semantic embedding.
    let mut docs = vec![HashMap::from([("url".to_string(), "doc1".to_string()), ("title".to_string(), "General AI Discussion".to_string()), ("content".to_string(), "Artificial intelligence is a branch of computer science that aims to create intelligent machines.".to_string())]), HashMap::from([("url".to_string(), "doc2".to_string()), ("title".to_string(), "Technical Specs".to_string()), ("content".to_string(), "The system ID for this specific deployment is ZX-999-BETA. This key is used for authentication.".to_string())]), HashMap::from([("url".to_string(), "doc3".to_string()), ("title".to_string(), "Weather Report".to_string()), ("content".to_string(), "Today it is sunny with a high of 25 degrees Celsius. Perfect for outdoor activities.".to_string())])];
    temp_rag.build_index(docs, /* filter_junk= */ false);
    let mut query = "What is the status of ZX-999-BETA?".to_string();
    let mut vector_results = temp_rag.search(query, /* k= */ 1);
    println!("\nVector Top Result: {}", if vector_results { vector_results[0]["title".to_string()] } else { "None".to_string() });
    let mut hybrid_results = temp_rag.hybrid_search(query, /* k= */ 3, /* alpha= */ 0.5_f64);
    println!("{}", "\nHybrid Search Results (query):".to_string());
    for r in hybrid_results.iter() {
        println!("- {}: {} (Score: {:.4})", r["url".to_string()], r["title".to_string()], r["fusion_score".to_string()]);
        // pass
    }
    assert!(hybrid_results.len() > 0);
    assert!(hybrid_results[0]["url".to_string()] == "doc2".to_string());
    let mut tricky_query = "outdoor ZX-999-BETA".to_string();
    let mut results = temp_rag.hybrid_search(tricky_query, /* k= */ 3, /* alpha= */ 0.3_f64);
    println!("{}", "\nHybrid Search Results (tricky):".to_string());
    for r in results.iter() {
        println!("- {}: {} (Score: {:.4})", r["url".to_string()], r["title".to_string()], r["fusion_score".to_string()]);
        // pass
    }
    assert!(results[0]["url".to_string()] == "doc2".to_string());
}

/// Verify that Reciprocal Rank Fusion correctly merges results.
pub fn test_rrf_fusion_logic(temp_rag: String) -> () {
    // Verify that Reciprocal Rank Fusion correctly merges results.
    let mut docs = 0..10.iter().map(|i| HashMap::from([("url".to_string(), i.to_string()), ("title".to_string(), format!("Doc {}", i)), ("content".to_string(), format!("This is the full content of doc {} which is now long enough.", i))])).collect::<Vec<_>>();
    temp_rag.build_index(docs, /* filter_junk= */ false);
    let mut results = temp_rag.hybrid_search("content of doc 5".to_string(), /* k= */ 5);
    assert!(results.len() <= 5);
    assert!(results[0]["url".to_string()] == "5".to_string());
}
