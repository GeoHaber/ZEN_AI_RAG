use anyhow::{Result, Context};
use crate::async_backend::{backen};
use tokio;

/// Test.
pub async fn test() -> () {
    // Test.
    println!("{}", "Testing LLM...".to_string());
    let _ctx = backend;
    {
        // async for
        while let Some(chunk) = backend.send_message_async("Say only 'HELLO'".to_string()).next().await {
            println!("Chunk: {}", repr(chunk));
            // pass
        }
    }
}
