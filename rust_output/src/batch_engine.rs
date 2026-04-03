/// zena_mode/batch_engine::py - Batch Analysis & AI Code Review Engine
/// Handles processing multiple files, generating AI reviews, and persisting results.

use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Orchestrates batch processing of multiple files for deep code review.
#[derive(Debug, Clone)]
pub struct BatchAnalyzer {
    pub backend: String,
    pub is_running: bool,
    pub _current_task: Option<asyncio::Task>,
}

impl BatchAnalyzer {
    pub fn new(backend: AsyncZenAIBackend) -> Self {
        Self {
            backend,
            is_running: false,
            _current_task: None,
        }
    }
    /// Main entry point for batch analysis.
    /// 
    /// Args:
    /// file_paths: List of absolute paths to files.
    /// on_progress: Callback taking (status_message, percentage_0_to_1).
    pub async fn analyze_files(&mut self, file_paths: Vec<String>, on_progress: Option<Box<dyn Fn(serde_json::Value)>>) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Main entry point for batch analysis.
        // 
        // Args:
        // file_paths: List of absolute paths to files.
        // on_progress: Callback taking (status_message, percentage_0_to_1).
        self.is_running = true;
        let mut results = vec![];
        let mut total_files = file_paths.len();
        if on_progress {
            on_progress(_("batch.progress_start".to_string()), 0.0_f64);
        }
        for (i, path_str) in file_paths.iter().enumerate().iter() {
            if !self.is_running {
                break;
            }
            let mut path = PathBuf::from(path_str);
            let mut filename = path.file_name().unwrap_or_default().to_str().unwrap_or("");
            let mut progress = (i / total_files);
            if on_progress {
                on_progress(format!(_("batch.reading".to_string()), /* filename= */ filename), progress);
            }
            // try:
            {
                let mut content = path.read_to_string(), /* errors= */ "ignore".to_string());
            }
            // except Exception as e:
            if on_progress {
                on_progress(_("batch.ai_review".to_string()), (progress + (0.5_f64 / total_files)));
            }
            let mut prompt = format!("Perform a deep code review of the following file: {}\n\n```\n{}\n```\n\nProvide analysis on: logic issues, security risks, performance improvements, and best practices.", filename, content);
            let mut full_review = "".to_string();
            // async for
            while let Some(chunk) = self.backend.send_message_async(prompt).next().await {
                full_review += chunk;
            }
            let mut analysis_filename = format!("{}_zena_analisis.md", path.file_stem().unwrap_or_default().to_str().unwrap_or(""));
            let mut analysis_path = (path.parent().unwrap_or(std::path::Path::new("")) / analysis_filename);
            if on_progress {
                on_progress(format!(_("batch.writing".to_string()), /* filename= */ analysis_filename), (progress + (0.8_f64 / total_files)));
            }
            // try:
            {
                let mut f = File::create(analysis_path)?;
                {
                    f.write(format!("# ZenAI Analysis: {}\n\n", filename));
                    f.write(full_review);
                }
                results.push(HashMap::from([("path".to_string(), path_str), ("status".to_string(), "completed".to_string()), ("report".to_string(), analysis_path.to_string())]));
            }
            // except Exception as e:
        }
        self.is_running = false;
        if on_progress {
            on_progress(_("batch.complete".to_string()), 1.0_f64);
        }
        Ok(HashMap::from([("total".to_string(), total_files), ("completed".to_string(), results.iter().filter(|r| r["status".to_string()] == "completed".to_string()).map(|r| r).collect::<Vec<_>>().len()), ("results".to_string(), results)]))
    }
    /// Cancel the current analysis.
    pub fn stop(&mut self) -> () {
        // Cancel the current analysis.
        self.is_running = false;
        if self._current_task {
            self._current_task.cancel();
        }
    }
}
