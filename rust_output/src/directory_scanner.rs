/// directory_scanner::py - Local directory RAG indexing

use anyhow::{Result, Context};
use crate::utils::{safe_print};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// DirectoryScanner class.
#[derive(Debug, Clone)]
pub struct DirectoryScanner {
    pub root_dir: PathBuf,
    pub documents: Vec<serde_json::Value>,
    pub supported_extensions: HashSet<serde_json::Value>,
    pub skip_dirs: HashSet<serde_json::Value>,
    pub max_file_size: String,
    pub max_pdf_size: String,
    pub extractor: UniversalExtractor,
}

impl DirectoryScanner {
    /// Initialize instance.
    pub fn new(root_dir: String) -> Self {
        Self {
            root_dir: PathBuf::from(root_dir),
            documents: vec![],
            supported_extensions: HashSet::from([".txt".to_string(), ".md".to_string(), ".py".to_string(), ".js".to_string(), ".html".to_string(), ".css".to_string(), ".json".to_string(), ".xml".to_string(), ".csv".to_string(), ".log".to_string(), ".yaml".to_string(), ".yml".to_string(), ".ini".to_string(), ".cfg".to_string(), ".conf".to_string(), ".rst".to_string(), ".tex".to_string(), ".sh".to_string(), ".bat".to_string(), ".ps1".to_string(), ".c".to_string(), ".cpp".to_string(), ".h".to_string(), ".java".to_string(), ".go".to_string(), ".rs".to_string(), ".php".to_string(), ".rb".to_string(), ".swift".to_string(), ".kt".to_string(), ".pdf".to_string(), ".png".to_string(), ".jpg".to_string(), ".jpeg".to_string(), ".bmp".to_string(), ".tiff".to_string(), ".webp".to_string()]),
            skip_dirs: HashSet::from(["__pycache__".to_string(), ".git".to_string(), ".svn".to_string(), "node_modules".to_string(), ".venv".to_string(), "venv".to_string(), "env".to_string(), ".env".to_string(), "dist".to_string(), "build".to_string(), ".idea".to_string(), ".vscode".to_string(), "target".to_string(), ".cache".to_string(), "cache".to_string(), "tmp".to_string(), "temp".to_string(), ".pytest_cache".to_string(), ".mypy_cache".to_string()]),
            max_file_size: ((10 * 1024) * 1024),
            max_pdf_size: ((50 * 1024) * 1024),
            extractor: Default::default(),
        }
    }
    /// Check if directory should be skipped.
    pub fn should_skip_dir(&self, dir_path: PathBuf) -> bool {
        // Check if directory should be skipped.
        (self.skip_dirs.contains(&dir_path.file_name().unwrap_or_default().to_str().unwrap_or("")) || dir_path.file_name().unwrap_or_default().to_str().unwrap_or("").starts_with(&*".".to_string()))
    }
    /// Check if file should be indexed.
    pub fn should_index_file(&mut self, file_path: PathBuf) -> Result<bool> {
        // Check if file should be indexed.
        let mut suffix = file_path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        if !self.supported_extensions.contains(&suffix) {
            false
        }
        // try:
        {
            let mut size_limit = if suffix == ".pdf".to_string() { self.max_pdf_size } else { self.max_file_size };
            if file_path.stat().st_size > size_limit {
                logger.debug(format!("[DirScanner] Skipping large file: {}", file_path));
                false
            }
        }
        // except Exception as _e:
        Ok(true)
    }
    /// Safely read file content based on type.
    pub fn read_file_safe(&mut self, file_path: PathBuf) -> Result<String> {
        // Safely read file content based on type.
        let mut suffix = file_path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        if (HashSet::from([".pdf".to_string(), ".png".to_string(), ".jpg".to_string(), ".jpeg".to_string(), ".bmp".to_string(), ".tiff".to_string(), ".webp".to_string()]).contains(&suffix) && self.extractor) {
            // try:
            {
                let (mut chunks, mut stats) = self.extractor.process(file_path);
                if chunks {
                    chunks.iter().map(|c| c.text).collect::<Vec<_>>().join(&"\n\n".to_string())
                }
                "".to_string()
            }
            // except Exception as e:
        }
        let mut encodings = vec!["utf-8".to_string(), "latin-1".to_string(), "cp1252".to_string(), "iso-8859-1".to_string()];
        for encoding in encodings.iter() {
            // try:
            {
                let mut f = File::open(file_path)?;
                {
                    f.read()
                }
            }
            // except (UnicodeDecodeError, UnicodeError) as _e:
            // except Exception as e:
        }
        Ok("".to_string())
    }
}

/// Scan part1 part 2.
pub fn _scan_part1_part2(r#self: String) -> Result<()> {
    // Scan part1 part 2.
    let get_stats = || {
        // Get scanning statistics.
        if !self.documents {
            HashMap::new()
        }
        let mut extensions = HashMap::new();
        for doc in self.documents.iter() {
            let mut ext = doc["extension".to_string()];
            extensions[ext] = (extensions.get(&ext).cloned().unwrap_or(0) + 1);
        }
        HashMap::from([("total_files".to_string(), self.documents.len()), ("total_size".to_string(), self.documents.iter().map(|doc| doc["size".to_string()]).collect::<Vec<_>>().iter().sum::<i64>()), ("extensions".to_string(), extensions), ("root_dir".to_string(), self.root_dir.to_string())])
    };
    let check_project_dependencies = || {
        // Analyze project imports and check for updates.
        // try:
        {
            // TODO: import sys
            sys::path.push(self.root_dir.to_string());
            // try:
            {
                // TODO: import dependency_manager
                safe_print(format!("\n📦 Analyzing dependencies for: {}", self.root_dir));
                dependency_manager.generate_requirements(self.root_dir);
                dependency_manager.check_updates();
                true
            }
            // except ImportError as _e:
        }
        // except Exception as e:
    Ok(})
}

/// Scan part 1.
pub fn _scan_part1(r#self: String) -> Result<()> {
    // Scan part 1.
    logger.info(format!("[DirScanner] ✅ Completed: {} files in {:.2}s", self.documents.len(), total_time));
    logger.info(format!("[DirScanner] Total content: {:.1} KB ({:.2} MB)", (total_size / 1024), (total_size / (1024 * 1024))));
    self.documents
    let scan = |max_files| {
        // Recursively scan directory and extract text content.
        let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut file_count = 0;
        logger.info(format!("[DirScanner] Starting scan of {}", self.root_dir));
        for (root, dirs, files) in os::walk(self.root_dir).iter() {
            let mut root_path = PathBuf::from(root);
            dirs[..] = dirs.iter().filter(|d| !self.should_skip_dir((root_path / d))).map(|d| d).collect::<Vec<_>>();
            for file in files.iter() {
                if file_count < max_files {
                    continue;
                }
                logger.info(format!("[DirScanner] Reached max files limit: {}", max_files));
                break;
                let mut file_path = (root_path / file);
                if !self.should_index_file(file_path) {
                    continue;
                }
                // try:
                {
                    let mut file_start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                    let mut content = self.read_file_safe(file_path);
                    if content.len() > 50 {
                        let mut relative_path = file_path.relative_to(self.root_dir);
                        self.documents.push(HashMap::from([("url".to_string(), file_path.to_string()), ("title".to_string(), relative_path.to_string()), ("content".to_string(), content), ("extension".to_string(), file_path.extension().unwrap_or_default().to_str().unwrap_or("")), ("size".to_string(), content.len())]));
                        let mut file_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - file_start);
                        file_count += 1;
                        if (file_count % 100) == 0 {
                            logger.info(format!("[DirScanner] Indexed {} files...", file_count));
                        }
                        logger.debug(format!("[DirScanner] ✅ Indexed: {} ({} chars) | Time: {:.2}s", relative_path, content.len(), file_time));
                    }
                }
                // except Exception as e:
            }
            if file_count >= max_files {
                break;
            }
        }
        (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
        self.documents.iter().map(|doc| doc["size".to_string()]).collect::<Vec<_>>().iter().sum::<i64>();
        _scan_part1(self);
    };
    Ok(_scan_part1_part2(self))
}
