use anyhow::{Result, Context};
use crate::test_utils::{_default_models_dir};
use std::path::PathBuf;

pub static MODEL_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub const MODEL_PATH: &str = "MODEL_DIR / 'qwen2.5-0.5b-instruct-q5_k_m.gguf";

pub static ROOT_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub const START_SCRIPT: &str = "ROOT_DIR / 'start_llm::py";

pub const BIN_DIR: &str = "ROOT_DIR / '_bin";

pub const LLAMA_EXE: &str = "llama-server::exe";

/// Return list of PIDs for llama-server::exe
pub fn get_llama_pids() -> () {
    // Return list of PIDs for llama-server::exe
    let mut pids = vec![];
    for proc in psutil.process_iter(vec!["pid".to_string(), "name".to_string()]).iter() {
        if proc.info["name".to_string()] == LLAMA_EXE {
            pids.push(proc.info["pid".to_string()]);
        }
    }
    pids
}

/// Cleanup helper
pub fn kill_all_llama() -> Result<()> {
    // Cleanup helper
    for proc in psutil.process_iter(vec!["pid".to_string(), "name".to_string()]).iter() {
        if proc.info["name".to_string()] != LLAMA_EXE {
            continue;
        }
        // try:
        {
            proc.kill();
        }
        // except Exception as _e:
    }
}

pub fn clean_env() -> () {
    kill_all_llama();
    /* yield */;
    kill_all_llama();
}

/// Helper: setup phase for test_engine_lifecycle.
pub fn _do_test_engine_lifecycle_setup() -> Result<()> {
    // Helper: setup phase for test_engine_lifecycle.
    let mut LLAMA_EXE_PATH = ((PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")) / "_bin".to_string()) / "llama-server::exe".to_string());
    if (!MODEL_PATH.exists() || !LLAMA_EXE_PATH.exists()) {
        pytest.skip(format!("Required model or LLM binary not found ({}, {})", MODEL_PATH, LLAMA_EXE_PATH));
    }
    println!("{}", "\n[Test] Starting Instance A...".to_string());
    let mut cmd = vec![sys::executable, START_SCRIPT.to_string(), "--model".to_string(), MODEL_PATH.to_string()];
    let mut proc_a = subprocess::Popen(cmd, /* cwd= */ ROOT_DIR, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::PIPE, /* stdin= */ subprocess::PIPE, /* text= */ true, /* shell= */ false);
    Ok((cmd, proc_a))
}

/// Helper: setup phase for test_engine_lifecycle.
pub fn _do_test_engine_lifecycle_init() -> Result<()> {
    // Helper: setup phase for test_engine_lifecycle.
    let (mut cmd, mut proc_a) = _do_test_engine_lifecycle_setup();
    let mut port_active = false;
    let mut pid_a = None;
    for i in 0..20.iter() {
        let mut pids = get_llama_pids();
        if pids {
            let mut pid_a = pids[0];
            // try:
            {
                let mut resp = /* reqwest::get( */&"http://127.0.0.1:8001/health".to_string()).cloned().unwrap_or(/* timeout= */ 1);
                if resp.status_code == 200 {
                    let mut port_active = true;
                    break;
                }
            }
            // except Exception as _e:
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
    }
    if !pid_a {
        let (mut out, mut err) = proc_a.communicate(/* timeout= */ 1);
        println!("STDOUT: {}", out);
        println!("STDERR: {}", err);
        pytest.fail("Instance A failed to start llama-server::exe".to_string());
    }
    println!("[Test] Instance A Running (PID: {})", pid_a);
    assert!(port_active, "API 8001 not responding");
    Ok((cmd, pid_a, proc_a))
}

/// 1. Start Engine (Instance A)
/// 2. Verify Running
/// 3. Start Engine (Instance B) -> Should kill A
/// 4. Verify A dead, B running
pub fn test_engine_lifecycle(clean_env: String) -> Result<()> {
    // 1. Start Engine (Instance A)
    // 2. Verify Running
    // 3. Start Engine (Instance B) -> Should kill A
    // 4. Verify A dead, B running
    let (mut cmd, mut pid_a, mut proc_a) = _do_test_engine_lifecycle_init();
    println!("{}", "[Test] Starting Instance B (Should kill A)...".to_string());
    let mut proc_b = subprocess::Popen(cmd, /* cwd= */ ROOT_DIR, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::PIPE, /* stdin= */ subprocess::PIPE, /* text= */ true, /* shell= */ false);
    std::thread::sleep(std::time::Duration::from_secs_f64(5));
    let mut current_pids = get_llama_pids();
    println!("[Test] Current PIDs: {}", current_pids);
    assert!(!current_pids.contains(&pid_a), "Instance A (PID {pid_a}) should have been killed!");
    assert!(current_pids.len() > 0, "Instance B should be running");
    let mut pid_b = current_pids[0];
    assert!(pid_b != pid_a, "PID should have changed");
    println!("[Test] Instance B Running (PID: {}) - Swap Successful", pid_b);
    proc_a.terminate();
    Ok(proc_b.terminate())
}
