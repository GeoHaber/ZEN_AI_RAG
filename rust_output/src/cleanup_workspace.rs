/// Workspace cleanup script - organize ZEN_AI_RAG into clean structure.
/// Creates: docs/, tests/, scripts/, OLD/ directories
/// Moves non-essential files to appropriate locations.

use anyhow::{Result, Context};
use std::path::PathBuf;

pub const ROOT: &str = "Path(file!()).resolve().parent.parent";

pub static DOCS_FILES: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static TESTS_FILES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static SCRIPTS_FILES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static OLD_FILES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static ESSENTIAL_FILES: std::sync::LazyLock<HashSet<serde_json::Value>> = std::sync::LazyLock::new(|| HashSet::new());

/// Colors class.
#[derive(Debug, Clone)]
pub struct Colors {
}

/// Create necessary directories.
pub fn ensure_dirs() -> () {
    // Create necessary directories.
    let mut dirs = vec!["docs".to_string(), "tests".to_string(), "scripts".to_string(), "OLD".to_string()];
    for d in dirs.iter() {
        let mut path = (ROOT / d);
        path.create_dir_all();
        println!("{}[DIR]{} {}/", Colors.GREEN, Colors.END, d);
    }
}

/// Safely move a file.
pub fn move_file(src: String, dest_dir: String) -> Result<()> {
    // Safely move a file.
    // try:
    {
        let mut src_path = (ROOT / src);
        let mut dest_path = ((ROOT / dest_dir) / src);
        if (src_path.exists() && !dest_path.exists()) {
            std::fs::rename(src_path.to_string(), dest_path.to_string());
            println!("{}[MOVE]{} {} -> {}/", Colors.GREEN, Colors.END, src, dest_dir);
            true
        }
    }
    // except Exception as _e:
    Ok(false)
}

/// Move files matching a pattern.
pub fn move_pattern(pattern: String, dest_dir: String) -> Result<()> {
    // Move files matching a pattern.
    // TODO: from glob import glob
    for filepath in glob((ROOT / pattern).to_string()).iter() {
        let mut filename = PathBuf::from(filepath).name;
        // try:
        {
            let mut dest_path = ((ROOT / dest_dir) / filename);
            if !dest_path.exists() {
                std::fs::rename(filepath, dest_path.to_string());
                println!("{}[MOVE]{} {} -> {}/", Colors.GREEN, Colors.END, filename, dest_dir);
            }
        }
        // except Exception as _e:
    }
}

/// Remove __pycache__ directories.
pub fn cleanup_pycache() -> Result<()> {
    // Remove __pycache__ directories.
    for pycache in ROOT.rglob("__pycache__".to_string()).iter() {
        // try:
        {
            std::fs::remove_dir_all(pycache).ok();
            println!("{}[DELETE]{} {}/", Colors.GREEN, Colors.END, pycache.relative_to(ROOT));
        }
        // except Exception as _e:
    }
}

/// Main.
pub fn main() -> () {
    // Main.
    os::chdir(ROOT.to_string());
    println!("\n{}{}=== ZEN_AI_RAG WORKSPACE CLEANUP ==={}\n", Colors.CYAN, Colors.BOLD, Colors.END);
    println!("{}Creating directories...{}", Colors.YELLOW, Colors.END);
    ensure_dirs();
    println!("\n{}Moving documentation files...{}", Colors.YELLOW, Colors.END);
    move_pattern("*.md".to_string(), "docs".to_string());
    move_pattern("*.txt".to_string(), "docs".to_string());
    move_pattern("*.log".to_string(), "docs".to_string());
    println!("\n{}Moving test files...{}", Colors.YELLOW, Colors.END);
    move_pattern("test_*.py".to_string(), "tests".to_string());
    move_pattern("verify_*.py".to_string(), "tests".to_string());
    move_file("run_tests::py".to_string(), "tests".to_string());
    move_file("pytest.ini".to_string(), "tests".to_string());
    println!("\n{}Moving script files...{}", Colors.YELLOW, Colors.END);
    for pattern in SCRIPTS_FILES.iter() {
        move_pattern(pattern, "scripts".to_string());
    }
    println!("\n{}Moving old/non-essential files...{}", Colors.YELLOW, Colors.END);
    for pattern in OLD_FILES.iter() {
        move_pattern(pattern, "OLD".to_string());
    }
    println!("\n{}Cleaning __pycache__...{}", Colors.YELLOW, Colors.END);
    cleanup_pycache();
    println!("\n{}{}=== CLEANUP COMPLETE ==={}\n", Colors.CYAN, Colors.BOLD, Colors.END);
    let mut root_files = ((ROOT.glob("*.py".to_string()).into_iter().collect::<Vec<_>>().len() + ROOT.glob("*.bat".to_string()).into_iter().collect::<Vec<_>>().len()) + ROOT.glob("*.sh".to_string()).into_iter().collect::<Vec<_>>().len());
    let mut docs_files = (ROOT / "docs".to_string()).glob("*".to_string()).into_iter().collect::<Vec<_>>().len();
    let mut tests_files = (ROOT / "tests".to_string()).glob("*".to_string()).into_iter().collect::<Vec<_>>().len();
    let mut scripts_files = (ROOT / "scripts".to_string()).glob("*".to_string()).into_iter().collect::<Vec<_>>().len();
    let mut old_files = (ROOT / "OLD".to_string()).glob("*".to_string()).into_iter().collect::<Vec<_>>().len();
    println!("{}Root directory:{} ~{} essential files", Colors.GREEN, Colors.END, root_files);
    println!("{}docs/:{} {} files", Colors.GREEN, Colors.END, docs_files);
    println!("{}tests/:{} {} files", Colors.GREEN, Colors.END, tests_files);
    println!("{}scripts/:{} {} files", Colors.GREEN, Colors.END, scripts_files);
    println!("{}OLD/:{} {} files", Colors.GREEN, Colors.END, old_files);
    println!();
}
