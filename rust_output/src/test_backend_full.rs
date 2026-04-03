/// test_backend_full::py - Comprehensive Headless Backend Verification
/// Tests LLM Connectivity, RAG performance, and API stability.

use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use crate::config_system::{config, EMOJI};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::path::PathBuf;
use tokio;

pub static BASE_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

/// Test llm chat.
pub async fn test_llm_chat() -> Result<()> {
    // Test llm chat.
    println!("🔎 {} Testing LLM Chat Connectivity...", EMOJI["robot".to_string()]);
    let mut backend = AsyncZenAIBackend();
    // try:
    {
        let _ctx = backend;
        {
            println!("  - Sending 'Say HELLO' to {}", backend.api_url);
            let mut full_response = "".to_string();
            // async for
            while let Some(chunk) = backend.send_message_async("Say only the word HELLO".to_string()).next().await {
                full_response += chunk;
            }
            if full_response.contains(&"HELLO".to_string()) {
                println!("  ✅ Received: {}", repr(full_response));
                true
            }
            println!("  ❌ Failed to get expected response. Received: {}", repr(full_response));
            false
        }
    }
    // except Exception as e:
}

/// Test rag standalone.
pub fn test_rag_standalone() -> Result<()> {
    // Test rag standalone.
    println!("🔎 {} Testing RAG Indexing & Retrieval...", EMOJI["database".to_string()]);
    let mut test_cache = PathBuf::from("tests/rag_test_cache".to_string());
    if test_cache.exists() {
        // try:
        {
            // TODO: import shutil
            std::fs::remove_dir_all(test_cache).ok();
        }
        // except Exception as _e:
    }
    let mut rag = LocalRAG(/* cache_dir= */ test_cache);
    // try:
    {
        let mut docs = vec![HashMap::from([("url".to_string(), "test://secret-file".to_string()), ("title".to_string(), "Secret Doc".to_string()), ("content".to_string(), "The top secret password for the ZenAI system is 'PURPLE-ORANGUTAN-77'. This is located in the basement.".to_string())])];
        println!("{}", "  - Building Index...".to_string());
        rag.build_index(docs, /* filter_junk= */ false);
        println!("{}", "  - Querying 'What is the secret password?'...".to_string());
        let mut results = rag.search("What is the secret password?".to_string(), /* k= */ 1);
        if (results.len() > 0 && results[0]["text".to_string()].contains(&"PURPLE-ORANGUTAN".to_string())) {
            println!("  ✅ RAG Success: Found secret content");
            drop(rag);
            // TODO: import gc
            gc.collect();
            std::thread::sleep(std::time::Duration::from_secs_f64(1));
            true
        } else {
            println!("  ❌ RAG Failure: Could not find indexed content");
            false
        }
    }
    // except Exception as e:
    // finally:
        // try:
        {
            // TODO: import shutil
            if test_cache.exists() {
                std::fs::remove_dir_all(test_cache).ok();
            }
        }
        // except Exception as _e:
}

/// Test hub api.
pub fn test_hub_api() -> Result<()> {
    // Test hub api.
    println!("🔎 {} Testing Hub API Status...", EMOJI["web".to_string()]);
    let mut hub_url = format!("http://{}:{}", config::host, config::mgmt_port);
    // try:
    {
        let mut resp = /* reqwest::get( */&format!("{}/models/available", hub_url)).cloned().unwrap_or(/* timeout= */ 5);
        if resp.status_code == 200 {
            println!("  ✅ Hub API Online");
            true
        } else {
            println!("  ❌ Hub API returned status {}", resp.status_code);
            false
        }
    }
    // except Exception as _e:
}

/// Main.
pub async fn main() -> () {
    // Main.
    println!("{}", ("=".to_string() * 60));
    println!("{}", "🚀 ZENAI BACKEND HEADLESS VERIFICATION".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut results = HashMap::from([("LLM Chat".to_string(), test_llm_chat().await), ("RAG Logic".to_string(), test_rag_standalone()), ("Hub Status".to_string(), test_hub_api())]);
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    println!("{}", "📊 FINAL REPORT".to_string());
    println!("{}", ("=".to_string() * 60));
    let mut all_ok = true;
    for (test, passed) in results.iter().iter() {
        let mut status = if passed { "✅ PASSED".to_string() } else { "❌ FAILED".to_string() };
        println!("{:<20} : {}", test, status);
        if !passed {
            let mut all_ok = false;
        }
    }
    if all_ok {
        println!("{}", "\n✨ BACKEND IS STABLE AND READY FOR INTEGRATION ✨".to_string());
        std::process::exit(0);
    } else {
        println!("{}", "\n⚠️ BACKEND HAS ISSUES. FIX BEFORE INTEGRATION.".to_string());
        std::process::exit(1);
    }
}
