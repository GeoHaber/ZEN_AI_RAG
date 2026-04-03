/// Human-in-the-Loop Conflict Resolution
/// 
/// Best practices from HITL research:
/// - Transparency: Show all claims, sources, credibility scores
/// - Agency: User decides what's true (expert judgment > algorithm)
/// - Feedback learning: System improves from user corrections
/// - Low friction: Simple voting interface for busy users
/// 
/// Based on patterns from:
/// - Crowdsourcing interfaces (Mechanical Turk, Amazon)
/// - Fact-checking platforms (Snopes, Full Fact)
/// - Active learning systems (human-in-loop ML)
/// - Trust frameworks (credibility assessment literature)

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// User's judgment on conflicting claims
#[derive(Debug, Clone)]
pub struct UserDecision {
}

/// Single version of a claim from one source
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaimVersion {
    pub text: String,
    pub source_name: String,
    pub source_type: String,
    pub source_date: Option<String>,
    pub credibility_score: f64,
    pub relevance_score: f64,
}

/// A conflict presented to user for judgment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictToResolve {
    pub conflict_id: String,
    pub original_query: String,
    pub subject: String,
    pub predicate: String,
    pub claim_1: ClaimVersion,
    pub claim_2: ClaimVersion,
    pub reasoning: String,
    pub timestamp: datetime,
}

/// User's decision on a conflict
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserJudgment {
    pub conflict_id: String,
    pub decision: UserDecision,
    pub confidence: f64,
    pub explanation: Option<String>,
    pub timestamp: datetime,
}

/// Feedback for ML system from user judgment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JudgmentFeedback {
    pub conflict_id: String,
    pub user_decision: UserDecision,
    pub system_vote: Option<String>,
    pub system_confidence: f64,
    pub user_confidence: f64,
    pub was_system_correct: bool,
    pub source_1_credibility: f64,
    pub source_2_credibility: f64,
    pub timestamp: datetime,
}

impl JudgmentFeedback {
    /// Did user disagree with system? Learn from this.
    pub fn is_learning_opportunity(&self) -> bool {
        // Did user disagree with system? Learn from this.
        !self.was_system_correct
    }
}

/// Presents conflicts to human for judgment.
/// 
/// HITL Pattern: Algorithm finds multiple versions →
/// Algorithm ranks by confidence → Human votes on best →
/// System learns from feedback
#[derive(Debug, Clone)]
pub struct HumanLoopConflictResolver {
    pub feedback_dir: String,
    pub judgments: HashMap<String, UserJudgment>,
}

impl HumanLoopConflictResolver {
    pub fn new(feedback_dir: PathBuf) -> Self {
        Self {
            feedback_dir: (feedback_dir || PathBuf::from("data/conflict_feedback".to_string())),
            judgments: HashMap::new(),
        }
    }
    /// Create conflict for human to judge.
    /// 
    /// Args:
    /// subject: What we're talking about (e.g., "Albert Einstein")
    /// predicate: What attribute (e.g., "born in")
    /// value_1, value_2: Conflicting values
    /// source_1, source_2: Evidence for each
    /// query: Original user query
    /// 
    /// Returns:
    /// ConflictToResolve object ready for UI display
    pub fn detect_conflict_for_human(&mut self, subject: String, predicate: String, value_1: String, source_1: HashMap<String, Box<dyn std::any::Any>>, value_2: String, source_2: HashMap<String, Box<dyn std::any::Any>>, query: String) -> ConflictToResolve {
        // Create conflict for human to judge.
        // 
        // Args:
        // subject: What we're talking about (e.g., "Albert Einstein")
        // predicate: What attribute (e.g., "born in")
        // value_1, value_2: Conflicting values
        // source_1, source_2: Evidence for each
        // query: Original user query
        // 
        // Returns:
        // ConflictToResolve object ready for UI display
        // TODO: import hashlib
        let mut conflict_id = hashlib::md5(format!("{}:{}:{}:{}", subject, predicate, value_1, value_2).as_bytes().to_vec()).hexdigest()[..12];
        let mut claim_1 = ClaimVersion(/* text= */ format!("{} {} {}", subject, predicate, value_1), /* source_name= */ source_1.get(&"name".to_string()).cloned().unwrap_or("Unknown".to_string()), /* source_type= */ source_1.get(&"type".to_string()).cloned().unwrap_or("web".to_string()), /* source_date= */ source_1.get(&"date".to_string()).cloned(), /* credibility_score= */ source_1.get(&"credibility".to_string()).cloned().unwrap_or(0.5_f64), /* relevance_score= */ source_1.get(&"relevance".to_string()).cloned().unwrap_or(source_1.get(&"score".to_string()).cloned().unwrap_or(0.5_f64)));
        let mut claim_2 = ClaimVersion(/* text= */ format!("{} {} {}", subject, predicate, value_2), /* source_name= */ source_2.get(&"name".to_string()).cloned().unwrap_or("Unknown".to_string()), /* source_type= */ source_2.get(&"type".to_string()).cloned().unwrap_or("web".to_string()), /* source_date= */ source_2.get(&"date".to_string()).cloned(), /* credibility_score= */ source_2.get(&"credibility".to_string()).cloned().unwrap_or(0.5_f64), /* relevance_score= */ source_2.get(&"relevance".to_string()).cloned().unwrap_or(source_2.get(&"score".to_string()).cloned().unwrap_or(0.5_f64)));
        let mut reasoning = self._generate_conflict_reasoning(claim_1, claim_2);
        ConflictToResolve(/* conflict_id= */ conflict_id, /* original_query= */ query, /* subject= */ subject, /* predicate= */ predicate, /* claim_1= */ claim_1, /* claim_2= */ claim_2, /* reasoning= */ reasoning)
    }
    /// Generate human-friendly explanation of why this is a conflict
    pub fn _generate_conflict_reasoning(&mut self, claim_1: ClaimVersion, claim_2: ClaimVersion) -> String {
        // Generate human-friendly explanation of why this is a conflict
        let mut source1_strong = claim_1.credibility_score > claim_2.credibility_score;
        self._compare_dates(claim_1.source_date, claim_2.source_date);
        let mut reasons = vec![];
        if claim_1.source_type != claim_2.source_type {
            reasons.push(format!("Different source types: {} vs {}", claim_1.source_type.to_uppercase(), claim_2.source_type.to_uppercase()));
        }
        if claim_1.source_date != claim_2.source_date {
            reasons.push(format!("Different publication dates: {} vs {}", (claim_1.source_date || "unknown".to_string()), (claim_2.source_date || "unknown".to_string())));
        }
        if ((claim_1.credibility_score - claim_2.credibility_score)).abs() > 0.2_f64 {
            let mut more_credible = if source1_strong { "first".to_string() } else { "second".to_string() };
            reasons.push(format!("{} source is more credible", /* capitalize */ more_credible.to_string()));
        }
        let mut reasoning = if reasons { reasons.join(&" | ".to_string()) } else { "Sources contain conflicting information".to_string() };
        reasoning
    }
    /// Format conflict for display in Streamlit UI
    pub fn format_conflict_for_ui(&self, conflict: ConflictToResolve) -> HashMap<String, Box<dyn std::any::Any>> {
        // Format conflict for display in Streamlit UI
        HashMap::from([("conflict_id".to_string(), conflict.conflict_id), ("subject".to_string(), conflict.subject), ("predicate".to_string(), conflict.predicate), ("query".to_string(), conflict.original_query), ("claim_1".to_string(), HashMap::from([("text".to_string(), conflict.claim_1.text), ("source".to_string(), conflict.claim_1.source_name), ("type".to_string(), conflict.claim_1.source_type), ("date".to_string(), conflict.claim_1.source_date), ("credibility".to_string(), conflict.claim_1.credibility_score), ("relevance".to_string(), conflict.claim_1.relevance_score)])), ("claim_2".to_string(), HashMap::from([("text".to_string(), conflict.claim_2.text), ("source".to_string(), conflict.claim_2.source_name), ("type".to_string(), conflict.claim_2.source_type), ("date".to_string(), conflict.claim_2.source_date), ("credibility".to_string(), conflict.claim_2.credibility_score), ("relevance".to_string(), conflict.claim_2.relevance_score)])), ("reasoning".to_string(), conflict.reasoning), ("timestamp".to_string(), conflict.timestamp.isoformat())])
    }
    /// Record user's vote on which claim is correct.
    /// 
    /// This is the learning signal for improving future decisions.
    pub fn record_user_judgment(&mut self, conflict_id: String, decision: UserDecision, user_confidence: f64, explanation: String) -> UserJudgment {
        // Record user's vote on which claim is correct.
        // 
        // This is the learning signal for improving future decisions.
        let mut judgment = UserJudgment(/* conflict_id= */ conflict_id, /* decision= */ decision, /* confidence= */ user_confidence, /* explanation= */ explanation);
        self.judgments[conflict_id] = judgment;
        self._save_judgment(judgment);
        judgment
    }
    /// Persist user judgment to disk
    pub fn _save_judgment(&mut self, judgment: UserJudgment) -> () {
        // Persist user judgment to disk
        let mut file_path = (self.feedback_dir / format!("{}.json", judgment.conflict_id));
        file_pathstd::fs::write(&serde_json::to_string(&HashMap::from([("conflict_id".to_string(), judgment.conflict_id), ("decision".to_string(), judgment.decision.value), ("confidence".to_string(), judgment.confidence), ("explanation".to_string(), judgment.explanation), ("timestamp".to_string(), judgment.timestamp.isoformat())])).unwrap());
    }
    /// Load all past user judgments
    pub fn _load_feedback_history(&mut self) -> Result<()> {
        // Load all past user judgments
        for file_path in self.feedback_dir.glob("*.json".to_string()).iter() {
            // try:
            {
                let mut data = serde_json::from_str(&file_path.read_to_string()).unwrap();
                let mut judgment = UserJudgment(/* conflict_id= */ data["conflict_id".to_string()], /* decision= */ UserDecision(data["decision".to_string()]), /* confidence= */ data["confidence".to_string()], /* explanation= */ data.get(&"explanation".to_string()).cloned(), /* timestamp= */ datetime::fromisoformat(data["timestamp".to_string()]));
                self.judgments[judgment.conflict_id] = judgment;
            }
            // except Exception as e:
        }
    }
    /// Analyze feedback patterns to improve system behavior
    pub fn get_feedback_statistics(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Analyze feedback patterns to improve system behavior
        if !self.judgments {
            HashMap::from([("total_judgments".to_string(), 0)])
        }
        let mut decisions = self.judgments.values().iter().map(|j| j.decision.value).collect::<Vec<_>>();
        let mut confidences = self.judgments.values().iter().map(|j| j.confidence).collect::<Vec<_>>();
        HashMap::from([("total_judgments".to_string(), self.judgments.len()), ("decision_distribution".to_string(), UserDecision.iter().map(|d| (d.value, decisions.iter().filter(|v| **v == d.value).count())).collect::<HashMap<_, _>>()), ("average_user_confidence".to_string(), (confidences.iter().sum::<i64>() / confidences.len())), ("high_confidence_judgments".to_string(), confidences.iter().filter(|c| c > 0.8_f64).map(|c| 1).collect::<Vec<_>>().iter().sum::<i64>()), ("uncertain_judgments".to_string(), confidences.iter().filter(|c| c < 0.5_f64).map(|c| 1).collect::<Vec<_>>().iter().sum::<i64>())])
    }
    /// Return true if date1 > date2 (more recent). Handle missing dates.
    pub fn _compare_dates(&self, date1: Option<String>, date2: Option<String>) -> Result<bool> {
        // Return true if date1 > date2 (more recent). Handle missing dates.
        if (!date1 || !date2) {
            false
        }
        // try:
        {
            // TODO: from datetime import datetime as dt
            let mut d1 = dt.fromisoformat(date1);
            let mut d2 = dt.fromisoformat(date2);
            d1 > d2
        }
        // except (ValueError, AttributeError) as _e:
    }
    /// What would the system vote? (for comparison)
    /// 
    /// Returns:
    /// (claim_number: 1 or 2, confidence: 0-1, reasoning: str)
    pub fn suggest_system_preference(&mut self, conflict: ConflictToResolve) -> (i64, f64, String) {
        // What would the system vote? (for comparison)
        // 
        // Returns:
        // (claim_number: 1 or 2, confidence: 0-1, reasoning: str)
        let mut score_1 = ((conflict.claim_1.credibility_score * 0.5_f64) + (conflict.claim_1.relevance_score * 0.3_f64));
        let mut score_2 = ((conflict.claim_2.credibility_score * 0.5_f64) + (conflict.claim_2.relevance_score * 0.3_f64));
        if self._compare_dates(conflict.claim_1.source_date, conflict.claim_2.source_date) {
            score_1 += 0.2_f64;
        } else if self._compare_dates(conflict.claim_2.source_date, conflict.claim_1.source_date) {
            score_2 += 0.2_f64;
        }
        let mut choice = if score_1 > score_2 { 1 } else { 2 };
        let mut confidence = score_1.max(score_2);
        let mut reasoning = format!("Based on source credibility ({}.credibility={:.2})", choice, score_1.max(score_2));
        (choice, confidence, reasoning)
    }
}
