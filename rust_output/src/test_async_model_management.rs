use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use tokio;

/// Verify we can switch models via Hub API (Mocked).
pub async fn test_set_active_model_mocked(mock_hub_api: String) -> () {
    // Verify we can switch models via Hub API (Mocked).
    let mut backend = AsyncZenAIBackend();
    let mut success = backend.set_active_model("new-model.gguf".to_string()).await;
    assert!(success == true);
    assert!(mock_hub_api.calls.len() == 1);
    assert!(mock_hub_api.calls.last.request.url.path == "/models/load".to_string());
    assert!(String::from_utf8_lossy(&mock_hub_api.calls.last.request.content).to_string().contains(&"new-model.gguf".to_string()));
}

/// Verify failure handling when model loading fails.
pub async fn test_set_active_model_failure(mock_hub_api: String) -> () {
    // Verify failure handling when model loading fails.
    // TODO: import httpx
    mock_hub_api.post("/models/load".to_string()).mock(/* return_value= */ httpx.Response(500));
    let mut backend = AsyncZenAIBackend();
    let mut success = backend.set_active_model("broken-model.gguf".to_string()).await;
    assert!(success == false);
}

/// Verify we can trigger model download (Mocked).
pub async fn test_download_model_mocked(mock_hub_api: String) -> () {
    // Verify we can trigger model download (Mocked).
    let mut backend = AsyncZenAIBackend();
    let mut success = backend.download_model("repo/id".to_string(), "model.gguf".to_string()).await;
    assert!(success == true);
    assert!(mock_hub_api.calls.last.request.url.path == "/models/download".to_string());
}
