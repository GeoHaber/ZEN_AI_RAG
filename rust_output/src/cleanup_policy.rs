/// cleanup_policy::py - Automated cleanup for uploads directory

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _CLEANUP_POLICY: std::sync::LazyLock<Option<UploadCleanupPolicy>> = std::sync::LazyLock::new(|| None);

/// Manages cleanup of old uploaded files.
#[derive(Debug, Clone)]
pub struct UploadCleanupPolicy {
    pub upload_dir: PathBuf,
    pub max_age_hours: String,
    pub max_files: String,
    pub max_size_mb: String,
    pub _lock: std::sync::Mutex<()>,
}

impl UploadCleanupPolicy {
    /// Initialize cleanup policy.
    /// 
    /// Args:
    /// upload_dir: Directory containing uploaded files
    /// max_age_hours: Delete files older than this (hours)
    /// max_files: Maximum number of files to keep
    /// max_size_mb: Maximum total size in MB
    pub fn new(upload_dir: PathBuf, max_age_hours: i64, max_files: i64, max_size_mb: i64) -> Self {
        Self {
            upload_dir: PathBuf::from(upload_dir),
            max_age_hours,
            max_files,
            max_size_mb,
            _lock: std::sync::Mutex::new(()),
        }
    }
}

/// Cleanup part1 part 2.
pub fn _cleanup_part1_part2(r#self: String) -> () {
    // Cleanup part1 part 2.
    let get_stats = || {
        // Get current upload directory stats.
        // 
        // Returns:
        // dict with stats: {'count': int, 'size_mb': float, 'oldest_hours': float}
        let _ctx = self._lock;
        {
            if !self.upload_dir.exists() {
                HashMap::from([("count".to_string(), 0), ("size_mb".to_string(), 0.0_f64), ("oldest_hours".to_string(), 0.0_f64)])
            }
            let mut files = self.upload_dir.glob("*".to_string()).iter().filter(|f| f.is_file()).map(|f| f).collect::<Vec<_>>();
            if !files {
                HashMap::from([("count".to_string(), 0), ("size_mb".to_string(), 0.0_f64), ("oldest_hours".to_string(), 0.0_f64)])
            }
            let mut total_size = files.iter().map(|f| f.stat().st_size).collect::<Vec<_>>().iter().sum::<i64>();
            let mut oldest_mtime = files.iter().map(|f| f.stat().st_mtime).collect::<Vec<_>>().iter().min().unwrap();
            let mut oldest_hours = ((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - oldest_mtime) / 3600);
            HashMap::from([("count".to_string(), files.len()), ("size_mb".to_string(), (((total_size / (1024 * 1024)) as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("oldest_hours".to_string(), ((oldest_hours as f64) * 10f64.powi(1)).round() / 10f64.powi(1))])
        }
    };
}

/// Continue _cleanup_part1 logic.
pub fn _cleanup_part1_continued(r#self: String, files_by_time: String, freed_mb: String, size: String) -> Result<()> {
    // Continue _cleanup_part1 logic.
    let cleanup = || {
        // Run cleanup based on policy.
        // 
        // Returns:
        // dict with cleanup stats: {'deleted': int, 'freed_mb': float}
        let _ctx = self._lock;
        {
            if !self.upload_dir.exists() {
                logger.debug(format!("[Cleanup] Upload directory does not exist: {}", self.upload_dir));
                HashMap::from([("deleted".to_string(), 0), ("freed_mb".to_string(), 0.0_f64)])
            }
            let mut files = self.upload_dir.glob("*".to_string()).into_iter().collect::<Vec<_>>();
            if !files {
                HashMap::from([("deleted".to_string(), 0), ("freed_mb".to_string(), 0.0_f64)])
            }
            let mut deleted_count = 0;
            let mut freed_bytes = 0;
            let mut current_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut max_age_seconds = (self.max_age_hours * 3600);
            for file_path in files.iter() {
                if !file_path.is_file() {
                    continue;
                }
                let mut file_age = (current_time - file_path.stat().st_mtime);
                if file_age > max_age_seconds {
                    // try:
                    {
                        let mut size = file_path.stat().st_size;
                        file_path.remove_file().ok();
                        deleted_count += 1;
                        freed_bytes += size;
                        logger.info(format!("[Cleanup] Deleted old file: {} (age: {:.1}h)", file_path.file_name().unwrap_or_default().to_str().unwrap_or(""), (file_age / 3600)));
                    }
                    // except Exception as e:
                }
            }
            let mut files = self.upload_dir.glob("*".to_string()).iter().filter(|f| f.is_file()).map(|f| f).collect::<Vec<_>>();
            if files.len() > self.max_files {
                let mut files_by_time = { let mut v = files.clone(); v.sort(); v };
                let mut files_to_delete = (files.len() - self.max_files);
                for file_path in files_by_time[..files_to_delete].iter() {
                    // try:
                    {
                        let mut size = file_path.stat().st_size;
                        file_path.remove_file().ok();
                        deleted_count += 1;
                        freed_bytes += size;
                        logger.info(format!("[Cleanup] Deleted excess file: {}", file_path.file_name().unwrap_or_default().to_str().unwrap_or("")));
                    }
                    // except Exception as e:
                }
            }
            let mut files = self.upload_dir.glob("*".to_string()).iter().filter(|f| f.is_file()).map(|f| f).collect::<Vec<_>>();
            (files.iter().map(|f| f.stat().st_size).collect::<Vec<_>>().iter().sum::<i64>() / (1024 * 1024));
        }
        _cleanup_part1(self);
    };
    Ok(_cleanup_part1_part2(self))
}

/// Cleanup part 1.
pub fn _cleanup_part1(r#self: String) -> Result<()> {
    // Cleanup part 1.
    if total_size_mb > self.max_size_mb {
        let mut files_by_time = { let mut v = files.clone(); v.sort(); v };
        for file_path in files_by_time.iter() {
            if total_size_mb <= self.max_size_mb {
                break;
            }
            // try:
            {
                let mut size = file_path.stat().st_size;
                file_path.remove_file().ok();
                deleted_count += 1;
                freed_bytes += size;
                total_size_mb -= (size / (1024 * 1024));
                logger.info(format!("[Cleanup] Deleted oversized file: {}", file_path.file_name().unwrap_or_default().to_str().unwrap_or("")));
            }
            // except Exception as e:
        }
    }
    let mut freed_mb = (freed_bytes / (1024 * 1024));
    if deleted_count > 0 {
        logger.info(format!("[Cleanup] Completed: {} files deleted, {:.2} MB freed", deleted_count, freed_mb));
    }
    HashMap::from([("deleted".to_string(), deleted_count), ("freed_mb".to_string(), ((freed_mb as f64) * 10f64.powi(2)).round() / 10f64.powi(2))])
    Ok(_cleanup_part1_continued(self, files_by_time, freed_mb, size))
}

/// Get or create global cleanup policy instance.
pub fn get_cleanup_policy(upload_dir: PathBuf) -> UploadCleanupPolicy {
    // Get or create global cleanup policy instance.
    // global/nonlocal _cleanup_policy
    if _cleanup_policy.is_none() {
        if upload_dir.is_none() {
            let mut upload_dir = (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / "uploads".to_string());
        }
        let mut _cleanup_policy = UploadCleanupPolicy(upload_dir, /* max_age_hours= */ 24, /* max_files= */ 100, /* max_size_mb= */ 500);
    }
    _cleanup_policy
}
