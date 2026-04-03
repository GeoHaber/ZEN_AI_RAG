use anyhow::{Result, Context};
use crate::batch_engine::{BatchAnalyzer};
use tokio;

/// Test batch analysis logic.
pub async fn test_batch_analysis_logic(tmp_path: String) -> () {
    // Test batch analysis logic.
    let mut mock_backend = MagicMock();
    let mut mock_gen = MagicMock();
    mock_gen.__aiter__.return_value = vec!["AI ".to_string(), "Review ".to_string(), "Content".to_string()];
    mock_backend::send_message_async.return_value = mock_gen;
    let mut analyzer = BatchAnalyzer(mock_backend);
    let mut file1 = (tmp_path / "test1.py".to_string());
    file1std::fs::write(&"print('hello')".to_string(), /* encoding= */ "utf-8".to_string());
    let mut file2 = (tmp_path / "test2.py".to_string());
    file2std::fs::write(&"def foo(): pass".to_string(), /* encoding= */ "utf-8".to_string());
    let mut files = vec![file1.to_string(), file2.to_string()];
    let mut progress_updates = vec![];
    let on_progress = |msg, pct| {
        progress_updates.push((msg, pct));
    };
    let mut result = analyzer.analyze_files(files, /* on_progress= */ on_progress).await;
    assert!(result["total".to_string()] == 2);
    assert!(result["completed".to_string()] == 2);
    assert!((tmp_path / "test1_zena_analisis.md".to_string()).exists());
    assert!((tmp_path / "test2_zena_analisis.md".to_string()).exists());
    let mut report_content = (tmp_path / "test1_zena_analisis.md".to_string()).read_to_string());
    assert!(report_content.contains(&"AI Review Content".to_string()));
    assert!(progress_updates.len() > 0);
    assert!(progress_updates[-1][1] == 1.0_f64);
}
