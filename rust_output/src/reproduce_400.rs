use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use crate::rag_pipeline::{LocalRAG};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static STRESS_TESTS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

/// Reproduce.
pub async fn reproduce() -> Result<()> {
    // Reproduce.
    logger.info("🧪 Starting Stress Test...".to_string());
    let mut backend = AsyncZenAIBackend();
    let _ctx = backend;
    {
        for (name, prompt) in STRESS_TESTS.iter() {
            logger.info(format!("\n⚡ Testing: {}", name));
            let mut char_count = prompt.len();
            logger.info(format!("📏 Size: {} chars", char_count));
            // try:
            {
                let mut response_text = "".to_string();
                let mut got_400 = false;
                // async for
                while let Some(chunk) = backend.send_message_async(prompt).next().await {
                    if chunk.contains(&"Server returned 400".to_string()) {
                        logger.error(format!("❌ CAUGHT 400 ERROR on {}: {}", name, chunk));
                        let mut got_400 = true;
                    } else {
                        response_text += chunk;
                    }
                }
                if got_400 {
                    logger.info("⚠️ Verified 400 Error Triggered!".to_string());
                } else if response_text {
                    logger.info("✅ Success".to_string());
                } else {
                    logger.warning("❓ No response, no error?".to_string());
                }
            }
            // except Exception as e:
        }
    }
}
