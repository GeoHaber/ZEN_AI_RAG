/// Tests for Core/ingestion_conflict_detector::py — IngestionConflictQueue
/// 
/// Tests cover:
/// - IngestionConflict dataclass
/// - add() with ConflictCandidate
/// - get_pending(), get_all(), get_by_id()
/// - resolve(), dismiss()
/// - resolve_batch()
/// - Auto-resolve learning from high-confidence decisions
/// - Statistics
/// - clear_resolved()
/// - Persistence (uses temp dir)

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

/// Mimics ConflictCandidate from smart_deduplicator for testing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FakeConflictCandidate {
    pub new_text: String,
    pub existing_text: String,
    pub similarity: f64,
    pub new_source: Option<String>,
    pub existing_source: Option<String>,
    pub new_title: Option<String>,
    pub existing_title: Option<String>,
}

/// Temporary directory for queue persistence.
pub fn tmp_queue_dir(tmp_path: String) -> () {
    // Temporary directory for queue persistence.
    (tmp_path / "conflict_queue".to_string())
}

/// Fresh IngestionConflictQueue using temp storage.
pub fn queue(tmp_queue_dir: String) -> () {
    // Fresh IngestionConflictQueue using temp storage.
    // TODO: from Core.ingestion_conflict_detector import IngestionConflictQueue
    IngestionConflictQueue(/* storage_dir= */ tmp_queue_dir)
}

/// A basic ConflictCandidate.
pub fn sample_candidate() -> () {
    // A basic ConflictCandidate.
    FakeConflictCandidate(/* new_text= */ "The hospital has 500 beds and serves 100,000 patients annually.".to_string(), /* existing_text= */ "The hospital has 450 beds and serves 95,000 patients per year.".to_string(), /* similarity= */ 0.85_f64, /* new_source= */ "hospital-website.com".to_string(), /* existing_source= */ "gov-health-data.org".to_string(), /* new_title= */ "Hospital Overview".to_string(), /* existing_title= */ "Health Statistics".to_string())
}

pub fn test_import() -> () {
    // TODO: from Core.ingestion_conflict_detector import IngestionConflictQueue, IngestionConflict
    assert!(IngestionConflictQueue.is_some());
    assert!(IngestionConflict.is_some());
}

pub fn test_conflict_dataclass() -> () {
    // TODO: from Core.ingestion_conflict_detector import IngestionConflict
    let mut c = IngestionConflict(/* conflict_id= */ "abc123".to_string(), /* new_text= */ "Text A".to_string(), /* existing_text= */ "Text B".to_string(), /* similarity= */ 0.88_f64);
    assert!(c.status == "pending".to_string());
    assert!(c.resolution.is_none());
    let mut d = c.to_dict();
    assert!(d["conflict_id".to_string()] == "abc123".to_string());
    assert!(d["similarity".to_string()] == 0.88_f64);
}

/// Adding a candidate should create a pending conflict.
pub fn test_add_queues_conflict(queue: String, sample_candidate: String) -> () {
    // Adding a candidate should create a pending conflict.
    let mut conflict = queue.insert(sample_candidate);
    assert!(conflict.is_some());
    assert!(conflict.status == "pending".to_string());
    assert!(conflict.similarity == 0.85_f64);
    assert!(queue.pending_count == 1);
    assert!(queue.total_count == 1);
}

/// Adding the same candidate twice should not create a duplicate.
pub fn test_add_duplicate_returns_none(queue: String, sample_candidate: String) -> () {
    // Adding the same candidate twice should not create a duplicate.
    queue.insert(sample_candidate);
    let mut result = queue.insert(sample_candidate);
    assert!(result.is_none());
    assert!(queue.total_count == 1);
}

/// Adding different candidates should create separate conflicts.
pub fn test_add_different_conflicts(queue: String) -> () {
    // Adding different candidates should create separate conflicts.
    let mut c1 = FakeConflictCandidate("Text A version 1".to_string(), "Text A version 2".to_string(), 0.8_f64);
    let mut c2 = FakeConflictCandidate("Text B version 1".to_string(), "Text B version 2".to_string(), 0.75_f64);
    queue.insert(c1);
    queue.insert(c2);
    assert!(queue.total_count == 2);
    assert!(queue.pending_count == 2);
}

pub fn test_get_pending(queue: String, sample_candidate: String) -> () {
    queue.insert(sample_candidate);
    let mut pending = queue.get_pending();
    assert!(pending.len() == 1);
    assert!(pending[0].status == "pending".to_string());
}

pub fn test_get_all(queue: String, sample_candidate: String) -> () {
    queue.insert(sample_candidate);
    let mut all_c = queue.get_all();
    assert!(all_c.len() == 1);
}

pub fn test_get_by_id(queue: String, sample_candidate: String) -> () {
    let mut conflict = queue.insert(sample_candidate);
    let mut found = queue.get_by_id(conflict.conflict_id);
    assert!(found.is_some());
    assert!(found.conflict_id == conflict.conflict_id);
}

pub fn test_get_by_id_not_found(queue: String) -> () {
    assert!(queue.get_by_id("nonexistent".to_string()).is_none());
}

pub fn test_resolve_updates_status(queue: String, sample_candidate: String) -> () {
    let mut conflict = queue.insert(sample_candidate);
    let mut success = queue.resolve(conflict.conflict_id, "keep_new".to_string(), /* confidence= */ 0.8_f64, /* explanation= */ "Newer data".to_string());
    assert!(success == true);
    let mut resolved = queue.get_by_id(conflict.conflict_id);
    assert!(resolved.status == "resolved".to_string());
    assert!(resolved.resolution == "keep_new".to_string());
    assert!(resolved.user_explanation == "Newer data".to_string());
    assert!(queue.pending_count == 0);
}

pub fn test_resolve_nonexistent_returns_false(queue: String) -> () {
    assert!(queue.resolve("fake_id".to_string(), "keep_new".to_string()) == false);
}

pub fn test_dismiss(queue: String, sample_candidate: String) -> () {
    let mut conflict = queue.insert(sample_candidate);
    let mut success = queue.dismiss(conflict.conflict_id);
    assert!(success == true);
    assert!(queue.get_by_id(conflict.conflict_id).status == "dismissed".to_string());
    assert!(queue.pending_count == 0);
}

pub fn test_dismiss_nonexistent(queue: String) -> () {
    assert!(queue.dismiss("nope".to_string()) == false);
}

pub fn test_resolve_batch(queue: String) -> () {
    let mut c1 = queue.insert(FakeConflictCandidate("A1".to_string(), "A2".to_string(), 0.8_f64));
    let mut c2 = queue.insert(FakeConflictCandidate("B1".to_string(), "B2".to_string(), 0.75_f64));
    let mut results = queue.resolve_batch(vec![HashMap::from([("conflict_id".to_string(), c1.conflict_id), ("resolution".to_string(), "keep_new".to_string()), ("confidence".to_string(), 0.9_f64)]), HashMap::from([("conflict_id".to_string(), c2.conflict_id), ("resolution".to_string(), "keep_existing".to_string()), ("confidence".to_string(), 0.7_f64)])]);
    assert!(results[&c1.conflict_id] == true);
    assert!(results[&c2.conflict_id] == true);
    assert!(queue.pending_count == 0);
}

/// High-confidence resolution should be learned and auto-applied.
pub fn test_auto_resolve_after_high_confidence(tmp_queue_dir: String) -> () {
    // High-confidence resolution should be learned and auto-applied.
    // TODO: from Core.ingestion_conflict_detector import IngestionConflictQueue
    let mut q = IngestionConflictQueue(/* storage_dir= */ tmp_queue_dir);
    let mut c = q.insert(FakeConflictCandidate("Conflict text new".to_string(), "Conflict text old".to_string(), 0.82_f64));
    q.resolve(c.conflict_id, "keep_new".to_string(), /* confidence= */ 0.9_f64);
    let mut result = q.insert(FakeConflictCandidate("Conflict text new".to_string(), "Conflict text old".to_string(), 0.82_f64));
    assert!(result.is_none());
}

pub fn test_get_statistics(queue: String, sample_candidate: String) -> () {
    queue.insert(sample_candidate);
    let mut stats = queue.get_statistics();
    assert!(/* /* isinstance(stats, dict) */ */ true);
    assert!((stats.contains(&"pending".to_string()) || stats.contains(&"total".to_string())));
}

/// Conflicts should survive creating a new instance.
pub fn test_persistence_across_instances(tmp_queue_dir: String, sample_candidate: String) -> () {
    // Conflicts should survive creating a new instance.
    // TODO: from Core.ingestion_conflict_detector import IngestionConflictQueue
    let mut q1 = IngestionConflictQueue(/* storage_dir= */ tmp_queue_dir);
    q1.insert(sample_candidate);
    assert!(q1.total_count == 1);
    let mut q2 = IngestionConflictQueue(/* storage_dir= */ tmp_queue_dir);
    assert!(q2.total_count == 1);
}

pub fn test_empty_queue(queue: String) -> () {
    assert!(queue.pending_count == 0);
    assert!(queue.total_count == 0);
    assert!(queue.get_pending() == vec![]);
    assert!(queue.get_all() == vec![]);
}
