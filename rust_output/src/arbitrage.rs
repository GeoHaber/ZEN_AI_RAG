/// arbitrage::py - Swarm Arbitrator for Multi-LLM Consensus
/// Ported and adapted from naughty-antonelli

use anyhow::{Result, Context};
use crate::config_system::{config, EMOJI};
use crate::profiler::{monitor};
use crate::utils::{safe_print, logger};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use tokio;

/// ConsensusMethod class.
#[derive(Debug, Clone)]
pub struct ConsensusMethod {
}

/// Consensus protocols for different task types.
#[derive(Debug, Clone)]
pub struct ConsensusProtocol {
}

/// Track agent accuracy and reliability over time using SQLite.
#[derive(Debug, Clone)]
pub struct AgentPerformanceTracker {
    pub db_path: String,
}

impl AgentPerformanceTracker {
    /// Initialize instance.
    pub fn new(db_path: String) -> Self {
        Self {
            db_path,
        }
    }
    /// Init db.
    pub fn _init_db(&mut self) -> Result<()> {
        // Init db.
        // try:
        {
            let mut conn = /* sqlite3 */ self.db_path;
            conn.execute("\n                CREATE TABLE IF NOT EXISTS agent_performance (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    agent_id TEXT NOT NULL,\n                    task_type TEXT,\n                    query_hash TEXT,\n                    response_text TEXT,\n                    was_selected INTEGER,\n                    consensus_score REAL,\n                    confidence REAL,\n                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP\n                )\n            ".to_string());
            conn.commit();
            conn.close();
        }
        // except Exception as e:
    }
    /// Record response.
    pub fn record_response(&mut self, agent_id: String, task_type: String, query_hash: String, response_text: String, was_selected: String, consensus_score: String, confidence: String, response_time: String) -> Result<()> {
        // Record response.
        // try:
        {
            let mut conn = /* sqlite3 */ self.db_path;
            conn.execute("\n                INSERT INTO agent_performance (agent_id, task_type, query_hash, response_text, was_selected, consensus_score, confidence)\n                VALUES (?, ?, ?, ?, ?, ?, ?)\n            ".to_string(), (agent_id, task_type, query_hash, response_text[..500], if was_selected { 1 } else { 0 }, consensus_score, confidence));
            conn.commit();
            conn.close();
        }
        // except Exception as e:
    }
    /// Get historical accuracy/selection rate for an agent.
    pub fn get_agent_reliability(&mut self, agent_id: String, task_type: String) -> Result<f64> {
        // Get historical accuracy/selection rate for an agent.
        // try:
        {
            let mut conn = /* sqlite3 */ self.db_path;
            if task_type {
                let mut cursor = conn.execute("\n                    SELECT AVG(was_selected) FROM agent_performance \n                    WHERE agent_id = ? AND task_type = ?\n                    AND timestamp > datetime('now', '-30 days')\n                ".to_string(), (agent_id, task_type));
            } else {
                let mut cursor = conn.execute("\n                    SELECT AVG(was_selected) FROM agent_performance \n                    WHERE agent_id = ?\n                    AND timestamp > datetime('now', '-30 days')\n                ".to_string(), (agent_id));
            }
            let mut res = cursor.fetchone()[0];
            conn.close();
            if res.is_some() { res } else { 0.5_f64 }
        }
        // except Exception as e:
    }
    /// Get overall performance stats.
    pub fn get_stats(&mut self) -> Result<HashMap> {
        // Get overall performance stats.
        // try:
        {
            let mut conn = /* sqlite3 */ self.db_path;
            let mut cursor = conn.execute("\n                SELECT COUNT(*), AVG(consensus_score), AVG(confidence) \n                FROM agent_performance\n            ".to_string());
            let (mut count, mut avg_cons, mut avg_conf) = cursor.fetchone();
            conn.close();
            HashMap::from([("total_queries".to_string(), (count || 0)), ("avg_consensus".to_string(), (avg_cons || 0.0_f64)), ("avg_confidence".to_string(), (avg_conf || 0.0_f64))])
        }
        // except Exception as e:
    }
}

/// Track API costs for budgeting.
#[derive(Debug, Clone)]
pub struct CostTracker {
    pub total_cost: f64,
}

impl CostTracker {
    pub fn new() -> Self {
        Self {
            total_cost: 0.0_f64,
        }
    }
    /// Record query.
    pub fn record_query(&mut self, model: String, content: String) -> () {
        // Record query.
        let mut tokens = (content.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len() * 1.3_f64);
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
        cost
    }
}

/// Base methods for SwarmArbitrator.
#[derive(Debug, Clone)]
pub struct _SwarmArbitratorBase {
    pub scan_ports: String,
    pub ports: Vec<serde_json::Value>,
    pub endpoints: Vec<serde_json::Value>,
    pub performance_tracker: AgentPerformanceTracker,
    pub cost_tracker: CostTracker,
    pub nli_model: Option<serde_json::Value>,
    pub latencies: HashMap<String, serde_json::Value>,
    pub reliability_penalty_threshold: f64,
}

impl _SwarmArbitratorBase {
    /// Initialize instance.
    pub fn new(ports: Vec<i64>) -> Self {
        Self {
            scan_ports: (vec![config::llm_port] + 8005..8013.into_iter().collect::<Vec<_>>()),
            ports: vec![],
            endpoints: vec![],
            performance_tracker: AgentPerformanceTracker(),
            cost_tracker: CostTracker(),
            nli_model: None,
            latencies: HashMap::new(),
            reliability_penalty_threshold: 0.4_f64,
        }
    }
    /// Synchronous version of swarm discovery using blocking httpx.Client.
    /// 
    /// This avoids starting an asyncio loop during import or in tests.
    pub fn discover_swarm_sync(&mut self) -> Result<()> {
        // Synchronous version of swarm discovery using blocking httpx.Client.
        // 
        // This avoids starting an asyncio loop during import or in tests.
        // TODO: import httpx as _httpx
        self.ports = vec![];
        if !config::swarm_enabled {
            self.ports = vec![config::llm_port];
            self.endpoints = vec![format!("http://{}:{}/v1/chat/completions", config::host, config::llm_port)];
            return;
        }
        // try:
        {
            let mut client = _httpx.Client();
            {
                for p in self.scan_ports.iter() {
                    // try:
                    {
                        let mut resp = client.get(&format!("http://{}:{}/health", config::host, p)).cloned().unwrap_or(/* timeout= */ 1.0_f64);
                        if (200, 503).contains(&resp.status_code) {
                            self.ports.push(p);
                        }
                    }
                    // except Exception as _e:
                }
            }
            if (config::swarm_enabled && self.ports.len() > 8) {
                self.ports = (vec![self.ports[0]] + self.ports[1..9]);
            }
            self.endpoints = self.ports.iter().map(|p| format!("http://{}:{}/v1/chat/completions", config::host, p)).collect::<Vec<_>>();
            logger.debug(format!("[Arbitrator] (sync) Live Swarm discovered on ports: {}", self.ports));
        }
        // except Exception as e:
    }
    /// Pre-load NLI model.
    pub async fn warmup(&mut self) -> () {
        // Pre-load NLI model.
        if self.nli_model.is_some() {
            return;
        }
        logger.info("[Arbitrator] Warming up NLI model...".to_string());
        // TODO: from sentence_transformers import CrossEncoder
        self.nli_model = CrossEncoder("cross-encoder/nli-distilroberta-base".to_string());
        let mut _ = self.nli_model.predict(vec![vec!["fact".to_string(), "context".to_string()]]);
        logger.info("[Arbitrator] NLI Model ready.".to_string());
    }
    /// Async heartbeat check to find live experts.
    pub async fn discover_swarm(&mut self) -> () {
        // Async heartbeat check to find live experts.
        self.ports = vec![];
        if !config::swarm_enabled {
            self.ports = vec![config::llm_port];
            self.endpoints = vec![format!("http://{}:{}/v1/chat/completions", config::host, config::llm_port)];
            logger.debug("[Arbitrator] Swarm disabled in config. Using main port only.".to_string());
            return;
        }
        let mut client = httpx.AsyncClient();
        {
            let mut tasks = vec![];
            for p in self.scan_ports.iter() {
                tasks.push(self._check_port(client, p));
            }
            let mut results = asyncio.gather(/* *tasks */, /* return_exceptions= */ true).await;
            for (port, is_live) in self.scan_ports.iter().zip(results.iter()).iter() {
                if (is_live && !/* /* isinstance(is_live, Exception) */ */ true) {
                    self.ports.push(port);
                }
            }
        }
        self.endpoints = self.ports.iter().map(|p| format!("http://{}:{}/v1/chat/completions", config::host, p)).collect::<Vec<_>>();
        self.ports.sort(/* key= */ |p| self.latencies.get(&p).cloned().unwrap_or(999));
        self.endpoints = self.ports.iter().map(|p| format!("http://{}:{}/v1/chat/completions", config::host, p)).collect::<Vec<_>>();
        logger.debug(format!("[Arbitrator] Live Swarm discovered (sorted by latency): {}", self.ports));
    }
    /// Check if a port is live and measure latency.
    pub async fn _check_port(&mut self, client: httpx::AsyncClient, port: i64) -> Result<bool> {
        // Check if a port is live and measure latency.
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            let mut resp = client.get(&format!("http://{}:{}/health", config::host, port)).cloned().unwrap_or(/* timeout= */ 1.0_f64).await;
            let mut latency = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
            if vec![200, 503].contains(&resp.status_code) {
                self.latencies[port] = latency;
                true
            }
            false
        }
        // except Exception as _e:
    }
    /// Route to optimal consensus protocol based on task type.
    pub fn select_protocol(&self, task_type: String) -> ConsensusProtocol {
        // Route to optimal consensus protocol based on task type.
        let mut mapping = HashMap::from([("factual".to_string(), ConsensusProtocol.CONSENSUS), ("reasoning".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("math".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("code".to_string(), ConsensusProtocol.WEIGHTED_VOTE), ("creative".to_string(), ConsensusProtocol.VOTING), ("general".to_string(), ConsensusProtocol.MAJORITY)]);
        mapping.get(&task_type.to_lowercase()).cloned().unwrap_or(ConsensusProtocol.HYBRID)
    }
    /// Detect significant semantic contradictions between expert responses.
    pub fn detect_contradictions(&mut self, responses: Vec<String>) -> Result<Vec<HashMap>> {
        // Detect significant semantic contradictions between expert responses.
        if responses.len() < 2 {
            vec![]
        }
        // try:
        {
            // TODO: from sklearn.metrics.pairwise import cosine_similarity
            if !/* hasattr(self, "_embedding_model".to_string()) */ true {
                // TODO: from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2".to_string());
            }
            let mut embeddings = self._embedding_model.encode(responses);
            let mut similarities = cosine_similarity(embeddings);
            let mut contradictions = vec![];
            for i in 0..responses.len().iter() {
                for j in (i + 1)..responses.len().iter() {
                    if similarities[&i][&j] < 0.2_f64 {
                        contradictions.push(HashMap::from([("pair".to_string(), ((i + 1), (j + 1))), ("similarity".to_string(), similarities[&i][&j].to_string().parse::<f64>().unwrap_or(0.0))]));
                    }
                }
            }
            contradictions
        }
        // except ImportError as _e:
    }
    /// Verify if the response is supported by the provided context chunks using NLI.
    /// Returns a 'fact_check_score' (0.0 - 1.0) and 'unsupported_sentences'.
    pub fn verify_hallucination(&mut self, response_text: String, context_chunks: Vec<String>) -> Result<HashMap> {
        // Verify if the response is supported by the provided context chunks using NLI.
        // Returns a 'fact_check_score' (0.0 - 1.0) and 'unsupported_sentences'.
        if !context_chunks {
            HashMap::from([("score".to_string(), 0.5_f64), ("reason".to_string(), "No context provided".to_string()), ("unsupported".to_string(), vec![])])
        }
        // try:
        {
            // TODO: from sentence_transformers import CrossEncoder
            if self.nli_model.is_none() {
                logger.info("[Arbitrator] Loading NLI model for hallucination check...".to_string());
                self.nli_model = CrossEncoder("cross-encoder/nli-distilroberta-base".to_string());
            }
            let mut sentences = re::split("(?<=[.!?])\\s+".to_string(), response_text).iter().filter(|s| s.len() > 10).map(|s| s.trim().to_string()).collect::<Vec<_>>();
            if !sentences {
                HashMap::from([("score".to_string(), 1.0_f64), ("reason".to_string(), "Response too short".to_string()), ("unsupported".to_string(), vec![])])
            }
            let mut supported_count = 0;
            let mut unsupported = vec![];
            for sent in sentences.iter() {
                let mut pairs = context_chunks.iter().map(|chunk| vec![chunk, sent]).collect::<Vec<_>>();
                let mut scores = self.nli_model.predict(pairs);
                let mut probs = (numpy.exp(scores) / numpy.sum(numpy.exp(scores), /* axis= */ 1, /* keepdims= */ true));
                let mut entailment_scores = probs[(.., 1)];
                let mut max_entailment = numpy.max(entailment_scores);
                if max_entailment > 0.6_f64 {
                    supported_count += 1;
                } else {
                    unsupported.push(sent);
                }
            }
            let mut score = (supported_count / sentences.len());
            HashMap::from([("score".to_string(), score), ("reason".to_string(), format!("{}/{} sentences supported by context", supported_count, sentences.len())), ("unsupported".to_string(), unsupported)])
        }
        // except Exception as e:
    }
    /// Extract confidence score from response using regex and linguistic markers.
    pub fn _extract_confidence(&self, response_text: String) -> f64 {
        // Extract confidence score from response using regex and linguistic markers.
        let mut r#match = regex::Regex::new(&"(\\d{1,3})%\\s*confident".to_string()).unwrap().is_match(&response_text.to_lowercase());
        if r#match {
            (r#match.group(1).to_string().parse::<f64>().unwrap_or(0.0) / 100.0_f64)
        }
        let mut r#match = regex::Regex::new(&"confidence:?\\s*(\\d\\.\\d+)".to_string()).unwrap().is_match(&response_text.to_lowercase());
        if r#match {
            r#match.group(1).to_string().parse::<f64>().unwrap_or(0.0)
        }
        let mut confidence_markers = HashMap::from([("\\b(certain|definite|absolutely|definitely)\\b".to_string(), 0.95_f64), ("\\b(very confident|quite sure|very likely)\\b".to_string(), 0.85_f64), ("\\b(confident|likely|probably)\\b".to_string(), 0.75_f64), ("\\b(think|believe|seems)\\b".to_string(), 0.6_f64), ("\\b(maybe|perhaps|possibly|might)\\b".to_string(), 0.5_f64), ("\\b(unsure|uncertain|not sure)\\b".to_string(), 0.3_f64)]);
        for (pattern, score) in confidence_markers.iter().iter() {
            if regex::Regex::new(&pattern).unwrap().is_match(&response_text.to_lowercase()) {
                score
            }
        }
        0.7_f64
    }
    /// Query a single model and return full text + timing + model name + confidence.
    pub async fn _query_model(&mut self, client: httpx::AsyncClient, endpoint: String, messages: Vec<HashMap>) -> Result<HashMap> {
        // Query a single model and return full text + timing + model name + confidence.
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            let mut payload = HashMap::from([("messages".to_string(), messages), ("stream".to_string(), false), ("temperature".to_string(), 0.7_f64), ("max_tokens".to_string(), 512)]);
            let mut response = client.post(endpoint, /* json= */ payload, /* timeout= */ 30.0_f64).await;
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
            if response.status_code == 200 {
                let mut data = response.json();
                let mut content = data["choices".to_string()][0]["message".to_string()]["content".to_string()].trim().to_string();
                let mut model_name = data.get(&"model".to_string()).cloned().unwrap_or("Unknown-Model".to_string());
                HashMap::from([("content".to_string(), content), ("time".to_string(), duration), ("model".to_string(), model_name), ("confidence".to_string(), self._extract_confidence(content))])
            }
            HashMap::from([("content".to_string(), format!("Error: {}", response.status_code)), ("time".to_string(), duration), ("model".to_string(), "N/A".to_string()), ("confidence".to_string(), 0.0_f64)])
        }
        // except Exception as e:
    }
}

/// Manages parallel LLM queries and implements arbitrage logic
/// to correct hallucinations and improve response quality.
#[derive(Debug, Clone)]
pub struct SwarmArbitrator {
}

impl SwarmArbitrator {
    /// Query with per-expert timeout and fallback.
    pub async fn _query_model_with_timeout(&mut self, client: httpx::AsyncClient, endpoint: String, messages: Vec<HashMap>, timeout: f64) -> Result<HashMap> {
        // Query with per-expert timeout and fallback.
        // try:
        {
            asyncio.wait_for(self._query_model(client, endpoint, messages), /* timeout= */ timeout).await
        }
        // except asyncio.TimeoutError as _e:
        // except Exception as e:
    }
    /// LiteLLM Bridge Placeholder (Improvement 12).
    pub async fn _query_external_agent(&self, model: String, messages: Vec<HashMap>) -> HashMap {
        // LiteLLM Bridge Placeholder (Improvement 12).
        logger.info(format!("[Bridge] External query to {} (Mocked)", model));
        HashMap::from([("content".to_string(), "[LITELLM MOCK RESPONSE]".to_string()), ("model".to_string(), model), ("time".to_string(), 0.5_f64), ("confidence".to_string(), 0.7_f64)])
    }
    /// AutoGen Integration Stub (Improvement 13).
    pub fn init_autogen_swarm(&self) -> () {
        // AutoGen Integration Stub (Improvement 13).
        logger.info("[AutoGen] Initializing AutoGen Swarm Manager (Mocked)".to_string());
        // pass
    }
    /// Calculate simple variance of confidence scores.
    pub fn _calculate_variance(&self, scores: Vec<f64>) -> f64 {
        // Calculate simple variance of confidence scores.
        if !scores {
            0.0_f64
        }
        let mut avg = (scores.iter().sum::<i64>() / scores.len());
        (scores.iter().map(|x| ((x - avg)).pow(2 as u32)).collect::<Vec<_>>().iter().sum::<i64>() / scores.len())
    }
    /// Decide if second reasoning/debate round is worth the cost.
    pub fn should_do_round_two(&self, agreement: f64, confidence_scores: Vec<f64>) -> bool {
        // Decide if second reasoning/debate round is worth the cost.
        if agreement > 0.8_f64 {
            false
        }
        if (confidence_scores.iter().sum::<i64>() / 1.max(confidence_scores.len())) > 0.85_f64 {
            false
        }
        if self._calculate_variance(confidence_scores) < 0.1_f64 {
            false
        }
        agreement < 0.6_f64
    }
    /// Calculate a rough agreement score (0.0 to 1.0) using word set overlap.
    pub fn _calculate_consensus_simple(&self, responses: Vec<String>) -> f64 {
        // Calculate a rough agreement score (0.0 to 1.0) using word set overlap.
        if responses.len() < 2 {
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
    /// Functional Bridge for External Agents (Improvement 12).
    pub async fn _query_external_agent(&mut self, model: String, messages: Vec<HashMap>) -> Result<HashMap> {
        // Functional Bridge for External Agents (Improvement 12).
        let mut api_key = (os::getenv("OPENAI_API_KEY".to_string()) || os::getenv("ANTHROPIC_API_KEY".to_string()) || os::getenv("GOOGLE_API_KEY".to_string()));
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
    pub fn _calculate_consensus(&mut self, responses: Vec<String>, method: ConsensusMethod) -> f64 {
        // Calculate consensus using specified method.
        if method == ConsensusMethod.WORD_SET {
            self._calculate_consensus_simple(responses)
        } else if method == ConsensusMethod.SEMANTIC {
            self._calculate_consensus_semantic(responses)
        } else if method == ConsensusMethod.HYBRID {
            ((self._calculate_consensus_simple(responses) + self._calculate_consensus_semantic(responses)) / 2.0_f64)
        }
    }
    /// Calculate consensus using semantic similarity if sentence_transformers is available.
    pub fn _calculate_consensus_semantic(&mut self, responses: Vec<HashMap>) -> Result<f64> {
        // Calculate consensus using semantic similarity if sentence_transformers is available.
        if !responses {
            0.0_f64
        }
        if responses.len() == 1 {
            1.0_f64
        }
        // try:
        {
            // TODO: from sentence_transformers import SentenceTransformer, util
            let mut model = SentenceTransformer("all-MiniLM-L6-v2".to_string());
            let mut texts = responses.iter().map(|r| r["content".to_string()]).collect::<Vec<_>>();
            let mut embeddings = model.encode(texts);
            let mut sim_matrix = util.cos_sim(embeddings, embeddings);
            let mut n = responses.len();
            let mut total_sim = ((sim_matrix.sum() - n) / (n * (n - 1)));
            total_sim.to_string().parse::<f64>().unwrap_or(0.0)
        }
        // except Exception as e:
    }
    /// Memory-First CoT Flow with Structured Terminal Tracing and Resilience.
    pub async fn get_cot_response(&mut self, text: String, system_prompt: String, verbose: bool, task_type: String) -> Result<AsyncGenerator</* unknown */>> {
        // Memory-First CoT Flow with Structured Terminal Tracing and Resilience.
        if !self.endpoints {
            self.discover_swarm().await;
        }
        safe_print(("\n".to_string() + ("=".to_string() * 80)));
        safe_print(format!("      🔍 SWARM INQUIRY: {}...", text[..150]));
        safe_print(("=".to_string() * 80));
        let mut query_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
        let mut trace_id = monitor.start_trace();
        monitor.log_trace(trace_id, format!("Swarm Inquiry Start (Task: {})", task_type));
        monitor.log_trace(trace_id, format!("Query Text: {}...", text[..100]));
        let mut expert_system_prompt = self.TASK_SYSTEM_PROMPTS.get(&task_type.to_lowercase()).cloned().unwrap_or(self.TASK_SYSTEM_PROMPTS["general".to_string()]);
        let mut expert_messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), expert_system_prompt)]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), text)])];
        /* yield format!("{} **Thinking...** (Swarm size: {})\n\n", EMOJI["loading".to_string()], self.endpoints.len()) */;
        let mut client = httpx.AsyncClient();
        {
            let mut raw_results = vec![];
            if self.endpoints.len() == 1 {
                safe_print(format!("[REASONING] Mode: Single-Model Reflection Loop"));
                let mut r1 = self._query_model_with_timeout(client, self.endpoints[0], expert_messages, /* timeout= */ 30.0_f64).await;
                safe_print(format!("  > Initial Logic ({}): {}...", r1["model".to_string()], r1["content".to_string()][..150]));
                let mut critique_msg = (expert_messages + vec![HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), r1["content".to_string()])]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), "Critique your previous answer for logic, accuracy, and completeness. Then provide a final corrected version.".to_string())])]);
                let mut r2 = self._query_model_with_timeout(client, self.endpoints[0], critique_msg, /* timeout= */ 30.0_f64).await;
                safe_print(format!("  > Self-Correction ({}): {}...", r2["model".to_string()], r2["content".to_string()][..150]));
                let mut raw_results = vec![r1, r2];
            } else {
                safe_print(format!("[REASONING] Querying {} Knowledge Experts...", self.endpoints.len()));
                let mut tasks = self.endpoints.iter().map(|ep| self._query_model_with_timeout(client, ep, expert_messages, /* timeout= */ 30.0_f64)).collect::<Vec<_>>();
                let mut raw_results = asyncio.gather(/* *tasks */).await;
            }
            let mut valid_results = raw_results.iter().filter(|r| (r["model".to_string()] != "N/A".to_string() && !r["content".to_string()].starts_with(&*"[".to_string()))).map(|r| r).collect::<Vec<_>>();
            for r in valid_results.iter() {
                self.cost_tracker.record_query(r["model".to_string()], r["content".to_string()]);
                monitor.log_trace(trace_id, format!("Expert {} responded in {:.2}s", r["model".to_string()], r["time".to_string()]));
            }
            if !valid_results {
                /* yield format!("{} **All experts failed or timed out.**\n\n", EMOJI["error".to_string()]) */;
                if self.endpoints[0] != format!("http://{}:{}/v1/chat/completions", HOST, PORTS["LLM_API".to_string()]) {
                    let mut fallback_ep = format!("http://{}:{}/v1/chat/completions", HOST, PORTS["LLM_API".to_string()]);
                    /* yield format!("🔄 **Fallback**: Attempting primary engine...\n\n") */;
                    let mut r_fallback = self._query_model_with_timeout(client, fallback_ep, messages, /* timeout= */ 45.0_f64).await;
                    if r_fallback["model".to_string()] != "N/A".to_string() {
                        let mut valid_results = vec![r_fallback];
                        self.cost_tracker.record_query(r_fallback["model".to_string()], r_fallback["content".to_string()]);
                    } else {
                        /* yield "❌ Critical failure: System unreachable.".to_string() */;
                        return;
                    }
                } else {
                    return;
                }
            }
            for (i, r) in valid_results.iter().enumerate().iter() {
                let mut agent_name = r.get(&"model".to_string()).cloned().unwrap_or(format!("Expert {}", (i + 1)));
                if (text.contains(&"[SOURCE]:".to_string()) || text.contains(&"Reference Context:".to_string())) {
                    // pass
                }
                safe_print(format!("  > Analysis [{}] ({:.2}s): {}...", agent_name, r["time".to_string()], r["content".to_string()][..300]));
            }
            let mut responses = valid_results.iter().map(|r| r["content".to_string()]).collect::<Vec<_>>();
            let mut confidence_scores = valid_results.iter().map(|r| r.get(&"confidence".to_string()).cloned().unwrap_or(0.7_f64)).collect::<Vec<_>>();
            let mut protocol = self.select_protocol(task_type);
            let mut contradictions = self.detect_contradictions(responses);
            let mut agreement = self._calculate_consensus(responses, ConsensusMethod.HYBRID);
            let mut confidence = if agreement > 0.6_f64 { "High".to_string() } else { if agreement > 0.3_f64 { "Medium".to_string() } else { "Low".to_string() } };
            if (self.should_do_round_two(agreement, confidence_scores) || contradictions) {
                safe_print(format!("[REASONING] Low agreement ({:.1%}) or contradictions found. Initiating Debate...", agreement));
                /* yield format!("⚖️ **Debate Initiated** ({:.1%} Agreement | {} Conflicts) - Refining insights...\n\n", agreement, contradictions.len()) */;
            }
            if verbose {
                for (i, resp_data) in valid_results.iter().enumerate().iter() {
                    let mut expert_label = format!("Expert {}", (i + 1));
                    /* yield format!("--- **{}** ({:.2}s) ---\n{}...\n\n", expert_label, resp_data["time".to_string()], resp_data["content".to_string()][..300]) */;
                }
                if contradictions {
                    /* yield "⚠️ **Contradictions detected** between some expert perspectives.\n\n".to_string() */;
                }
                /* yield format!("⚖️ **Arbitrage Hub**: Synthesizing ({} Consensus)...\n\n", confidence) */;
            }
            let mut referee_endpoint = if self.endpoints { self.endpoints[0] } else { format!("http://{}:{}/v1/chat/completions", config::host, config::llm_port) };
            safe_print("\n[DECISION MATRIX]".to_string());
            safe_print(format!("  PROCESSOR: Master Arbitrator (Active)"));
            safe_print(format!("  RATIONALE: {} Consensus ({:.1%}) across {} nodes.", confidence, agreement, responses.len()));
            if contradictions {
                safe_print(format!("  ALERTS: {} major contradictions detected.", contradictions.len()));
            }
            safe_print("  STATUS: Processing final synthesis...".to_string());
            let mut contradiction_info = "".to_string();
            if contradictions {
                let mut contradiction_info = "\nWARNING: The following experts significantly disagreed:\n".to_string();
                for c in contradictions.iter() {
                    contradiction_info += format!("- Expert {} vs Expert {} (Similarity: {:.2})\n", c["pair".to_string()][0], c["pair".to_string()][1], c["similarity".to_string()]);
                }
            }
            let mut arbitrage_prompt = format!("\nYou are the **Swarm Referee**. I have received {} expert responses.\nCONSENSUS: {} ({:.1%})\n{}\n\nUSER QUERY: {}\n\nEXPERT CONTRIBUTIONS:\n{}\n\nINSTRUCTIONS:\n- Harmonize the insights and resolve any conflicts.\n- Provide a clean, unified, and authoritative final answer.\n- Append a 'Summary of Reasoning' if the experts had major disagreements.\n\nFINAL VERIFIED RESPONSE:\n", responses.len(), confidence, agreement, contradiction_info, text[..500], responses.iter().enumerate().iter().map(|(i, r)| format!("--- Expert {} ---\n{}\n", (i + 1), r)).collect::<Vec<_>>().join(&char::from(10 as u8).to_string()));
            let mut referee_messages = vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "Resolve conflicts and provide the final verified truth.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), arbitrage_prompt)])];
            let mut payload = HashMap::from([("messages".to_string(), referee_messages), ("stream".to_string(), true), ("temperature".to_string(), 0.2_f64), ("max_tokens".to_string(), -1)]);
            safe_print(((("\n".to_string() + ("-".to_string() * 40)) + "\n🚀 FINAL RESPONSE STREAMING:\n".to_string()) + ("-".to_string() * 40)));
            let mut full_referee_text = "".to_string();
            let mut start_ref = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            // try:
            {
                let mut response = client.stream("POST".to_string(), referee_endpoint, /* json= */ payload, /* timeout= */ httpx.Timeout(60.0_f64, /* connect= */ 5.0_f64));
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
                                full_referee_text += content;
                                safe_print(content);
                                /* yield content */;
                            }
                        }
                        // except Exception as _e:
                    }
                }
            }
            // except Exception as e:
            let mut dur_ref = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_ref);
            safe_print((((("\n".to_string() + ("-".to_string() * 40)) + format!("\n✅ COMPLETED in {:.1}s\n", dur_ref)) + ("=".to_string() * 80)) + "\n".to_string()));
            for r in valid_results.iter() {
                self.performance_tracker.get_agent_reliability(r["model".to_string()], task_type);
                let mut final_selection = true;
                if (text.contains(&"[SOURCE]:".to_string()) || text.contains(&"Reference Context:".to_string())) {
                    let mut fact_check = self.verify_hallucination(r["content".to_string()], vec![text]);
                    if fact_check["score".to_string()] < self.reliability_penalty_threshold {
                        logger.warning(format!("[Arbitrator] Penalizing {} for low fact-check score: {}", r["model".to_string()], fact_check["score".to_string()]));
                        let mut final_selection = false;
                    }
                }
                self.performance_tracker.record_response(/* agent_id= */ r["model".to_string()], /* task_type= */ task_type, /* query_hash= */ query_hash, /* response_text= */ r["content".to_string()], /* was_selected= */ final_selection, /* consensus_score= */ agreement, /* confidence= */ r.get(&"confidence".to_string()).cloned().unwrap_or(0.7_f64), /* response_time= */ r["time".to_string()]);
            }
            let mut explanation = format!("\n\n---\n📊 **Swarm Metrics**: Consensus **{:.1%}** | Synthesis **{:.1}s** | Cost **${:.4}**\n", agreement, dur_ref, self.cost_tracker.total_cost);
            explanation += format!("🧠 **Decision Rationale**: Logic verified using `{}` protocol across {} nodes.", protocol.value, responses.len());
            /* yield explanation */;
        }
    }
}

pub fn get_arbitrator() -> () {
    SwarmArbitrator()
}
