use anyhow::{Result, Context};
use crate::swarm_arbitrator::{SwarmArbitrator};
use std::collections::HashMap;
use tokio;

/// AsyncIterator class.
#[derive(Debug, Clone)]
pub struct AsyncIterator {
    pub items: iter,
}

impl AsyncIterator {
    pub fn new(items: String) -> Self {
        Self {
            items: iter(items),
        }
    }
    pub fn __aiter__(&self) -> () {
        self
    }
    /// Anext.
    pub async fn __anext__(&self) -> Result<()> {
        // Anext.
        // try:
        {
            next(self.items)
        }
        // except StopIteration as _e:
    }
}

/// TestTrafficController class.
#[derive(Debug, Clone)]
pub struct TestTrafficController {
}

impl TestTrafficController {
    /// Setup.
    pub fn setUp(&mut self) -> () {
        // Setup.
        self.arbitrator = SwarmArbitrator(/* config= */ HashMap::from([("enabled".to_string(), true)]));
        self.arbitrator.endpoints = vec!["http://local:8001/v1/chat/completions".to_string(), "http://expert:8005/v1/chat/completions".to_string()];
        self.arbitrator.host = "127.0.0.1".to_string();
    }
    /// Test that easy queries stay on fast LLM
    pub async fn test_traffic_controller_easy(&mut self) -> () {
        // Test that easy queries stay on fast LLM
        let mut mock_eval = HashMap::from([("difficulty".to_string(), "easy".to_string()), ("confidence".to_string(), 0.95_f64), ("reasoning".to_string(), "Simple factual question".to_string())]);
        let mut mock_diff = patch.object(self.arbitrator, "_evaluate_query_difficulty".to_string(), /* new_callable= */ AsyncMock);
        {
            mock_diff.return_value = mock_eval;
            let mut mock_stream = patch.object(self.arbitrator, "_stream_from_llm".to_string());
            {
                mock_stream.return_value = AsyncIterator(vec!["Fast response".to_string()]);
                let mut responses = vec![];
                // async for
                while let Some(chunk) = self.arbitrator._traffic_controller_mode("What is 2+2?".to_string()).next().await {
                    responses.push(chunk);
                }
                let mut full_resp = responses.join(&"".to_string());
                assert!(full_resp.contains("💨 **Fast response**".to_string()));
                mock_stream.assert_called_with(self.arbitrator.endpoints[0], "What is 2+2?".to_string(), "You are a helpful AI assistant.".to_string());
            }
        }
    }
    /// Test that hard queries go to expert LLM
    pub async fn test_traffic_controller_hard(&mut self) -> () {
        // Test that hard queries go to expert LLM
        let mut mock_eval = HashMap::from([("difficulty".to_string(), "hard".to_string()), ("confidence".to_string(), 0.4_f64), ("reasoning".to_string(), "Complex reasoning required".to_string())]);
        let mut mock_diff = patch.object(self.arbitrator, "_evaluate_query_difficulty".to_string(), /* new_callable= */ AsyncMock);
        {
            mock_diff.return_value = mock_eval;
            let mut mock_stream = patch.object(self.arbitrator, "_stream_from_llm".to_string());
            {
                mock_stream.return_value = AsyncIterator(vec!["Expert response".to_string()]);
                let mut responses = vec![];
                // async for
                while let Some(chunk) = self.arbitrator._traffic_controller_mode("Prove P=NP".to_string()).next().await {
                    responses.push(chunk);
                }
                let mut full_resp = responses.join(&"".to_string());
                assert!(full_resp.contains("🚀 **Expert routing**".to_string()));
                mock_stream.assert_called_with(self.arbitrator.endpoints[1], "Prove P=NP".to_string(), "You are a helpful AI assistant.".to_string());
            }
        }
    }
}
