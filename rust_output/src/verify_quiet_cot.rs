use anyhow::{Result, Context};
use crate::arbitrage::{SwarmArbitrator};
use tokio;

/// Test quiet cot logic.
pub async fn test_quiet_cot_logic() -> () {
    // Test quiet cot logic.
    println!("{}", "--- TESTING QUIET COT EVOLUTION (Phase 19) ---".to_string());
    let mut arb = SwarmArbitrator();
    arb.endpoints = vec!["http://127.0.0.1:8001/v1/chat/completions".to_string()];
    println!("\n[Test 1] Single-LLM Self-Reflection (Quiet Mode)...");
    let mut prompt = "Why is the sky blue?".to_string();
    let mut chunks = vec![];
    // async for
    while let Some(chunk) = arb.get_cot_response(prompt, "You are ZenAI.".to_string(), /* verbose= */ false).next().await {
        chunks.push(chunk);
    }
    println!("Captured {} stream chunks.", chunks.len());
    let mut full_response = chunks.join(&"".to_string());
    println!("Final Response Length: {}", full_response.len());
    if (full_response.contains(&"--- **Expert".to_string()) || full_response.contains(&"--- **Reflection".to_string())) {
        println!("{}", "❌ FAILED: Intermediate thoughts found in Quiet Mode output!".to_string());
    } else {
        println!("{}", "✅ PASSED: Intermediate thoughts kept in memory.".to_string());
    }
    if full_response.contains(&"Swarm Metrics".to_string()) {
        println!("{}", "✅ PASSED: Swarm Metrics footer present.".to_string());
    } else {
        println!("{}", "❌ FAILED: Swarm Metrics footer missing.".to_string());
    }
    println!("{}", "\n[Test 2] Verbose Mode Validation...".to_string());
    let mut v_chunks = vec![];
    // async for
    while let Some(chunk) = arb.get_cot_response(prompt, "You are ZenAI.".to_string(), /* verbose= */ true).next().await {
        v_chunks.push(chunk);
    }
    let mut v_full = v_chunks.join(&"".to_string());
    if v_full.contains(&"--- **Reflection**".to_string()) {
        println!("{}", "✅ PASSED: Intermediate thoughts visible in Verbose Mode.".to_string());
    } else {
        println!("{}", "❌ FAILED: Intermediate thoughts missing from Verbose Mode.".to_string());
    }
}
