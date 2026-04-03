use anyhow::{Result, Context};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;

pub const NUM_DOCS: i64 = 100;

pub const DOC_LENGTH: i64 = 2000;

pub static TEST_DIR: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());

pub const DB_PATH: &str = "TEST_DIR / 'rag_db";

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Generate random documents to simulate load.
pub fn generate_synthetic_data(num_docs: String, length: String) -> () {
    // Generate random documents to simulate load.
    let mut docs = vec![];
    logger.info(format!("Generating {} synthetic documents...", num_docs));
    for i in 0..num_docs.iter() {
        let mut text = random.choices((string.ascii_letters + (" ".to_string() * 10)), /* k= */ length).join(&"".to_string());
        if (i % 10) == 0 {
            text += " The secret password is BlueSky.".to_string();
        }
        docs.push(HashMap::from([("content".to_string(), text), ("url".to_string(), format!("http://fake.com/doc_{}", i)), ("title".to_string(), format!("Synthetic Doc {}", i))]));
    }
    docs
}

/// Run benchmark.
pub fn run_benchmark() -> () {
    // Run benchmark.
    if TEST_DIR.exists() {
        std::fs::remove_dir_all(TEST_DIR).ok();
    }
    TEST_DIR.create_dir_all();
    let mut docs = generate_synthetic_data(NUM_DOCS, DOC_LENGTH);
    let mut rag = LocalRAG(/* cache_dir= */ DB_PATH);
    logger.info("--- Starting Ingest Benchmark ---".to_string());
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    rag.build_index(docs);
    let mut end_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut ingest_duration = (end_time - start_time);
    let mut docs_per_sec = (NUM_DOCS / ingest_duration);
    rag.save(DB_PATH);
    let mut total_size = (DB_PATH.glob("**/*".to_string()).iter().filter(|f| f.is_file()).map(|f| f.stat().st_size).collect::<Vec<_>>().iter().sum::<i64>() / (1024 * 1024));
    logger.info(format!("Ingest Complete: {:.2}s", ingest_duration));
    logger.info(format!("Throughput: {:.2} docs/sec", docs_per_sec));
    logger.info(format!("Storage Size: {:.2} MB", total_size));
    logger.info("--- Starting Search Benchmark ---".to_string());
    let mut search_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut results = rag.search("secret password BlueSky".to_string(), /* k= */ 3);
    let mut search_end = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut search_latency = ((search_end - search_start) * 1000);
    logger.info(format!("Search Latency: {:.2} ms", search_latency));
    logger.info(format!("Found: {} results", results.len()));
    if results {
        logger.info(format!("Top Result Score: {:.4}", results[0].get(&"score".to_string()).cloned().unwrap_or(0)));
    }
    println!("\n=== BENCHMARK RESULTS (Baseline) ===");
    println!("Documents: {}", NUM_DOCS);
    println!("Total Time: {:.4} s", ingest_duration);
    println!("Throughput: {:.2} docs/s", docs_per_sec);
    println!("Search Latency: {:.2} ms", search_latency);
    println!("Storage: {:.2} MB", total_size);
    println!("{}", "====================================".to_string());
}
