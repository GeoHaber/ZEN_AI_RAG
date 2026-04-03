use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::rag_pipeline::{AsyncLocalRAG};
use crate::scraper::{WebsiteScraper};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Run verification.
pub async fn run_verification() -> () {
    // Run verification.
    println!("{}", ("=".to_string() * 60));
    println!("{}", "🕷️  WEBSITE RAG VERIFICATION START".to_string());
    println!("{}", ("=".to_string() * 60));
    println!("{}", "\n[1] Initializing Vector DB...".to_string());
    let mut rag = AsyncLocalRAG();
    println!("✅ RAG Initialized. Collection: {}", rag.collection_name);
    let mut target_url = "https://example.com".to_string();
    println!("\n[2] Scraping {}...", target_url);
    let mut scraper = WebsiteScraper(target_url);
    let mut result = asyncio.to_thread(scraper::scrape, /* max_pages= */ 1).await;
    if !result["success".to_string()] {
        println!("❌ Scraping Failed: {}", result.get(&"error".to_string()).cloned());
        return;
    }
    let mut docs = result["documents".to_string()];
    println!("✅ Scraped {} documents.", docs.len());
    println!("   - Title: {}", docs[0]["title".to_string()]);
    println!("   - Content Preview: {}...", docs[0]["content".to_string()][..50]);
    println!("{}", "\n[3] Ingesting to Qdrant...".to_string());
    rag.build_index_async(docs).await;
    println!("{}", "✅ Indexing Complete".to_string());
    println!("{}", "\n[4] Searching for content...".to_string());
    let mut query = "What is this domain for?".to_string();
    let mut results = rag.search_async(query, /* k= */ 3).await;
    println!("✅ Found {} matches.", results.len());
    for (i, r) in results.iter().enumerate().iter() {
        println!("   [{}] Score: {:.3} | Text: {}...", (i + 1), r["score".to_string()], r["text".to_string()][..60]);
        // pass
    }
    if results.iter().map(|r| r["text".to_string()].to_lowercase().contains(&"example".to_string())).collect::<Vec<_>>().iter().any(|v| *v) {
        println!("{}", "\n🎉 SUCCESS: Website content retrieved from RAG!".to_string());
    } else {
        println!("{}", "\n⚠️ WARNING: Content mismatch.".to_string());
    }
    println!("{}", ("=".to_string() * 60));
}
