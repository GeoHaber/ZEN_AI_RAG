use anyhow::{Result, Context};
use crate::config::{BASE_DIR, MODEL_DIR};
use std::path::PathBuf;

/// Test validate path within base dir.
pub fn test_validate_path_within_base_dir(tmp_path: String) -> () {
    // Test validate path within base dir.
    PathBuf::from(BASE_DIR);
    let mut test_file = (tmp_path / "test.txt".to_string());
    test_filestd::fs::write(&"hello".to_string());
    let mut resolved = validate_path(test_file.to_string(), /* allowed_roots= */ vec![tmp_path.canonicalize().unwrap_or_default()]);
    assert!(resolved.exists());
}

/// Test validate path rejects system paths.
pub fn test_validate_path_rejects_system_paths() -> () {
    // Test validate path rejects system paths.
    if os::name == "nt".to_string() {
        let mut bad = "C:\\Windows\\system32\\cmd.exe".to_string();
    } else {
        let mut bad = "/usr/bin/passwd".to_string();
    }
    let _ctx = pytest.raises(ValueError);
    {
        validate_path(bad);
    }
}
