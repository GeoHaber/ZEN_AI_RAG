use anyhow::{Result, Context};
use std::path::PathBuf;

pub const APP_NAME: &str = "ZenAI";

pub const ENTRY_POINT: &str = "start_llm::py";

pub const ICON_PATH: &str = "ui/static/favicon.ico";

pub const DIST_DIR: &str = "dist";

pub const WORK_DIR: &str = "build";

/// Wipe previous build artifacts.
pub fn clean_build_dirs() -> () {
    // Wipe previous build artifacts.
    if os::path.exists(DIST_DIR) {
        std::fs::remove_dir_all(DIST_DIR).ok();
    }
    if os::path.exists(WORK_DIR) {
        std::fs::remove_dir_all(WORK_DIR).ok();
    }
}

/// Helper: setup phase for build.
pub fn _do_build_setup() -> () {
    // Helper: setup phase for build.
    clean_build_dirs();
    let mut hidden_imports = vec!["nicegui".to_string(), "uvicorn".to_string(), "fastapi".to_string(), "starlette".to_string(), "pypdf".to_string(), "sentence_transformers".to_string(), "numpy".to_string(), "requests".to_string(), "zena_mode".to_string(), "ui".to_string()];
    let mut args = vec![ENTRY_POINT, format!("--name={}", APP_NAME), "--onedir".to_string(), "--windowed".to_string(), "--console".to_string(), "--clean".to_string(), "--noconfirm".to_string()];
    for hidden in hidden_imports.iter() {
        args.push(format!("--hidden-import={}", hidden));
    }
    args
}

/// Build.
pub fn build() -> () {
    // Build.
    let mut args = _do_build_setup();
    // TODO: import nicegui
    let mut nicegui_path = PathBuf::from(nicegui.file!()).parent().unwrap_or(std::path::Path::new(""));
    args.push(format!("--add-data={}{}nicegui", nicegui_path, os::pathsep));
    args.push(format!("--add-data=ui{}ui", os::pathsep));
    args.push(format!("--add-data=zena_mode{}zena_mode", os::pathsep));
    println!("{}", "🔨 Starting PyInstaller Build...".to_string());
    PyInstaller.__main__.run(args);
    println!("{}", "✅ Build Complete.".to_string());
    println!("{}", "📦 Copying External Assets...".to_string());
    let mut target_dir = (PathBuf::from(DIST_DIR) / APP_NAME);
    let mut src_bin = PathBuf::from("_bin".to_string());
    if src_bin.exists() {
        shutil::copytree(src_bin, (target_dir / "_bin".to_string()), /* dirs_exist_ok= */ true);
        println!("{}", "   + Copied _bin/".to_string());
    }
    if PathBuf::from("config::json".to_string()).exists() {
        std::fs::copy("config::json".to_string(), target_dir).unwrap();
        println!("{}", "   + Copied config::json".to_string());
    }
    if PathBuf::from(".env".to_string()).exists() {
        std::fs::copy(".env".to_string(), target_dir).unwrap();
        println!("{}", "   + Copied .env".to_string());
    }
    println!("🚀 Release ready at: {}", target_dir.absolute());
}
