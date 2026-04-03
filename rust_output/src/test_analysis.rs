use anyhow::{Result, Context};
use crate::analysis::{analyze_and_write_report};

/// Test analyze and write report.
pub fn test_analyze_and_write_report(tmp_path: String, monkeypatch: String) -> () {
    // Test analyze and write report.
    let mut f = (tmp_path / "sample.py".to_string());
    fstd::fs::write(&"\nimport subprocess\ndef bar():\n    global x\n    x = 1\ndef foo():\n    eval('1+1')\n".to_string());
    monkeypatch.setattr(security, "validate_path".to_string(), |p| true);
    let mut report = analyze_and_write_report(vec![f.to_string()], /* job_id= */ "test123".to_string());
    assert!(report["job_id".to_string()] == "test123".to_string());
    assert!(report["files".to_string()].len() == 1);
    let mut issues = report["files".to_string()][0]["issues".to_string()];
    assert!(issues.iter().map(|i| (i.get(&"message".to_string()).cloned().unwrap_or("".to_string()).contains(&"subprocess".to_string()) || i.get(&"message".to_string()).cloned().unwrap_or("".to_string()).contains(&"eval".to_string()) || i.get(&"message".to_string()).cloned().unwrap_or("".to_string()).contains(&"uses eval".to_string()))).collect::<Vec<_>>().iter().any(|v| *v));
}
