/// verify_install::py - ZEN_AI_RAG Installation Verification
/// 
/// Checks that all required dependencies are properly installed.
/// Run this after installation to verify everything is ready.
/// 
/// Usage:
/// python verify_install::py

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub const GREEN: &str = "\\x1b[92m";

pub const RED: &str = "\\x1b[91m";

pub const YELLOW: &str = "\\x1b[93m";

pub const CYAN: &str = "\\x1b[96m";

pub const RESET: &str = "\\x1b[0m";

pub const BOLD: &str = "\\x1b[1m";

/// Check if a package is installed.
/// 
/// Args:
/// import_name: Name to use in import statement
/// display_name: Human-friendly display name
/// optional: If true, missing is a warning not error
/// 
/// Returns:
/// true if package found, false otherwise
pub fn check_package(import_name: String, display_name: String, optional: bool) -> Result<bool> {
    // Check if a package is installed.
    // 
    // Args:
    // import_name: Name to use in import statement
    // display_name: Human-friendly display name
    // optional: If true, missing is a warning not error
    // 
    // Returns:
    // true if package found, false otherwise
    // try:
    {
        __import__(import_name);
        let mut status = format!("{}✓{}", GREEN, RESET);
        let mut category = if !optional { "REQUIRED".to_string() } else { "OPTIONAL".to_string() };
        println!("  {} {:45} [{}]", status, display_name, category);
        true
    }
    // except ImportError as _e:
}

/// Check if a file/directory exists.
pub fn check_file(filepath: String, display_name: String, optional: bool) -> bool {
    // Check if a file/directory exists.
    let mut path = PathBuf::from(filepath);
    let mut exists = path.exists();
    let mut status = if exists { format!("{}✓{}", GREEN, RESET) } else { format!("{}✗{}", RED, RESET) };
    let mut category = if (optional && !exists) { "WARNING".to_string() } else { if !exists { "REQUIRED".to_string() } else { "OK".to_string() } };
    println!("  {} {:45} [{}]", status, display_name, category);
    exists
}

/// Helper: setup phase for _do_main_setup.
pub fn _do_do_main_setup_setup() -> () {
    // Helper: setup phase for _do_main_setup.
    println!("{}", ("\n".to_string() + ("=".to_string() * 85)));
    println!("{}{}ZEN_AI_RAG Installation Verification{}", BOLD, CYAN, RESET);
    println!("{}", (("=".to_string() * 85) + "\n".to_string()));
    let mut results = HashMap::from([("required".to_string(), HashMap::from([("passed".to_string(), 0), ("failed".to_string(), 0)])), ("optional".to_string(), HashMap::from([("passed".to_string(), 0), ("failed".to_string(), 0)])), ("files".to_string(), HashMap::from([("passed".to_string(), 0), ("failed".to_string(), 0)]))]);
    println!("{}Core Dependencies (REQUIRED):{}", BOLD, RESET);
    let mut core_packages = vec![("nicegui".to_string(), "NiceGUI - Web UI Framework".to_string()), ("uvicorn".to_string(), "Uvicorn - ASGI Server".to_string()), ("requests".to_string(), "Requests - HTTP Client".to_string()), ("httpx".to_string(), "HTTPX - Async HTTP".to_string()), ("bs4".to_string(), "BeautifulSoup4 - HTML Parsing".to_string())];
    for (import_name, display_name) in core_packages.iter() {
        if check_package(import_name, display_name) {
            results["required".to_string()]["passed".to_string()] += 1;
        } else {
            results["required".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    println!("{}LLM & RAG Integration (REQUIRED):{}", BOLD, RESET);
    let mut rag_packages = vec![("qdrant_client".to_string(), "Qdrant Client - Vector Database".to_string()), ("sentence_transformers".to_string(), "Sentence Transformers - Embeddings".to_string()), ("rank_bm25".to_string(), "BM25 - Ranking Algorithm".to_string())];
    for (import_name, display_name) in rag_packages.iter() {
        if check_package(import_name, display_name) {
            results["required".to_string()]["passed".to_string()] += 1;
        } else {
            results["required".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    (display_name, import_name, results)
}

/// Helper: setup phase for main.
pub fn _do_main_setup() -> () {
    // Helper: setup phase for main.
    let (mut display_name, mut import_name, mut results) = _do_do_main_setup_setup();
    println!("{}Document Processing (REQUIRED):{}", BOLD, RESET);
    let mut doc_packages = vec![("PyPDF2".to_string(), "PyPDF2 - PDF Processing".to_string()), ("fitz".to_string(), "PyMuPDF - PDF/Image Processing".to_string()), ("pypdf".to_string(), "PyPDF - Modern PDF Library".to_string())];
    for (import_name, display_name) in doc_packages.iter() {
        if check_package(import_name, display_name) {
            results["required".to_string()]["passed".to_string()] += 1;
        } else {
            results["required".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    println!("{}Audio Processing (REQUIRED for Voice):{}", BOLD, RESET);
    let mut audio_packages = vec![("faster_whisper".to_string(), "Faster Whisper - STT".to_string()), ("piper".to_string(), "Piper TTS - Text-to-Speech".to_string()), ("sounddevice".to_string(), "SoundDevice - Audio I/O".to_string())];
    for (import_name, display_name) in audio_packages.iter() {
        if check_package(import_name, display_name) {
            results["required".to_string()]["passed".to_string()] += 1;
        } else {
            results["required".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    (display_name, import_name, results)
}

/// Helper: setup phase for main.
pub fn _do_main_init() -> () {
    // Helper: setup phase for main.
    let (mut display_name, mut import_name, mut results) = _do_main_setup();
    println!("{}ML & Utilities (REQUIRED):{}", BOLD, RESET);
    let mut util_packages = vec![("numpy".to_string(), "NumPy - Numerical Computing".to_string()), ("scipy".to_string(), "SciPy - Scientific Computing".to_string()), ("pydantic".to_string(), "Pydantic - Data Validation".to_string()), ("dotenv".to_string(), "Python-dotenv - Config Management".to_string())];
    for (import_name, display_name) in util_packages.iter() {
        if check_package(import_name, display_name) {
            results["required".to_string()]["passed".to_string()] += 1;
        } else {
            results["required".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    println!("{}Testing Tools (OPTIONAL):{}", BOLD, RESET);
    let mut test_packages = vec![("pytest".to_string(), "Pytest - Testing Framework".to_string()), ("pytest_asyncio".to_string(), "Pytest AsyncIO - Async Testing".to_string())];
    for (import_name, display_name) in test_packages.iter() {
        if check_package(import_name, display_name, /* optional= */ true) {
            results["optional".to_string()]["passed".to_string()] += 1;
        } else {
            results["optional".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    println!("{}Vision Tools (OPTIONAL):{}", BOLD, RESET);
    let mut vision_packages = vec![("cv2".to_string(), "OpenCV - Computer Vision".to_string()), ("PIL".to_string(), "Pillow - Image Processing".to_string())];
    for (import_name, display_name) in vision_packages.iter() {
        if check_package(import_name, display_name, /* optional= */ true) {
            results["optional".to_string()]["passed".to_string()] += 1;
        } else {
            results["optional".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    (display_name, results)
}

/// Run verification checks.
pub fn main() -> () {
    // Run verification checks.
    let (mut display_name, mut results) = _do_main_init();
    println!("{}Directory Structure:{}", BOLD, RESET);
    let mut dirs = vec![("zena_mode".to_string(), "Core application module".to_string()), ("ui".to_string(), "UI components".to_string()), ("local_llm".to_string(), "Local LLM management".to_string()), ("models".to_string(), "AI model storage directory".to_string()), ("qdrant_storage".to_string(), "Vector database storage".to_string())];
    for (dirname, display_name) in dirs.iter() {
        if check_file(dirname, display_name, /* optional= */ true) {
            results["files".to_string()]["passed".to_string()] += 1;
        } else {
            results["files".to_string()]["failed".to_string()] += 1;
        }
    }
    println!();
    println!("{}", ("=".to_string() * 85));
    println!("{}Summary:{}", BOLD, RESET);
    println!("{}", ("=".to_string() * 85));
    let mut required_ok = results["required".to_string()]["failed".to_string()] == 0;
    results["optional".to_string()]["failed".to_string()] == 0;
    println!("\n  Required Packages: {}{}{} passed, {}{}{} failed", GREEN, results["required".to_string()]["passed".to_string()], RESET, RED, results["required".to_string()]["failed".to_string()], RESET);
    println!("  Optional Packages: {}{}{} passed, {}{}{} warnings", GREEN, results["optional".to_string()]["passed".to_string()], RESET, YELLOW, results["optional".to_string()]["failed".to_string()], RESET);
    println!("  Directory Structure: {}{}{} OK, {}{}{} missing (optional)", GREEN, results["files".to_string()]["passed".to_string()], RESET, YELLOW, results["files".to_string()]["failed".to_string()], RESET);
    if required_ok {
        println!("\n{}{}✓ Installation Verified - Ready to Use!{}", GREEN, BOLD, RESET);
        println!("\nNext: Run 'python zena.py' to start the application");
        println!("{}", (("=".to_string() * 85) + "\n".to_string()));
        0
    } else {
        println!("\n{}{}✗ Installation Failed - Missing required packages{}", RED, BOLD, RESET);
        println!("\nFix with: pip install -r requirements.txt");
        println!("{}", (("=".to_string() * 85) + "\n".to_string()));
        1
    }
}
