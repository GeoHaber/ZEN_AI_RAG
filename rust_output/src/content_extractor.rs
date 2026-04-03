/// Content Extractor v2.1 — Modular Architecture (Facade)
/// 
/// This file maintains the backward-compatible API for content extraction
/// while delegating the actual work to specialized submodules in src.extractors.

use anyhow::{Result, Context};
use crate::file_extractor::{FolderScanner};
use crate::markdown_converter::{HTMLToStructuredMarkdown};
use crate::web_extractor::{WebScanner};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _HTML_CONVERTER: std::sync::LazyLock<HTMLToStructuredMarkdown> = std::sync::LazyLock::new(|| Default::default());

pub static _HAS_OCR: std::sync::LazyLock<getattr> = std::sync::LazyLock::new(|| Default::default());

/// Scan website and extract structured content.
pub fn scan_web(start_url: String, max_pages: i64, progress_callback: Option<Box<dyn Fn>>, page_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> (String, Vec<HashMap>, Vec<HashMap>) {
    // Scan website and extract structured content.
    let mut scanner = WebScanner();
    scanner.scan(start_url, /* max_pages= */ max_pages, /* progress_callback= */ progress_callback, /* page_callback= */ page_callback, /* completed_items= */ kwargs.get(&"completed_items".to_string()).cloned())
}

/// Validate folder path before scanning.
pub fn check_scan_path_allowed(folder: String) -> Option<String> {
    // Validate folder path before scanning.
    if (!folder || !folder.to_string().trim().to_string()) {
        "Folder path is empty".to_string()
    }
    let mut folder_path = PathBuf::from(folder).canonicalize().unwrap_or_default();
    if !folder_path.exists() {
        "Folder not found".to_string()
    }
    if !folder_path.is_dir() {
        "Path is not a directory".to_string()
    }
    if /* hasattr(FolderScanner, "_scan_blocked_reason".to_string()) */ true { FolderScanner._scan_blocked_reason(folder_path) } else { None }
}

/// Scan folder and extract content from all supported file types.
pub fn scan_folder(folder: String, progress_callback: Option<Box<dyn Fn>>, max_depth: i64, max_files: i64, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> (String, Vec<HashMap>, Vec<HashMap>) {
    // Scan folder and extract content from all supported file types.
    let mut scanner = FolderScanner(/* max_depth= */ max_depth, /* max_files= */ max_files);
    scanner.scan(folder, /* progress_callback= */ progress_callback, /* completed_items= */ kwargs.get(&"completed_items".to_string()).cloned())
}

/// Count files in a directory tree up to *max_depth* levels.
pub fn count_files_in_path(folder: String, max_depth: i64) -> Result<i64> {
    // Count files in a directory tree up to *max_depth* levels.
    // try:
    {
        let mut folder_path = PathBuf::from(folder);
        if (!folder_path.exists() || !folder_path.is_dir()) {
            0
        }
        let mut count = 0;
        for item in folder_path.rglob("*".to_string()).iter() {
            if item.is_file() {
                let mut rel = item.relative_to(folder_path);
                if rel.parts.len() <= max_depth {
                    count += 1;
                }
            }
        }
        count
    }
    // except Exception as _e:
}
