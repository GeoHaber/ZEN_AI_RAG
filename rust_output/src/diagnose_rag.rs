/// diagnose_rag::py - End-to-End RAG Diagnostics

use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::rag_pipeline::{AsyncLocalRAG};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Test rag.
pub async fn test_rag() -> Result<()> {
    // Test rag.
    println!("{}", ("=".to_string() * 60));
    println!("{}", "🔍 RAG DIAGNOSTICS START".to_string());
    println!("{}", ("=".to_string() * 60));
    println!("{}", "[1] Initializing Pipeline...".to_string());
    // try:
    {
        let mut rag = AsyncLocalRAG();
        println!("{}", "✅ Pipeline Initialized".to_string());
    }
    // except Exception as _e:
    println!("{}", "\n[2] Checking Embeddings...".to_string());
    if rag.model {
        println!("✅ Transformer Loaded: {}", rag.model);
        // pass
    } else {
        println!("{}", "❌ Transformer NOT Loaded (Lazy Load pending?)".to_string());
    }
    println!("{}", "\n[3] Ingesting Test Document...".to_string());
    let mut test_text = "The secret code for the vault is 'Blue-Omega-99'. Do not share this.".to_string();
    // try:
    {
        let mut chunk = HashMap::from([("text".to_string(), test_text), ("title".to_string(), "Secret Doc".to_string()), ("url".to_string(), "internal://test".to_string())]);
        rag.add_chunks_async(vec![chunk]).await;
        println!("{}", "✅ Ingestion Triggered".to_string());
    }
    // except Exception as _e:
    println!("{}", "\n[4] Querying...".to_string());
    let mut query = "What is the secret code?".to_string();
    // try:
    {
        let mut results = rag.search_async(query, /* k= */ 3).await;
        println!("✅ Search returned {} results", results.len());
        let mut found = false;
        for r in results.iter() {
            let mut text = r.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            let mut score = r.get(&"score".to_string()).cloned().unwrap_or(0.0_f64);
            println!("   - Match ({:.3}): {}...", score, text[..50]);
            if text.contains(&"Blue-Omega-99".to_string()) {
                let mut found = true;
            }
        }
        if found {
            println!("{}", "\n🎉 SUCCESS: Secret code retrieved!".to_string());
        } else {
            println!("{}", "\n⚠️ FAILURE: Secret code NOT found in results.".to_string());
        }
    }
    // except Exception as _e:
    Ok(println!("{}", ("=".to_string() * 60)))
}
