/// Core/answer_refinement::py — Post-Generation Answer Refinement Engine
/// 
/// Catches and fixes answer quality issues BEFORE displaying to the user:
/// 1. Hallucination detection → request LLM to revise with grounded facts
/// 2. Completeness check → request elaboration if answer is too terse
/// 3. Internal consistency → detect & resolve self-contradictions
/// 4. Citation grounding → ensure claims reference actual source content
/// 5. Quality scoring → attach a quality score for UI display
/// 
/// Works as a middleware between LLM answer generation and UI display.
/// 
/// Usage:
/// refiner = AnswerRefinementEngine(llm_generate_fn, hallucination_detector)
/// result = await refiner.refine(query, answer, context, sources)
/// display(result.answer, result.quality_score)

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Result of answer refinement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RefinementResult {
    pub answer: String,
    pub original_answer: String,
    pub was_revised: bool,
    pub revision_count: i64,
    pub revision_reasons: Vec<String>,
    pub quality_score: f64,
    pub hallucination_probability: f64,
    pub word_count: i64,
}

impl RefinementResult {
    pub fn revision_reason(&self) -> Option<String> {
        if self.revision_reasons {
            self.revision_reasons.join(&"; ".to_string())
        }
        None
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("answer".to_string(), self.answer), ("was_revised".to_string(), self.was_revised), ("revision_count".to_string(), self.revision_count), ("revision_reason".to_string(), self.revision_reason), ("quality_score".to_string(), self.quality_score), ("hallucination_probability".to_string(), self.hallucination_probability)])
    }
}

/// Polish LLM answers before displaying to user.
/// 
/// Pipeline:
/// answer → hallucination_check → completeness_check → consistency_check → done
#[derive(Debug, Clone)]
pub struct AnswerRefinementEngine {
    pub llm_generate: String,
    pub detector: String,
    pub min_words: String,
    pub max_attempts: String,
}

impl AnswerRefinementEngine {
    /// Args:
    /// llm_generate_fn: Async callable(prompt: str) → str for re-generation.
    /// If None, refinement prompts are skipped (score-only mode).
    /// hallucination_detector: Instance of AdvancedHallucinationDetector.
    /// min_answer_words: Threshold below which answer is considered too short.
    /// max_refinement_attempts: Max LLM re-calls for fixing issues.
    pub fn new(llm_generate_fn: Option<Box<dyn Fn>>, hallucination_detector: String, min_answer_words: i64, max_refinement_attempts: i64) -> Self {
        Self {
            llm_generate: llm_generate_fn,
            detector: hallucination_detector,
            min_words: min_answer_words,
            max_attempts: max_refinement_attempts,
        }
    }
    /// Refine an answer through the quality pipeline.
    /// 
    /// Args:
    /// query: Original user query.
    /// answer: LLM-generated answer.
    /// context: RAG context (concatenated evidence).
    /// sources: List of source dicts/strings.
    /// max_attempts: Override max refinement attempts.
    /// 
    /// Returns:
    /// RefinementResult with possibly revised answer and quality metadata.
    pub async fn refine(&mut self, query: String, answer: String, context: String, sources: Option<Vec>, max_attempts: Option<i64>) -> Result<RefinementResult> {
        // Refine an answer through the quality pipeline.
        // 
        // Args:
        // query: Original user query.
        // answer: LLM-generated answer.
        // context: RAG context (concatenated evidence).
        // sources: List of source dicts/strings.
        // max_attempts: Override max refinement attempts.
        // 
        // Returns:
        // RefinementResult with possibly revised answer and quality metadata.
        let mut max_att = if max_attempts.is_some() { max_attempts } else { self.max_attempts };
        let mut original = answer;
        let mut reasons = vec![];
        let mut revisions = 0;
        let mut halluc_prob = 0.0_f64;
        if self.detector {
            let mut evidence = if sources { self._sources_to_texts(sources) } else { vec![context] };
            let mut report = self.detector.detect_hallucinations(answer, evidence);
            let mut halluc_prob = report.probability;
            if (halluc_prob > 0.25_f64 && revisions < max_att && self.llm_generate) {
                logger.warning(format!("[Refiner] Hallucination probability {:.0%}, requesting revision", halluc_prob));
                let mut prompt = self._hallucination_fix_prompt(answer, context, report.summary);
                // try:
                {
                    let mut answer = self.llm_generate(prompt).await;
                    revisions += 1;
                    reasons.push(format!("Hallucination fix ({:.0%} → re-grounded)", halluc_prob));
                    let mut report2 = self.detector.detect_hallucinations(answer, evidence);
                    let mut halluc_prob = report2.probability;
                }
                // except Exception as e:
            }
        }
        let mut word_count = answer.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len();
        if (word_count < self.min_words && revisions < max_att && self.llm_generate) {
            logger.info(format!("[Refiner] Answer too short ({} words), requesting elaboration", word_count));
            let mut prompt = self._elaboration_prompt(query, answer, context);
            // try:
            {
                let mut answer = self.llm_generate(prompt).await;
                revisions += 1;
                reasons.push(format!("Elaborated (was {} words)", word_count));
            }
            // except Exception as e:
        }
        let mut contradictions = self._find_contradictions(answer);
        if (contradictions && revisions < max_att && self.llm_generate) {
            logger.info(format!("[Refiner] {} internal contradictions found", contradictions.len()));
            let mut prompt = self._consistency_prompt(answer, context, contradictions);
            // try:
            {
                let mut answer = self.llm_generate(prompt).await;
                revisions += 1;
                reasons.push(format!("Fixed {} internal contradiction(s)", contradictions.len()));
            }
            // except Exception as e:
        }
        let mut quality = self._score_quality(answer, context, halluc_prob);
        Ok(RefinementResult(/* answer= */ answer, /* original_answer= */ original, /* was_revised= */ revisions > 0, /* revision_count= */ revisions, /* revision_reasons= */ reasons, /* quality_score= */ quality, /* hallucination_probability= */ halluc_prob, /* word_count= */ answer.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len()))
    }
    pub fn _hallucination_fix_prompt(&self, answer: String, context: String, halluc_summary: String) -> String {
        format!("The answer below contains hallucinated or unsupported claims.\n\nDETECTED ISSUES:\n{}\n\nOriginal Answer:\n{}\n\nSource Material:\n{}\n\nINSTRUCTIONS:\n- Revise the answer to ONLY include claims directly supported by the source material.\n- Remove any hallucinated or unsupported claims.\n- Keep the helpful structure and tone.\n- If you cannot verify a claim, say 'According to the sources...' or omit it.\n- Do NOT add new information not in the sources.\n", halluc_summary, answer, context[..2000])
    }
    pub fn _elaboration_prompt(&self, query: String, answer: String, context: String) -> String {
        format!("The answer to the user's question is very brief. Please provide a more complete and detailed answer.\n\nUser Question: {}\n\nOriginal Answer: {}\n\nRelevant Context:\n{}\n\nPlease provide a thorough answer that fully addresses the question using information from the context above. Stay factual.", query, answer, context[..2000])
    }
    pub fn _consistency_prompt(&self, answer: String, context: String, contradictions: Vec<String>) -> String {
        let mut issues = contradictions.iter().map(|c| format!("  - {}", c)).collect::<Vec<_>>().join(&"\n".to_string());
        format!("The answer below has internal contradictions:\n{}\n\nOriginal Answer:\n{}\n\nContext:\n{}\n\nPlease revise the answer to be internally consistent and factually aligned with the context.", issues, answer, context[..1500])
    }
    /// Find obvious internal contradictions in the answer.
    pub fn _find_contradictions(&self, text: String) -> Vec<String> {
        // Find obvious internal contradictions in the answer.
        let mut sentences = re::split("(?<=[.!?])\\s+".to_string(), text).iter().filter(|s| s.trim().to_string()).map(|s| s.trim().to_string()).collect::<Vec<_>>();
        let mut contradictions = vec![];
        for (i, s1) in sentences.iter().enumerate().iter() {
            for s2 in sentences[(i + 1)..].iter() {
                let mut s1_l = s1.to_lowercase();
                let mut s2_l = s2.to_lowercase();
                for pattern in vec!["(\\w+)\\s+is\\s+(\\w+)".to_string(), "(\\w+)\\s+are\\s+(\\w+)".to_string()].iter() {
                    let mut m1 = regex::Regex::new(&pattern).unwrap().is_match(&s1_l);
                    if m1 {
                        let (mut subj, mut val) = (m1.group(1), m1.group(2));
                        let mut neg = format!("{} is not {}", subj, val);
                        let mut neg2 = format!("{} are not {}", subj, val);
                        if (s2_l.contains(&neg) || s2_l.contains(&neg2)) {
                            contradictions.push(format!("\"{}\" vs \"{}\"", s1[..60], s2[..60]));
                        }
                    }
                }
                let mut nums1 = re::findall("\\b(\\d+(?:\\.\\d+)?)\\b".to_string(), s1);
                let mut nums2 = re::findall("\\b(\\d+(?:\\.\\d+)?)\\b".to_string(), s2);
                let mut words1 = s1_l.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>();
                let mut words2 = s2_l.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>();
                let mut overlap = ((words1 & words2).len() / (words1 | words2).len().max(1));
                if (overlap > 0.5_f64 && nums1 && nums2 && nums1.into_iter().collect::<HashSet<_>>() != nums2.into_iter().collect::<HashSet<_>>()) {
                    contradictions.push(format!("Number conflict: \"{}\" vs \"{}\"", s1[..50], s2[..50]));
                }
            }
        }
        contradictions[..5]
    }
    /// Score answer quality 0–1.
    pub fn _score_quality(&self, answer: String, context: String, halluc_prob: f64) -> f64 {
        // Score answer quality 0–1.
        let mut score = 1.0_f64;
        score -= (halluc_prob * 0.5_f64);
        let mut words = answer.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len();
        if words < 15 {
            score *= 0.6_f64;
        } else if words < 30 {
            score *= 0.8_f64;
        } else if words > 800 {
            score *= 0.85_f64;
        }
        if regex::Regex::new(&"(?:^|\\n)\\s*[\\-\\*\\d]+[\\.\\)]\\s".to_string()).unwrap().is_match(&answer) {
            score *= 1.05_f64;
        }
        if answer.contains(&"\n\n".to_string()) {
            score *= 1.03_f64;
        }
        let mut refs = re::findall("\\[\\d+\\]|\\(source|\\(citation\\)|according to".to_string(), answer, re::I).len();
        if refs >= 1 {
            score *= 1.05_f64;
        }
        0.0_f64.max(score.min(1.0_f64))
    }
    /// Normalize various source formats to plain text list.
    pub fn _sources_to_texts(&self, sources: Vec<serde_json::Value>) -> Vec<String> {
        // Normalize various source formats to plain text list.
        let mut texts = vec![];
        for src in sources.iter() {
            if /* /* isinstance(src, str) */ */ true {
                texts.push(src);
            } else if /* /* isinstance(src, dict) */ */ true {
                texts.push(src.get(&"text".to_string()).cloned().unwrap_or(src.to_string()));
            } else {
                texts.push(src.to_string());
            }
        }
        texts
    }
}
