use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use tokio;

/// Verify we can fetch models from Port 8002 (Mocked).
pub async fn test_fetch_models_mocked(mock_hub_api: String) -> () {
    // Verify we can fetch models from Port 8002 (Mocked).
    let mut backend = AsyncZenAIBackend();
    let mut models = backend.get_models().await;
    assert!(/* /* isinstance(models, list) */ */ true);
    assert!(models::contains(&"mock-model-1.gguf".to_string()));
    assert!(mock_hub_api.calls.len() == 1);
}

/// Verify we can get a streaming response from Port 8001 (Mocked).
pub async fn test_chat_completion_mocked(mock_llm_api: String) -> () {
    // Verify we can get a streaming response from Port 8001 (Mocked).
    let mut backend = AsyncZenAIBackend();
    let mut response_text = "".to_string();
    let _ctx = backend;
    {
        // async for
        while let Some(chunk) = backend.send_message_async("Say hello in English.".to_string()).next().await {
            response_text += chunk;
        }
    }
    assert!(response_text == "Hello world!".to_string());
    assert!(mock_llm_api.calls.len() == 1);
    assert!(mock_llm_api.calls.last.request.method == "POST".to_string());
}
