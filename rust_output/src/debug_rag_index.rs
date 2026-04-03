use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::rag_pipeline::{LocalRAG};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Debug index.
pub fn debug_index() -> Result<()> {
    // Debug index.
    println!("📂 Loading RAG Index from: {}", config::rag_cache_dir);
    let mut rag = LocalRAG();
    let mut query = "CTO".to_string();
    println!("\n🔍 Searching for: '{}'", query);
    let mut results = rag.search(query, /* k= */ 10);
    if !results {
        println!("{}", "❌ No results found. Index might be empty or missing term.".to_string());
    } else {
        println!("✅ Found {} chunks:", results.len());
        for (i, res) in results.iter().enumerate().iter() {
            let mut content = res.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..200].replace(&*"\n".to_string(), &*" ".to_string());
            println!("[{}] Score: {:.4} | Source: {} | {}...", (i + 1), res.get(&"score".to_string()).cloned().unwrap_or(0), res.get(&"title".to_string()).cloned(), content);
        }
    }
    println!("\n🔍 Hybrid Search for: '{}'", query);
    // try:
    {
        let mut results = rag.hybrid_search(query, /* k= */ 10);
        for (i, res) in results.iter().enumerate().iter() {
            let mut content = res.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..200].replace(&*"\n".to_string(), &*" ".to_string());
            println!("[{}] Score: {:.4} | Source: {} | {}...", (i + 1), res.get(&"fusion_score".to_string()).cloned().unwrap_or(0), res.get(&"title".to_string()).cloned(), content);
        }
    }
    // except Exception as _e:
}
