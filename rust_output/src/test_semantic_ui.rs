use anyhow::{Result, Context};
use crate::live_diagnostics::{run_semantic_ui_audit};
use crate::registry::{UI_METADATA};
use tokio;

/// Test semantic audit logic.
pub async fn test_semantic_audit_logic() -> () {
    // Test semantic audit logic.
    let mut mock_backend = MagicMock();
    let mock_stream = |prompt| {
        /* yield "The UI Registry looks ".to_string() */;
        /* yield "well-structured and logically sound. ".to_string() */;
        /* yield "All current actions are appropriate for a local AI assistant.".to_string() */;
    };
    mock_backend::send_message_async.side_effect = |p| mock_stream(p);
    let mut passed = run_semantic_ui_audit(mock_backend).await;
    assert!(passed == true);
    assert!(mock_backend::send_message_async.called);
    let mock_error_stream = |prompt| {
        /* yield "There is an error in the logic ".to_string() */;
        /* yield "of the settings button mapping.".to_string() */;
    };
    mock_backend::send_message_async.side_effect = |p| mock_error_stream(p);
    let mut passed_with_error = run_semantic_ui_audit(mock_backend).await;
    assert!(passed_with_error == false);
}

/// Ensure every ID in registry has metadata (Spec #8 Compliance).
pub async fn test_ui_registry_completeness() -> () {
    // Ensure every ID in registry has metadata (Spec #8 Compliance).
    // TODO: from ui.registry import UI_IDS, UI_METADATA
    let mut raw_ids = dir(UI_IDS).iter().filter(|attr| (!attr.starts_with(&*"__".to_string()) && /* /* isinstance(/* getattr(UI_IDS, attr) */ */ Default::default(), str) */ true)).map(|attr| /* getattr(UI_IDS, attr) */ Default::default()).collect::<Vec<_>>();
    for rid in raw_ids.iter() {
        assert!(UI_METADATA.contains(&rid), "UI ID {} is missing metadata. Spec violation!", rid);
    }
}
