/// Core/evaluation::py — Answer & Retrieval Quality Evaluation.
/// 
/// AnswerEvaluator:
/// - Faithfulness (answer grounded in sources)
/// - Relevance (answer addresses the query)
/// - Completeness (all aspects of query covered)
/// - Conciseness (appropriate length)
/// 
/// RetrievalEvaluator:
/// - Precision@K, Recall@K, MRR, F1
/// 
/// Ported from ZEN_RAG.

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _ANSWER_EVALUATOR: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _RETRIEVAL_EVALUATOR: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Evaluate RAG answer quality on multiple dimensions.
/// 
/// Usage:
/// evaluator = get_answer_evaluator()
/// scores = evaluator.evaluate(question, answer, source_texts)
#[derive(Debug, Clone)]
pub struct AnswerEvaluator {
    pub llm_config: String,
    pub evaluation_history: deque,
}

impl AnswerEvaluator {
    pub fn new(llm_config: Option<HashMap>) -> Self {
        Self {
            llm_config: (llm_config || HashMap::new()),
            evaluation_history: Default::default(),
        }
    }
    /// Evaluate answer quality. Returns dict with scores [0-1].
    pub fn evaluate(&mut self, question: String, answer: String, source_texts: Vec<String>) -> HashMap<String, f64> {
        // Evaluate answer quality. Returns dict with scores [0-1].
        if (!answer || !question) {
            HashMap::from([("overall".to_string(), 0.0_f64), ("faithfulness".to_string(), 0.0_f64), ("relevance".to_string(), 0.0_f64), ("completeness".to_string(), 0.0_f64), ("conciseness".to_string(), 0.0_f64)])
        }
        let mut faithfulness = self._score_faithfulness(answer, source_texts);
        let mut relevance = self._score_relevance(answer, question);
        let mut completeness = self._score_completeness(answer, question);
        let mut conciseness = self._score_conciseness(answer);
        let mut overall = ((((faithfulness * 0.35_f64) + (relevance * 0.3_f64)) + (completeness * 0.2_f64)) + (conciseness * 0.15_f64));
        let mut scores = HashMap::from([("overall".to_string(), ((overall as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("faithfulness".to_string(), ((faithfulness as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("relevance".to_string(), ((relevance as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("completeness".to_string(), ((completeness as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("conciseness".to_string(), ((conciseness as f64) * 10f64.powi(3)).round() / 10f64.powi(3))]);
        self.evaluation_history.push(HashMap::from([("question".to_string(), question[..100]), ("scores".to_string(), scores)]));
        scores
    }
    /// Score how well the answer is grounded in sources.
    pub fn _score_faithfulness(&mut self, answer: String, source_texts: Vec<String>) -> f64 {
        // Score how well the answer is grounded in sources.
        if !source_texts {
            0.5_f64
        }
        let mut key_words = self._extract_key_words(answer);
        if !key_words {
            0.5_f64
        }
        let mut combined_source = source_texts.join(&" ".to_string()).to_lowercase();
        let mut found = key_words.iter().filter(|w| combined_source.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
        if key_words { (found / key_words.len()) } else { 0.5_f64 }
    }
    /// Score answer relevance to the question.
    pub fn _score_relevance(&mut self, answer: String, question: String) -> f64 {
        // Score answer relevance to the question.
        let mut q_keywords = self._extract_key_words(question);
        if !q_keywords {
            0.5_f64
        }
        let mut answer_lower = answer.to_lowercase();
        let mut found = q_keywords.iter().filter(|w| answer_lower.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut base_score = (found / q_keywords.len());
        if self._has_direct_answer_pattern(answer, question) {
            let mut base_score = 1.0_f64.min((base_score + 0.1_f64));
        }
        base_score
    }
    /// Score how completely the answer addresses the question.
    pub fn _score_completeness(&mut self, answer: String, question: String) -> f64 {
        // Score how completely the answer addresses the question.
        let mut sentences = self._split_sentences(answer);
        if !sentences {
            0.0_f64
        }
        let mut q_aspects = re::findall("\\b\\w{4,}\\b".to_string(), question.to_lowercase()).into_iter().collect::<HashSet<_>>();
        if !q_aspects {
            0.7_f64
        }
        let mut answer_lower = answer.to_lowercase();
        let mut covered = q_aspects.iter().filter(|w| answer_lower.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
        (covered / q_aspects.len())
    }
    /// Score answer conciseness (optimal: 20-200 words).
    pub fn _score_conciseness(answer: String) -> f64 {
        // Score answer conciseness (optimal: 20-200 words).
        let mut word_count = answer.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len();
        if (20 <= word_count) && (word_count <= 200) {
            1.0_f64
        }
        if word_count < 20 {
            0.7_f64
        }
        if word_count > 200 {
            let mut penalty = 0.5_f64.min(((word_count - 200) / 400));
            0.3_f64.max((1.0_f64 - penalty))
        }
        0.5_f64
    }
    pub fn _split_sentences(text: String) -> Vec<String> {
        // TODO: from Core.constants import split_sentences
        split_sentences(text)
    }
    pub fn _extract_key_words(&self, text: String) -> Vec<String> {
        // TODO: from Core.constants import extract_key_words
        extract_key_words(text, /* min_length= */ 3)
    }
    pub fn _has_direct_answer_pattern(answer: String, question: String) -> bool {
        let mut answer_lower = answer.to_lowercase();
        let mut patterns = vec!["^yes[,.]".to_string(), "^no[,.]".to_string(), "^the answer is".to_string(), "^it is".to_string(), "^they are".to_string()];
        patterns.iter().map(|p| regex::Regex::new(&p).unwrap().is_match(&answer_lower)).collect::<Vec<_>>().iter().any(|v| *v)
    }
    pub fn get_statistics(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        if !self.evaluation_history {
            HashMap::from([("message".to_string(), "No evaluations yet".to_string())])
        }
        let mut scores = self.evaluation_history.iter().map(|e| e["scores".to_string()]).collect::<Vec<_>>();
        let mut avg_scores = HashMap::from([("overall".to_string(), (scores.iter().map(|s| s["overall".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / scores.len())), ("faithfulness".to_string(), (scores.iter().map(|s| s["faithfulness".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / scores.len())), ("relevance".to_string(), (scores.iter().map(|s| s["relevance".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / scores.len())), ("completeness".to_string(), (scores.iter().map(|s| s["completeness".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / scores.len())), ("conciseness".to_string(), (scores.iter().map(|s| s["conciseness".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / scores.len()))]);
        HashMap::from([("total_evaluations".to_string(), self.evaluation_history.len()), ("average_scores".to_string(), avg_scores), ("recent_evaluations".to_string(), self.evaluation_history.into_iter().collect::<Vec<_>>()[-10..])])
    }
}

/// Evaluate retrieval quality (Precision@K, Recall@K, MRR, F1).
#[derive(Debug, Clone)]
pub struct RetrievalEvaluator {
}

impl RetrievalEvaluator {
    pub fn calculate_metrics(&self, retrieved_docs: Vec<String>, relevant_docs: Vec<String>, k: i64) -> HashMap<String, f64> {
        let mut top_k = retrieved_docs[..k];
        let mut relevant_in_top_k = (top_k.into_iter().collect::<HashSet<_>>() & relevant_docs.into_iter().collect::<HashSet<_>>()).len();
        let mut precision_at_k = if k > 0 { (relevant_in_top_k / k) } else { 0.0_f64 };
        let mut recall_at_k = if relevant_docs { (relevant_in_top_k / relevant_docs.len()) } else { 0.0_f64 };
        let mut mrr = 0.0_f64;
        for (i, doc) in retrieved_docs.iter().enumerate().iter() {
            if relevant_docs.contains(&doc) {
                let mut mrr = (1.0_f64 / (i + 1));
                break;
            }
        }
        let mut f1 = 0.0_f64;
        if (precision_at_k + recall_at_k) > 0 {
            let mut f1 = ((2 * (precision_at_k * recall_at_k)) / (precision_at_k + recall_at_k));
        }
        HashMap::from([(format!("precision@{}", k), precision_at_k), (format!("recall@{}", k), recall_at_k), ("mrr".to_string(), mrr), ("f1".to_string(), f1)])
    }
}

pub fn get_answer_evaluator(llm_config: Option<HashMap>) -> AnswerEvaluator {
    // global/nonlocal _answer_evaluator
    if _answer_evaluator.is_none() {
        let mut _answer_evaluator = AnswerEvaluator(llm_config);
    }
    _answer_evaluator
}

pub fn get_retrieval_evaluator() -> RetrievalEvaluator {
    // global/nonlocal _retrieval_evaluator
    if _retrieval_evaluator.is_none() {
        let mut _retrieval_evaluator = RetrievalEvaluator();
    }
    _retrieval_evaluator
}
