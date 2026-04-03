use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use crate::rag_pipeline::{LocalRAG};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static QA_PAIRS: std::sync::LazyLock<Vec<Vec<String>>> = std::sync::LazyLock::new(|| Vec::new());

/// Run benchmark part 1.
pub fn _run_benchmark_part1() -> Result<()> {
    // Run benchmark part 1.
    let mut avg_score = (results.iter().map(|r| r["score".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / results.len());
    let mut avg_duration = (results.iter().map(|r| r["duration".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / results.len());
    let mut summary = HashMap::from([("timestamp".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()), ("avg_quality_score".to_string(), avg_score), ("avg_latency".to_string(), avg_duration), ("detailed_results".to_string(), results)]);
    let mut report_path = PathBuf::from("tests/quality_report.json".to_string());
    let mut f = File::create(report_path)?;
    {
        json::dump(summary, f, /* indent= */ 4);
    }
    logger.info(format!("\n🏆 Benchmark Complete!"));
    logger.info(format!("📊 AVG Quality: {:.2}", avg_score));
    logger.info(format!("⏱️ AVG Latency: {:.1}s", avg_duration));
    Ok(logger.info(format!("📄 Report saved to {}", report_path)))
}

/// Run benchmark.
pub async fn run_benchmark() -> Result<()> {
    // Run benchmark.
    logger.info("🚀 Starting ZenAI Quality Benchmark...".to_string());
    let mut backend = AsyncZenAIBackend();
    let mut rag = LocalRAG();
    let mut results = vec![];
    let _ctx = backend;
    {
        if !backend.health_check().await {
            logger.error("❌ Backend offline! Start 'python start_llm::py' first.".to_string());
            return;
        }
        for (question, reference) in QA_PAIRS.iter() {
            logger.info(format!("❓ Testing: {}", question));
            let mut final_prompt = question;
            // try:
            {
                logger.info(format!("[RAG] Searching knowledge base for: '{}...'", question[..30]));
                let mut relevant_chunks = rag.hybrid_search(question, /* k= */ 5, /* alpha= */ 0.5_f64);
                if relevant_chunks {
                    logger.info(format!("[RAG] Found {} chunks.", relevant_chunks.len()));
                    let mut context_parts = relevant_chunks.iter().map(|c| format!("Source: {}\n{}", c.get(&"title".to_string()).cloned().unwrap_or("Unknown".to_string()), c["text".to_string()])).collect::<Vec<_>>();
                    let mut context = context_parts.join(&"\n\n".to_string());
                    let mut final_prompt = format!("SOURCES:\n{}\n\nUSER QUESTION: {}\n\nANSWER:", context, question);
                }
            }
            // except Exception as re:
            let mut full_response = "".to_string();
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            // async for
            while let Some(chunk) = backend.send_message_async(final_prompt).next().await {
                full_response += chunk;
            }
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
            let mut ref_emb = rag.model.encode(vec![reference], /* normalize_embeddings= */ true)[0];
            let mut ans_emb = rag.model.encode(vec![full_response], /* normalize_embeddings= */ true)[0];
            // TODO: import numpy as np
            let mut similarity = np.dot(ref_emb, ans_emb);
            logger.info(format!("✅ Score: {:.2} | Time: {:.1}s", similarity, duration));
            results.push(HashMap::from([("question".to_string(), question), ("response".to_string(), full_response), ("score".to_string(), similarity.to_string().parse::<f64>().unwrap_or(0.0)), ("duration".to_string(), duration)]));
        }
    }
    Ok(_run_benchmark_part1())
}
