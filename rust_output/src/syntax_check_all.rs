use anyhow::{Result, Context};
use std::path::PathBuf;

/// Check syntax.
pub fn check_syntax(directory: String) -> Result<()> {
    // Check syntax.
    println!("🔍 Starting Syntax Check in: {}", directory);
    println!("{}", ("=".to_string() * 60));
    let mut error_count = 0;
    let mut checked_count = 0;
    for (root, dirs, files) in os::walk(directory).iter() {
        if (root.contains(&".venv".to_string()) || root.contains(&".git".to_string()) || root.contains(&"__pycache__".to_string())) {
            continue;
        }
        for file in files.iter() {
            if !file.ends_with(&*".py".to_string()) {
                continue;
            }
            checked_count += 1;
            let mut full_path = (PathBuf::from(root) / file).to_string();
            // try:
            {
                py_compile.compile(full_path, /* doraise= */ true);
            }
            // except py_compile.PyCompileError as _e:
            // except Exception as _e:
        }
    }
    println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
    if error_count == 0 {
        println!("✅ Success! Scanned {} files. No syntax errors found.", checked_count);
        std::process::exit(0);
    } else {
        println!("❌ Failed! Found {} syntax errors in {} files.", error_count, checked_count);
        std::process::exit(1);
    }
}
