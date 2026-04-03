/// STAT router — classify query as STAT (numbers/SQL), DOC (text), or HYBRID.
/// 
/// Used to decide whether to run the STAT path (schema + examples from Qdrant → SQL → execute)
/// or the normal RAG path (retrieve chunks → LLM answer). See docs/GOLDEN_INTERACTION_FLOW.md.

use anyhow::{Result, Context};

pub const STAT_KEYWORDS_RO: &str = "('rata', 'ocupare', 'secție', 'secți', 'sectie', 'paturi', 'procent', 'număr', 'total', 'pe secție', 'per sectie', 'pe fiecare', 'în data de', 'data de', 'la data', 'aggregat', 'statistic', 'kpi', 'indicator', 'top 5', 'top 10', 'media', 'diferență', 'diferenta', 'câte', 'cate', 'câți', 'cati', 'grad de ocupare', 'paturi reale', 'paturi libere', 'structură', 'structura')";

pub const STAT_KEYWORDS_EN: &str = "('rate', 'occupancy', 'per section', 'per department', 'by section', 'on date', 'as of', 'aggregate', 'statistic', 'kpi', 'metric', 'top 5', 'top 10', 'average', 'difference', 'how many', 'count')";

/// Classify query into STAT (numbers/SQL), DOC (text-only), or HYBRID.
/// 
/// Returns:
/// "STAT"  — use STAT path (schema + examples → SQL → execute).
/// "DOC"   — use normal RAG (chunks → LLM).
/// "HYBRID" — use STAT path, optionally augmented with DOC context (treated as STAT for now).
pub fn route(query: String) -> Literal</* unknown */> {
    // Classify query into STAT (numbers/SQL), DOC (text-only), or HYBRID.
    // 
    // Returns:
    // "STAT"  — use STAT path (schema + examples → SQL → execute).
    // "DOC"   — use normal RAG (chunks → LLM).
    // "HYBRID" — use STAT path, optionally augmented with DOC context (treated as STAT for now).
    if (!query || !query.trim().to_string()) {
        "DOC".to_string()
    }
    let mut q = query.trim().to_string().to_lowercase();
    let mut q_norm = q.replace(&*"ă".to_string(), &*"a".to_string()).replace(&*"â".to_string(), &*"a".to_string()).replace(&*"î".to_string(), &*"i".to_string()).replace(&*"ș".to_string(), &*"s".to_string()).replace(&*"ț".to_string(), &*"t".to_string());
    for kw in STAT_KEYWORDS_RO.iter() {
        let mut kw_norm = kw.replace(&*"ă".to_string(), &*"a".to_string()).replace(&*"â".to_string(), &*"a".to_string()).replace(&*"î".to_string(), &*"i".to_string()).replace(&*"ș".to_string(), &*"s".to_string()).replace(&*"ț".to_string(), &*"t".to_string());
        if (q_norm.contains(&kw_norm) || q.contains(&kw)) {
            "STAT".to_string()
        }
    }
    for kw in STAT_KEYWORDS_EN.iter() {
        if q.contains(&kw) {
            "STAT".to_string()
        }
    }
    "DOC".to_string()
}

/// true if the query should use the STAT path.
pub fn is_stat_query(query: String) -> bool {
    // true if the query should use the STAT path.
    ("STAT".to_string(), "HYBRID".to_string()).contains(&route(query))
}
