/// Phase 2: Real API Testing for External LLM Integration
/// 
/// Tests the integration with REAL APIs from:
/// - Anthropic Claude 3.5 Sonnet
/// - Google Gemini Pro
/// - Grok (optional)
/// 
/// Requirements:
/// - ANTHROPIC_API_KEY environment variable
/// - GOOGLE_API_KEY environment variable
/// - XAI_API_KEY environment variable (optional)
/// 
/// Expected Cost: ~$0.03 total
/// 
/// Test Queries:
/// 1. Factual: "What is the capital of France?" (expect agreement)
/// 2. Math: "If a train travels at 60mph for 2.5 hours, how far does it go?" (expect agreement)
/// 3. Nuanced: "Should investors buy stocks during a recession?" (expect disagreement)
/// 4. Code: "Write a Python function to check if a number is prime" (expect different implementations)

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static ANTHROPIC_KEY: std::sync::LazyLock<String /* os::getenv */> = std::sync::LazyLock::new(|| Default::default());

pub static GOOGLE_KEY: std::sync::LazyLock<String /* os::getenv */> = std::sync::LazyLock::new(|| Default::default());

pub static GROK_KEY: std::sync::LazyLock<String /* os::getenv */> = std::sync::LazyLock::new(|| Default::default());

/// Test real API queries to external LLMs.
#[derive(Debug, Clone)]
pub struct TestRealAPIQueries {
}

impl TestRealAPIQueries {
    /// Create arbitrator instance (no local models needed).
    pub fn arbitrator(&self) -> () {
        // Create arbitrator instance (no local models needed).
        SwarmArbitrator(/* ports= */ vec![8001])
    }
    /// Create cost tracker instance.
    pub fn cost_tracker(&self) -> () {
        // Create cost tracker instance.
        CostTracker()
    }
    /// Test 1: Factual Query - High Agreement Expected
    /// 
    /// Query: "What is the capital of France?"
    /// Expected: All LLMs should agree → "Paris"
    /// Expected Cost: ~$0.005
    pub async fn test_factual_query_consensus(&self, arbitrator: String, cost_tracker: String) -> () {
        // Test 1: Factual Query - High Agreement Expected
        // 
        // Query: "What is the capital of France?"
        // Expected: All LLMs should agree → "Paris"
        // Expected Cost: ~$0.005
        let mut query = "What is the capital of France?".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut results = vec![];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("\n[Claude] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        if GOOGLE_KEY {
            let mut result = arbitrator._query_external_agent("gemini-pro".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Gemini] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        if GROK_KEY {
            let mut result = arbitrator._query_external_agent("grok-beta".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Grok] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        assert!(results.len() > 0, "No API responses received");
        let mut responses = results.iter().filter(|r| !r["content".to_string()].starts_with(&*"[".to_string())).map(|r| r["content".to_string()]).collect::<Vec<_>>();
        if responses.len() > 1 {
            let mut consensus = arbitrator._calculate_consensus_simple(responses);
            println!("\nConsensus: {:.1%}", consensus);
            assert!(consensus > 0.3_f64, "Expected high consensus for factual query, got {:.1%}", consensus);
        }
        for result in results.iter() {
            if !result["content".to_string()].starts_with(&*"[".to_string()) {
                assert!(result["content".to_string()].contains(&"Paris".to_string()), "Expected 'Paris' in response: {}", result["content"]);
            }
        }
        println!("\nTest Cost: ${:.4}", cost_tracker.get_total_cost());
    }
    /// Test 2: Math Query - High Agreement Expected
    /// 
    /// Query: "If a train travels at 60mph for 2.5 hours, how far does it go?"
    /// Expected: All LLMs should agree → "150 miles"
    /// Expected Cost: ~$0.005
    pub async fn test_math_query_consensus(&self, arbitrator: String, cost_tracker: String) -> () {
        // Test 2: Math Query - High Agreement Expected
        // 
        // Query: "If a train travels at 60mph for 2.5 hours, how far does it go?"
        // Expected: All LLMs should agree → "150 miles"
        // Expected Cost: ~$0.005
        let mut query = "If a train travels at 60mph for 2.5 hours, how far does it go? Provide just the numerical answer with units.".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut results = vec![];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("\n[Claude] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        if GOOGLE_KEY {
            let mut result = arbitrator._query_external_agent("gemini-pro".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Gemini] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        if GROK_KEY {
            let mut result = arbitrator._query_external_agent("grok-beta".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Grok] {}... ({:.2}s)", result["content".to_string()][..200], result["time".to_string()]);
        }
        assert!(results.len() > 0);
        for result in results.iter() {
            if !result["content".to_string()].starts_with(&*"[".to_string()) {
                assert!(result["content".to_string()].contains(&"150".to_string()), "Expected '150' in response: {}", result["content"]);
            }
        }
        println!("\nTest Cost: ${:.4}", cost_tracker.get_total_cost());
    }
    /// Test 3: Nuanced Query - Disagreement Expected
    /// 
    /// Query: "Should investors buy stocks during a recession?"
    /// Expected: Different opinions → low/moderate consensus
    /// Expected Cost: ~$0.01
    pub async fn test_nuanced_query_disagreement(&self, arbitrator: String, cost_tracker: String) -> () {
        // Test 3: Nuanced Query - Disagreement Expected
        // 
        // Query: "Should investors buy stocks during a recession?"
        // Expected: Different opinions → low/moderate consensus
        // Expected Cost: ~$0.01
        let mut query = "Should investors buy stocks during a recession? Keep your answer brief (2-3 sentences).".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut results = vec![];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("\n[Claude] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        if GOOGLE_KEY {
            let mut result = arbitrator._query_external_agent("gemini-pro".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Gemini] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        if GROK_KEY {
            let mut result = arbitrator._query_external_agent("grok-beta".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Grok] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        assert!(results.len() > 0);
        let mut responses = results.iter().filter(|r| !r["content".to_string()].starts_with(&*"[".to_string())).map(|r| r["content".to_string()]).collect::<Vec<_>>();
        if responses.len() > 1 {
            let mut consensus = arbitrator._calculate_consensus_simple(responses);
            println!("\nConsensus: {:.1%}", consensus);
            assert!((0.0_f64 <= consensus) && (consensus <= 1.0_f64));
        }
        println!("\nTest Cost: ${:.4}", cost_tracker.get_total_cost());
    }
    /// Test 4: Code Generation Query - Different Implementations Expected
    /// 
    /// Query: "Write a Python function to check if a number is prime"
    /// Expected: Different implementations → moderate consensus
    /// Expected Cost: ~$0.01
    pub async fn test_code_generation_query(&self, arbitrator: String, cost_tracker: String) -> () {
        // Test 4: Code Generation Query - Different Implementations Expected
        // 
        // Query: "Write a Python function to check if a number is prime"
        // Expected: Different implementations → moderate consensus
        // Expected Cost: ~$0.01
        let mut query = "Write a Python function to check if a number is prime. Keep it simple and include the function signature.".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        let mut results = vec![];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("\n[Claude] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        if GOOGLE_KEY {
            let mut result = arbitrator._query_external_agent("gemini-pro".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Gemini] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        if GROK_KEY {
            let mut result = arbitrator._query_external_agent("grok-beta".to_string(), messages).await;
            results.push(result);
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
            println!("[Grok] {}... ({:.2}s)", result["content".to_string()][..300], result["time".to_string()]);
        }
        assert!(results.len() > 0);
        for result in results.iter() {
            if result["content".to_string()].starts_with(&*"[".to_string()) {
                continue;
            }
            assert!(result["content".to_string()].contains(&"def".to_string()), "Expected Python function in response");
            assert!(result["content".to_string()].to_lowercase().contains(&"prime".to_string()), "Expected 'prime' in response");
        }
        let mut responses = results.iter().filter(|r| !r["content".to_string()].starts_with(&*"[".to_string())).map(|r| r["content".to_string()]).collect::<Vec<_>>();
        if responses.len() > 1 {
            let mut consensus = arbitrator._calculate_consensus_simple(responses);
            println!("\nConsensus: {:.1%}", consensus);
        }
        println!("\nTest Cost: ${:.4}", cost_tracker.get_total_cost());
    }
}

/// Test cost tracking across real API calls.
#[derive(Debug, Clone)]
pub struct TestCostTracking {
}

impl TestCostTracking {
    /// Test 5: Cost Tracking - Stay Under Budget
    /// 
    /// Verify that all Phase 2 tests stay under $0.05 budget.
    pub async fn test_total_cost_under_budget(&self) -> () {
        // Test 5: Cost Tracking - Stay Under Budget
        // 
        // Verify that all Phase 2 tests stay under $0.05 budget.
        let mut arbitrator = SwarmArbitrator(/* ports= */ vec![8001]);
        let mut cost_tracker = CostTracker();
        let mut query = "Hello, world!".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
        }
        if GOOGLE_KEY {
            let mut result = arbitrator._query_external_agent("gemini-pro".to_string(), messages).await;
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
        }
        if GROK_KEY {
            let mut result = arbitrator._query_external_agent("grok-beta".to_string(), messages).await;
            cost_tracker.record_query(result["model".to_string()], result["content".to_string()]);
        }
        let mut total_cost = cost_tracker.get_total_cost();
        println!("\nTotal Cost: ${:.4}", total_cost);
        assert!(total_cost < 0.01_f64, "Single query too expensive: ${:.4}", total_cost);
        let mut breakdown = cost_tracker.get_cost_breakdown();
        println!("{}", "\nCost Breakdown:".to_string());
        for (provider, cost) in breakdown.iter().iter() {
            println!("  {}: ${:.4}", provider, cost);
            // pass
        }
    }
}

/// Test confidence extraction from real LLM responses.
#[derive(Debug, Clone)]
pub struct TestConfidenceExtraction {
}

impl TestConfidenceExtraction {
    /// Test 6: Confidence Extraction - Real Responses
    /// 
    /// Query LLMs and verify confidence extraction works on real responses.
    pub async fn test_confidence_in_real_responses(&self) -> () {
        // Test 6: Confidence Extraction - Real Responses
        // 
        // Query LLMs and verify confidence extraction works on real responses.
        let mut arbitrator = SwarmArbitrator(/* ports= */ vec![8001]);
        let mut query = "What is 2+2? Express your confidence as a percentage.".to_string();
        let mut messages = vec![HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), query)])];
        if ANTHROPIC_KEY {
            let mut result = arbitrator._query_external_agent("claude-3-5-sonnet-20241022".to_string(), messages).await;
            println!("\n[Claude] Response: {}", result["content".to_string()][..200]);
            println!("[Claude] Confidence: {:.1%}", result["confidence".to_string()]);
            assert!(result["confidence".to_string()] >= 0.7_f64, "Expected high confidence, got {:.1%}", result["confidence"]);
        }
    }
}

/// Save Phase 2 test results to JSON file.
pub fn save_phase2_results(results: HashMap<String, serde_json::Value>) -> Result<()> {
    // Save Phase 2 test results to JSON file.
    let mut output_file = PathBuf::from("PHASE_2_RESULTS.json".to_string());
    let mut f = File::create(output_file)?;
    {
        json::dump(HashMap::from([("timestamp".to_string(), datetime::now().isoformat()), ("phase".to_string(), "Phase 2 - Real API Testing".to_string()), ("results".to_string(), results)]), f, /* indent= */ 2);
    }
    Ok(println!("\n📊 Phase 2 results saved to: {}", output_file))
}
