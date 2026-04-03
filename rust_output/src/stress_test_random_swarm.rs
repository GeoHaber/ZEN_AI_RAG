use anyhow::{Result, Context};
use crate::arbitrage::{SwarmArbitrator};
use crate::test_utils::{_default_models_dir};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub const ROOT: &str = "Path(file!()).resolve().parent.parent";

pub static MODEL_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const START_LLM_SCRIPT: &str = "Path(file!()).resolve().parent.parent / 'start_llm::py";

pub const PORTS: &str = "[8001] + list(range(8005, 8011))";

pub const REF_PORT: i64 = 8001;

pub fn get_available_models() -> () {
    MODEL_DIR.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>()
}

/// Kill any existing llama-server or start_llm processes.
pub fn kill_swarm() -> () {
    // Kill any existing llama-server or start_llm processes.
    println!("{}", "[Clean] Cleaning up existing processes...".to_string());
    std::process::Command::new("sh").arg("-c").arg(vec!["taskkill".to_string().output().unwrap(), "/F".to_string(), "/IM".to_string(), "llama-server::exe".to_string(), "/T".to_string()], /* capture_output= */ true, /* shell= */ false);
    std::thread::sleep(std::time::Duration::from_secs_f64(2));
}

/// Launch a single LLM instance on a specific port.
pub fn start_expert(model_path: String, port: String, agent_idx: String) -> Result<()> {
    // Launch a single LLM instance on a specific port.
    let mut env = os::environ.clone();
    env["LLM_PORT".to_string()] = port.to_string();
    env["LLM_THREADS".to_string()] = "2".to_string();
    let mut cmd = vec![sys::executable, START_LLM_SCRIPT.to_string(), "--guard-bypass".to_string(), "--model".to_string(), model_path.to_string()];
    let mut log_dir = PathBuf::from("logs".to_string());
    log_dir.create_dir_all();
    let mut log_file = File::create((log_dir / format!("expert_{}.log", agent_idx)))?;
    let mut process = subprocess::Popen(cmd, /* env= */ env, /* cwd= */ START_LLM_SCRIPT.parent().unwrap_or(std::path::Path::new("")).to_string(), /* stdout= */ log_file, /* stderr= */ log_file, /* creationflags= */ if os::name == "nt".to_string() { subprocess::CREATE_NO_WINDOW } else { 0 }, /* shell= */ false);
    Ok((process, log_file))
}

/// Wait until all requested ports are responding to health check.
pub async fn wait_for_swarm(ports: String) -> Result<()> {
    // Wait until all requested ports are responding to health check.
    // TODO: import httpx
    let mut client = httpx.AsyncClient();
    {
        for port in ports.iter() {
            let mut ready = false;
            for _ in 0..30.iter() {
                // try:
                {
                    let mut resp = client.get(&format!("http://127.0.0.1:{}/health", port)).cloned().unwrap_or(/* timeout= */ 2.0_f64).await;
                    if resp.status_code == 200 {
                        let mut ready = true;
                        break;
                    }
                }
                // except Exception as _e:
                asyncio.sleep(2).await;
            }
            if !ready {
                println!("[Warning] Port {} timed out during startup.", port);
                // pass
            }
        }
    }
}

/// Run tier test.
pub async fn run_tier_test(n: String) -> () {
    // Run tier test.
    println!("\n{}", ("=".to_string() * 80));
    println!("🚀 STARTING STRESS TEST TIER: N={}", n);
    println!("{}", ("=".to_string() * 80));
    let mut models = get_available_models();
    if !models {
        println!("{}", "Error: No models found in C:\\AI\\Models".to_string());
        return;
    }
    let mut selected_models = random.sample(models, n.min(models::len()));
    while selected_models.len() < n {
        selected_models.push(random.choice(models));
    }
    kill_swarm();
    let mut processes = vec![];
    let mut log_files = vec![];
    println!("[Setup] Launching {} random models...", n);
    for i in 0..n.iter() {
        let mut port = PORTS[&i];
        let mut m = selected_models[&i];
        println!("  > Agent {} [Identity]: {}", (i + 1), m.name);
        let (mut p, mut log_f) = start_expert(m, port, (i + 1));
        processes.push(p);
        log_files.push(log_f);
    }
    println!("{}", "[Setup] Waiting for experts to initialize (this can take 20s+)...".to_string());
    wait_for_swarm(PORTS[..n]).await;
    let mut arbitrator = SwarmArbitrator(/* ports= */ PORTS[..n]);
    let mut question = "If I have 3 oranges and eat 2, then buy 5 more, how many do I have? Explain the logic.".to_string();
    println!("{}", "\n[Audit] Submitting Question: ".to_string(), question);
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut full_answer = "".to_string();
    // async for
    while let Some(chunk) = arbitrator.get_cot_response(question, "You are a logical math expert.".to_string(), /* verbose= */ false).next().await {
        full_answer += chunk;
    }
    let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
    println!("\n[Metrics] Global Tier Completion: {:.2}s", total_time);
    for p in processes.iter() {
        p.terminate();
    }
    for f in log_files.iter() {
        f.close();
    }
    kill_swarm();
}

/// Main.
pub async fn main() -> Result<()> {
    // Main.
    let mut tiers = vec![1, 3, 5, 7];
    for n in tiers.iter() {
        // try:
        {
            run_tier_test(n).await;
            println!("\n[Tier {}] Completed successfully.", n);
        }
        // except Exception as _e:
        println!("{}", "\nCooldown (10s)...".to_string());
        asyncio.sleep(10).await;
    }
}
