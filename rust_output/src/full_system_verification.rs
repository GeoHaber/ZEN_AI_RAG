use anyhow::{Result, Context};
use std::fs::File;
use std::io::{self, Read, Write};

/// Run test.
pub fn run_test(name: String, script_path: String) -> Result<()> {
    // Run test.
    println!("\n{}", ("=".to_string() * 60));
    println!("🧪 RUNNING: {}", name);
    println!("{}", ("=".to_string() * 60));
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    // try:
    {
        let mut env = os::environ.clone();
        env["PYTHONPATH".to_string()] = std::env::current_dir().unwrap().to_str().unwrap().to_string();
        let mut result = std::process::Command::new("sh").arg("-c").arg(vec![sys::executable, script_path], /* capture_output= */ true, /* text= */ true, /* timeout= */ 120, /* env= */ env, /* shell= */ false).output().unwrap();
        let mut duration = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start);
        println!("{}", result.stdout);
        if result.stderr {
            println!("{}", "--- STDERR ---".to_string());
            println!("{}", result.stderr);
        }
        if result.returncode == 0 {
            println!("✅ PASS ({:.2}s)", duration);
            (true, duration)
        } else {
            println!("❌ FAIL (Exit Code: {})", result.returncode);
            (false, duration)
        }
    }
    // except Exception as e:
}

/// Check efficiency.
pub fn check_efficiency() -> Result<()> {
    // Check efficiency.
    println!("\n{}", ("=".to_string() * 60));
    println!("📊 EFFICIENCY AUDIT");
    println!("{}", ("=".to_string() * 60));
    // try:
    {
        let mut result = std::process::Command::new("sh").arg("-c").arg(vec!["tasklist".to_string().output().unwrap(), "/FI".to_string(), "IMAGENAME eq python.exe".to_string()], /* capture_output= */ true, /* text= */ true, /* shell= */ false);
        println!("{}", result.stdout);
        let mut count = result.stdout.iter().filter(|v| **v == "python.exe".to_string()).count();
        println!("Python Processes Detected: {}", count);
        if count > 10 {
            println!("{}", "⚠️ WARNING: High number of Python processes detected (Risk of Zombies).".to_string());
        } else {
            println!("{}", "✅ Process count is within normal limits.".to_string());
        }
    }
    // except Exception as _e:
}

/// Main.
pub fn main() -> () {
    // Main.
    let mut tests = vec![("Backend Integration".to_string(), "tests/test_async_backend::py".to_string()), ("RAG Pipeline".to_string(), "tests/test_rag_pipeline::py".to_string()), ("Voice Diagnostics (Port 8005)".to_string(), "tests/diagnose_voice_pipeline::py".to_string()), ("Swarm Endpoints".to_string(), "tests/verify_swarm_fix::py".to_string())];
    let mut results = vec![];
    println!("{}", "\n🚀 STARTING FULL SYSTEM REGRESSION TEST".to_string());
    for (name, path) in tests.iter() {
        if os::path.exists(path) {
            let (mut passed, mut duration) = run_test(name, path);
            results.push((name, passed, duration));
        } else {
            println!("⚠️ SKIPPING {}: File not found ({})", name, path);
            results.push((name, false, 0));
        }
    }
    check_efficiency();
    println!("\n{}", ("=".to_string() * 60));
    println!("📝 FINAL REPORT");
    println!("{}", ("=".to_string() * 60));
    let mut all_pass = true;
    for (name, passed, duration) in results.iter() {
        let mut status = if passed { "✅ PASS".to_string() } else { "❌ FAIL".to_string() };
        println!("{} | {:<30} | {:.2}s", status, name, duration);
        if !passed {
            let mut all_pass = false;
        }
    }
    if all_pass {
        println!("{}", "\n🎉 ALL SYSTEMS GO!".to_string());
        std::process::exit(0);
    } else {
        println!("{}", "\n⚠️ SOME TESTS FAILED".to_string());
        std::process::exit(1);
    }
}
