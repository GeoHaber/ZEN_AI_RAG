use anyhow::{Result, Context};
use crate::async_backend::{AsyncZenAIBacken};
use crate::config_system::{config};
use crate::model_manager::*;
use crate::registry::{UI_IDS, MONKEY_TARGETS, UI_METADATA};
use std::collections::HashMap;
use tokio;

pub static MONKEY_PROMPTS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Check service.
pub async fn check_service(name: String, url: String, timeout: String) -> Result<()> {
    // Check service.
    // try:
    {
        let mut client = httpx.AsyncClient();
        {
            let mut resp = client.get(&url).cloned().unwrap_or(/* timeout= */ timeout).await;
            if resp.status_code == 200 {
                println!("✅ {:15} | Online ({})", name, url);
                true
            } else {
                println!("⚠️ {:15} | Warning: Status {} ({})", name, resp.status_code, url);
                false
            }
        }
    }
    // except Exception as _e:
}

/// Run monkey test.
pub async fn run_monkey_test(backend: String, iterations: String) -> Result<()> {
    // Run monkey test.
    println!("{}", ("\n".to_string() + ("🐒".to_string() * 25)));
    println!("{}", "      LIVE MONKEY TEST: CHAOS INJECTION".to_string());
    println!("{}", (("🐒".to_string() * 25) + "\n".to_string()));
    let mut success_count = 0;
    for i in 1..(iterations + 1).iter() {
        let mut prompt = random.choice(MONKEY_PROMPTS);
        println!("[{}/{}] 🐒 Monkey injecting: \"{}\"", i, iterations, prompt);
        let mut full_text = "".to_string();
        let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        // try:
        {
            // async for
            while let Some(chunk) = backend.send_message_async(prompt).next().await {
                full_text += chunk;
                if (full_text.len() % 20) == 0 {
                    println!("{}", ".".to_string());
                }
            }
            let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
            if full_text.trim().to_string() {
                println!(" ✅ Received {} chars ({:.1}s)", full_text.len(), duration);
                success_count += 1;
            } else {
                println!(" ❌ RECEIVED EMPTY RESPONSE!");
                // pass
            }
        }
        // except Exception as _e:
    }
    println!("\n🐒 Monkey Test Complete: {}/{} successful injections.", success_count, iterations);
    Ok(success_count == iterations)
}

/// Run ui chaos test.
pub async fn run_ui_chaos_test(backend: String, iterations: String) -> Result<()> {
    // Run ui chaos test.
    println!("{}", ("\n".to_string() + ("🌀".to_string() * 25)));
    println!("{}", "      UI SMART CHAOS TEST: AI-VALIDATED POKING".to_string());
    println!("{}", (("🌀".to_string() * 25) + "\n".to_string()));
    let mut success_count = 0;
    let mut client = httpx.AsyncClient();
    {
        for i in 1..(iterations + 1).iter() {
            let mut target_id = random.choice(MONKEY_TARGETS);
            let mut description = UI_METADATA.get(&target_id).cloned().unwrap_or("Unknown action".to_string());
            println!("[{}/{}] 🌀 Poking: {} ({})", i, iterations, target_id, description);
            let mut prompt = format!("UI Action: Click '{}'. Based on this action, what is the expected UI change? Answer in 1 short sentence.", description);
            println!("{}", "  🤖 AI Prediction: ".to_string());
            // async for
            while let Some(chunk) = backend.send_message_async(prompt).next().await {
                println!("{}", chunk.trim().to_string());
            }
            println!();
            // try:
            {
                let mut resp = client.post(format!("http://{}:8080/test/click/{}", HOST, target_id), /* timeout= */ 2.0_f64).await;
                if resp.status_code == 200 {
                    println!("{}", " ✅ Triggered".to_string());
                    success_count += 1;
                } else {
                    println!(" ⚠️ Failed (Status {})", resp.status_code);
                    // pass
                }
            }
            // except Exception as e:
            asyncio.sleep(random.uniform(0.5_f64, 1.5_f64)).await;
        }
    }
    println!("\n🌀 UI Chaos Test Complete: {}/{} successful pokes.", success_count, iterations);
    Ok(success_count > 0)
}

/// Uses the LLM to verify if the UI Registry makes sense according to its metadata.
pub async fn run_semantic_ui_audit(backend: String) -> Result<()> {
    // Uses the LLM to verify if the UI Registry makes sense according to its metadata.
    println!("{}", ("\n".to_string() + ("🧠".to_string() * 25)));
    println!("{}", "      AI SEMANTIC UI AUDIT".to_string());
    println!("{}", (("🧠".to_string() * 25) + "\n".to_string()));
    let mut registry_dump = serde_json::to_string(&UI_METADATA).unwrap();
    let mut prompt = format!("\n    As the ZenAI Quality Auditor, analyze the following UI Registry and its metadata descriptions.\n    Registry:\n    {}\n    \n    Determine:\n    1. Are these actions logical for a local AI assistant?\n    2. Are the descriptions clear enough for an automated monkey?\n    3. Identify any potentially 'dead' paths or missing critical controls.\n    \n    Provide a concise audit report.\n    ", registry_dump);
    println!("{}", "🚀 AI is auditing the UI Registry...".to_string());
    let mut full_response = "".to_string();
    // async for
    while let Some(chunk) = backend.send_message_async(prompt).next().await {
        full_response += chunk;
        println!("{}", chunk);
    }
    println!("{}", "\n\n✅ Audit Complete.".to_string());
    Ok(!full_response.to_lowercase().contains(&"error".to_string()))
}

/// Run diagnostics.
pub async fn run_diagnostics(monkey_mode: String) -> Result<()> {
    // Run diagnostics.
    println!("{}", ("\n".to_string() + ("=".to_string() * 50)));
    println!("{}", "      ZENAI LIVE DIAGNOSTICS & SYSTEM CHECK".to_string());
    println!("{}", (("=".to_string() * 50) + "\n".to_string()));
    let mut infra_healthy = true;
    infra_healthy &= check_service("Engine API".to_string(), format!("http://{}:{}/health", config::host, config::llm_port)).await;
    infra_healthy &= check_service("Hub API".to_string(), format!("http://{}:{}/models/available", config::host, config::mgmt_port)).await;
    infra_healthy &= check_service("UI Server".to_string(), format!("http://{}:8080", config::host)).await;
    if !infra_healthy {
        println!("{}", "\n😱 SYSTEM UNHEALTHY: Some core services are offline.".to_string());
        println!("{}", "Please ensure 'python start_llm::py' and 'python zena.py' are running.".to_string());
    }
    println!("{}", ("\n".to_string() + ("-".to_string() * 50)));
    println!("{}", "🧪 TESTING LLM GENERATION (Multi-Prompt Injection)".to_string());
    println!("{}", ("-".to_string() * 50));
    let mut backend = AsyncZenAIBackend();
    let mut test_prompts = vec![HashMap::from([("name".to_string(), "Simple Greeting".to_string()), ("prompt".to_string(), "Say only 'HELLO'".to_string())]), HashMap::from([("name".to_string(), "Internal Knowledge".to_string()), ("prompt".to_string(), "What documents are in the help system? (Tests RAG)".to_string())]), HashMap::from([("name".to_string(), "Swarm Analysis".to_string()), ("prompt".to_string(), "What are the benefits of local LLMs? (Tests Engine)".to_string())])];
    let mut all_passed = true;
    // try:
    {
        let _ctx = backend;
        {
            for test in test_prompts.iter() {
                println!("\n🚀 Testing: {}", test["name".to_string()]);
                println!("Prompt : \"{}\"", test["prompt".to_string()]);
                println!("{}", "Response: ".to_string());
                let mut full_text = "".to_string();
                let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                // async for
                while let Some(chunk) = backend.send_message_async(test["prompt".to_string()]).next().await {
                    full_text += chunk;
                    println!("{}", chunk);
                }
                let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
                println!("\n(Received {} chars in {:.2}s)", full_text.len(), duration);
                if full_text.len() > 2 {
                    println!("✅ {}: PASS", test["name".to_string()]);
                    // pass
                } else {
                    println!("❌ {}: FAIL (Empty or too short)", test["name".to_string()]);
                    let mut all_passed = false;
                }
            }
        }
    }
    // except Exception as e:
    if monkey_mode {
        all_passed &= run_monkey_test(backend, /* iterations= */ 3).await;
        all_passed &= run_ui_chaos_test(backend, /* iterations= */ 5).await;
        all_passed &= run_semantic_ui_audit(backend).await;
    }
    println!("{}", ("\n".to_string() + ("=".to_string() * 50)));
    if (infra_healthy && all_passed) {
        println!("{}", "🎉 SYSTEM READY: All live tests passed!".to_string());
    } else {
        println!("{}", "🛠️ ACTION REQUIRED: System is alive but responses are failing.".to_string());
    }
    Ok(println!("{}", (("=".to_string() * 50) + "\n".to_string())))
}
