/// zena_mode/query_processor::py — Intelligent Query Processing & Expansion
/// ========================================================================
/// 
/// Adapted from RAG_RAT Core/query_processor::py for ZEN_AI_RAG.
/// 
/// Features:
/// - Query normalisation & cleanup
/// - Intent detection (factual / how-to / comparison / opinion / causal)
/// - Short-query rewriting hints
/// - Synonym-based query expansion (no LLM dependency)
/// - Multi-query generation for comprehensive retrieval

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _INSTANCE: std::sync::LazyLock<Option<QueryProcessor>> = std::sync::LazyLock::new(|| None);

/// Intelligent query processing for better retrieval.
#[derive(Debug, Clone)]
pub struct QueryProcessor {
    pub expansion_enabled: String,
    pub rewriting_enabled: String,
}

impl QueryProcessor {
    /// Configure query expansion and rewriting toggles.
    pub fn new() -> Self {
        Self {
            expansion_enabled: expansion_enabled,
            rewriting_enabled: rewriting_enabled,
        }
    }
    /// Process, normalise, classify, and optionally expand a user query.
    /// 
    /// Returns
    /// -------
    /// dict
    /// ``original``, ``processed``, ``alternatives``, ``intent``
    pub fn process_query(&mut self, query: String) -> HashMap<String, Box<dyn std::any::Any>> {
        // Process, normalise, classify, and optionally expand a user query.
        // 
        // Returns
        // -------
        // dict
        // ``original``, ``processed``, ``alternatives``, ``intent``
        let mut result = HashMap::from([("original".to_string(), query), ("processed".to_string(), query), ("alternatives".to_string(), vec![]), ("intent".to_string(), None)]);
        let mut processed = self._normalise(query);
        result["processed".to_string()] = processed;
        result["intent".to_string()] = self._detect_intent(processed);
        if (self.rewriting_enabled && self._needs_rewriting(processed)) {
            let mut rewritten = self._rewrite_query(processed);
            if rewritten {
                result["processed".to_string()] = rewritten;
                logger.info("Rewrote query: '%s' → '%s'".to_string(), query, rewritten);
            }
        }
        if (expand && self.expansion_enabled) {
            result["alternatives".to_string()] = self._expand_query(result["processed".to_string()]);
        }
        result
    }
    /// Generate *n* related sub-queries for comprehensive retrieval.
    pub fn generate_multi_queries(&mut self, query: String, n: i64) -> Vec<String> {
        // Generate *n* related sub-queries for comprehensive retrieval.
        let mut queries = vec![query];
        let mut intent = self._detect_intent(query);
        let mut q_lower = query.to_lowercase();
        if intent == "factual".to_string() {
            let mut base = regex::Regex::new(&"^what is\\s+".to_string()).unwrap().replace_all(&"".to_string(), q_lower).to_string().trim().to_string();
            queries.push(format!("What is the background of {}?", base));
            queries.push(format!("What are examples of {}?", base));
        } else if intent == "how-to".to_string() {
            let mut base = regex::Regex::new(&"^how to\\s+".to_string()).unwrap().replace_all(&"".to_string(), q_lower).to_string().trim().to_string();
            queries.push(format!("What do I need before {}?", base));
            queries.push(format!("What are common mistakes when {}?", base));
        } else if intent == "comparison".to_string() {
            let mut parts = re::split("\\s+vs\\.?\\s+|\\s+versus\\s+".to_string(), query, /* flags= */ re::I);
            if parts.len() == 2 {
                queries.push(format!("What is {}?", parts[0].trim().to_string()));
                queries.push(format!("What is {}?", parts[1].trim().to_string()));
            }
        } else {
            queries.push(format!("{} detailed explanation", query));
            queries.push(format!("{} examples", query));
        }
        queries[..n]
    }
    /// Remove extra whitespace and add ``?`` if it looks like a question.
    pub fn _normalise(query: String) -> String {
        // Remove extra whitespace and add ``?`` if it looks like a question.
        let mut query = regex::Regex::new(&"\\s+".to_string()).unwrap().replace_all(&" ".to_string(), query.trim().to_string()).to_string();
        let mut q_words = HashSet::from(["what".to_string(), "when".to_string(), "where".to_string(), "who".to_string(), "why".to_string(), "how".to_string(), "which".to_string(), "can".to_string(), "could".to_string(), "would".to_string(), "should".to_string(), "is".to_string(), "are".to_string(), "does".to_string(), "do".to_string()]);
        let mut first = if query.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>() { query.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>()[0] } else { "".to_string() };
        if ((q_words.contains(&first) || query.ends_with(&*"?".to_string())) && !query.ends_with(&*"?".to_string())) {
            query += "?".to_string();
        }
        query
    }
    /// Return true if the query is too short or too long for good retrieval.
    pub fn _needs_rewriting(query: String) -> bool {
        // Return true if the query is too short or too long for good retrieval.
        let mut words = query.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
        (words.len() < 3 || words.len() > 50)
    }
    /// Heuristic rewriting (no LLM). Returns *None* if no improvement.
    pub fn _rewrite_query(query: String) -> Option<String> {
        // Heuristic rewriting (no LLM). Returns *None* if no improvement.
        let mut words = query.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
        if words.len() < 3 {
            format!("Please explain {}?", query.trim_end_matches(|c: char| "?".to_string().contains(c)).to_string())
        }
        if words.len() > 50 {
            (words[..40].join(&" ".to_string()) + "?".to_string())
        }
        None
    }
    /// Synonym-based expansion — returns up to 3 alternatives.
    pub fn _expand_query(query: String) -> Vec<String> {
        // Synonym-based expansion — returns up to 3 alternatives.
        let mut synonyms = HashMap::from([("what is".to_string(), vec!["define".to_string(), "explain".to_string(), "describe".to_string()]), ("how to".to_string(), vec!["steps to".to_string(), "way to".to_string(), "method to".to_string()]), ("why".to_string(), vec!["reason for".to_string(), "cause of".to_string(), "explanation for".to_string()]), ("when".to_string(), vec!["time of".to_string(), "date of".to_string(), "period of".to_string()]), ("where".to_string(), vec!["location of".to_string(), "place of".to_string(), "position of".to_string()])]);
        let mut q_lower = query.to_lowercase();
        let mut alts = vec![];
        for (phrase, replacements) in synonyms.iter().iter() {
            if !q_lower.contains(&phrase) {
                continue;
            }
            for r in replacements.iter() {
                alts.push(/* capitalize */ q_lower.replace(&*phrase, &*r).to_string());
            }
        }
        alts[..3]
    }
    /// Classify the query intent (factual, how-to, comparison, etc.).
    pub fn _detect_intent(query: String) -> String {
        // Classify the query intent (factual, how-to, comparison, etc.).
        let mut q = query.to_lowercase();
        if ("what".to_string(), "when".to_string(), "where".to_string(), "who".to_string(), "define".to_string(), "explain".to_string()).iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "factual".to_string()
        }
        if (q.contains(&"how".to_string()) || q.contains(&"steps".to_string())) {
            "how-to".to_string()
        }
        if ("compare".to_string(), "difference".to_string(), "vs".to_string(), "versus".to_string(), "better".to_string()).iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "comparison".to_string()
        }
        if ("should".to_string(), "recommend".to_string(), "best".to_string(), "opinion".to_string()).iter().map(|w| q.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            "opinion".to_string()
        }
        if (q.contains(&"why".to_string()) || q.contains(&"reason".to_string())) {
            "causal".to_string()
        }
        "general".to_string()
    }
}

/// Return the global :class:`QueryProcessor` singleton.
pub fn get_query_processor() -> QueryProcessor {
    // Return the global :class:`QueryProcessor` singleton.
    // global/nonlocal _instance
    if _instance.is_none() {
        let mut _instance = QueryProcessor();
    }
    _instance
}
