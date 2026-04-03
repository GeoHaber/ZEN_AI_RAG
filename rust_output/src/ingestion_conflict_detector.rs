/// Core/ingestion_conflict_detector::py — HITL Conflict Queue for RAG Ingestion
/// 
/// When the SmartDeduplicator finds chunks that are semantically similar but
/// textually different (potential conflicts), this module:
/// 1. Queues them for human review
/// 2. Provides a batch review API for the Streamlit UI
/// 3. Records user decisions and updates chunk metadata in Qdrant
/// 4. Learns from past decisions to auto-resolve trivial conflicts
/// 
/// Integrates with:
/// - Core/smart_deduplicator::py (ConflictCandidate input)
/// - Core/human_loop_resolver::py (HumanLoopConflictResolver)
/// - ui/human_conflict_ui.py (Streamlit display)
/// - zena_mode/rag_pipeline::py (Qdrant metadata updates)
/// 
/// Usage (in rag_pipeline::py build_index):
/// conflict_queue = IngestionConflictQueue()
/// 
/// for chunk in chunks:
/// result = dedup::should_skip_chunk(text, embedding)
/// if result.conflict:
/// conflict_queue.add(result.conflict)
/// 
/// # After ingestion, present conflicts in UI
/// pending = conflict_queue.get_pending()

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// A pair of chunks flagged during ingestion as semantically similar
/// but containing potentially conflicting information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionConflict {
    pub conflict_id: String,
    pub new_text: String,
    pub existing_text: String,
    pub similarity: f64,
    pub new_source: Option<String>,
    pub existing_source: Option<String>,
    pub new_title: Option<String>,
    pub existing_title: Option<String>,
    pub detected_at: f64,
    pub status: String,
    pub resolution: Option<String>,
    pub user_confidence: f64,
    pub user_explanation: Option<String>,
    pub resolved_at: Option<f64>,
}

impl IngestionConflict {
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        asdict(self)
    }
}

/// Manages a queue of conflicts detected during RAG ingestion.
/// 
/// Persists to disk so conflicts survive app restarts.
#[derive(Debug, Clone)]
pub struct IngestionConflictQueue {
    pub storage_dir: String,
    pub _queue: Vec<IngestionConflict>,
    pub _auto_resolve_cache: HashMap<String, String>,
}

impl IngestionConflictQueue {
    pub fn new(storage_dir: Option<PathBuf>) -> Self {
        Self {
            storage_dir: (storage_dir || PathBuf::from("data/conflict_queue".to_string())),
            _queue: Vec::new(),
            _auto_resolve_cache: HashMap::new(),
        }
    }
    /// Add a ConflictCandidate from SmartDeduplicator to the queue.
    /// 
    /// Args:
    /// conflict_candidate: ConflictCandidate dataclass from smart_deduplicator::py
    /// 
    /// Returns:
    /// IngestionConflict if queued, None if auto-resolved.
    pub fn add(&mut self, conflict_candidate: String) -> Option<IngestionConflict> {
        // Add a ConflictCandidate from SmartDeduplicator to the queue.
        // 
        // Args:
        // conflict_candidate: ConflictCandidate dataclass from smart_deduplicator::py
        // 
        // Returns:
        // IngestionConflict if queued, None if auto-resolved.
        let mut cid = hashlib::md5(format!("{}|{}", conflict_candidate.new_text[..100], conflict_candidate.existing_text[..100]).as_bytes().to_vec()).hexdigest()[..12];
        if self._queue.iter().map(|c| c.conflict_id == cid).collect::<Vec<_>>().iter().any(|v| *v) {
            None
        }
        let mut fingerprint = self._fingerprint(conflict_candidate.new_text, conflict_candidate.existing_text);
        if self._auto_resolve_cache.contains(&fingerprint) {
            let mut resolution = self._auto_resolve_cache[&fingerprint];
            logger.info(format!("[ConflictQueue] Auto-resolved conflict {} → {}", cid, resolution));
            let mut conflict = IngestionConflict(/* conflict_id= */ cid, /* new_text= */ conflict_candidate.new_text, /* existing_text= */ conflict_candidate.existing_text, /* similarity= */ conflict_candidate.similarity, /* new_source= */ conflict_candidate.new_source, /* existing_source= */ conflict_candidate.existing_source, /* new_title= */ conflict_candidate.new_title, /* existing_title= */ conflict_candidate.existing_title, /* detected_at= */ /* getattr */ std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64(), /* status= */ "auto_resolved".to_string(), /* resolution= */ resolution, /* resolved_at= */ std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64());
            self._queue.push(conflict);
            self._save_one(conflict);
            None
        }
        let mut conflict = IngestionConflict(/* conflict_id= */ cid, /* new_text= */ conflict_candidate.new_text, /* existing_text= */ conflict_candidate.existing_text, /* similarity= */ conflict_candidate.similarity, /* new_source= */ conflict_candidate.new_source, /* existing_source= */ conflict_candidate.existing_source, /* new_title= */ conflict_candidate.new_title, /* existing_title= */ conflict_candidate.existing_title, /* detected_at= */ /* getattr */ std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64());
        self._queue.push(conflict);
        self._save_one(conflict);
        logger.info(format!("[ConflictQueue] Queued conflict {} (sim={:.2})", cid, conflict_candidate.similarity));
        conflict
    }
    /// Get all unresolved conflicts.
    pub fn get_pending(&mut self) -> Vec<IngestionConflict> {
        // Get all unresolved conflicts.
        self._queue.iter().filter(|c| c.status == "pending".to_string()).map(|c| c).collect::<Vec<_>>()
    }
    /// Get all conflicts (pending + resolved).
    pub fn get_all(&self) -> Vec<IngestionConflict> {
        // Get all conflicts (pending + resolved).
        self._queue.into_iter().collect::<Vec<_>>()
    }
    /// Get a specific conflict by ID.
    pub fn get_by_id(&mut self, conflict_id: String) -> Option<IngestionConflict> {
        // Get a specific conflict by ID.
        for c in self._queue.iter() {
            if c.conflict_id == conflict_id {
                c
            }
        }
        None
    }
    pub fn pending_count(&self) -> i64 {
        self._queue.iter().filter(|c| c.status == "pending".to_string()).map(|c| 1).collect::<Vec<_>>().iter().sum::<i64>()
    }
    pub fn total_count(&self) -> i64 {
        self._queue.len()
    }
    /// Record user's resolution for a conflict.
    /// 
    /// Args:
    /// conflict_id: ID of the conflict to resolve.
    /// resolution: One of "keep_new", "keep_existing", "keep_both", "discard_both".
    /// confidence: User confidence in the decision (0–1).
    /// explanation: Optional free-text explanation.
    /// 
    /// Returns:
    /// true if conflict was found and resolved.
    pub fn resolve(&mut self, conflict_id: String, resolution: String, confidence: f64, explanation: Option<String>) -> bool {
        // Record user's resolution for a conflict.
        // 
        // Args:
        // conflict_id: ID of the conflict to resolve.
        // resolution: One of "keep_new", "keep_existing", "keep_both", "discard_both".
        // confidence: User confidence in the decision (0–1).
        // explanation: Optional free-text explanation.
        // 
        // Returns:
        // true if conflict was found and resolved.
        let mut conflict = self.get_by_id(conflict_id);
        if !conflict {
            false
        }
        conflict.status = "resolved".to_string();
        conflict.resolution = resolution;
        conflict.user_confidence = confidence;
        conflict.user_explanation = explanation;
        conflict.resolved_at = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        self._save_one(conflict);
        if confidence >= 0.85_f64 {
            let mut fingerprint = self._fingerprint(conflict.new_text, conflict.existing_text);
            self._auto_resolve_cache[fingerprint] = resolution;
            self._save_auto_resolve();
        }
        logger.info(format!("[ConflictQueue] Resolved {} → {} (confidence={:.0%})", conflict_id, resolution, confidence));
        true
    }
    /// Dismiss a conflict without resolution.
    pub fn dismiss(&mut self, conflict_id: String) -> bool {
        // Dismiss a conflict without resolution.
        let mut conflict = self.get_by_id(conflict_id);
        if !conflict {
            false
        }
        conflict.status = "dismissed".to_string();
        conflict.resolved_at = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        self._save_one(conflict);
        true
    }
    /// Resolve multiple conflicts at once.
    /// 
    /// Args:
    /// resolutions: List of {conflict_id, resolution, confidence?, explanation?}
    /// 
    /// Returns:
    /// {conflict_id: success_bool}
    pub fn resolve_batch(&mut self, resolutions: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> HashMap<String, bool> {
        // Resolve multiple conflicts at once.
        // 
        // Args:
        // resolutions: List of {conflict_id, resolution, confidence?, explanation?}
        // 
        // Returns:
        // {conflict_id: success_bool}
        let mut results = HashMap::new();
        for r in resolutions.iter() {
            let mut cid = r["conflict_id".to_string()];
            results[cid] = self.resolve(cid, r["resolution".to_string()], r.get(&"confidence".to_string()).cloned().unwrap_or(0.7_f64), r.get(&"explanation".to_string()).cloned());
        }
        results
    }
    /// Get queue statistics.
    pub fn get_statistics(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Get queue statistics.
        let mut pending = self._queue.iter().filter(|c| c.status == "pending".to_string()).map(|c| c).collect::<Vec<_>>();
        let mut resolved = self._queue.iter().filter(|c| c.status == "resolved".to_string()).map(|c| c).collect::<Vec<_>>();
        let mut auto_resolved = self._queue.iter().filter(|c| c.status == "auto_resolved".to_string()).map(|c| c).collect::<Vec<_>>();
        let mut dismissed = self._queue.iter().filter(|c| c.status == "dismissed".to_string()).map(|c| c).collect::<Vec<_>>();
        HashMap::from([("total".to_string(), self._queue.len()), ("pending".to_string(), pending.len()), ("resolved".to_string(), resolved.len()), ("auto_resolved".to_string(), auto_resolved.len()), ("dismissed".to_string(), dismissed.len()), ("avg_similarity".to_string(), if self._queue { (self._queue.iter().map(|c| c.similarity).collect::<Vec<_>>().iter().sum::<i64>() / self._queue.len()) } else { 0.0_f64 }), ("avg_confidence".to_string(), if resolved { (resolved.iter().map(|c| c.user_confidence).collect::<Vec<_>>().iter().sum::<i64>() / resolved.len()) } else { 0.0_f64 }), ("auto_resolve_patterns".to_string(), self._auto_resolve_cache.len())])
    }
    /// Alias for get_statistics() for UI compatibility (e.g. conflict_queue_panel).
    pub fn get_stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Alias for get_statistics() for UI compatibility (e.g. conflict_queue_panel).
        self.get_statistics()
    }
    /// Persist one conflict to disk.
    pub fn _save_one(&mut self, conflict: IngestionConflict) -> Result<()> {
        // Persist one conflict to disk.
        let mut path = (self.storage_dir / format!("{}.json", conflict.conflict_id));
        // try:
        {
            pathstd::fs::write(&serde_json::to_string(&conflict.to_dict()).unwrap(), /* encoding= */ "utf-8".to_string());
        }
        // except Exception as e:
    }
    /// Load all conflicts from disk.
    pub fn _load(&mut self) -> Result<()> {
        // Load all conflicts from disk.
        self._queue.clear();
        for path in { let mut v = self.storage_dir.glob("*.json".to_string()).clone(); v.sort(); v }.iter() {
            if path.file_name().unwrap_or_default().to_str().unwrap_or("") == "_auto_resolve.json".to_string() {
                continue;
            }
            // try:
            {
                let mut data = serde_json::from_str(&path.read_to_string())).unwrap();
                let mut conflict = IngestionConflict(/* ** */ data);
                self._queue.push(conflict);
            }
            // except Exception as e:
        }
        let mut ar_path = (self.storage_dir / "_auto_resolve.json".to_string());
        if ar_path.exists() {
            // try:
            {
                self._auto_resolve_cache = serde_json::from_str(&ar_path.read_to_string())).unwrap();
            }
            // except Exception as _e:
        }
        if self._queue {
            let mut pending = self._queue.iter().filter(|c| c.status == "pending".to_string()).map(|c| 1).collect::<Vec<_>>().iter().sum::<i64>();
            logger.info(format!("[ConflictQueue] Loaded {} conflicts ({} pending)", self._queue.len(), pending));
        }
    }
    /// Persist auto-resolve cache.
    pub fn _save_auto_resolve(&mut self) -> Result<()> {
        // Persist auto-resolve cache.
        let mut path = (self.storage_dir / "_auto_resolve.json".to_string());
        // try:
        {
            pathstd::fs::write(&serde_json::to_string(&self._auto_resolve_cache).unwrap(), /* encoding= */ "utf-8".to_string());
        }
        // except Exception as exc:
    }
    /// Create a content-level fingerprint for auto-resolution learning.
    /// Uses sorted content-word sets so order doesn't matter.
    pub fn _fingerprint(&self, text_a: String, text_b: String) -> String {
        // Create a content-level fingerprint for auto-resolution learning.
        // Uses sorted content-word sets so order doesn't matter.
        let mut stopwords = HashSet::from(["the".to_string(), "a".to_string(), "an".to_string(), "is".to_string(), "are".to_string(), "was".to_string(), "were".to_string(), "in".to_string(), "on".to_string(), "at".to_string(), "to".to_string(), "for".to_string(), "of".to_string()]);
        let mut a_words = { let mut v = (text_a.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>() - stopwords).clone(); v.sort(); v }[..15];
        let mut b_words = { let mut v = (text_b.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>() - stopwords).clone(); v.sort(); v }[..15];
        let mut combined = ((a_words.join(&"|".to_string()) + "||".to_string()) + b_words.join(&"|".to_string()));
        hashlib::md5(combined.as_bytes().to_vec()).hexdigest()[..12]
    }
    /// Remove resolved/dismissed conflicts from queue and disk.
    pub fn clear_resolved(&mut self) -> Result<()> {
        // Remove resolved/dismissed conflicts from queue and disk.
        let mut to_remove = self._queue.iter().filter(|c| ("resolved".to_string(), "dismissed".to_string(), "auto_resolved".to_string()).contains(&c.status)).map(|c| c).collect::<Vec<_>>();
        for c in to_remove.iter() {
            let mut path = (self.storage_dir / format!("{}.json", c.conflict_id));
            // try:
            {
                path.unlink(/* missing_ok= */ true);
            }
            // except Exception as exc:
        }
        Ok(self._queue = self._queue.iter().filter(|c| c.status == "pending".to_string()).map(|c| c).collect::<Vec<_>>())
    }
}
