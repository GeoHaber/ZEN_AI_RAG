use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};

pub static _MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const MODEL_PATH: &str = "_MODELS_DIR / 'qwen2.5-0.5b-instruct-q5_k_m.gguf";

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const START_SCRIPT: &str = "ROOT_DIR / 'start_llm::py";

/// Wait for port.
pub fn wait_for_port(port: String, timeout: String) -> Result<()> {
    // Wait for port.
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    let mut url = format!("http://127.0.0.1:{}/health", port);
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) < timeout {
        // try:
        {
            let mut resp = /* reqwest::get( */&url).cloned().unwrap_or(/* timeout= */ 1);
            if resp.status_code == 200 {
                println!("[Multi] Port {} is READY (200 OK)", port);
                true
            } else if resp.status_code == 503 {
                // pass
            }
        }
        // except Exception as _e:
        std::thread::sleep(std::time::Duration::from_secs_f64(0.5_f64));
    }
    Ok(false)
}

/// Launch instance.
pub fn launch_instance(port: String, env: String) -> Result<()> {
    // Launch instance.
    let mut my_env = env.clone();
    my_env["LLM_PORT".to_string()] = port.to_string();
    let mut cmd = vec![sys::executable, START_SCRIPT.to_string(), "--model".to_string(), MODEL_PATH.to_string(), "--guard-bypass".to_string()];
    let mut proc = subprocess::Popen(cmd, /* cwd= */ ROOT_DIR, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::PIPE, /* text= */ true, /* env= */ my_env, /* stdin= */ subprocess::PIPE, /* shell= */ false);
    Ok(proc)
}

/// Test running FOUR instances of llama.cpp simultaneously.
/// Captures stdout directly to verify process output ("Direct Capture").
pub fn test_multi_process_concurrency() -> Result<()> {
    // Test running FOUR instances of llama.cpp simultaneously.
    // Captures stdout directly to verify process output ("Direct Capture").
    if !MODEL_PATH.exists() {
        pytest.skip("Test model missing".to_string());
    }
    let mut ports = vec![8005, 8006, 8007, 8008];
    let mut procs = vec![];
    println!("\n[Multi] Launching {} Parallel Instances...", ports.len());
    // try:
    {
        for port in ports.iter() {
            println!("[Multi] Launching Port {}...", port);
            let mut proc = launch_instance(port, os::environ);
            procs.push((port, proc));
        }
        for (port, proc) in procs.iter() {
            if !wait_for_port(port) {
                pytest.fail(format!("Instance on Port {} failed to start", port));
            }
            println!("[Multi] Port {} READY (PID: {})", port, proc.pid);
        }
        println!("{}", "[Multi] verify_direct_traffic (Hit all endpoints)...".to_string());
        for (port, _) in procs.iter() {
            let mut resp = /* reqwest::get( */&format!("http://127.0.0.1:{}/props", port)).cloned().unwrap_or(/* timeout= */ 5);
            assert!(resp.status_code == 200);
            println!("[Multi] Port {} response: {} bytes", port, resp.content.len());
        }
        println!("{}", "[Multi] SUCCESS: 4-Way Concurrency Achieved.".to_string());
    }
    // finally:
        println!("{}", "[Multi] Teardown...".to_string());
        for (_, proc) in procs.iter() {
            proc.terminate();
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(2));
        for (_, proc) in procs.iter() {
            // try:
            {
                proc.kill();
            }
            // except Exception as _e:
        }
}
