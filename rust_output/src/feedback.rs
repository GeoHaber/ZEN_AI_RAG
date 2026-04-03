/// FeedbackCollector — ring-buffer feedback store with per-model aggregation.
/// 
/// Extracted from api_server::py.

use anyhow::{Result, Context};
use std::collections::HashMap;

/// Ring-buffer feedback store with per-model aggregation.
#[derive(Debug, Clone)]
pub struct FeedbackCollector {
    pub _events: deque,
    pub _total: i64,
    pub _model_stats: HashMap<String, HashMap<String, Box<dyn std::any::Any>>>,
}

impl FeedbackCollector {
    pub fn new(max_events: i64) -> Self {
        Self {
            _events: Default::default(),
            _total: 0,
            _model_stats: HashMap::new(),
        }
    }
    /// Record one piece of feedback. Returns the stored entry.
    pub fn submit(&mut self, model: String, thumbs: Option<String>, rating: Option<i64>, tags: Option<Vec<String>>, response_id: Option<String>, comment: Option<String>) -> HashMap<String, Box<dyn std::any::Any>> {
        // Record one piece of feedback. Returns the stored entry.
        let mut entry = HashMap::from([("feedback_id".to_string(), /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().hex[..12]), ("response_id".to_string(), response_id), ("model".to_string(), model), ("thumbs".to_string(), thumbs), ("rating".to_string(), rating), ("tags".to_string(), (tags || vec![])), ("comment".to_string(), comment), ("timestamp".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64())]);
        self._events.push(entry);
        self._total += 1;
        self._update_model_stats(entry);
        entry
    }
    pub fn _update_model_stats(&mut self, entry: HashMap<String, Box<dyn std::any::Any>>) -> () {
        let mut model = entry["model".to_string()];
        if !self._model_stats.contains(&model) {
            self._model_stats[model] = HashMap::from([("total".to_string(), 0), ("thumbs_up".to_string(), 0), ("thumbs_down".to_string(), 0), ("rating_sum".to_string(), 0.0_f64), ("rating_count".to_string(), 0), ("tag_counts".to_string(), HashMap::new())]);
        }
        let mut s = self._model_stats[&model];
        s["total".to_string()] += 1;
        if entry["thumbs".to_string()] == "up".to_string() {
            s["thumbs_up".to_string()] += 1;
        } else if entry["thumbs".to_string()] == "down".to_string() {
            s["thumbs_down".to_string()] += 1;
        }
        if entry["rating".to_string()].is_some() {
            s["rating_sum".to_string()] += entry["rating".to_string()];
            s["rating_count".to_string()] += 1;
        }
        for tag in entry.get(&"tags".to_string()).cloned().unwrap_or(vec![]).iter() {
            s["tag_counts".to_string()][tag] = (s["tag_counts".to_string()].get(&tag).cloned().unwrap_or(0) + 1);
        }
    }
    /// Return newest-first feedback entries.
    pub fn history(&mut self, last_n: i64, model: Option<String>) -> Vec<HashMap> {
        // Return newest-first feedback entries.
        let mut events = self._events.into_iter().collect::<Vec<_>>();
        events.reverse();
        if model {
            let mut events = events.iter().filter(|e| e["model".to_string()] == model).map(|e| e).collect::<Vec<_>>();
        }
        events[..last_n]
    }
    /// Per-model aggregate stats.
    pub fn model_summary(&mut self, model: String) -> Option<HashMap<String, Box<dyn std::any::Any>>> {
        // Per-model aggregate stats.
        let mut s = self._model_stats.get(&model).cloned();
        if !s {
            None
        }
        let mut avg_rating = if s["rating_count".to_string()] > 0 { (((s["rating_sum".to_string()] / s["rating_count".to_string()]) as f64) * 10f64.powi(2)).round() / 10f64.powi(2) } else { None };
        let mut approval = (((s["thumbs_up".to_string()] / (s["thumbs_up".to_string()] + s["thumbs_down".to_string()]).max(1)) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
        HashMap::from([("model".to_string(), model), ("total_feedback".to_string(), s["total".to_string()]), ("thumbs_up".to_string(), s["thumbs_up".to_string()]), ("thumbs_down".to_string(), s["thumbs_down".to_string()]), ("approval_rate".to_string(), approval), ("avg_rating".to_string(), avg_rating), ("top_tags".to_string(), { let mut v = s["tag_counts".to_string()].iter().clone(); v.sort(); v }[..10])])
    }
    /// Summaries for every model that has feedback.
    pub fn all_summaries(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Summaries for every model that has feedback.
        self._model_stats.iter().map(|model| (model, self.model_summary(model))).collect::<HashMap<_, _>>()
    }
    /// Per-model score adjustments derived from feedback.
    /// 
    /// Positive = boost, negative = penalise. Scale: -10 to +10 points.
    pub fn routing_adjustments(&mut self) -> HashMap<String, f64> {
        // Per-model score adjustments derived from feedback.
        // 
        // Positive = boost, negative = penalise. Scale: -10 to +10 points.
        let mut adjustments = HashMap::new();
        for model in self._model_stats.iter() {
            let mut summary = self.model_summary(model);
            if (!summary || summary["total_feedback".to_string()] < 3) {
                continue;
            }
            let mut adj = 0.0_f64;
            adj += ((summary["approval_rate".to_string()] - 0.5_f64) * 10.0_f64);
            if summary["avg_rating".to_string()].is_some() {
                adj += ((summary["avg_rating".to_string()] - 3.0_f64) * 2.5_f64);
            }
            adjustments[model] = ((adj as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
        }
        adjustments
    }
    /// Global feedback stats.
    pub fn stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Global feedback stats.
        HashMap::from([("total_feedback".to_string(), self._total), ("models_with_feedback".to_string(), self._model_stats.len()), ("buffer_size".to_string(), self._events.len()), ("buffer_capacity".to_string(), self._events.maxlen)])
    }
    /// Clear feedback. Returns count of cleared entries.
    pub fn clear(&mut self, model: Option<String>) -> i64 {
        // Clear feedback. Returns count of cleared entries.
        if model {
            let mut before = self._events.len();
            self._events = r#type(self._events)(self._events.iter().filter(|e| e["model".to_string()] != model).map(|e| e).collect::<Vec<_>>(), /* maxlen= */ self._events.maxlen);
            let mut cleared = (before - self._events.len());
            if self._model_stats.contains(&model) {
                drop(self._model_stats[model]);
            }
            cleared
        } else {
            let mut cleared = self._events.len();
            self._events.clear();
            self._model_stats.clear();
            self._total = 0;
            cleared
        }
    }
}
