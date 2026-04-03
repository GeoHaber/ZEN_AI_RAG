use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use std::collections::HashMap;
use tokio;

/// TestAsyncRefactor class.
#[derive(Debug, Clone)]
pub struct TestAsyncRefactor {
}

impl TestAsyncRefactor {
    /// Test get models success.
    pub async fn test_get_models_success(&self) -> () {
        // Test get models success.
        let mut backend = AsyncZenAIBackend();
        let mut mock_response = MagicMock();
        mock_response.status_code = 200;
        mock_response.json::return_value = vec!["model_a".to_string(), "model_b".to_string()];
        let mut mock_client = AsyncMock();
        mock_client.__aenter__.return_value = mock_client;
        mock_client.__aexit__.return_value = None;
        mock_client.get.return_value = mock_response;
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut models = backend.get_models().await;
        }
        assert!(models == vec!["model_a".to_string(), "model_b".to_string()]);
        mock_client.get.assert_called_with("http://127.0.0.1:8002/models/available".to_string(), /* timeout= */ 2.0_f64);
    }
    /// Test get models failure fallback.
    pub async fn test_get_models_failure_fallback(&self) -> () {
        // Test get models failure fallback.
        let mut backend = AsyncZenAIBackend();
        let mut mock_client = AsyncMock();
        mock_client.__aenter__.return_value = mock_client;
        mock_client.__aexit__.return_value = None;
        mock_client.get.side_effect = Exception("Connection Refused".to_string());
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut models = backend.get_models().await;
        }
        assert!(models::iter().map(|m| m.contains(&"qwen2.5-coder".to_string())).collect::<Vec<_>>().iter().any(|v| *v));
    }
    /// Test download model.
    pub async fn test_download_model(&self) -> () {
        // Test download model.
        let mut backend = AsyncZenAIBackend();
        let mut mock_response = MagicMock();
        mock_response.status_code = 200;
        let mut mock_client = AsyncMock();
        mock_client.__aenter__.return_value = mock_client;
        mock_client.__aexit__.return_value = None;
        mock_client.post.return_value = mock_response;
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut success = backend.download_model("repo".to_string(), "file".to_string()).await;
        }
        assert!(success == true);
        mock_client.post.assert_called_with("http://127.0.0.1:8002/models/download".to_string(), /* json= */ HashMap::from([("repo_id".to_string(), "repo".to_string()), ("filename".to_string(), "file".to_string())]), /* timeout= */ 5.0_f64);
    }
    /// Test set active model.
    pub async fn test_set_active_model(&self) -> () {
        // Test set active model.
        let mut backend = AsyncZenAIBackend();
        let mut mock_response = MagicMock();
        mock_response.status_code = 200;
        let mut mock_client = AsyncMock();
        mock_client.__aenter__.return_value = mock_client;
        mock_client.__aexit__.return_value = None;
        mock_client.post.return_value = mock_response;
        /* let _ctx = mock::/* mock::patch(...) */ — use mockall crate */;
        {
            let mut success = backend.set_active_model("new_model".to_string()).await;
        }
        assert!(success == true);
    }
}
