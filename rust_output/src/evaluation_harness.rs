/// Core/evaluation_harness::py — RAG Evaluation Harness for ZEN_RAG.
/// 
/// Phase 3.3: Compute standard IR and NLP metrics for RAG quality assessment.
/// 
/// Metrics:
/// - NDCG@k  (Normalized Discounted Cumulative Gain)
/// - MRR     (Mean Reciprocal Rank)
/// - Hit@k   (fraction of queries with at least one relevant doc in top-k)
/// - BLEU    (BiLingual Evaluation Understudy, requires nltk)
/// - ROUGE-L (Longest Common Subsequence recall, requires rouge-score)
/// - Precision@k, Recall@k
/// 
/// Usage:
/// harness = EvaluationHarness(rag=my_rag, llm=my_llm)
/// results = harness.run(test_cases=[
/// {"query": "What is X?", "expected": "X is ...", "relevant_docs": ["url1"]},
/// ])
/// harness.print_report(results)
/// harness.save_report(results, "eval_results.json")

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// End-to-end RAG evaluation harness.
/// 
/// Supports:
/// - Retrieval metrics: NDCG@k, MRR, Hit@k, Precision@k, Recall@k
/// - Generation metrics: BLEU, ROUGE-L
/// - Latency tracking
/// - JSON report export
#[derive(Debug, Clone)]
pub struct EvaluationHarness {
    pub rag: String,
    pub llm: String,
    pub k: String,
    pub output_dir: PathBuf,
}

impl EvaluationHarness {
    /// Args:
    /// rag: LocalRAG instance.
    /// llm: Optional LLM for answer generation evaluation.
    /// k: Top-k for retrieval metrics.
    /// output_dir: Directory for saved reports.
    pub fn new(rag: Box<dyn std::any::Any>, llm: Box<dyn std::any::Any>, k: i64, output_dir: String) -> Self {
        Self {
            rag,
            llm,
            k,
            output_dir: PathBuf::from(output_dir),
        }
    }
    /// Run evaluation over a list of test cases.
    /// 
    /// Each test case dict:
    /// - query (str): The question
    /// - expected (str): Reference answer for BLEU/ROUGE
    /// - relevant_docs (List[str]): URLs/titles of relevant documents
    /// - relevance_scores (Dict[str, float]): Optional graded relevance (0-1)
    /// 
    /// Returns:
    /// Aggregated metrics dict + per-sample results.
    pub fn run(&mut self, test_cases: Vec<HashMap>, verbose: bool) -> Result<HashMap> {
        // Run evaluation over a list of test cases.
        // 
        // Each test case dict:
        // - query (str): The question
        // - expected (str): Reference answer for BLEU/ROUGE
        // - relevant_docs (List[str]): URLs/titles of relevant documents
        // - relevance_scores (Dict[str, float]): Optional graded relevance (0-1)
        // 
        // Returns:
        // Aggregated metrics dict + per-sample results.
        let mut per_sample = vec![];
        let mut t0_total = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        for (i, tc) in test_cases.iter().enumerate().iter() {
            let mut query = tc.get(&"query".to_string()).cloned().unwrap_or("".to_string());
            let mut expected = tc.get(&"expected".to_string()).cloned().unwrap_or("".to_string());
            let mut relevant_docs = tc.get(&"relevant_docs".to_string()).cloned().unwrap_or(vec![]).into_iter().collect::<HashSet<_>>();
            let mut rel_scores_map = tc.get(&"relevance_scores".to_string()).cloned().unwrap_or(HashMap::new());
            if !query {
                continue;
            }
            if verbose {
                logger.info(format!("[Eval] Sample {}/{}: {}...", (i + 1), test_cases.len(), query[..60]));
            }
            let mut t0 = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            // try:
            {
                let mut retrieved = self.rag.hybrid_search(query, /* k= */ self.k, /* rerank= */ true);
            }
            // except Exception as e:
            let mut latency = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - t0);
            let mut relevances = self._compute_relevances(retrieved, relevant_docs, rel_scores_map);
            let mut ideal = { let mut v = relevances.clone(); v.sort(); v };
            let mut sample_metrics = HashMap::from([("query".to_string(), query), ("latency_s".to_string(), ((latency as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("n_retrieved".to_string(), retrieved.len()), (format!("ndcg@{}", self.k), ((_ndcg(relevances, ideal, self.k) as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("mrr".to_string(), ((_mrr(relevances) as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), (format!("hit@{}", self.k), _hit_at_k(relevances, self.k)), (format!("precision@{}", self.k), ((_precision_at_k(relevances, self.k) as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), (format!("recall@{}", self.k), ((_recall_at_k(relevances, relevant_docs.len(), self.k) as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("bleu".to_string(), 0.0_f64), ("rouge_l".to_string(), 0.0_f64), ("generated_answer".to_string(), "".to_string())]);
            if (self.llm && expected) {
                let mut generated = self._generate_answer(query, retrieved);
                sample_metrics["generated_answer".to_string()] = generated;
                if generated {
                    sample_metrics["bleu".to_string()] = ((_bleu_score(expected, generated) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
                    sample_metrics["rouge_l".to_string()] = ((_rouge_l(expected, generated) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
                }
            }
            per_sample.push(sample_metrics);
        }
        let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - t0_total);
        let mut agg = self._aggregate(per_sample, total_time);
        Ok(HashMap::from([("summary".to_string(), agg), ("samples".to_string(), per_sample)]))
    }
    /// Compute relevance score for each retrieved chunk.
    pub fn _compute_relevances(&self, retrieved: Vec<HashMap>, relevant_docs: HashSet<String>, rel_scores_map: HashMap<String, f64>) -> Vec<f64> {
        // Compute relevance score for each retrieved chunk.
        let mut relevances = vec![];
        for chunk in retrieved.iter() {
            let mut url = (chunk.get(&"url".to_string()).cloned().unwrap_or("".to_string()) || "".to_string());
            let mut title = (chunk.get(&"title".to_string()).cloned().unwrap_or("".to_string()) || "".to_string());
            let mut combined = ((url + " ".to_string()) + title);
            if rel_scores_map {
                let mut score = rel_scores_map.get(&url).cloned().unwrap_or(0.0_f64).max(rel_scores_map.get(&title).cloned().unwrap_or(0.0_f64));
                relevances.push(score);
            } else {
                let mut is_rel = relevant_docs.iter().filter(|rd| rd).map(|rd| (combined.contains(&rd) || rd.contains(&combined))).collect::<Vec<_>>().iter().any(|v| *v);
                relevances.push(if is_rel { 1.0_f64 } else { 0.0_f64 });
            }
        }
        relevances
    }
    /// Generate answer using LLM for BLEU/ROUGE evaluation.
    pub fn _generate_answer(&mut self, query: String, context_chunks: Vec<HashMap>) -> Result<String> {
        // Generate answer using LLM for BLEU/ROUGE evaluation.
        // try:
        {
            let mut context = context_chunks[..5].iter().map(|c| c.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..500]).collect::<Vec<_>>().join(&"\n\n".to_string());
            let mut prompt = format!("Answer concisely based on context:\n\nContext:\n{}\n\nQuestion: {}\n\nAnswer:", context, query);
            if /* hasattr(self.llm, "query_sync".to_string()) */ true {
                self.llm.query_sync(prompt, /* max_tokens= */ 200).trim().to_string()
            } else if /* hasattr(self.llm, "generate".to_string()) */ true {
                self.llm.generate(prompt).trim().to_string()
            }
        }
        // except Exception as e:
        Ok("".to_string())
    }
    /// Compute mean metrics across all samples.
    pub fn _aggregate(&self, per_sample: Vec<HashMap>, total_time: f64) -> HashMap {
        // Compute mean metrics across all samples.
        if !per_sample {
            HashMap::new()
        }
        let mut metric_keys = per_sample[0].iter().filter(|k| /* /* isinstance(per_sample[0][&k], (int, float) */) */ true).map(|k| k).collect::<Vec<_>>();
        let mut agg = HashMap::from([("n_samples".to_string(), per_sample.len()), ("total_time_s".to_string(), ((total_time as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("avg_latency_s".to_string(), (((per_sample.iter().map(|s| s["latency_s".to_string()]).collect::<Vec<_>>().iter().sum::<i64>() / per_sample.len()) as f64) * 10f64.powi(3)).round() / 10f64.powi(3))]);
        for key in metric_keys.iter() {
            let mut values = per_sample.iter().filter(|s| s.contains(&key)).map(|s| s[&key]).collect::<Vec<_>>();
            if values {
                agg[format!("mean_{}", key)] = (((values.iter().sum::<i64>() / values.len()) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
            }
        }
        agg
    }
    /// Print formatted evaluation report.
    pub fn print_report(&self, results: HashMap<String, serde_json::Value>) -> () {
        // Print formatted evaluation report.
        let mut summary = results.get(&"summary".to_string()).cloned().unwrap_or(HashMap::new());
        println!("{}", ("\n".to_string() + ("=".to_string() * 60)));
        println!("{}", "ZEN_RAG EVALUATION REPORT".to_string());
        println!("{}", ("=".to_string() * 60));
        println!("Samples evaluated : {}", summary.get(&"n_samples".to_string()).cloned().unwrap_or(0));
        println!("Total time        : {:.1}s", summary.get(&"total_time_s".to_string()).cloned().unwrap_or(0));
        println!("Avg latency       : {:.3}s", summary.get(&"avg_latency_s".to_string()).cloned().unwrap_or(0));
        println!("{}", ("-".to_string() * 60));
        for (key, val) in summary.iter().iter() {
            if (key.starts_with(&*"mean_".to_string()) && !key.contains(&"latency".to_string())) {
                let mut metric_name = key.replace(&*"mean_".to_string(), &*"".to_string()).to_uppercase();
                println!("{:<20}: {:.4}", metric_name, val);
            }
        }
        println!("{}", ("=".to_string() * 60));
    }
    /// Save evaluation results to JSON.
    pub fn save_report(&mut self, results: HashMap<String, serde_json::Value>, filename: String) -> Result<PathBuf> {
        // Save evaluation results to JSON.
        if !filename {
            let mut ts = datetime::now().strftime("%Y%m%d_%H%M%S".to_string());
            let mut filename = format!("eval_{}.json", ts);
        }
        let mut out_path = (self.output_dir / filename);
        let mut f = File::create(out_path)?;
        {
            json::dump(results, f, /* indent= */ 2, /* ensure_ascii= */ false);
        }
        logger.info(format!("[Eval] Report saved to {}", out_path));
        Ok(out_path)
    }
}

/// Discounted Cumulative Gain at k.
pub fn _dcg(relevances: Vec<f64>, k: i64) -> f64 {
    // Discounted Cumulative Gain at k.
    relevances[..k].iter().enumerate().iter().map(|(i, rel)| (rel / math::log2((i + 2)))).collect::<Vec<_>>().iter().sum::<i64>()
}

/// NDCG@k. relevances[i] = relevance score of i-th retrieved doc.
pub fn _ndcg(retrieved: Vec<f64>, ideal: Vec<f64>, k: i64) -> f64 {
    // NDCG@k. relevances[i] = relevance score of i-th retrieved doc.
    let mut idcg = _dcg({ let mut v = ideal.clone(); v.sort(); v }, k);
    if idcg == 0 {
        0.0_f64
    }
    (_dcg(retrieved, k) / idcg)
}

/// Mean Reciprocal Rank (expects relevances list; returns 1/rank for first relevant).
pub fn _mrr(retrieved: Vec<f64>) -> f64 {
    // Mean Reciprocal Rank (expects relevances list; returns 1/rank for first relevant).
    for (rank, rel) in retrieved.iter().enumerate().iter() {
        if rel > 0 {
            (1.0_f64 / rank)
        }
    }
    0.0_f64
}

/// 1 if any relevant doc in top-k, else 0.
pub fn _hit_at_k(retrieved: Vec<f64>, k: i64) -> f64 {
    // 1 if any relevant doc in top-k, else 0.
    if retrieved[..k].iter().map(|r| r > 0).collect::<Vec<_>>().iter().any(|v| *v) { 1.0_f64 } else { 0.0_f64 }
}

/// Fraction of top-k retrieved docs that are relevant.
pub fn _precision_at_k(retrieved: Vec<f64>, k: i64) -> f64 {
    // Fraction of top-k retrieved docs that are relevant.
    if k == 0 {
        0.0_f64
    }
    (retrieved[..k].iter().filter(|r| r > 0).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>() / k)
}

/// Fraction of all relevant docs found in top-k.
pub fn _recall_at_k(retrieved: Vec<f64>, n_relevant: i64, k: i64) -> f64 {
    // Fraction of all relevant docs found in top-k.
    if n_relevant == 0 {
        0.0_f64
    }
    (retrieved[..k].iter().filter(|r| r > 0).map(|r| 1).collect::<Vec<_>>().iter().sum::<i64>() / n_relevant)
}

/// Compute sentence BLEU-1 (unigram precision). No external deps.
pub fn _bleu_score(reference: String, hypothesis: String) -> f64 {
    // Compute sentence BLEU-1 (unigram precision). No external deps.
    let mut ref_tokens = reference.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
    let mut hyp_tokens = hypothesis.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
    if (!hyp_tokens || !ref_tokens) {
        0.0_f64
    }
    let mut ref_set = ref_tokens.into_iter().collect::<HashSet<_>>();
    let mut matches = hyp_tokens.iter().filter(|t| ref_set.contains(&t)).map(|t| 1).collect::<Vec<_>>().iter().sum::<i64>();
    (matches / hyp_tokens.len())
}

/// ROUGE-L F1 via LCS (pure Python).
pub fn _rouge_l(reference: String, hypothesis: String) -> f64 {
    // ROUGE-L F1 via LCS (pure Python).
    let mut r#ref = reference.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
    let mut hyp = hypothesis.to_lowercase().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
    if (!r#ref || !hyp) {
        0.0_f64
    }
    let (mut m, mut n) = (r#ref.len(), hyp.len());
    let mut dp = 0..(m + 1).iter().map(|_| (vec![0] * (n + 1))).collect::<Vec<_>>();
    for i in 1..(m + 1).iter() {
        for j in 1..(n + 1).iter() {
            dp[&i][j] = if r#ref[(i - 1)] == hyp[(j - 1)] { (dp[(i - 1)][(j - 1)] + 1) } else { dp[(i - 1)][&j].max(dp[&i][(j - 1)]) };
        }
    }
    let mut lcs = dp[&m][&n];
    let mut precision = (lcs / n);
    let mut recall = (lcs / m);
    if (precision + recall) == 0 {
        0.0_f64
    }
    (((2 * precision) * recall) / (precision + recall))
}
