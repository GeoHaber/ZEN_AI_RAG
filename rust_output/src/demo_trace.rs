use anyhow::{Result, Context};
use crate::arbitrage::{SwarmArbitrator};
use tokio;

/// Demo trace.
pub async fn demo_trace() -> () {
    // Demo trace.
    println!("{}", "[DEBUG] Initializing Arbitrator with Auto-Discovery...".to_string());
    let mut arb = SwarmArbitrator();
    if arb.endpoints.len() < 2 {
        println!("{}", "[!] Swarm currently Standalone. Forcing mock expansion for demonstration...".to_string());
        let mut base = if arb.endpoints { arb.endpoints[0] } else { "http://127.0.0.1:8001/v1/chat/completions".to_string() };
        arb.endpoints = (vec![base] * 5);
        arb.ports = (vec![8001] * 5);
    }
    println!("[DEBUG] Active Experts: {}", arb.endpoints.len());
    let mut query = "Why do we use Chain of Thought in LLMs?".to_string();
    let mut sys_prompt = "You are an AI Architecture Expert. Be concise.".to_string();
    println!("{}", "\n--- STARTING LIVE MULTI-EXPERT TRACE ---\n".to_string());
    // async for
    while let Some(_) = arb.get_cot_response(query, sys_prompt, /* verbose= */ false).next().await {
        // pass
    }
}
