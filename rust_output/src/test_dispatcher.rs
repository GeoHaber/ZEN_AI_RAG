use anyhow::{Result, Context};
use crate::dispatcher::{FastDispatcher};
use tokio;

/// Verify instant regex responses.
pub async fn test_level_0_regex() -> () {
    // Verify instant regex responses.
    let mut dispatcher = FastDispatcher(/* backend= */ None);
    let mut res = dispatcher::dis/* mock::patch("hello".to_string() */).await;
    assert!(res["type".to_string()] == "direct".to_string());
    assert!(res["content".to_string()].contains(&"Hello".to_string()));
    let mut res = dispatcher::dis/* mock::patch("what time is it?".to_string() */).await;
    assert!(res["type".to_string()] == "direct".to_string());
    assert!(res["content".to_string()].contains(&"It is currently".to_string()));
}

/// Verify heuristic routing.
pub async fn test_level_1_heuristics() -> () {
    // Verify heuristic routing.
    let mut mock_rag = MagicMock();
    let mut dispatcher = FastDispatcher(/* backend= */ None, /* rag_system= */ mock_rag);
    let mut res = dispatcher::dis/* mock::patch("write a python script to sort a list".to_string() */).await;
    assert!(res["type".to_string()] == "expert".to_string());
    assert!(res["expert".to_string()] == "code".to_string());
    let mut res = dispatcher::dis/* mock::patch("search for moon landing".to_string() */).await;
    assert!(res["type".to_string()] == "rag".to_string());
    let mut res = dispatcher::dis/* mock::patch("tell me a joke".to_string() */).await;
    assert!(res["type".to_string()] == "chat".to_string());
}
