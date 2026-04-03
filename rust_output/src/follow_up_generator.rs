/// Core/follow_up_generator::py — AI-powered follow-up question generator.
/// 
/// After every RAG answer, generates 3 contextual follow-up questions that
/// the user might naturally want to ask next. Makes the conversation feel
/// alive and guides users to explore the indexed data deeper.
/// 
/// Usage:
/// gen = FollowUpGenerator(llm=my_llm)
/// questions = gen.generate("How many beds are free?", answer_text, sources)
/// # Returns: ["Which ward has most free beds?", "Trend vs yesterday?", ...]

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const _PROMPT: &str = "You are a helpful assistant. The user just asked a question and received an answer.\\nGenerate exactly 3 short follow-up questions the user might want to ask next.\\n\\nRules:\\n- Each question must be directly related to the answer content\\n- Keep each question under 60 characters\\n- Make them diverse (don\\'t repeat the same angle)\\n- Be specific to facts mentioned in the answer\\n- Output ONLY the 3 questions, one per line, no numbering or bullets\\n\\nOriginal question: \"{query}\"\\n\\nAnswer summary: \"{answer_snippet}\"\\n\\n3 follow-up questions:";

pub static _GENERIC_FOLLOW_UPS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Generates contextual follow-up questions using LLM or templates.
#[derive(Debug, Clone)]
pub struct FollowUpGenerator {
    pub llm: String,
    pub timeout: String,
}

impl FollowUpGenerator {
    pub fn new(llm: Box<dyn std::any::Any>, timeout: f64) -> Self {
        Self {
            llm,
            timeout,
        }
    }
    /// Generate follow-up questions based on query + answer.
    /// 
    /// Args:
    /// query: The original user question.
    /// answer: The assistant's answer (HTML will be stripped).
    /// sources: Retrieved source chunks (for domain context).
    /// n: Number of follow-up questions to generate (default 3).
    /// 
    /// Returns:
    /// List of follow-up question strings (may be fewer than n if generation fails).
    pub fn generate(&mut self, query: String, answer: String, sources: Vec<HashMap>, n: i64) -> Result<Vec<String>> {
        // Generate follow-up questions based on query + answer.
        // 
        // Args:
        // query: The original user question.
        // answer: The assistant's answer (HTML will be stripped).
        // sources: Retrieved source chunks (for domain context).
        // n: Number of follow-up questions to generate (default 3).
        // 
        // Returns:
        // List of follow-up question strings (may be fewer than n if generation fails).
        let mut clean_answer = _strip_html(answer)[..600];
        if self.llm.is_some() {
            // try:
            {
                self._llm_generate(query, clean_answer, n)
            }
            // except Exception as e:
        }
        Ok(self._template_generate(query, (sources || vec![]), n))
    }
    pub fn _llm_generate(&mut self, query: String, answer_snippet: String, n: i64) -> Vec<String> {
        let mut prompt = format!(_PROMPT, /* query= */ query[..200], /* answer_snippet= */ answer_snippet[..400]);
        if /* hasattr(self.llm, "query_sync".to_string()) */ true {
            let mut resp = self.llm.query_sync(prompt, /* max_tokens= */ 150, /* temperature= */ 0.7_f64);
        } else if /* hasattr(self.llm, "generate".to_string()) */ true {
            let mut resp = self.llm.generate(prompt);
        } else {
            _GENERIC_FOLLOW_UPS[..n]
        }
        if (!resp || !resp.trim().to_string()) {
            _GENERIC_FOLLOW_UPS[..n]
        }
        let mut lines = resp.trim().to_string().split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|line| (line.trim().to_string() && line.trim().to_string().len() > 5)).map(|line| _clean_question(line)).collect::<Vec<_>>();
        let mut filtered = lines.iter().filter(|q| (q && !q.to_lowercase().starts_with(&*("here".to_string(), "follow".to_string(), "question".to_string(), "sure".to_string())))).map(|q| q).collect::<Vec<_>>();
        if filtered { filtered[..n] } else { _GENERIC_FOLLOW_UPS[..n] }
    }
    /// Fast template-based follow-ups extracted from source content.
    pub fn _template_generate(&self, query: String, sources: Vec<HashMap>, n: i64) -> Vec<String> {
        // Fast template-based follow-ups extracted from source content.
        let mut follow_ups = vec![];
        let mut q_lower = query.to_lowercase();
        if ("how many".to_string(), "count".to_string(), "total".to_string(), "beds".to_string(), "patients".to_string()).iter().map(|w| q_lower.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            follow_ups += vec!["How does this compare to yesterday?".to_string(), "Which department has the most capacity?".to_string(), "Show me the weekly trend.".to_string()];
        } else if ("what is".to_string(), "explain".to_string(), "describe".to_string(), "define".to_string()).iter().map(|w| q_lower.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            follow_ups += vec!["Can you give an example?".to_string(), "What are the key benefits?".to_string(), "How does this work in practice?".to_string()];
        } else if ("how to".to_string(), "steps".to_string(), "process".to_string(), "guide".to_string()).iter().map(|w| q_lower.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            follow_ups += vec!["What are the requirements?".to_string(), "How long does this take?".to_string(), "What could go wrong?".to_string()];
        } else if ("contact".to_string(), "phone".to_string(), "email".to_string(), "address".to_string()).iter().map(|w| q_lower.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            follow_ups += vec!["What are the opening hours?".to_string(), "Is there an online alternative?".to_string(), "Who is the contact person?".to_string()];
        } else {
            let mut follow_ups = _GENERIC_FOLLOW_UPS.into_iter().collect::<Vec<_>>();
        }
        follow_ups[..n]
    }
}

/// Remove HTML tags from text.
pub fn _strip_html(text: String) -> String {
    // Remove HTML tags from text.
    regex::Regex::new(&"<[^>]+>".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string().trim().to_string()
}

/// Strip numbering, bullets, quotes from a line.
pub fn _clean_question(line: String) -> String {
    // Strip numbering, bullets, quotes from a line.
    let mut line = line.trim().to_string();
    let mut line = regex::Regex::new(&"^[\\d]+[\\.\\)]\\s*".to_string()).unwrap().replace_all(&"".to_string(), line).to_string();
    let mut line = regex::Regex::new(&"^[-*•]\\s*".to_string()).unwrap().replace_all(&"".to_string(), line).to_string();
    let mut line = line.trim_matches(|c: char| "\"'".to_string().contains(c)).to_string();
    if (line && !line.ends_with(&*"?".to_string())) {
        line += "?".to_string();
    }
    line.trim().to_string()
}
