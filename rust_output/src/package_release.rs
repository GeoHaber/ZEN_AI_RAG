use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

/// Helper: setup phase for create_dist_zip.
pub fn _do_create_dist_zip_setup() -> () {
    // Helper: setup phase for create_dist_zip.
    println!("{}", "📦 Packing ZenAI for Release...".to_string());
    let mut ROOT_DIR = PathBuf::from(std::env::current_dir().unwrap().to_str().unwrap().to_string());
    let mut DIST_DIR = (ROOT_DIR / "dist".to_string());
    DIST_DIR.create_dir_all();
    let mut ZIP_NAME = (DIST_DIR / "ZenAI_Dist.zip".to_string());
    let mut INCLUDES = vec!["zena.py".to_string(), "requirements.txt".to_string(), "README.md".to_string(), "USER_MANUAL.md".to_string(), "config::json".to_string(), "config::py".to_string(), "utils::py".to_string(), "config_system::py".to_string(), "security.py".to_string(), "async_backend::py".to_string(), "locales".to_string(), "ui".to_string(), "zena_mode".to_string(), "ui_components.py".to_string(), "settings::py".to_string(), "state_management::py".to_string(), "zena_startup.log".to_string(), "experimental_voice_lab".to_string(), "tests".to_string()];
    (INCLUDES, ROOT_DIR, ZIP_NAME)
}

/// Create dist zip.
pub fn create_dist_zip() -> Result<()> {
    // Create dist zip.
    let (mut INCLUDES, mut ROOT_DIR, mut ZIP_NAME) = _do_create_dist_zip_setup();
    let mut zipf = zipfile.ZipFile(ZIP_NAME, "w".to_string(), zipfile.ZIP_DEFLATED);
    {
        for item in INCLUDES.iter() {
            let mut src_path = (ROOT_DIR / item);
            if !src_path.exists() {
                println!("⚠️ Warning: {} not found, skipping.", item);
                continue;
            }
            if src_path.is_file() {
                println!("  Adding file: {}", item);
                zipf.write(src_path, /* arcname= */ item);
            } else if src_path.is_dir() {
                println!("  Adding dir:  {}", item);
                for (root, dirs, files) in os::walk(src_path).iter() {
                    if root.contains(&"__pycache__".to_string()) {
                        continue;
                    }
                    if root.contains(&".venv".to_string()) {
                        continue;
                    }
                    if root.contains(&".git".to_string()) {
                        continue;
                    }
                    if root.contains(&"node_modules".to_string()) {
                        continue;
                    }
                    for file in files.iter() {
                        if file.ends_with(&*".pyc".to_string()) {
                            continue;
                        }
                        let mut full_path = (PathBuf::from(root) / file);
                        let mut rel_path = full_path.relative_to(ROOT_DIR);
                        zipf.write(full_path, /* arcname= */ rel_path.to_string());
                    }
                }
            }
        }
    }
    println!("\n✅ Release created at: {}", ZIP_NAME);
    println!("📦 Size: {:.2} MB", ((ZIP_NAME.stat().st_size / 1024) / 1024));
    Ok(ZIP_NAME)
}
