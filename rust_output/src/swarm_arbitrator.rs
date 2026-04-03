/// swarm_arbitrator::py - Enhanced Multi-LLM Consensus System
/// Ported from ZEN_AI_RAG with 2026 research-backed improvements.
/// 
/// Features:
/// - Async-first parallel dispatch
/// - Semantic consensus (embeddings)
/// - Confidence extraction & weighted voting
/// - Task-based protocol routing
/// - Agent performance tracking
/// - Adaptive round selection
/// - Progressive streaming
/// - Full TDD coverage

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const EXPERTRESPONSE: &str = "Dict[str, Any]";

pub static DEFAULT_CONFIG: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

/// Consensus calculation methods.
#[derive(Debug, Clone)]
pub struct ConsensusMethod {
}

/// Consensus protocols for different task types.
#[derive(Debug, Clone)]
pub struct ConsensusProtocol {
}

/// Task classification types.
#[derive(Debug, Clone)]
pub struct TaskType {
}

/// Request for swarm arbitration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArbitrationRequest {
    pub id: String,
    pub query: String,
    pub task_type: String,
    pub timestamp: f64,
}

/// Track agent accuracy and reliability over time.
#[derive(Debug, Clone)]
pub struct AgentPerformanceTracker {
    pub db_path: String,
}

impl AgentPerformanceTracker {
    pub fn new(db_path: String) -> Self {
        Self {
            db_path,
        }
    }
    /// Create performance tracking tables.
    pub fn _init_db(&mut self) -> Result<()> {
        // Create performance tracking tables.
        let mut conn = /* sqlite3 */ self.db_path;
        conn.execute("\n            CREATE TABLE IF NOT EXISTS agent_performance (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                agent_id TEXT NOT NULL,\n                task_type TEXT,\n                query_hash TEXT,\n                response_text TEXT,\n                was_selected INTEGER,\n                consensus_score REAL,\n                confidence REAL,\n                response_time REAL,\n                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP\n            )\n        ".to_string());
        conn.execute("\n            CREATE INDEX IF NOT EXISTS idx_agent_task\n            ON agent_performance(agent_id, task_type)\n        ".to_string());
        conn.commit();
        Ok(conn.close())
    }
    /// Record agent response for future analysis.
    pub fn record_response(&mut self, agent_id: String, task_type: String, query_hash: String, response_text: String, was_selected: bool, consensus_score: f64, confidence: f64, response_time: f64) -> Result<()> {
        // Record agent response for future analysis.
        let mut conn = /* sqlite3 */ self.db_path;
        conn.execute("\n            INSERT INTO agent_performance\n            (agent_id, task_type, query_hash, response_text, was_selected,\n             consensus_score, confidence, response_time)\n            VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n        ".to_string(), (agent_id, task_type, query_hash, response_text[..500], if was_selected { 1 } else { 0 }, consensus_score, confidence, response_time));
        conn.commit();
        Ok(conn.close())
    }
    /// Get historical accuracy for agent.
    pub fn get_agent_reliability(&mut self, agent_id: String, task_type: Option<String>) -> Result<f64> {
        // Get historical accuracy for agent.
        let mut conn = /* sqlite3 */ self.db_path;
        if task_type {
            let mut query = "\n                SELECT AVG(was_selected)\n                FROM agent_performance\n                WHERE agent_id = ? AND task_type = ?\n                AND timestamp > datetime('now', '-30 days')\n            ".to_string();
            let mut params = (agent_id, task_type);
        } else {
            let mut query = "\n                SELECT AVG(was_selected)\n                FROM agent_performance\n                WHERE agent_id = ?\n                AND timestamp > datetime('now', '-30 days')\n            ".to_string();
            let mut params = (agent_id);
        }
        let mut cursor = conn.execute(query, params);
        let mut result = cursor.fetchone()[0];
        conn.close();
        Ok(if result.is_some() { result } else { 0.5_f64 })
    }
    /// Get overall statistics.
    pub fn get_stats(&mut self) -> Result<HashMap> {
        // Get overall statistics.
        let mut conn = /* sqlite3 */ self.db_path;
        let mut cursor = conn.execute("\n            SELECT\n                COUNT(*) as total_queries,\n                COUNT(DISTINCT agent_id) as unique_agents,\n                AVG(consensus_score) as avg_consensus,\n                AVG(confidence) as avg_confidence,\n                AVG(response_time) as avg_response_time\n            FROM agent_performance\n            WHERE timestamp > datetime('now', '-7 days')\n        ".to_string());
        let mut row = cursor.fetchone();
        conn.close();
        Ok(HashMap::from([("total_queries".to_string(), row[0]), ("unique_agents".to_string(), row[1]), ("avg_consensus".to_string(), (row[2] || 0.0_f64)), ("avg_confidence".to_string(), (row[3] || 0.0_f64)), ("avg_response_time".to_string(), (row[4] || 0.0_f64))]))
    }
}

/// Track API costs for budgeting (Improvement #12 companion).
#[derive(Debug, Clone)]
pub struct CostTracker {
    pub total_cost: f64,
    pub cost_breakdown: HashMap<String, serde_json::Value>,
}

impl CostTracker {
    pub fn new() -> Self {
        Self {
            total_cost: 0.0_f64,
            cost_breakdown: HashMap::new(),
        }
    }
    /// Record a query cost.
    /// 
    /// Args:
    /// model: Model name (e.g., "claude-3", "gpt-4")
    /// content: Response content (for token estimation if tokens not provided)
    /// tokens: Explicit token count (optional)
    /// 
    /// Returns:
    /// Cost of this query in dollars
    pub fn record_query(&mut self, model: String, content: String, tokens: i64) -> () {
        // Record a query cost.
        // 
        // Args:
        // model: Model name (e.g., "claude-3", "gpt-4")
        // content: Response content (for token estimation if tokens not provided)
        // tokens: Explicit token count (optional)
        // 
        // Returns:
        // Cost of this query in dollars
        if tokens.is_none() {
            let mut tokens = (content.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len() * 1.3_f64);
        }
        let mut cost_per_1k = 0.0_f64;
        for (m, c) in self.COSTS.iter().iter() {
            if !model.to_lowercase().contains(&m) {
                continue;
            }
            let mut cost_per_1k = c;
            break;
        }
        let mut cost = ((tokens / 1000.0_f64) * cost_per_1k);
        self.total_cost += cost;
        if !self.cost_breakdown.contains(&model) {
            self.cost_breakdown[model] = 0.0_f64;
        }
        self.cost_breakdown[model] += cost;
        cost
    }
    /// Get total cost across all queries.
    pub fn get_total_cost(&self) -> f64 {
        // Get total cost across all queries.
        self.total_cost
    }
    /// Get cost breakdown by provider.
    pub fn get_cost_breakdown(&self) -> HashMap<String, f64> {
        // Get cost breakdown by provider.
        self.cost_breakdown.clone()
    }
    /// Estimate cost for a query without recording it.
    /// 
    /// Args:
    /// model: Model name
    /// tokens: Token count
    /// 
    /// Returns:
    /// Estimated cost in dollars
    pub fn estimate_cost(&mut self, model: String, tokens: i64) -> f64 {
        // Estimate cost for a query without recording it.
        // 
        // Args:
        // model: Model name
        // tokens: Token count
        // 
        // Returns:
        // Estimated cost in dollars
        let mut cost_per_1k = 0.0_f64;
        for (m, c) in self.COSTS.iter().iter() {
            if !model.to_lowercase().contains(&m) {
                continue;
            }
            let mut cost_per_1k = c;
            break;
        }
        ((tokens / 1000.0_f64) * cost_per_1k)
    }
}

/// Dedicated RAG storage for expert opinions to reduce hallucinations.
/// Stores query -> expert_consensus mappings.
#[derive(Debug, Clone)]
pub struct RagedSwarmStorage {
    pub db_path: String,
}

impl RagedSwarmStorage {
    pub fn new(db_path: String) -> Self {
        Self {
            db_path,
        }
    }
    /// Init db.
    pub fn _init_db(&mut self) -> Result<()> {
        // Init db.
        let mut conn = /* sqlite3 */ self.db_path;
        conn.execute("\n            CREATE TABLE IF NOT EXISTS swarm_memory (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                query_hash TEXT,\n                query_text TEXT,\n                consensus_response TEXT,\n                contributing_experts TEXT,\n                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP\n            )\n        ".to_string());
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS swarm_fts USING fts5(query_text, consensus_response)".to_string());
        conn.commit();
        Ok(conn.close())
    }
    /// Store a finalized consensus.
    pub fn store_consensus(&mut self, query: String, response: String, experts: Vec<String>) -> Result<()> {
        // Store a finalized consensus.
        let mut conn = /* sqlite3 */ self.db_path;
        let mut q_hash = hashlib::sha256(query.as_bytes().to_vec()).hexdigest();
        // try:
        {
            conn.execute("\n                INSERT INTO swarm_memory (query_hash, query_text, consensus_response, contributing_experts)\n                VALUES (?, ?, ?, ?)\n            ".to_string(), (q_hash, query, response, serde_json::to_string(&experts).unwrap()));
            conn.execute("INSERT INTO swarm_fts (query_text, consensus_response) VALUES (?, ?)".to_string(), (query, response));
            conn.commit();
        }
        // except Exception as e:
        // finally:
            Ok(conn.close())
    }
    /// Retrieve similar past swarm decisions.
    pub fn retrieve_similar(&mut self, query: String, limit: i64) -> Result<Vec<HashMap>> {
        // Retrieve similar past swarm decisions.
        let mut conn = /* sqlite3 */ self.db_path;
        // try:
        {
            let mut cursor = conn.execute("\n                SELECT query_text, consensus_response FROM swarm_fts \n                WHERE swarm_fts MATCH ? ORDER BY rank LIMIT ?\n            ".to_string(), (query, limit));
            let mut results = vec![];
            for row in cursor.iter() {
                results.push(HashMap::from([("query".to_string(), row[0]), ("response".to_string(), row[1])]));
            }
            results
        }
        // except Exception as _e:
        // finally:
            Ok(conn.close())
    }
}

/// Base methods for SwarmArbitrator.
#[derive(Debug, Clone)]
pub struct _SwarmArbitratorBase {
    pub config: HashMap<String, serde_json::Value>,
    pub host: String,
    pub scan_ports: String,
    pub ports: Vec<serde_json::Value>,
    pub endpoints: Vec<serde_json::Value>,
    pub swarm_memory: String,
    pub _embedding_model: Option<serde_json::Value>,
    pub performance_tracker: AgentPerformanceTracker,
}

impl _SwarmArbitratorBase {
    /// Initialize instance.
    pub fn new(ports: Option<Vec<i64>>, host: String, config: Option<HashMap>) -> Self {
        Self {
            config: HashMap::new(),
            host,
            scan_ports: (ports || (vec![8001] + 8006..8013.into_iter().collect::<Vec<_>>())),
            ports: vec![],
            endpoints: vec![],
            swarm_memory: if self.config::get(&"rag_swarm_enabled".to_string()).cloned().unwrap_or(true) { RagedSwarmStorage() } else { None },
            _embedding_model: None,
            performance_tracker: Default::default(),
        }
    }
    /// Async heartbeat check to find live experts (parallel).
    pub async fn discover_swarm(&mut self) -> () {
        // Async heartbeat check to find live experts (parallel).
        self.ports = vec![];
        if !self.config["enabled".to_string()] {
            self.ports = vec![8001];
            self.endpoints = vec![format!("http://{}:8001/v1/chat/completions", self.host)];
            logger.debug("[Arbitrator] Swarm disabled. Using main port only.".to_string());
            return;
        }
        let mut client = httpx.AsyncClient();
        {
            let mut tasks = self.scan_ports.iter().map(|p| self._check_port(client, p)).collect::<Vec<_>>();
            let mut results = asyncio.gather(/* *tasks */, /* return_exceptions= */ true).await;
            for (port, is_live) in self.scan_ports.iter().zip(results.iter()).iter() {
                if (is_live && !/* /* isinstance(is_live, Exception) */ */ true) {
                    self.ports.push(port);
                }
            }
        }
        let mut max_size = self.config["size".to_string()];
        if (max_size > 0 && self.ports.len() > max_size) {
            self.ports = (vec![self.ports[0]] + self.ports[1..max_size]);
        }
        self.endpoints = self.ports.iter().map(|p| format!("http://{}:{}/v1/chat/completions", self.host, p)).collect::<Vec<_>>();
        logger.info(format!("[Arbitrator] Discovered {} live experts: {}", self.ports.len(), self.ports));
    }
    /// Check if a port is live.
    pub async fn _check_port(&mut self, client: httpx::AsyncClient, port: i64) -> Result<bool> {
        // Check if a port is live.
        // try:
        {
            let mut resp = client.get(&format!("http://{}:{}/health", self.host, port)).cloned().unwrap_or(/* timeout= */ 1.0_f64).await;
            vec![200, 503].contains(&resp.status_code)
        }
        // except Exception as _e:
    }
    /// Query model with timeout and fallback.
    pub async fn _query_model_with_timeout(&mut self, client: httpx::AsyncClient, endpoint: String, messages: Vec<HashMap>, timeout: f64) -> Result<HashMap> {
        // Query model with timeout and fallback.
        let mut timeout = (timeout || self.config["timeout_per_expert".to_string()]);
        // try:
        {
            asyncio.wait_for(self._query_model(client, endpoint, messages), /* timeout= */ timeout).await
        }
        // except asyncio.TimeoutError as _e:
        // except Exception as e:
    }
    /// Query a single model and return full response + metadata.
    pub async fn _query_model(&mut self, client: httpx::AsyncClient, endpoint: String, messages: Vec<HashMap>) -> Result<HashMap> {
        // Query a single model and return full response + metadata.
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            let mut payload = HashMap::from([("messages".to_string(), messages), ("stream".to_string(), false), ("temperature".to_string(), 0.7_f64), ("max_tokens".to_string(), 512)]);
            let mut response = client.post(endpoint, /* json= */ payload, /* timeout= */ 60.0_f64).await;
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
            if response.status_code == 200 {
                let mut data = response.json();
                let mut content = data["choices".to_string()][0]["message".to_string()]["content".to_string()].trim().to_string();
                let mut model_name = data.get(&"model".to_string()).cloned().unwrap_or("Unknown-Model".to_string());
                let mut confidence = self._extract_confidence(content);
                HashMap::from([("content".to_string(), content), ("time".to_string(), duration), ("model".to_string(), model_name), ("confidence".to_string(), confidence), ("error".to_string(), false)])
            }
            HashMap::from([("content".to_string(), format!("Error: HTTP {}", response.status_code)), ("time".to_string(), duration), ("model".to_string(), "N/A".to_string()), ("confidence".to_string(), 0.0_f64), ("error".to_string(), true)])
        }
        // except Exception as e:
    }
    /// Extract confidence score from response.
    /// 
    /// Looks for patterns:
    /// - "I'm 90% confident" → 0.9
    /// - "Confidence: 0.85" → 0.85
    /// - "I'm quite sure" → 0.8
    /// - "I think maybe" → 0.5
    pub fn _extract_confidence(&self, response_text: String) -> f64 {
        // Extract confidence score from response.
        // 
        // Looks for patterns:
        // - "I'm 90% confident" → 0.9
        // - "Confidence: 0.85" → 0.85
        // - "I'm quite sure" → 0.8
        // - "I think maybe" → 0.5
        let mut r#match = regex::Regex::new(&"(\\d{1,3})%\\s*confident".to_string()).unwrap().is_match(&response_text.to_lowercase());
        if r#match {
            (r#match.group(1).to_string().parse::<f64>().unwrap_or(0.0) / 100.0_f64)
        }
        let mut r#match = regex::Regex::new(&"confidence:?\\s*(\\d\\.\\d+)".to_string()).unwrap().is_match(&response_text.to_lowercase());
        if r#match {
            1.0_f64.min(r#match.group(1).to_string().parse::<f64>().unwrap_or(0.0))
        }
        let mut confidence_markers = vec![("\\b(certain|definite|absolutely|definitely)\\b".to_string(), 0.95_f64), ("\\b(very confident|quite sure|very likely)\\b".to_string(), 0.85_f64), ("\\b(confident|likely|probably)\\b".to_string(), 0.75_f64), ("\\b(think|believe|seems)\\b".to_string(), 0.6_f64), ("\\b(maybe|perhaps|possibly|might)\\b".to_string(), 0.5_f64), ("\\b(unsure|uncertain|not sure)\\b".to_string(), 0.3_f64)];
        for (pattern, score) in confidence_markers.iter() {
            if regex::Regex::new(&pattern).unwrap().is_match(&response_text.to_lowercase()) {
                score
            }
        }
        0.7_f64
    }
    /// Functional Bridge for External Agents (Improvement 12).
    /// 
    /// Queries external LLM APIs (Anthropic Claude, Google Gemini, Grok) using
    /// httpx for async API calls.
    /// 
    /// Args:
    /// model: Model name (e.g., "claude-3-5-sonnet", "gemini-pro", "grok-beta")
    /// messages: List of message dicts with "role" and "content" keys
    /// 
    /// Returns:
    /// Dict with keys:
    /// - content: Response text or error message
    /// - model: Model name
    /// - time: Response time in seconds
    /// - confidence: Extracted confidence score (0.0-1.0)
    pub async fn _query_external_agent(&mut self, model: String, messages: Vec<HashMap>) -> Result<HashMap> {
        // Functional Bridge for External Agents (Improvement 12).
        // 
        // Queries external LLM APIs (Anthropic Claude, Google Gemini, Grok) using
        // httpx for async API calls.
        // 
        // Args:
        // model: Model name (e.g., "claude-3-5-sonnet", "gemini-pro", "grok-beta")
        // messages: List of message dicts with "role" and "content" keys
        // 
        // Returns:
        // Dict with keys:
        // - content: Response text or error message
        // - model: Model name
        // - time: Response time in seconds
        // - confidence: Extracted confidence score (0.0-1.0)
        // TODO: import os
        let mut api_key = (os::getenv("OPENAI_API_KEY".to_string()) || os::getenv("ANTHROPIC_API_KEY".to_string()) || os::getenv("GOOGLE_API_KEY".to_string()) || os::getenv("XAI_API_KEY".to_string()));
        if !api_key {
            HashMap::from([("content".to_string(), "[ERROR: No API Key found for external agent]".to_string()), ("model".to_string(), model), ("time".to_string(), 0.0_f64), ("confidence".to_string(), 0.0_f64)])
        }
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            let mut client = httpx.AsyncClient();
            {
                let mut payload = HashMap::from([("model".to_string(), model), ("messages".to_string(), messages), ("temperature".to_string(), 0.7_f64)]);
                let mut url = "https://api.openai.com/v1/chat/completions".to_string();
                let mut headers = HashMap::from([("Authorization".to_string(), format!("Bearer {}", api_key))]);
                let mut response = client.post(url, /* json= */ payload, /* headers= */ headers, /* timeout= */ 60.0_f64).await;
                if response.status_code == 200 {
                    let mut data = response.json();
                    let mut content = data["choices".to_string()][0]["message".to_string()]["content".to_string()].trim().to_string();
                    HashMap::from([("content".to_string(), content), ("time".to_string(), (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start)), ("model".to_string(), model), ("confidence".to_string(), self._extract_confidence(content))])
                }
                HashMap::from([("content".to_string(), format!("[API Error: {}]", response.status_code)), ("model".to_string(), model), ("time".to_string(), (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start)), ("confidence".to_string(), 0.0_f64)])
            }
        }
        // except Exception as e:
    }
    /// Calculate consensus using specified method.
    pub fn _calculate_consensus(&mut self, responses: Vec<String>, method: Option<ConsensusMethod>) -> f64 {
        // Calculate consensus using specified method.
        let mut method = (method || ConsensusMethod[&self.config["consensus_method".to_string()].to_uppercase()]);
        if method == ConsensusMethod.WORD_SET {
            self._calculate_consensus_wordset(responses)
        } else if method == ConsensusMethod.SEMANTIC {
            self._calculate_consensus_semantic(responses)
        } else if method == ConsensusMethod.HYBRID {
            let mut word_score = self._calculate_consensus_wordset(responses);
            let mut semantic_score = self._calculate_consensus_semantic(responses);
            ((word_score + semantic_score) / 2.0_f64)
        } else {
            self._calculate_consensus_wordset(responses)
        }
    }
    /// Original word-set intersection/union method.
    pub fn _calculate_consensus_wordset(&self, responses: Vec<String>) -> f64 {
        // Original word-set intersection/union method.
        if responses.len() == 0 {
            0.0_f64
        }
        if responses.len() == 1 {
            1.0_f64
        }
        let mut sets = responses.iter().map(|r| r.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>()).collect::<Vec<_>>();
        if !sets.iter().all(|v| *v) {
            0.0_f64
        }
        let mut common = set.intersection(/* *sets */);
        let mut union = set.union(/* *sets */);
        if union { (common.len() / union.len()) } else { 0.0_f64 }
    }
    /// Semantic similarity using sentence embeddings.
    pub fn _calculate_consensus_semantic(&mut self, responses: Vec<String>) -> Result<f64> {
        // Semantic similarity using sentence embeddings.
        // try:
        {
            if self._embedding_model.is_none() {
                // TODO: from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2".to_string());
                logger.info("[Arbitrator] Loaded semantic embedding model".to_string());
            }
            // TODO: from sklearn.metrics.pairwise import cosine_similarity
            // TODO: import numpy as np
            let mut embeddings = self._embedding_model.encode(responses);
            let mut similarities = cosine_similarity(embeddings);
            let mut n = responses.len();
            if n < 2 {
                1.0_f64
            }
            let mut total_sim = ((similarities.sum() - n) / (n * (n - 1)));
            total_sim.to_string().parse::<f64>().unwrap_or(0.0)
        }
        // except ImportError as _e:
    }
}

/// Enhanced multi-LLM consensus system with research-backed improvements.
/// 
/// Features:
/// - Async parallel dispatch
/// - Semantic consensus
/// - Confidence extraction
/// - Weighted voting
/// - Task-based protocol routing
/// - Agent performance tracking
/// - Adaptive round selection
#[derive(Debug, Clone)]
pub struct SwarmArbitrator {
}

impl SwarmArbitrator {
    /// Select optimal protocol based on task type (research-backed).
    pub fn select_protocol(&mut self, task_type: String) -> ConsensusProtocol {
        // Select optimal protocol based on task type (research-backed).
        if !self.config["protocol_routing".to_string()] {
            ConsensusProtocol.WEIGHTED_VOTE
        }
        let mut protocol_map = HashMap::from([("factual".to_string(), ConsensusProtocol.CONSENSUS), ("quick_qa".to_string(), ConsensusProtocol.CONSENSUS), ("reasoning".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("math".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("code".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("creative".to_string(), ConsensusProtocol.VOTING), ("general".to_string(), ConsensusProtocol.MAJORITY)]);
        protocol_map.get(&task_type.to_lowercase()).cloned().unwrap_or(ConsensusProtocol.HYBRID)
    }
    /// Decide if second debate round is worth the cost.
    pub fn should_do_round_two(&mut self, agreement: f64, confidence_scores: Vec<f64>) -> bool {
        // Decide if second debate round is worth the cost.
        if !self.config["adaptive_rounds".to_string()] {
            false
        }
        if agreement > 0.8_f64 {
            logger.info(format!("[Arbitrator] Skipping Round 2: High agreement ({:.1%})", agreement));
            false
        }
        if confidence_scores {
            let mut avg_confidence = (confidence_scores.iter().sum::<i64>() / confidence_scores.len());
            if avg_confidence > 0.85_f64 {
                logger.info(format!("[Arbitrator] Skipping Round 2: High confidence ({:.1%})", avg_confidence));
                false
            }
        }
        logger.info(format!("[Arbitrator] Round 2 needed: agreement={:.1%}", agreement));
        true
    }
    /// Traffic controller mode for 2 LLMs.
    /// 
    /// Strategy:
    /// 1. Fast LLM evaluates difficulty
    /// 2. Easy → Fast LLM answers
    /// 3. Hard → Powerful LLM answers
    /// 4. Medium → Get second opinion
    pub async fn _traffic_controller_mode(&mut self, query: String, system_prompt: String) -> AsyncGenerator</* unknown */> {
        // Traffic controller mode for 2 LLMs.
        // 
        // Strategy:
        // 1. Fast LLM evaluates difficulty
        // 2. Easy → Fast LLM answers
        // 3. Hard → Powerful LLM answers
        // 4. Medium → Get second opinion
        let mut fast_llm = self.endpoints[0];
        let mut powerful_llm = self.endpoints[1];
        if self.endpoints {
            /* yield "🚦 Evaluating query complexity...\n".to_string() */;
            let mut evaluation = self._evaluate_query_difficulty(query, /* evaluator_endpoint= */ fast_llm).await;
        } else {
            let mut evaluation = HashMap::from([("difficulty".to_string(), "medium".to_string()), ("confidence".to_string(), 0.5_f64)]);
        }
        let mut difficulty = evaluation::get(&"difficulty".to_string()).cloned().unwrap_or("medium".to_string());
        let mut confidence = evaluation::get(&"confidence".to_string()).cloned().unwrap_or(0.5_f64);
        let mut threshold = self.config::get(&"traffic_controller_threshold".to_string()).cloned().unwrap_or(0.8_f64);
        if (difficulty == "easy".to_string() && confidence > threshold) {
            /* yield format!("💨 **Fast response** ({}, confidence: {:.0%})\n\n", difficulty, confidence) */;
            // async for
            while let Some(chunk) = self._stream_from_llm(fast_llm, query, system_prompt).next().await {
                /* yield chunk */;
            }
        } else if (difficulty == "hard".to_string() || confidence < 0.5_f64) {
            /* yield format!("🚀 **Expert routing** ({}, confidence: {:.0%})\n\n", difficulty, confidence) */;
            // async for
            while let Some(chunk) = self._stream_from_llm(powerful_llm, query, system_prompt).next().await {
                /* yield chunk */;
            }
        } else {
            /* yield format!("⚖️ **Verification** ({}, confidence: {:.0%})\n\n", difficulty, confidence) */;
            let mut fast_answer = self._get_answer(fast_llm, query, system_prompt).await;
            let mut powerful_answer = self._get_answer(powerful_llm, query, system_prompt).await;
            let mut agreement = self._calculate_consensus(vec![fast_answer, powerful_answer]);
            if agreement > 0.7_f64 {
                /* yield fast_answer */;
            } else {
                /* yield powerful_answer */;
            }
        }
    }
    /// Use fast LLM to classify query difficulty.
    /// 
    /// Args:
    /// query: The user query
    /// evaluator_endpoint: Endpoint to use for evaluation (defaults to self.endpoints[0])
    /// 
    /// Returns:
    /// {
    /// "difficulty": "easy|medium|hard",
    /// "domain": "code|math|creative|factual|reasoning",
    /// "confidence": 0.0-1.0,
    /// "reasoning": "brief explanation"
    /// }
    pub async fn _evaluate_query_difficulty(&mut self, query: String, evaluator_endpoint: String) -> Result<HashMap> {
        // Use fast LLM to classify query difficulty.
        // 
        // Args:
        // query: The user query
        // evaluator_endpoint: Endpoint to use for evaluation (defaults to self.endpoints[0])
        // 
        // Returns:
        // {
        // "difficulty": "easy|medium|hard",
        // "domain": "code|math|creative|factual|reasoning",
        // "confidence": 0.0-1.0,
        // "reasoning": "brief explanation"
        // }
        if evaluator_endpoint {
            let mut controller_endpoint = evaluator_endpoint;
        } else if self.endpoints {
            let mut controller_endpoint = self.endpoints[0];
        } else {
            let mut controller_endpoint = format!("http://{}:8001/v1/chat/completions", self.host);
        }
        let mut eval_prompt = format!("Analyze this query and respond ONLY with JSON:\n\nQuery: {}\n\n{{\n    \"difficulty\": \"easy|medium|hard\",\n    \"domain\": \"code|math|creative|factual|reasoning\",\n    \"confidence\": 0.0-1.0,\n    \"reasoning\": \"1 sentence\"\n}}\n\nRules:\n- \"easy\": Factual QA, simple math, definitions\n- \"medium\": Code, explanations, analysis\n- \"hard\": Complex reasoning, research, proofs\n\nJSON:", query);
        // try:
        {
            let mut client = httpx.AsyncClient();
            {
                let mut response = self._query_model_with_timeout(client, controller_endpoint, vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), eval_prompt)])], /* timeout= */ 5.0_f64).await;
                let mut content = response["content".to_string()];
                if content.contains(&"```json".to_string()) {
                    let mut content = content.split("```json".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[1].split("```".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim().to_string();
                } else if content.contains(&"```".to_string()) {
                    let mut content = content.split("```".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[1].split("```".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].trim().to_string();
                }
                let mut result = serde_json::from_str(&content).unwrap();
                result
            }
        }
        // except Exception as e:
    }
    /// Stream response from a single LLM.
    pub async fn _stream_from_llm(&self, endpoint: String, query: String, system_prompt: String) -> Result<AsyncGenerator</* unknown */>> {
        // Stream response from a single LLM.
        let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut payload = HashMap::from([("messages".to_string(), messages), ("stream".to_string(), true), ("temperature".to_string(), 0.7_f64), ("max_tokens".to_string(), -1)]);
        let mut client = httpx.AsyncClient();
        {
            let mut response = client.stream("POST".to_string(), endpoint, /* json= */ payload, /* timeout= */ 120.0_f64);
            {
                // async for
                while let Some(line) = response.aiter_lines().next().await {
                    if !line.starts_with(&*"data: ".to_string()) {
                        continue;
                    }
                    let mut json_str = line[6..];
                    if json_str.trim().to_string() == "[DONE]".to_string() {
                        break;
                    }
                    // try:
                    {
                        let mut data = serde_json::from_str(&json_str).unwrap();
                        let mut content = data["choices".to_string()][0]["delta".to_string()].get(&"content".to_string()).cloned().unwrap_or("".to_string());
                        if content {
                            /* yield content */;
                        }
                    }
                    // except Exception as _e:
                }
            }
        }
    }
    /// Get complete answer from a single LLM (non-streaming).
    pub async fn _get_answer(&mut self, endpoint: String, query: String, system_prompt: String) -> String {
        // Get complete answer from a single LLM (non-streaming).
        let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut client = httpx.AsyncClient();
        {
            let mut response = self._query_model_with_timeout(client, endpoint, messages).await;
            response["content".to_string()]
        }
    }
    /// Structured consensus decision (non-streaming) for API usage.
    pub async fn arbiter_decision(&mut self, request: ArbitrationRequest) -> HashMap {
        // Structured consensus decision (non-streaming) for API usage.
        let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        if !self.endpoints {
            self.discover_swarm().await;
        }
        if !self.endpoints {
            HashMap::from([("consensus_answer".to_string(), "Error: No experts available.".to_string()), ("individual_responses".to_string(), vec![]), ("method".to_string(), "failure".to_string()), ("confidence".to_string(), 0.0_f64), ("duration".to_string(), 0.0_f64)])
        }
        let mut sys_prompt = HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are a swarm expert. Answer concisely.".to_string())]);
        let mut messages = vec![sys_prompt, HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), request.query)])];
        let mut client = httpx.AsyncClient();
        {
            let mut tasks = self.endpoints.iter().map(|ep| self._query_model_with_timeout(client, ep, messages)).collect::<Vec<_>>();
            let mut results = asyncio.gather(/* *tasks */).await;
        }
        let mut valid_results = results.iter().filter(|r| !r.get(&"error".to_string()).cloned()).map(|r| r).collect::<Vec<_>>();
        let mut responses = valid_results.iter().map(|r| r["content".to_string()]).collect::<Vec<_>>();
        let mut agreement = self._calculate_consensus(responses);
        let mut t_type = if /* hasattr(request.task_type, "value".to_string()) */ true { request.task_type.value } else { request.task_type.to_string() };
        let mut protocol = self.select_protocol(t_type);
        let mut referee_endpoint = self.endpoints[0];
        let mut prompt = self._build_arbitrage_prompt(request.query, responses, agreement, protocol);
        let mut final_answer = self._get_answer(referee_endpoint, prompt, "You are the Swarm Referee.".to_string()).await;
        HashMap::from([("consensus_answer".to_string(), final_answer), ("individual_responses".to_string(), valid_results), ("method".to_string(), protocol.value), ("confidence".to_string(), agreement), ("duration".to_string(), (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time))])
    }
    /// Continue get_consensus logic.
    pub async fn _get_consensus_continued(&mut self, messages: String, protocol: String, response: String) -> Result<()> {
        // Continue get_consensus logic.
        let mut client = httpx.AsyncClient();
        {
            logger.info(format!("[Arbitrator] Round 1: Querying {} experts...", self.endpoints.len()));
            let mut tasks = self.endpoints.iter().map(|ep| self._query_model_with_timeout(client, ep, messages)).collect::<Vec<_>>();
            let mut raw_results = asyncio.gather(/* *tasks */).await;
            let mut valid_results = raw_results.iter().filter(|r| !r.get(&"error".to_string()).cloned().unwrap_or(false)).map(|r| r).collect::<Vec<_>>();
            let mut failed_count = (raw_results.len() - valid_results.len());
            if valid_results.len() < self.config["min_experts".to_string()] {
                /* yield format!("❌ **Insufficient experts:** {}/{} available\n", valid_results.len(), self.config["min_experts".to_string()]) */;
                if valid_results.len() > 0 {
                    /* yield "**Fallback:** Using available expert(s)...\n\n".to_string() */;
                } else {
                    return;
                }
            }
            if failed_count > 0 {
                /* yield format!("⚠️ {} expert(s) unavailable\n", failed_count) */;
            }
            let mut responses = valid_results.iter().map(|r| r["content".to_string()]).collect::<Vec<_>>();
            let mut confidence_scores = valid_results.iter().map(|r| r["confidence".to_string()]).collect::<Vec<_>>();
            let mut agreement = self._calculate_consensus(responses);
            let mut confidence_label = if agreement > 0.6_f64 { "High".to_string() } else { if agreement > 0.3_f64 { "Medium".to_string() } else { "Low".to_string() } };
            if verbose {
                /* yield format!("\n### Expert Responses ({} Consensus: {:.1%})\n\n", confidence_label, agreement) */;
                for (i, r) in valid_results.iter().enumerate().iter() {
                    /* yield format!("**Expert {}** ({}, {:.1}s, {:.0%} confident):\n", (i + 1), r["model".to_string()], r["time".to_string()], r["confidence".to_string()]) */;
                    /* yield format!("{}...\n\n", r["content".to_string()][..300]) */;
                }
            }
            if self.should_do_round_two(agreement, confidence_scores) {
                /* yield format!("⚖️ **Low consensus** ({:.1%}) - Cross-critique round...\n\n", agreement) */;
                let mut critique_tasks = vec![];
                for (i, endpoint) in raw_results.iter().enumerate().iter().filter(|(j, r)| !r.get(&"error".to_string()).cloned()).map(|(j, r)| self.endpoints[&j]).collect::<Vec<_>>().iter().enumerate().iter() {
                    let mut other_responses = 0..responses.len().iter().filter(|j| j != i).map(|j| responses[&j]).collect::<Vec<_>>();
                    let mut critique_prompt = self._build_critique_prompt(/* original= */ responses[&i], /* others= */ other_responses, /* question= */ text);
                    critique_tasks.push(self._query_model_with_timeout(client, endpoint, critique_prompt));
                }
                let mut revised_results = asyncio.gather(/* *critique_tasks */).await;
                let mut valid_revised = revised_results.iter().filter(|r| !r.get(&"error".to_string()).cloned().unwrap_or(false)).map(|r| r).collect::<Vec<_>>();
                if valid_revised.len() > 0 {
                    let mut responses = valid_revised.iter().map(|r| r["content".to_string()]).collect::<Vec<_>>();
                    let mut agreement = self._calculate_consensus(responses);
                    /* yield format!("✅ **Revised consensus:** {:.1%}\n\n", agreement) */;
                }
            }
            /* yield format!("🔮 **Synthesizing final answer...**\n\n") */;
            let mut arbitrage_prompt = self._build_arbitrage_prompt(/* question= */ text, /* responses= */ responses, /* agreement= */ agreement, /* protocol= */ protocol);
            let mut referee_messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are the Swarm Referee. Synthesize expert opinions into a unified answer.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), arbitrage_prompt)])];
            let mut referee_endpoint = self.endpoints[0];
            let mut payload = HashMap::from([("messages".to_string(), referee_messages), ("stream".to_string(), true), ("temperature".to_string(), 0.2_f64), ("max_tokens".to_string(), -1)]);
            let mut full_answer = "".to_string();
            let mut start_synthesis = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            // try:
            {
                let mut response = client.stream("POST".to_string(), referee_endpoint, /* json= */ payload, /* timeout= */ 120.0_f64);
                {
                    // async for
                    while let Some(line) = response.aiter_lines().next().await {
                        if !line.starts_with(&*"data: ".to_string()) {
                            continue;
                        }
                        let mut json_str = line[6..];
                        if json_str.trim().to_string() == "[DONE]".to_string() {
                            break;
                        }
                        // try:
                        {
                            let mut data = serde_json::from_str(&json_str).unwrap();
                            let mut content = data["choices".to_string()][0]["delta".to_string()].get(&"content".to_string()).cloned().unwrap_or("".to_string());
                            if content {
                                full_answer += content;
                                /* yield content */;
                            }
                        }
                        // except Exception as _e:
                    }
                }
            }
            // except Exception as e:
            let mut synthesis_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_synthesis);
            if self.performance_tracker {
                let mut query_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                for (i, r) in valid_results.iter().enumerate().iter() {
                    self.performance_tracker.record_response(/* agent_id= */ r["model".to_string()], /* task_type= */ task_type, /* query_hash= */ query_hash, /* response_text= */ r["content".to_string()], /* was_selected= */ i == 0, /* consensus_score= */ agreement, /* confidence= */ r["confidence".to_string()], /* response_time= */ r["time".to_string()]);
                }
            }
            /* yield format!("\n\n---\n📊 **Swarm Metrics:** Consensus **{:.1%}** | ", agreement) */;
            /* yield format!("Experts **{}** | Synthesis **{:.1}s** | Protocol **{}**\n", valid_results.len(), synthesis_time, protocol.value) */;
        }
    }
    /// Get consensus answer from expert swarm.
    /// 
    /// Process:
    /// 1. Discover available experts
    /// 2. Parallel query all experts
    /// 3. Calculate consensus score
    /// 4. (Optional) Round 2 cross-critique
    /// 5. Referee synthesis
    /// 6. Track performance
    pub async fn get_consensus(&mut self, text: String, system_prompt: String, task_type: String, verbose: bool) -> AsyncGenerator</* unknown */> {
        // Get consensus answer from expert swarm.
        // 
        // Process:
        // 1. Discover available experts
        // 2. Parallel query all experts
        // 3. Calculate consensus score
        // 4. (Optional) Round 2 cross-critique
        // 5. Referee synthesis
        // 6. Track performance
        if !self.endpoints {
            self.discover_swarm().await;
        }
        let mut num_llms = self.endpoints.len();
        if num_llms == 0 {
            /* yield "❌ **Error:** No experts available.\n".to_string() */;
            return;
        } else if num_llms == 1 {
            logger.info("[Arbitrator] Single LLM mode".to_string());
            let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), text)])];
            let mut client = httpx.AsyncClient();
            {
                let mut response = self._query_model_with_timeout(client, self.endpoints[0], messages).await;
                /* yield response["content".to_string()] */;
            }
            return;
        } else if num_llms == 2 {
            logger.info("[Arbitrator] Traffic controller mode (2 LLMs)".to_string());
            // async for
            while let Some(chunk) = self._traffic_controller_mode(text, system_prompt).next().await {
                /* yield chunk */;
            }
            return;
        }
        logger.info(format!("[Arbitrator] Consensus mode ({} LLMs)", num_llms));
        let mut messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), system_prompt)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), text)])];
        let mut protocol = self.select_protocol(task_type);
        /* yield format!("🔄 **Analyzing...** ({} experts, {} protocol)\n\n", self.endpoints.len(), protocol.value) */;
        _get_consensus_continued(self, messages, protocol, response).await;
    }
    /// Build prompt for cross-critique round.
    pub fn _build_critique_prompt(&self, original: String, others: Vec<String>, question: String) -> Vec<HashMap> {
        // Build prompt for cross-critique round.
        let mut other_text = others.iter().enumerate().iter().map(|(i, o)| format!("--- Alternative View {} ---\n{}", (i + 1), o)).collect::<Vec<_>>().join(&"\n\n".to_string());
        let mut prompt = format!("You previously answered: \"{}\"\n\nYour answer was:\n{}\n\nOther experts provided different perspectives:\n{}\n\nAfter reviewing these alternative views:\n1. Do you still stand by your answer?\n2. If not, provide a revised answer incorporating valid points from others.\n3. If yes, explain why your answer is more accurate.\n\nRevised or confirmed answer:", question, original, other_text);
        vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), prompt)])]
    }
    /// Build referee synthesis prompt based on protocol.
    pub fn _build_arbitrage_prompt(&self, question: String, responses: Vec<String>, agreement: f64, protocol: ConsensusProtocol) -> String {
        // Build referee synthesis prompt based on protocol.
        let mut expert_text = responses.iter().enumerate().iter().map(|(i, r)| format!("--- Expert {} ---\n{}", (i + 1), r)).collect::<Vec<_>>().join(&"\n\n".to_string());
        if protocol == ConsensusProtocol.CONSENSUS {
            let mut strategy = "Find the single correct answer. Converge expert opinions to the most accurate truth.".to_string();
        } else if protocol == ConsensusProtocol.WEIGHTED_VOTE {
            let mut strategy = "Weight expert opinions by reliability and confidence. Prioritize high-confidence answers.".to_string();
        } else if protocol == ConsensusProtocol.VOTING {
            let mut strategy = "Respect diverse viewpoints. Present a balanced synthesis of all perspectives.".to_string();
        } else {
            let mut strategy = "Harmonize insights and resolve any conflicts into a unified answer.".to_string();
        }
        let mut prompt = format!("You are the Swarm Referee. {} experts have responded.\n\n**Consensus Level:** {} ({:.1%})\n**Strategy:** {}\n\n**User Question:**\n{}\n\n**Expert Contributions:**\n{}\n\n**Instructions:**\n- Synthesize a clean, unified, authoritative final answer\n- If major disagreements exist, explain which view is most accurate and why\n- Be concise but complete\n\n**Final Verified Answer:**", responses.len(), if agreement > 0.6_f64 { "High".to_string() } else { if agreement > 0.3_f64 { "Medium".to_string() } else { "Low".to_string() } }, agreement, strategy, question, expert_text);
        prompt
    }
}

/// Factory function to create arbitrator instance.
pub fn get_arbitrator(config: Option<HashMap>) -> SwarmArbitrator {
    // Factory function to create arbitrator instance.
    SwarmArbitrator(/* config= */ config)
}
