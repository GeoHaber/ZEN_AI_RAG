use anyhow::{Result, Context};
use std::collections::HashSet;
use std::path::PathBuf;

/// Helper: setup phase for cleanup_project.
pub fn _do_cleanup_project_setup() -> () {
    // Helper: setup phase for cleanup_project.
    println!("{}", "🧹 Starting Project Cleanup...".to_string());
    let mut ROOT = PathBuf::from(std::env::current_dir().unwrap().to_str().unwrap().to_string());
    let mut EXTRA_DIR = (ROOT / "_Extra_files".to_string());
    EXTRA_DIR.create_dir_all();
    let mut KEEPERS = HashSet::from(["zena.py".to_string(), "config::json".to_string(), "config::py".to_string(), "utils::py".to_string(), "config_system::py".to_string(), "security.py".to_string(), "async_backend::py".to_string(), "ui_components.py".to_string(), "settings::py".to_string(), "state_management::py".to_string(), "locales".to_string(), "ui".to_string(), "zena_mode".to_string(), "models".to_string(), "README.md".to_string(), "USER_MANUAL.md".to_string(), "INSTALL.md".to_string(), "requirements.txt".to_string(), ".git".to_string(), ".venv".to_string(), ".pytest_cache".to_string(), "__pycache__".to_string(), ".gitignore".to_string(), ".coverage".to_string(), "dist".to_string(), "rag_cache".to_string(), "qdrant_storage".to_string(), "conversation_cache".to_string(), "benchmarks".to_string(), "tests".to_string(), "scripts".to_string(), "run_tests::py".to_string(), "pytest.ini".to_string(), "cleanup_extras::py".to_string(), "experimental_voice_lab".to_string(), "_Extra_files".to_string()]);
    (EXTRA_DIR, KEEPERS, ROOT)
}

/// Cleanup project.
pub fn cleanup_project() -> Result<()> {
    // Cleanup project.
    let (mut EXTRA_DIR, mut KEEPERS, mut ROOT) = _do_cleanup_project_setup();
    let mut moved_count = 0;
    for item in ROOT.iterdir().iter() {
        let mut name = item.name;
        if KEEPERS.contains(&name) {
            println!("  Existing: {} (Keep)", name);
            continue;
        }
        println!("  ➡️ Moving: {} -> _Extra_files/", name);
        let mut dest = (EXTRA_DIR / name);
        // try:
        {
            std::fs::rename(item.to_string(), dest.to_string());
            moved_count += 1;
        }
        // except Exception as _e:
    }
    Ok(println!("\n✅ Cleanup Complete. Moved {} items to _Extra_files/.", moved_count))
}
